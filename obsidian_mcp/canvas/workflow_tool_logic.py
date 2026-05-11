"""
Logic for workflow MCP tools.

Implements project management operations: status, propose, start, finish,
approve, complete, normalize, init_project. All functions return Result[str].
"""

from __future__ import annotations

from pathlib import Path

from ..config import get_vault_path
from ..result import Result
from ..utils import get_logger
from . import engine
from .models import (
    CanvasFile,
    Edge,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
)
from .workflow_logic import (
    all_deps_green,
    extract_task_id,
    extract_task_title,
    find_task_by_id,
    generate_group_prefix,
    get_next_task_id,
    get_workflow_mode,
    is_task_card,
    normalize,
    validate_transition,
)

logger = get_logger(__name__)


def _resolve_canvas_path(canvas_path: str) -> Result[str]:
    """Resolve a canvas path to an absolute path using the vault root.

    Mirrors the same helper in canvas_logic.py so that kanvas workflow
    tools write files inside the vault instead of the server's CWD.

    Absolute paths are returned as-is (for test compatibility).
    Relative paths require OBSIDIAN_VAULT_PATH to be configured.
    """
    abs_path = Path(canvas_path)

    if not abs_path.is_absolute():
        vault_path = get_vault_path()
        if vault_path is None:
            return Result.fail(
                "Vault path is not configured (OBSIDIAN_VAULT_PATH missing)."
            )
        abs_path = vault_path / canvas_path

    if abs_path.suffix != ".canvas":
        return Result.fail(f"Not a .canvas file: {canvas_path}")

    return Result.ok(str(abs_path))


def _load_project_canvas(canvas_path: str) -> Result[CanvasFile]:
    """Load a canvas and verify it's a project canvas (has kanvas metadata)."""
    resolved = _resolve_canvas_path(canvas_path)
    if not resolved.success:
        return Result.fail(resolved.error)  # type: ignore[arg-type]

    try:
        canvas = engine.load_canvas(resolved.data)  # type: ignore[arg-type]
    except FileNotFoundError:
        return Result.fail(f"Canvas file not found: {canvas_path}")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error loading canvas: {exc}")

    if canvas.kanvas is None:
        return Result.fail(
            "Not a project canvas (no 'kanvas' metadata). "
            "Use canvas_init_project to initialize, or use generic canvas tools."
        )
    return Result.ok(canvas)


def _save(canvas: CanvasFile) -> Result[str]:
    """Save and normalize."""
    try:
        engine.save_canvas(canvas)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error saving canvas: {exc}")
    normalize(canvas.path)
    return Result.ok("saved")


def _get_state_label(color: str) -> str:
    """Get human-readable label for a color."""
    labels = {
        "0": "Blocked",
        "1": "To Do",
        "2": "Doing",
        "4": "Done",
        "5": "Review",
        "6": "Proposed",
    }
    return labels.get(color, "Unknown")


def get_status(canvas_path: str) -> Result[str]:
    """Get a board overview: tasks by state, groups, anomalies."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    mode = get_workflow_mode(canvas)  # type: ignore[arg-type]

    state_counts: dict[str, list[str]] = {}
    for node in canvas.nodes:  # type: ignore[union-attr]
        if not is_task_card(node):
            continue
        label = _get_state_label(node.color)
        tid = extract_task_id(node.text) or node.id
        state_counts.setdefault(label, []).append(tid)

    groups = engine.find_nodes_by_type(canvas, "group")  # type: ignore[arg-type]

    lines = [
        f"Project Board: {canvas_path}",
        f"Mode: {mode.value}",
        f"Groups: {', '.join(g.label for g in groups)}",
        "",
    ]

    for state in ["To Do", "Doing", "Review", "Blocked", "Proposed", "Done"]:
        tasks = state_counts.get(state, [])
        if tasks:
            lines.append(f"{state} ({len(tasks)}): {', '.join(tasks)}")

    total = sum(len(v) for v in state_counts.values())
    lines.append(f"\nTotal tasks: {total}")

    return Result.ok("\n".join(lines))


def show_task(canvas_path: str, task_id: str) -> Result[str]:
    """Show details for a specific task."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    node = find_task_by_id(canvas, task_id)  # type: ignore[arg-type]
    if node is None:
        return Result.fail(f"Task '{task_id}' not found.")

    state = _get_state_label(node.color)
    title = extract_task_title(node.text) or "(no title)"
    group = engine.find_group_for_node(canvas, node)  # type: ignore[arg-type]
    group_label = group.label if group else "(none)"

    desc_lines = node.text.strip().split("\n")[1:]
    description = "\n".join(desc_lines).strip() or "(no description)"

    deps = engine.get_dependencies(canvas, node)  # type: ignore[arg-type]
    dependents = engine.get_dependents(canvas, node)  # type: ignore[arg-type]

    lines = [
        f"Task: {task_id} — {title}",
        f"State: {state}",
        f"Group: {group_label}",
        f"Description: {description}",
    ]

    if deps:
        dep_strs = [
            f"{extract_task_id(d.text) or d.id} ({_get_state_label(d.color)})"
            for d in deps
        ]
        lines.append(f"Depends on: {', '.join(dep_strs)}")

    if dependents:
        dep_strs = [
            f"{extract_task_id(d.text) or d.id} ({_get_state_label(d.color)})"
            for d in dependents
        ]
        lines.append(f"Blocks: {', '.join(dep_strs)}")

    return Result.ok("\n".join(lines))


def get_ready_tasks(canvas_path: str) -> Result[str]:
    """Get red tasks with all dependencies met."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    ready = []
    for node in canvas.nodes:  # type: ignore[union-attr]
        if not is_task_card(node):
            continue
        if node.color != TaskState.TODO.value:
            continue
        if all_deps_green(canvas, node):  # type: ignore[arg-type]
            tid = extract_task_id(node.text) or node.id
            title = extract_task_title(node.text) or ""
            ready.append(f"  {tid}: {title}")

    if not ready:
        return Result.ok("No ready tasks.")

    return Result.ok(f"Ready tasks ({len(ready)}):\n" + "\n".join(ready))


def get_blocked_tasks(canvas_path: str) -> Result[str]:
    """Get gray tasks and what blocks them."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    blocked = []
    for node in canvas.nodes:  # type: ignore[union-attr]
        if not is_task_card(node):
            continue
        if node.color != TaskState.BLOCKED.value:
            continue
        tid = extract_task_id(node.text) or node.id
        deps = engine.get_dependencies(canvas, node)  # type: ignore[arg-type]
        unmet = [
            extract_task_id(d.text) or d.id
            for d in deps
            if d.color != TaskState.DONE.value
        ]
        blocked.append(f"  {tid}: blocked by {', '.join(unmet)}")

    if not blocked:
        return Result.ok("No blocked tasks.")

    return Result.ok(f"Blocked tasks ({len(blocked)}):\n" + "\n".join(blocked))


def _transition_task(
    canvas_path: str,
    task_id: str,
    to_state: TaskState,
    check_deps: bool = False,
) -> Result[str]:
    """Generic task state transition."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    mode = get_workflow_mode(canvas)  # type: ignore[arg-type]
    node = find_task_by_id(canvas, task_id)  # type: ignore[arg-type]
    if node is None:
        return Result.fail(f"Task '{task_id}' not found.")

    try:
        from_state = TaskState(node.color)
    except ValueError:
        return Result.fail(f"Task '{task_id}' has unknown color '{node.color}'.")

    # Special case: blocked tasks can't be started — give a meaningful error
    if check_deps and from_state == TaskState.BLOCKED:
        deps = engine.get_dependencies(canvas, node)  # type: ignore[arg-type]
        unmet = [
            extract_task_id(d.text) or d.id
            for d in deps
            if d.color != TaskState.DONE.value
        ]
        return Result.fail(
            f"Cannot start '{task_id}': task is blocked by unmet dependencies: {', '.join(unmet)}"
        )

    validation = validate_transition(from_state, to_state, mode)
    if not validation.success:
        return Result.fail(validation.error)  # type: ignore[arg-type]

    if check_deps and not all_deps_green(canvas, node):  # type: ignore[arg-type]
        deps = engine.get_dependencies(canvas, node)  # type: ignore[arg-type]
        unmet = [
            extract_task_id(d.text) or d.id
            for d in deps
            if d.color != TaskState.DONE.value
        ]
        return Result.fail(
            f"Cannot start '{task_id}': blocked by unmet dependencies: {', '.join(unmet)}"
        )

    node.color = to_state.value
    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    logger.info("Task %s: %s → %s", task_id, from_state.name, to_state.name)
    return Result.ok(
        f"Task {task_id}: {_get_state_label(from_state.value)} → {_get_state_label(to_state.value)}"
    )


def start_task(canvas_path: str, task_id: str) -> Result[str]:
    """Start a task: red → orange. Validates dependencies are met."""
    return _transition_task(canvas_path, task_id, TaskState.DOING, check_deps=True)


def finish_task(canvas_path: str, task_id: str) -> Result[str]:
    """Finish a task: orange → cyan."""
    return _transition_task(canvas_path, task_id, TaskState.REVIEW)


def pause_task(canvas_path: str, task_id: str) -> Result[str]:
    """Pause a task: orange → red."""
    return _transition_task(canvas_path, task_id, TaskState.TODO)


def approve_task(canvas_path: str, task_id: str) -> Result[str]:
    """Approve a proposed task: purple → red. RELAXED mode only."""
    return _transition_task(canvas_path, task_id, TaskState.TODO)


def complete_task(canvas_path: str, task_id: str) -> Result[str]:
    """Mark a task as done: cyan → green. RELAXED mode only."""
    return _transition_task(canvas_path, task_id, TaskState.DONE)


def edit_task(canvas_path: str, task_id: str, text: str) -> Result[str]:
    """Update a task's description. Must be orange (or also cyan in RELAXED mode)."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    mode = get_workflow_mode(canvas)  # type: ignore[arg-type]
    node = find_task_by_id(canvas, task_id)  # type: ignore[arg-type]
    if node is None:
        return Result.fail(f"Task '{task_id}' not found.")

    allowed_states = {TaskState.DOING.value}
    if mode == WorkflowMode.RELAXED:
        allowed_states.add(TaskState.REVIEW.value)

    if node.color not in allowed_states:
        state = _get_state_label(node.color)
        suffix = " or Review" if mode == WorkflowMode.RELAXED else ""
        return Result.fail(
            f"Cannot edit task '{task_id}' in state '{state}'. Must be Doing{suffix}."
        )

    tid = extract_task_id(node.text)
    title = extract_task_title(node.text) or ""
    node.text = f"## {tid} {title}\n{text}"

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Task {task_id} description updated.")


def add_dependency(canvas_path: str, from_task: str, to_task: str) -> Result[str]:
    """Add a dependency between two tasks. Rejects cycles."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    from_node = find_task_by_id(canvas, from_task)  # type: ignore[arg-type]
    if from_node is None:
        return Result.fail(f"Task '{from_task}' not found.")
    to_node = find_task_by_id(canvas, to_task)  # type: ignore[arg-type]
    if to_node is None:
        return Result.fail(f"Task '{to_task}' not found.")

    if engine.has_cycle(canvas, from_node.id, to_node.id):  # type: ignore[arg-type]
        return Result.fail(
            f"Adding dependency {from_task} → {to_task} would create a cycle."
        )

    from_side, to_side = engine.pick_edge_sides(from_node, to_node)
    new_edge = Edge(
        id=engine.generate_edge_id(),
        from_node=from_node.id,
        to_node=to_node.id,
        from_side=from_side,
        to_side=to_side,
    )
    engine.add_edge(canvas, new_edge)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    return Result.ok(f"Dependency added: {from_task} blocks {to_task}")


def _resolve_group_prefix(canvas: CanvasFile, group_node: Node) -> str:
    """Find or generate a task ID prefix for a group."""
    existing_prefixes: list[str] = []
    for node in canvas.nodes:
        tid = extract_task_id(node.text)
        if tid:
            p = tid.split("-", maxsplit=1)[0]
            if p not in existing_prefixes:
                existing_prefixes.append(p)

    for node in canvas.nodes:
        if node.type != "text":
            continue
        if engine.find_group_for_node(canvas, node) != group_node:
            continue
        tid = extract_task_id(node.text)
        if tid:
            return tid.split("-", maxsplit=1)[0]

    return generate_group_prefix(group_node.label, existing_prefixes)


def _resolve_dep_nodes(canvas: CanvasFile, depends_on: list[str]) -> Result[list[Node]]:
    """Resolve a list of task IDs to Node objects, failing if any is missing."""
    dep_nodes: list[Node] = []
    for dep_ref in depends_on:
        dep_node = find_task_by_id(canvas, dep_ref)
        if dep_node is None:
            return Result.fail(f"Dependency '{dep_ref}' not found.")
        dep_nodes.append(dep_node)
    return Result.ok(dep_nodes)


def _add_edges_for_deps(
    canvas: CanvasFile, dep_nodes: list[Node], new_node: Node
) -> None:
    """Add dependency edges from dep_nodes to new_node."""
    for dep_node in dep_nodes:
        from_side, to_side = engine.pick_edge_sides(dep_node, new_node)
        edge = Edge(
            id=engine.generate_edge_id(),
            from_node=dep_node.id,
            to_node=new_node.id,
            from_side=from_side,
            to_side=to_side,
        )
        engine.add_edge(canvas, edge)


def propose_task(
    canvas_path: str,
    group: str,
    title: str,
    description: str,
    depends_on: list[str] | None = None,
) -> Result[str]:
    """Propose a new task (creates purple card). Auto-assigns ID."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    groups = engine.find_nodes_by_type(canvas, "group")  # type: ignore[arg-type]
    group_node = next((g for g in groups if g.label == group), None)
    if group_node is None:
        return Result.fail(f"Group '{group}' not found.")

    group_prefix = _resolve_group_prefix(canvas, group_node)  # type: ignore[arg-type]
    task_id = get_next_task_id(canvas, group_prefix)  # type: ignore[arg-type]

    dep_nodes: list[Node] = []
    if depends_on:
        dep_result = _resolve_dep_nodes(canvas, depends_on)  # type: ignore[arg-type]
        if not dep_result.success:
            return Result.fail(dep_result.error)  # type: ignore[arg-type]
        dep_nodes = dep_result.data  # type: ignore[assignment]

    x, y = engine.compute_node_placement(canvas, group_node, dep_nodes)  # type: ignore[arg-type]
    new_node = Node(
        id=engine.generate_node_id(),
        type="text",
        x=x,
        y=y,
        width=280,
        height=160,
        text=f"## {task_id} {title}\n{description}",
        color=TaskState.PROPOSED.value,
    )
    engine.add_node(canvas, new_node)  # type: ignore[arg-type]
    _add_edges_for_deps(canvas, dep_nodes, new_node)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    logger.info("Proposed task %s in group '%s'", task_id, group)
    return Result.ok(f"Proposed task: {task_id} — {title}")


def propose_group(canvas_path: str, label: str) -> Result[str]:
    """Propose a new group for the project canvas."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)  # type: ignore[arg-type]

    canvas = load_result.data
    existing = engine.find_nodes_by_type(canvas, "group")  # type: ignore[arg-type]
    x = 0
    if existing:
        rightmost = max(existing, key=lambda g: g.x + g.width)
        x = rightmost.x + rightmost.width + 50

    new_group = Node(
        id=engine.generate_node_id(),
        type="group",
        x=x,
        y=0,
        width=400,
        height=800,
        label=label,
    )
    engine.add_node(canvas, new_group)  # type: ignore[arg-type]

    save_result = _save(canvas)  # type: ignore[arg-type]
    if not save_result.success:
        return save_result

    logger.info("Proposed group '%s'", label)
    return Result.ok(f"Group added: {label}")


_LEGEND_TEXT = """# Legend
| Color | State |
|-------|-------|
| Purple | Proposed |
| Red | To Do |
| Orange | Doing |
| Cyan | Review |
| Green | Done |
| Gray | Blocked |"""


def _add_init_task(
    canvas: CanvasFile,
    task_def: dict,
    group_nodes: dict[str, Node],
    group_prefix_map: dict[str, str],
    title_to_node: dict[str, Node],
) -> Result[str]:
    """Add a single task definition to a canvas during init_project."""
    group_label = task_def["group"]
    if group_label not in group_nodes:
        return Result.fail(f"Group '{group_label}' not in groups list.")

    prefix = group_prefix_map[group_label]
    task_id = get_next_task_id(canvas, prefix)
    title = task_def["title"]
    desc = task_def.get("desc", "")
    group_node = group_nodes[group_label]

    dep_nodes: list[Node] = []
    for dep_title in task_def.get("depends_on", []):
        dep_node = title_to_node.get(dep_title.lower())
        if dep_node is None:
            return Result.fail(
                f"Dependency '{dep_title}' not found (must reference an earlier task title)."
            )
        dep_nodes.append(dep_node)

    x, y = engine.compute_node_placement(canvas, group_node, dep_nodes)
    new_node = Node(
        id=engine.generate_node_id(),
        type="text",
        x=x,
        y=y,
        width=280,
        height=160,
        text=f"## {task_id} {title}\n{desc}",
        color=TaskState.PROPOSED.value,
    )
    engine.add_node(canvas, new_node)
    title_to_node[title.lower()] = new_node
    _add_edges_for_deps(canvas, dep_nodes, new_node)
    return Result.ok(task_id)


def init_project(
    canvas_path: str,
    groups: list[str],
    tasks: list[dict] | None = None,
    mode: str = "strict",
) -> Result[str]:
    """Initialize a new project canvas with groups, legend, and optional tasks."""
    resolved = _resolve_canvas_path(canvas_path)
    if not resolved.success:
        return Result.fail(resolved.error)  # type: ignore[arg-type]

    resolved_path = resolved.unwrap()

    if Path(resolved_path).exists():
        return Result.fail(f"Canvas already exists: {canvas_path}")

    Path(resolved_path).parent.mkdir(parents=True, exist_ok=True)

    canvas = CanvasFile(
        path=resolved_path,
        nodes=[],
        edges=[],
        kanvas=KanvasMetadata(mode=WorkflowMode(mode)),
    )

    group_nodes: dict[str, Node] = {}
    for i, label in enumerate(groups):
        group_node = Node(
            id=engine.generate_node_id(),
            type="group",
            x=i * 450,
            y=0,
            width=400,
            height=800,
            label=label,
        )
        engine.add_node(canvas, group_node)
        group_nodes[label] = group_node

    engine.add_node(
        canvas,
        Node(
            id="legend",
            type="text",
            x=len(groups) * 450,
            y=0,
            width=220,
            height=300,
            text=_LEGEND_TEXT,
            color="0",
        ),
    )

    existing_prefixes: list[str] = []
    group_prefix_map: dict[str, str] = {}
    for label in groups:
        prefix = generate_group_prefix(label, existing_prefixes)
        group_prefix_map[label] = prefix
        existing_prefixes.append(prefix)

    title_to_node: dict[str, Node] = {}
    for task_def in tasks or []:
        result = _add_init_task(
            canvas, task_def, group_nodes, group_prefix_map, title_to_node
        )
        if not result.success:
            return Result.fail(result.error)  # type: ignore[arg-type]

    engine.save_canvas(canvas)
    logger.info(
        "Initialized project canvas at %s with %d groups", canvas_path, len(groups)
    )

    task_count = len(tasks) if tasks else 0
    return Result.ok(
        f"Project canvas created: {canvas_path}\n"
        f"Groups: {', '.join(groups)}\n"
        f"Tasks: {task_count} proposed\n"
        f"Mode: {mode}"
    )
