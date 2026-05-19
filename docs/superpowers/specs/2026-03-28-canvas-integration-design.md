# Canvas Integration Design

**Date:** 2026-03-28
**Status:** Draft
**Scope:** Add canvas management tools to obsidian-mcp-server

## Overview

Integrate Obsidian Canvas management into the existing obsidian-mcp-server as a new module. Two layers: generic canvas operations (CRUD on any `.canvas` file in the vault) and a project management workflow inspired by [Kanvas](https://github.com/XMihura/Kanvas) with color-coded task states, dependency tracking, and configurable agent permissions.

Canvas files live in the vault alongside project documentation (e.g., `Projects/my-project/Board.canvas`).

## Architecture

### Module structure

New package `obsidian_mcp/canvas/` with three layers:

```
obsidian_mcp/
  canvas/
    __init__.py
    models.py            # Dataclasses: Node, Edge, CanvasFile, TaskState, WorkflowMode
    engine.py            # Canvas I/O + pure operations (CRUD, placement, cycles)
    canvas_logic.py      # Logic for generic tools
    canvas_tools.py      # 8 generic MCP tools (any canvas)
    workflow_logic.py    # State machine, dependency tracking, normalize, validation
    workflow_tools.py    # 16 project management MCP tools (Kanvas workflow)
```

### Dependency flow

```
workflow_tools.py → workflow_logic.py → engine.py → models.py
canvas_tools.py  → canvas_logic.py   → engine.py → models.py
```

### Registration

Two functions added to `server.py`:
- `register_canvas_tools(mcp)` — generic tools
- `register_workflow_tools(mcp)` — project management tools

Follows the existing pattern (e.g., `navigation.py` registers tools, `navigation_logic.py` implements).

## Models

```python
@dataclass
class Node:
    id: str
    type: str            # "text" | "group" | "file" | "link"
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    label: str = ""      # for groups
    color: str = ""      # "0"-"6" or empty
    file: str = ""       # for file nodes
    url: str = ""        # for link nodes

@dataclass
class Edge:
    id: str
    from_node: str
    to_node: str
    from_side: str = "bottom"
    to_side: str = "top"
    label: str = ""

@dataclass
class KanvasMetadata:
    mode: WorkflowMode = WorkflowMode.STRICT
    version: str = "1.0"

@dataclass
class CanvasFile:
    path: str
    nodes: list[Node]
    edges: list[Edge]
    kanvas: KanvasMetadata | None = None  # present only in project canvases

class TaskState(str, Enum):
    BLOCKED  = "0"   # gray
    TODO     = "1"   # red
    DOING    = "2"   # orange
    DONE     = "4"   # green
    REVIEW   = "5"   # cyan
    PROPOSED = "6"   # purple

class WorkflowMode(str, Enum):
    STRICT  = "strict"
    RELAXED = "relaxed"
```

### WorkflowMode behavior

| Action | STRICT | RELAXED |
|--------|--------|---------|
| Propose task (→ purple) | Yes | Yes |
| Start task (red → orange) | Yes | Yes |
| Finish task (orange → cyan) | Yes | Yes |
| Pause task (orange → red) | Yes | Yes |
| Approve task (purple → red) | No | Yes |
| Complete task (cyan → green) | No | Yes |
| Edit task description | Orange only | Orange + cyan |
| Remove cards | No | No |

### Workflow mode storage

Stored as a custom field in the canvas JSON. Obsidian ignores unknown fields:

```json
{
  "nodes": [...],
  "edges": [...],
  "kanvas": {
    "mode": "strict",
    "version": "1.0"
  }
}
```

## Engine — pure operations

`engine.py` provides canvas I/O and operations with no workflow opinion.

### I/O
- `load_canvas(path: str) -> CanvasFile`
- `save_canvas(canvas: CanvasFile) -> None`

### Queries
- `find_node(canvas, node_id) -> Node | None`
- `find_nodes_by_type(canvas, type) -> list[Node]`
- `find_group_for_node(canvas, node) -> Node | None`
- `get_dependencies(canvas, node) -> list[Node]` — nodes blocking this one (inbound edges)
- `get_dependents(canvas, node) -> list[Node]` — nodes this one blocks (outbound edges)
- `has_cycle(canvas, from_id, to_id) -> bool`

### Mutations
- `add_node(canvas, node) -> Node`
- `update_node(canvas, node_id, **changes) -> Node`
- `remove_node(canvas, node_id) -> None` — also removes connected edges
- `add_edge(canvas, edge) -> Edge`
- `remove_edge(canvas, edge_id) -> None`
- `add_node_to_group(canvas, node, group) -> None`

### Placement
- `compute_node_placement(canvas, group, depends_on) -> tuple[int, int]`
- `pick_edge_sides(from_node, to_node) -> tuple[str, str]`

All functions are pure: receive `CanvasFile`, mutate in-place, caller decides when to save.

## Generic canvas tools (8 tools)

Tools for reading/writing any `.canvas` file. No workflow assumptions.

| Tool | Description |
|------|-------------|
| `canvas.read(canvas_path)` | Read canvas summary: nodes, edges, groups (human-readable, not raw JSON) |
| `canvas.list(folder="")` | List all `.canvas` files in the vault or a folder |
| `canvas.add_card(canvas_path, text, group="", color="", width=280, height=160)` | Add a text card, optionally inside a group |
| `canvas.add_group(canvas_path, label)` | Create a group/area |
| `canvas.add_edge(canvas_path, from_id, to_id, label="")` | Connect two nodes with an arrow |
| `canvas.update_card(canvas_path, node_id, text="", color="")` | Update text and/or color of a card |
| `canvas.remove_card(canvas_path, node_id)` | Delete a card and its edges |
| `canvas.remove_edge(canvas_path, edge_id)` | Delete a connection |

## Workflow tools (16 tools)

Project management tools implementing the Kanvas workflow. All operate with task IDs (`DV-01`, `RS-03`...).

### Bootstrap

| Tool | Description |
|------|-------------|
| `canvas_init_project(canvas_path, groups, tasks=[], mode="strict")` | Create a project canvas with legend, groups, and optional initial tasks (purple). Sets workflow mode. |

### Read

| Tool | Description |
|------|-------------|
| `canvas_status(canvas_path)` | Board overview: tasks by state, groups, anomalies |
| `canvas_show_task(canvas_path, task_id)` | Task detail: description, state, dependencies, dependents |
| `canvas_ready_tasks(canvas_path)` | Red tasks with all dependencies met |
| `canvas_blocked_tasks(canvas_path)` | Gray tasks and what blocks them |

### Lifecycle

| Tool | Description |
|------|-------------|
| `canvas_propose_task(canvas_path, group, title, description, depends_on=[])` | Create purple task. Auto-assigns ID. |
| `canvas_propose_group(canvas_path, label)` | Create a new project group |
| `canvas_start_task(canvas_path, task_id)` | Red → Orange. Validates all deps are green. |
| `canvas_finish_task(canvas_path, task_id)` | Orange → Cyan. |
| `canvas_pause_task(canvas_path, task_id)` | Orange → Red. |
| `canvas_approve_task(canvas_path, task_id)` | Purple → Red. RELAXED mode only. |
| `canvas_complete_task(canvas_path, task_id)` | Cyan → Green. RELAXED mode only. |

### Edit

| Tool | Description |
|------|-------------|
| `canvas_edit_task(canvas_path, task_id, text)` | Update description. Orange only (orange+cyan in RELAXED). |
| `canvas_add_dependency(canvas_path, from_task, to_task)` | Add dependency edge with cycle detection. |

### Maintenance

| Tool | Description |
|------|-------------|
| `canvas_normalize(canvas_path)` | Assign IDs to untagged cards, auto-manage blocked states. |

## Normalize behavior

Runs implicitly on every workflow write operation. Also callable explicitly.

### What it does
1. **Cards without task ID** — assigns next available `XX-NN` based on containing group
2. **Blocked states** — red card with unmet deps → gray; gray card with all deps green → red
3. **Orphan cards** — cards outside any group get prefix `G` (general)
4. **Duplicate IDs** — renumbers if collision detected

### What it does NOT do
- Delete cards
- Change titles or descriptions
- Move cards visually (respects manual layout)
- Touch cards without task ID pattern (legends, free-form notes, diagrams)

## Bootstrap flow

When creating a new project canvas:

1. **Agent interviews user** — 3-5 questions: what is the project, main areas of work, immediate priorities, existing code/docs to review
2. **Agent calls `canvas_init_project`** — creates canvas with legend, groups, tasks as purple cards, dependency edges, and `kanvas` metadata field
3. **User reviews in Obsidian** — approves cards (purple → red), deletes unwanted ones, rearranges, adds their own
4. **Next session** — agent runs `canvas_normalize` to pick up manual changes, then `canvas_ready_tasks` to start working

## Task ID format

Same convention as Kanvas:
- Pattern: `## XX-NN Title` in card text (regex: `^##\s+([A-Z]{1,3})-(\d{2})\s+(.*)$`)
- Prefix derived from group label: 1 letter if unambiguous, 2-3 if needed, initials for multi-word
- Number: 2-digit zero-padded (`01`-`99`)
- Cards outside groups: prefix `G`

## Logging

Uses the existing logging system (`obsidian_mcp/utils/logging.py`):
- Every canvas mutation: what changed, before/after state
- Validation errors: invalid transitions, blocked attempts
- Normalize actions: which cards recolored and why

## Out of scope

- Migrating existing MCP tools to English (separate project)
- CLAUDE.md for the repo
- Canvas Watcher plugin for real-time Obsidian linting
- Canvas files outside the vault
- Batch import from JSON on stdin (can be added later as enhancement)
