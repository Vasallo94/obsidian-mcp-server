"""
Workflow logic for the Kanvas project management system.

Implements the state machine, task ID generation, normalize,
and transition validation. This layer knows about workflow rules
but does not know about MCP tools.
"""

from __future__ import annotations

from typing import Optional

from ..result import Result
from ..utils import get_logger
from . import engine
from .models import (
    TASK_ID_RE,
    CanvasFile,
    Node,
    TaskState,
    WorkflowMode,
)

logger = get_logger(__name__)

# Valid state transitions: (from_state, to_state) → required modes
_TRANSITIONS: dict[tuple[TaskState, TaskState], set[WorkflowMode]] = {
    (TaskState.TODO, TaskState.DOING): {WorkflowMode.STRICT, WorkflowMode.RELAXED},
    (TaskState.DOING, TaskState.REVIEW): {WorkflowMode.STRICT, WorkflowMode.RELAXED},
    (TaskState.DOING, TaskState.TODO): {WorkflowMode.STRICT, WorkflowMode.RELAXED},
    (TaskState.PROPOSED, TaskState.TODO): {WorkflowMode.RELAXED},
    (TaskState.REVIEW, TaskState.DONE): {WorkflowMode.RELAXED},
}

# IDs that are never treated as task cards
_NON_TASK_IDS = {"canvas-errors", "canvas-warnings", "legend"}


def extract_task_id(text: str) -> Optional[str]:
    """Extract task ID ('XX-NN') from card text. Returns None if not a task."""
    match = TASK_ID_RE.search(text)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None


def extract_task_title(text: str) -> Optional[str]:
    """Extract task title from card text (after '## XX-NN ')."""
    match = TASK_ID_RE.search(text)
    if match:
        return match.group(3).strip()
    return None


def is_task_card(node: Node) -> bool:
    """Check if a node is a task card (text node with task ID pattern)."""
    if node.type != "text":
        return False
    if node.id in _NON_TASK_IDS:
        return False
    return extract_task_id(node.text) is not None


def _has_task_like_text(node: Node) -> bool:
    """Check if a text node has content that should get a task ID."""
    if node.type != "text":
        return False
    if node.id in _NON_TASK_IDS:
        return False
    if not node.text.strip():
        return False
    if extract_task_id(node.text) is not None:
        return False
    if node.color in ("", "0"):
        first_line = node.text.strip().split("\n")[0]
        if first_line.startswith("# "):
            return False
    return True


def generate_group_prefix(label: str, existing_prefixes: list[str]) -> str:
    """Generate a 1-3 letter prefix from a group label."""
    words = label.strip().split()
    if len(words) > 1:
        prefix = "".join(w[0].upper() for w in words)[:3]
        if prefix not in existing_prefixes:
            return prefix

    word = label.strip().upper()

    # Try single-letter first
    if word[:1] not in existing_prefixes:
        return word[:1]

    # Try consonant-based abbreviation (first consonant + next consonant)
    consonants = [c for c in word if c not in "AEIOU"]
    if len(consonants) >= 2:
        prefix = consonants[0] + consonants[1]
        if prefix not in existing_prefixes:
            return prefix

    # Fall back to sequential length expansion
    for length in range(2, min(4, len(word) + 1)):
        prefix = word[:length]
        if prefix not in existing_prefixes:
            return prefix

    return word[:3]


def get_next_task_id(canvas: CanvasFile, prefix: str) -> str:
    """Get the next available task ID for a given prefix."""
    existing_numbers: list[int] = []
    for node in canvas.nodes:
        task_id = extract_task_id(node.text)
        if task_id and task_id.startswith(prefix + "-"):
            num_str = task_id.split("-", maxsplit=1)[1]
            existing_numbers.append(int(num_str))

    next_num = max(existing_numbers, default=0) + 1
    return f"{prefix}-{next_num:02d}"


def find_task_by_id(canvas: CanvasFile, task_id: str) -> Optional[Node]:
    """Find a task card by its task ID (e.g., 'DV-01'). Case-insensitive."""
    task_id_upper = task_id.upper()
    for node in canvas.nodes:
        extracted = extract_task_id(node.text)
        if extracted and extracted.upper() == task_id_upper:
            return node
    return None


def all_deps_green(canvas: CanvasFile, node: Node) -> bool:
    """Check if all dependencies of a node are in DONE (green) state."""
    deps = engine.get_dependencies(canvas, node)
    return all(d.color == TaskState.DONE.value for d in deps)


def get_workflow_mode(canvas: CanvasFile) -> WorkflowMode:
    """Get the workflow mode from canvas metadata. Defaults to STRICT."""
    if canvas.kanvas is not None:
        return canvas.kanvas.mode
    return WorkflowMode.STRICT


def validate_transition(
    from_state: TaskState,
    to_state: TaskState,
    mode: WorkflowMode,
) -> Result[str]:
    """Validate a workflow state transition."""
    key = (from_state, to_state)
    allowed_modes = _TRANSITIONS.get(key)

    if allowed_modes is None:
        return Result.fail(
            f"Invalid transition: {from_state.name} → {to_state.name}. "
            f"No such transition exists."
        )

    if mode not in allowed_modes:
        return Result.fail(
            f"Transition {from_state.name} → {to_state.name} requires "
            f"RELAXED mode (current: {mode.value})."
        )

    return Result.ok(f"{from_state.name} → {to_state.name}")


def _collect_existing_prefixes(canvas: CanvasFile) -> list[str]:
    """Collect all task ID prefixes already in use across the canvas."""
    prefixes: list[str] = []
    for node in canvas.nodes:
        tid = extract_task_id(node.text)
        if tid:
            prefix = tid.split("-", maxsplit=1)[0]
            if prefix not in prefixes:
                prefixes.append(prefix)
    return prefixes


def _build_group_prefixes(
    canvas: CanvasFile, existing_prefixes: list[str]
) -> dict[str, str]:
    """Map group IDs to their task ID prefixes."""
    groups = engine.find_nodes_by_type(canvas, "group")
    group_prefixes: dict[str, str] = {}
    for group in groups:
        group_nodes = [
            n
            for n in canvas.nodes
            if n.type == "text" and engine.find_group_for_node(canvas, n) == group
        ]
        existing_group_prefix = None
        for gn in group_nodes:
            tid = extract_task_id(gn.text)
            if tid:
                existing_group_prefix = tid.split("-", maxsplit=1)[0]
                break
        if existing_group_prefix:
            group_prefixes[group.id] = existing_group_prefix
        else:
            prefix = generate_group_prefix(group.label, existing_prefixes)
            group_prefixes[group.id] = prefix
            existing_prefixes.append(prefix)
    return group_prefixes


def _assign_task_ids(
    canvas: CanvasFile,
    group_prefixes: dict[str, str],
    existing_prefixes: list[str],
) -> list[str]:
    """Assign task IDs to cards that don't have one yet. Returns change messages."""
    changes: list[str] = []
    for node in canvas.nodes:
        if not _has_task_like_text(node):
            continue
        group = engine.find_group_for_node(canvas, node)
        if group and group.id in group_prefixes:
            prefix = group_prefixes[group.id]
        else:
            prefix = "G"
            if "G" not in existing_prefixes:
                existing_prefixes.append("G")
        task_id = get_next_task_id(canvas, prefix)
        lines = node.text.strip().split("\n")
        first_line = lines[0]
        rest = "\n".join(lines[1:])
        node.text = f"## {task_id} {first_line}"
        if rest:
            node.text += f"\n{rest}"
        changes.append(f"Assigned {task_id} to card [{node.id}]")
        logger.info("Assigned task ID %s to card [%s]", task_id, node.id)
    return changes


def _update_blocked_states(canvas: CanvasFile) -> list[str]:
    """Update blocked/unblocked states based on dependency colors. Returns change messages."""
    changes: list[str] = []
    for node in canvas.nodes:
        if not is_task_card(node):
            continue
        deps = engine.get_dependencies(canvas, node)
        if not deps:
            continue
        deps_met = all_deps_green(canvas, node)
        tid = extract_task_id(node.text)
        if node.color == TaskState.TODO.value and not deps_met:
            node.color = TaskState.BLOCKED.value
            changes.append(f"{tid}: red → gray (unmet dependencies)")
            logger.info("Blocked task %s: unmet dependencies", tid)
        elif node.color == TaskState.BLOCKED.value and deps_met:
            node.color = TaskState.TODO.value
            changes.append(f"{tid}: gray → red (dependencies met)")
            logger.info("Unblocked task %s: all dependencies met", tid)
    return changes


def normalize(canvas_path: str) -> Result[str]:
    """Normalize a project canvas: assign task IDs, manage blocked states."""
    try:
        canvas = engine.load_canvas(canvas_path)
    except FileNotFoundError:
        return Result.fail(f"Canvas file not found: {canvas_path}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error loading canvas: {exc}")

    existing_prefixes = _collect_existing_prefixes(canvas)
    group_prefixes = _build_group_prefixes(canvas, existing_prefixes)
    changes = _assign_task_ids(canvas, group_prefixes, existing_prefixes)
    changes += _update_blocked_states(canvas)

    engine.save_canvas(canvas)

    if not changes:
        return Result.ok("Canvas is already normalized. No changes needed.")

    summary = f"Normalized canvas ({len(changes)} changes):\n" + "\n".join(
        f"  - {c}" for c in changes
    )
    return Result.ok(summary)
