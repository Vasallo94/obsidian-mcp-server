# Canvas Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add canvas management tools (generic CRUD + Kanvas-inspired project workflow) to the obsidian-mcp-server.

**Architecture:** New `obsidian_mcp/canvas/` package with three layers: models (dataclasses/enums), engine (pure I/O and operations on canvas JSON), and tools (MCP tool registration split into generic and workflow). Follows the existing two-file pattern (tools + logic separation) and returns `Result[str]` from all logic functions.

**Tech Stack:** Python 3.11+, FastMCP, Pydantic, pytest. Zero new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-28-canvas-integration-design.md`

---

## File Map

```
obsidian_mcp/canvas/
  __init__.py              # Public exports
  models.py                # Node, Edge, CanvasFile, KanvasMetadata, TaskState, WorkflowMode
  engine.py                # Canvas I/O, queries, mutations, placement
  canvas_logic.py          # Logic for generic canvas tools
  canvas_tools.py          # 8 generic MCP tools
  workflow_logic.py         # State machine, normalize, task ID generation
  workflow_tool_logic.py    # Logic for workflow tools (status, propose, lifecycle, init)
  workflow_tools.py         # 16 workflow MCP tools (registration layer)

tests/canvas/
  __init__.py
  conftest.py              # Shared fixtures (tmp canvas files, sample canvases)
  test_models.py           # Model serialization tests
  test_engine.py           # Engine unit tests
  test_canvas_logic.py     # Generic tool logic tests
  test_workflow_logic.py   # Workflow logic tests
  test_workflow_tools.py   # Workflow tool logic integration tests
  test_integration.py      # End-to-end workflow tests

Modified:
  obsidian_mcp/tools/__init__.py   # Add canvas exports
  obsidian_mcp/server.py           # Register canvas + workflow tools
```

---

### Task 1: Models

**Files:**
- Create: `obsidian_mcp/canvas/__init__.py`
- Create: `obsidian_mcp/canvas/models.py`
- Create: `tests/canvas/__init__.py`
- Create: `tests/canvas/test_models.py`

- [ ] **Step 1: Create package skeleton**

```bash
mkdir -p obsidian_mcp/canvas tests/canvas
touch obsidian_mcp/canvas/__init__.py tests/canvas/__init__.py
```

- [ ] **Step 2: Write model tests**

Create `tests/canvas/test_models.py`:

```python
"""Tests for canvas data models."""

import json
import pytest

from obsidian_mcp.canvas.models import (
    CanvasFile,
    Edge,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
)


class TestNode:
    """Tests for Node dataclass."""

    def test_create_text_node(self):
        node = Node(
            id="abc123",
            type="text",
            x=100,
            y=200,
            width=280,
            height=160,
            text="## DV-01 Build feature\nDescription here",
            color="1",
        )
        assert node.id == "abc123"
        assert node.type == "text"
        assert node.color == "1"
        assert node.text == "## DV-01 Build feature\nDescription here"

    def test_create_group_node(self):
        node = Node(
            id="grp1",
            type="group",
            x=0,
            y=0,
            width=400,
            height=800,
            label="Development",
        )
        assert node.type == "group"
        assert node.label == "Development"

    def test_node_defaults(self):
        node = Node(id="x", type="text", x=0, y=0, width=100, height=100)
        assert node.text == ""
        assert node.label == ""
        assert node.color == ""
        assert node.file == ""
        assert node.url == ""

    def test_node_to_dict(self):
        node = Node(id="a", type="text", x=10, y=20, width=280, height=160, text="hi")
        d = node.to_dict()
        assert d["id"] == "a"
        assert d["type"] == "text"
        assert d["text"] == "hi"
        assert "label" not in d  # empty defaults excluded

    def test_node_from_dict(self):
        data = {"id": "b", "type": "text", "x": 0, "y": 0, "width": 280, "height": 160, "text": "hello", "color": "2"}
        node = Node.from_dict(data)
        assert node.id == "b"
        assert node.color == "2"
        assert node.text == "hello"

    def test_node_from_dict_missing_optional(self):
        data = {"id": "c", "type": "group", "x": 0, "y": 0, "width": 400, "height": 600, "label": "Testing"}
        node = Node.from_dict(data)
        assert node.label == "Testing"
        assert node.text == ""


class TestEdge:
    """Tests for Edge dataclass."""

    def test_create_edge(self):
        edge = Edge(id="e1", from_node="a", to_node="b")
        assert edge.from_side == "bottom"
        assert edge.to_side == "top"

    def test_edge_to_dict(self):
        edge = Edge(id="e1", from_node="a", to_node="b", from_side="right", to_side="left")
        d = edge.to_dict()
        assert d["fromNode"] == "a"
        assert d["toNode"] == "b"
        assert d["fromSide"] == "right"

    def test_edge_from_dict(self):
        data = {"id": "e2", "fromNode": "x", "toNode": "y", "fromSide": "bottom", "toSide": "top"}
        edge = Edge.from_dict(data)
        assert edge.from_node == "x"
        assert edge.to_node == "y"


class TestCanvasFile:
    """Tests for CanvasFile dataclass."""

    def test_create_empty_canvas(self):
        canvas = CanvasFile(path="/tmp/test.canvas", nodes=[], edges=[])
        assert canvas.kanvas is None

    def test_canvas_to_dict_without_kanvas(self):
        canvas = CanvasFile(path="/tmp/test.canvas", nodes=[], edges=[])
        d = canvas.to_dict()
        assert d == {"nodes": [], "edges": []}
        assert "kanvas" not in d

    def test_canvas_to_dict_with_kanvas(self):
        meta = KanvasMetadata(mode=WorkflowMode.STRICT)
        canvas = CanvasFile(path="/tmp/test.canvas", nodes=[], edges=[], kanvas=meta)
        d = canvas.to_dict()
        assert d["kanvas"] == {"mode": "strict", "version": "1.0"}

    def test_canvas_from_dict(self):
        data = {
            "nodes": [
                {"id": "n1", "type": "text", "x": 0, "y": 0, "width": 280, "height": 160, "text": "hello"}
            ],
            "edges": [
                {"id": "e1", "fromNode": "n1", "toNode": "n2", "fromSide": "bottom", "toSide": "top"}
            ],
        }
        canvas = CanvasFile.from_dict("/tmp/test.canvas", data)
        assert len(canvas.nodes) == 1
        assert len(canvas.edges) == 1
        assert canvas.nodes[0].text == "hello"

    def test_canvas_from_dict_with_kanvas(self):
        data = {
            "nodes": [],
            "edges": [],
            "kanvas": {"mode": "relaxed", "version": "1.0"},
        }
        canvas = CanvasFile.from_dict("/tmp/t.canvas", data)
        assert canvas.kanvas is not None
        assert canvas.kanvas.mode == WorkflowMode.RELAXED


class TestTaskState:
    """Tests for TaskState enum."""

    def test_values(self):
        assert TaskState.BLOCKED == "0"
        assert TaskState.TODO == "1"
        assert TaskState.DOING == "2"
        assert TaskState.DONE == "4"
        assert TaskState.REVIEW == "5"
        assert TaskState.PROPOSED == "6"

    def test_from_color_string(self):
        assert TaskState("1") == TaskState.TODO
        assert TaskState("6") == TaskState.PROPOSED


class TestWorkflowMode:
    """Tests for WorkflowMode enum."""

    def test_values(self):
        assert WorkflowMode.STRICT == "strict"
        assert WorkflowMode.RELAXED == "relaxed"
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
python -m pytest tests/canvas/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'obsidian_mcp.canvas'`

- [ ] **Step 4: Implement models**

Create `obsidian_mcp/canvas/models.py`:

```python
"""
Data models for Obsidian Canvas files.

Defines the core structures used to represent canvas elements (nodes, edges),
canvas files, and the Kanvas workflow metadata (task states, workflow modes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Optional


class TaskState(str, Enum):
    """Color-coded task states for the Kanvas workflow."""

    BLOCKED = "0"   # gray
    TODO = "1"      # red
    DOING = "2"     # orange
    DONE = "4"      # green
    REVIEW = "5"    # cyan
    PROPOSED = "6"  # purple


class WorkflowMode(str, Enum):
    """Agent permission level for workflow operations."""

    STRICT = "strict"    # agent can't approve/complete
    RELAXED = "relaxed"  # agent can approve and complete


# Regex to extract task ID from card text: "## XX-NN Title"
TASK_ID_RE = re.compile(r"^##\s+([A-Z]{1,3})-(\d{2})\s+(.*)$", re.MULTILINE)


@dataclass
class Node:
    """A node in an Obsidian Canvas file (card, group, file embed, or link)."""

    id: str
    type: str  # "text" | "group" | "file" | "link"
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    label: str = ""
    color: str = ""
    file: str = ""
    url: str = ""

    # Fields that are excluded from serialization when empty
    _OPTIONAL_FIELDS = {"text", "label", "color", "file", "url"}

    def to_dict(self) -> dict:
        """Serialize to Obsidian Canvas JSON format."""
        d: dict = {}
        for f in fields(self):
            val = getattr(self, f.name)
            if f.name in self._OPTIONAL_FIELDS and val == "":
                continue
            d[f.name] = val
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Node:
        """Deserialize from Obsidian Canvas JSON format."""
        return cls(
            id=data["id"],
            type=data["type"],
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 280),
            height=data.get("height", 160),
            text=data.get("text", ""),
            label=data.get("label", ""),
            color=data.get("color", ""),
            file=data.get("file", ""),
            url=data.get("url", ""),
        )


@dataclass
class Edge:
    """A directional connection between two nodes. fromNode blocks toNode."""

    id: str
    from_node: str
    to_node: str
    from_side: str = "bottom"
    to_side: str = "top"
    label: str = ""

    _OPTIONAL_FIELDS = {"label"}

    def to_dict(self) -> dict:
        """Serialize to Obsidian Canvas JSON format (camelCase keys)."""
        d = {
            "id": self.id,
            "fromNode": self.from_node,
            "toNode": self.to_node,
            "fromSide": self.from_side,
            "toSide": self.to_side,
        }
        if self.label:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, data: dict) -> Edge:
        """Deserialize from Obsidian Canvas JSON format (camelCase keys)."""
        return cls(
            id=data["id"],
            from_node=data["fromNode"],
            to_node=data["toNode"],
            from_side=data.get("fromSide", "bottom"),
            to_side=data.get("toSide", "top"),
            label=data.get("label", ""),
        )


@dataclass
class KanvasMetadata:
    """Workflow metadata stored in the canvas JSON under the 'kanvas' key."""

    mode: WorkflowMode = WorkflowMode.STRICT
    version: str = "1.0"

    def to_dict(self) -> dict:
        return {"mode": self.mode.value, "version": self.version}

    @classmethod
    def from_dict(cls, data: dict) -> KanvasMetadata:
        return cls(
            mode=WorkflowMode(data.get("mode", "strict")),
            version=data.get("version", "1.0"),
        )


@dataclass
class CanvasFile:
    """An Obsidian .canvas file with optional Kanvas workflow metadata."""

    path: str
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    kanvas: Optional[KanvasMetadata] = None

    def to_dict(self) -> dict:
        """Serialize to the JSON structure Obsidian expects."""
        d: dict = {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
        if self.kanvas is not None:
            d["kanvas"] = self.kanvas.to_dict()
        return d

    @classmethod
    def from_dict(cls, path: str, data: dict) -> CanvasFile:
        """Deserialize from parsed canvas JSON."""
        nodes = [Node.from_dict(n) for n in data.get("nodes", [])]
        edges = [Edge.from_dict(e) for e in data.get("edges", [])]
        kanvas = None
        if "kanvas" in data:
            kanvas = KanvasMetadata.from_dict(data["kanvas"])
        return cls(path=path, nodes=nodes, edges=edges, kanvas=kanvas)
```

- [ ] **Step 5: Update `__init__.py`**

Create `obsidian_mcp/canvas/__init__.py`:

```python
"""
Canvas management module for the Obsidian MCP server.

Provides generic canvas CRUD operations and a Kanvas-inspired
project management workflow with color-coded task states.
"""

from .models import (
    CanvasFile,
    Edge,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
    TASK_ID_RE,
)

__all__ = [
    "CanvasFile",
    "Edge",
    "KanvasMetadata",
    "Node",
    "TaskState",
    "WorkflowMode",
    "TASK_ID_RE",
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/canvas/test_models.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add obsidian_mcp/canvas/__init__.py obsidian_mcp/canvas/models.py tests/canvas/__init__.py tests/canvas/test_models.py
git commit -m "feat(canvas): add data models for canvas nodes, edges, and workflow"
```

---

### Task 2: Engine — I/O and queries

**Files:**
- Create: `obsidian_mcp/canvas/engine.py`
- Create: `tests/canvas/conftest.py`
- Create: `tests/canvas/test_engine.py`

- [ ] **Step 1: Create test fixtures**

Create `tests/canvas/conftest.py`:

```python
"""Shared fixtures for canvas tests."""

import json
import pytest
from pathlib import Path

from obsidian_mcp.canvas.models import CanvasFile, Edge, KanvasMetadata, Node, WorkflowMode


SAMPLE_CANVAS_DATA = {
    "nodes": [
        {"id": "grp1", "type": "group", "x": 0, "y": 0, "width": 400, "height": 800, "label": "Development"},
        {"id": "grp2", "type": "group", "x": 450, "y": 0, "width": 400, "height": 800, "label": "Testing"},
        {"id": "t1", "type": "text", "x": 20, "y": 50, "width": 280, "height": 160, "text": "## DV-01 Build API\nCreate REST endpoints", "color": "4"},
        {"id": "t2", "type": "text", "x": 20, "y": 250, "width": 280, "height": 160, "text": "## DV-02 Add auth\nAdd authentication", "color": "1"},
        {"id": "t3", "type": "text", "x": 470, "y": 50, "width": 280, "height": 160, "text": "## TS-01 Write tests\nUnit tests for API", "color": "0"},
        {"id": "t4", "type": "text", "x": 20, "y": 450, "width": 280, "height": 160, "text": "## DV-03 Refactor\nClean up code", "color": "6"},
        {"id": "legend", "type": "text", "x": 900, "y": 0, "width": 200, "height": 300, "text": "# Legend\nColors mean things", "color": "0"},
    ],
    "edges": [
        {"id": "e1", "fromNode": "t1", "toNode": "t2", "fromSide": "bottom", "toSide": "top"},
        {"id": "e2", "fromNode": "t1", "toNode": "t3", "fromSide": "right", "toSide": "left"},
        {"id": "e3", "fromNode": "t2", "toNode": "t3", "fromSide": "right", "toSide": "left"},
    ],
    "kanvas": {"mode": "strict", "version": "1.0"},
}


@pytest.fixture
def tmp_canvas(tmp_path) -> Path:
    """Create a temporary canvas file with sample data."""
    canvas_path = tmp_path / "Project.canvas"
    canvas_path.write_text(json.dumps(SAMPLE_CANVAS_DATA), encoding="utf-8")
    return canvas_path


@pytest.fixture
def empty_canvas(tmp_path) -> Path:
    """Create an empty canvas file."""
    canvas_path = tmp_path / "Empty.canvas"
    canvas_path.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")
    return canvas_path


@pytest.fixture
def sample_canvas_file() -> CanvasFile:
    """Return an in-memory CanvasFile from sample data."""
    return CanvasFile.from_dict("/tmp/sample.canvas", SAMPLE_CANVAS_DATA)
```

- [ ] **Step 2: Write engine tests**

Create `tests/canvas/test_engine.py`:

```python
"""Tests for canvas engine — I/O and queries."""

import json
import pytest
from pathlib import Path

from obsidian_mcp.canvas.engine import (
    add_edge,
    add_node,
    find_group_for_node,
    find_node,
    find_nodes_by_type,
    get_dependencies,
    get_dependents,
    has_cycle,
    load_canvas,
    remove_edge,
    remove_node,
    save_canvas,
    update_node,
)
from obsidian_mcp.canvas.models import CanvasFile, Edge, Node


class TestLoadSave:
    """Tests for canvas I/O."""

    def test_load_canvas(self, tmp_canvas):
        canvas = load_canvas(str(tmp_canvas))
        assert len(canvas.nodes) == 7
        assert len(canvas.edges) == 3
        assert canvas.kanvas is not None
        assert canvas.kanvas.mode.value == "strict"

    def test_load_canvas_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_canvas("/nonexistent/path.canvas")

    def test_load_canvas_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.canvas"
        bad.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_canvas(str(bad))

    def test_save_canvas(self, tmp_path):
        path = str(tmp_path / "out.canvas")
        canvas = CanvasFile(path=path, nodes=[], edges=[])
        save_canvas(canvas)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data == {"nodes": [], "edges": []}

    def test_save_preserves_kanvas_metadata(self, tmp_path):
        from obsidian_mcp.canvas.models import KanvasMetadata, WorkflowMode
        path = str(tmp_path / "out.canvas")
        canvas = CanvasFile(
            path=path, nodes=[], edges=[],
            kanvas=KanvasMetadata(mode=WorkflowMode.RELAXED),
        )
        save_canvas(canvas)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["kanvas"]["mode"] == "relaxed"

    def test_roundtrip(self, tmp_canvas):
        canvas = load_canvas(str(tmp_canvas))
        save_canvas(canvas)
        canvas2 = load_canvas(str(tmp_canvas))
        assert len(canvas2.nodes) == len(canvas.nodes)
        assert len(canvas2.edges) == len(canvas.edges)


class TestQueries:
    """Tests for node/edge query functions."""

    def test_find_node(self, sample_canvas_file):
        node = find_node(sample_canvas_file, "t1")
        assert node is not None
        assert "DV-01" in node.text

    def test_find_node_not_found(self, sample_canvas_file):
        assert find_node(sample_canvas_file, "nonexistent") is None

    def test_find_nodes_by_type_text(self, sample_canvas_file):
        text_nodes = find_nodes_by_type(sample_canvas_file, "text")
        assert len(text_nodes) == 5  # 4 tasks + legend

    def test_find_nodes_by_type_group(self, sample_canvas_file):
        groups = find_nodes_by_type(sample_canvas_file, "group")
        assert len(groups) == 2

    def test_find_group_for_node(self, sample_canvas_file):
        t1 = find_node(sample_canvas_file, "t1")
        group = find_group_for_node(sample_canvas_file, t1)
        assert group is not None
        assert group.label == "Development"

    def test_find_group_for_node_outside(self, sample_canvas_file):
        legend = find_node(sample_canvas_file, "legend")
        group = find_group_for_node(sample_canvas_file, legend)
        assert group is None

    def test_get_dependencies(self, sample_canvas_file):
        t2 = find_node(sample_canvas_file, "t2")
        deps = get_dependencies(sample_canvas_file, t2)
        assert len(deps) == 1
        assert deps[0].id == "t1"

    def test_get_dependencies_none(self, sample_canvas_file):
        t1 = find_node(sample_canvas_file, "t1")
        deps = get_dependencies(sample_canvas_file, t1)
        assert len(deps) == 0

    def test_get_dependents(self, sample_canvas_file):
        t1 = find_node(sample_canvas_file, "t1")
        dependents = get_dependents(sample_canvas_file, t1)
        assert len(dependents) == 2  # t2 and t3

    def test_has_cycle_no_cycle(self, sample_canvas_file):
        assert has_cycle(sample_canvas_file, "t3", "t4") is False

    def test_has_cycle_direct(self, sample_canvas_file):
        # t1 → t2 exists; adding t2 → t1 would create cycle
        assert has_cycle(sample_canvas_file, "t2", "t1") is True

    def test_has_cycle_indirect(self, sample_canvas_file):
        # t1 → t2 → t3 exists; adding t3 → t1 would create cycle
        assert has_cycle(sample_canvas_file, "t3", "t1") is True


class TestMutations:
    """Tests for node/edge mutation functions."""

    def test_add_node(self, sample_canvas_file):
        new_node = Node(id="new1", type="text", x=0, y=0, width=280, height=160, text="New card")
        result = add_node(sample_canvas_file, new_node)
        assert result.id == "new1"
        assert find_node(sample_canvas_file, "new1") is not None

    def test_update_node(self, sample_canvas_file):
        updated = update_node(sample_canvas_file, "t1", text="Updated text", color="2")
        assert updated.text == "Updated text"
        assert updated.color == "2"

    def test_update_node_not_found(self, sample_canvas_file):
        with pytest.raises(ValueError, match="not found"):
            update_node(sample_canvas_file, "nonexistent", text="x")

    def test_remove_node(self, sample_canvas_file):
        remove_node(sample_canvas_file, "t2")
        assert find_node(sample_canvas_file, "t2") is None
        # Edges connected to t2 should also be removed
        edge_ids = [e.id for e in sample_canvas_file.edges]
        assert "e1" not in edge_ids  # t1 → t2
        assert "e3" not in edge_ids  # t2 → t3
        # Edge e2 (t1 → t3) should remain
        assert "e2" in edge_ids

    def test_remove_node_not_found(self, sample_canvas_file):
        with pytest.raises(ValueError, match="not found"):
            remove_node(sample_canvas_file, "nonexistent")

    def test_add_edge(self, sample_canvas_file):
        new_edge = Edge(id="enew", from_node="t4", to_node="t2")
        result = add_edge(sample_canvas_file, new_edge)
        assert result.id == "enew"
        assert len(sample_canvas_file.edges) == 4

    def test_remove_edge(self, sample_canvas_file):
        remove_edge(sample_canvas_file, "e1")
        assert len(sample_canvas_file.edges) == 2

    def test_remove_edge_not_found(self, sample_canvas_file):
        with pytest.raises(ValueError, match="not found"):
            remove_edge(sample_canvas_file, "nonexistent")
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/canvas/test_engine.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'obsidian_mcp.canvas.engine'`

- [ ] **Step 4: Implement engine**

Create `obsidian_mcp/canvas/engine.py`:

```python
"""
Canvas engine — pure operations on Obsidian Canvas files.

Handles I/O (load/save), queries (find nodes, dependencies, cycles),
and mutations (add/remove/update nodes and edges). No workflow opinion —
this layer knows about canvas structure but not about task states or
workflow rules.

All mutation functions operate in-place on a CanvasFile instance.
The caller decides when to save.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Optional

from .models import CanvasFile, Edge, Node

from ..utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------


def load_canvas(path: str) -> CanvasFile:
    """Load a .canvas file and return a CanvasFile instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Canvas file not found: {path}")

    raw = file_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    logger.debug("Loaded canvas from %s: %d nodes, %d edges", path, len(data.get("nodes", [])), len(data.get("edges", [])))
    return CanvasFile.from_dict(path, data)


def save_canvas(canvas: CanvasFile) -> None:
    """Write a CanvasFile to disk as JSON."""
    data = canvas.to_dict()
    Path(canvas.path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.debug("Saved canvas to %s: %d nodes, %d edges", canvas.path, len(canvas.nodes), len(canvas.edges))


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------


def generate_node_id() -> str:
    """Generate a short unique ID for a new node."""
    return uuid.uuid4().hex[:16]


def generate_edge_id() -> str:
    """Generate a short unique ID for a new edge."""
    return uuid.uuid4().hex[:16]


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def find_node(canvas: CanvasFile, node_id: str) -> Optional[Node]:
    """Find a node by ID. Returns None if not found."""
    for node in canvas.nodes:
        if node.id == node_id:
            return node
    return None


def find_nodes_by_type(canvas: CanvasFile, node_type: str) -> list[Node]:
    """Return all nodes of a given type."""
    return [n for n in canvas.nodes if n.type == node_type]


def find_group_for_node(canvas: CanvasFile, node: Node) -> Optional[Node]:
    """Find the group that visually contains a node (by bounding box)."""
    if node.type == "group":
        return None
    groups = find_nodes_by_type(canvas, "group")
    for group in groups:
        if (
            group.x <= node.x
            and group.y <= node.y
            and group.x + group.width >= node.x + node.width
            and group.y + group.height >= node.y + node.height
        ):
            return group
    return None


def get_dependencies(canvas: CanvasFile, node: Node) -> list[Node]:
    """Get nodes that block this node (inbound edges: fromNode → this node)."""
    dep_ids = [e.from_node for e in canvas.edges if e.to_node == node.id]
    return [n for n in canvas.nodes if n.id in dep_ids]


def get_dependents(canvas: CanvasFile, node: Node) -> list[Node]:
    """Get nodes that this node blocks (outbound edges: this node → toNode)."""
    dep_ids = [e.to_node for e in canvas.edges if e.from_node == node.id]
    return [n for n in canvas.nodes if n.id in dep_ids]


def has_cycle(canvas: CanvasFile, from_id: str, to_id: str) -> bool:
    """Check if adding an edge from_id → to_id would create a cycle.

    Uses DFS from to_id backward through existing edges. If we reach
    from_id, adding the edge would close a loop.
    """
    # Build adjacency: node → list of nodes it depends on (from_node values)
    adj: dict[str, list[str]] = {}
    for edge in canvas.edges:
        adj.setdefault(edge.to_node, []).append(edge.from_node)

    # DFS from to_id following existing dependency chains
    visited: set[str] = set()
    stack = [from_id]  # start from from_id, follow its dependencies
    while stack:
        current = stack.pop()
        if current == to_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(adj.get(current, []))
    return False


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def add_node(canvas: CanvasFile, node: Node) -> Node:
    """Add a node to the canvas."""
    canvas.nodes.append(node)
    return node


def update_node(canvas: CanvasFile, node_id: str, **changes) -> Node:
    """Update attributes of an existing node.

    Raises:
        ValueError: If the node is not found.
    """
    node = find_node(canvas, node_id)
    if node is None:
        raise ValueError(f"Node '{node_id}' not found")
    for key, value in changes.items():
        if hasattr(node, key):
            setattr(node, key, value)
    return node


def remove_node(canvas: CanvasFile, node_id: str) -> None:
    """Remove a node and all its connected edges.

    Raises:
        ValueError: If the node is not found.
    """
    node = find_node(canvas, node_id)
    if node is None:
        raise ValueError(f"Node '{node_id}' not found")
    canvas.nodes.remove(node)
    canvas.edges = [
        e for e in canvas.edges
        if e.from_node != node_id and e.to_node != node_id
    ]


def add_edge(canvas: CanvasFile, edge: Edge) -> Edge:
    """Add an edge to the canvas."""
    canvas.edges.append(edge)
    return edge


def remove_edge(canvas: CanvasFile, edge_id: str) -> None:
    """Remove an edge by ID.

    Raises:
        ValueError: If the edge is not found.
    """
    for i, edge in enumerate(canvas.edges):
        if edge.id == edge_id:
            canvas.edges.pop(i)
            return
    raise ValueError(f"Edge '{edge_id}' not found")


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def compute_node_placement(
    canvas: CanvasFile,
    group: Optional[Node],
    depends_on: list[Node],
) -> tuple[int, int]:
    """Compute x, y position for a new node.

    Places the node inside the group if provided, below the lowest
    existing node in that group. If depends_on nodes exist, places
    below the lowest dependency.
    """
    if group is not None:
        # Find lowest node in group
        group_nodes = [
            n for n in canvas.nodes
            if n.type != "group" and find_group_for_node(canvas, n) == group
        ]
        if group_nodes:
            lowest = max(group_nodes, key=lambda n: n.y + n.height)
            return group.x + 20, lowest.y + lowest.height + 40
        return group.x + 20, group.y + 60

    if depends_on:
        lowest = max(depends_on, key=lambda n: n.y + n.height)
        return lowest.x, lowest.y + lowest.height + 40

    # Default: find lowest node overall
    if canvas.nodes:
        lowest = max(canvas.nodes, key=lambda n: n.y + n.height)
        return lowest.x, lowest.y + lowest.height + 40
    return 0, 0


def pick_edge_sides(from_node: Node, to_node: Node) -> tuple[str, str]:
    """Choose edge attachment sides based on relative node positions."""
    dx = to_node.x - from_node.x
    dy = to_node.y - from_node.y

    if abs(dy) >= abs(dx):
        # Vertical relationship
        if dy > 0:
            return "bottom", "top"
        return "top", "bottom"
    # Horizontal relationship
    if dx > 0:
        return "right", "left"
    return "left", "right"
```

- [ ] **Step 5: Update canvas `__init__.py` exports**

Add engine exports to `obsidian_mcp/canvas/__init__.py`:

```python
"""
Canvas management module for the Obsidian MCP server.

Provides generic canvas CRUD operations and a Kanvas-inspired
project management workflow with color-coded task states.
"""

from .models import (
    CanvasFile,
    Edge,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
    TASK_ID_RE,
)
from .engine import (
    load_canvas,
    save_canvas,
    find_node,
    find_nodes_by_type,
    find_group_for_node,
    get_dependencies,
    get_dependents,
    has_cycle,
    add_node,
    update_node,
    remove_node,
    add_edge,
    remove_edge,
    compute_node_placement,
    pick_edge_sides,
    generate_node_id,
    generate_edge_id,
)

__all__ = [
    "CanvasFile",
    "Edge",
    "KanvasMetadata",
    "Node",
    "TaskState",
    "WorkflowMode",
    "TASK_ID_RE",
    "load_canvas",
    "save_canvas",
    "find_node",
    "find_nodes_by_type",
    "find_group_for_node",
    "get_dependencies",
    "get_dependents",
    "has_cycle",
    "add_node",
    "update_node",
    "remove_node",
    "add_edge",
    "remove_edge",
    "compute_node_placement",
    "pick_edge_sides",
    "generate_node_id",
    "generate_edge_id",
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
python -m pytest tests/canvas/test_engine.py -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add obsidian_mcp/canvas/engine.py obsidian_mcp/canvas/__init__.py tests/canvas/conftest.py tests/canvas/test_engine.py
git commit -m "feat(canvas): add engine with I/O, queries, mutations, and placement"
```

---

### Task 3: Generic canvas logic

**Files:**
- Create: `obsidian_mcp/canvas/canvas_logic.py`
- Create: `tests/canvas/test_canvas_logic.py`

- [ ] **Step 1: Write tests**

Create `tests/canvas/test_canvas_logic.py`:

```python
"""Tests for generic canvas tool logic."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from obsidian_mcp.canvas.canvas_logic import (
    read_canvas,
    list_canvases,
    add_card,
    add_group,
    add_canvas_edge,
    update_card,
    remove_card,
    remove_canvas_edge,
)


class TestReadCanvas:
    """Tests for canvas_read logic."""

    def test_read_canvas(self, tmp_canvas):
        result = read_canvas(str(tmp_canvas))
        assert result.success
        assert "DV-01" in result.data
        assert "Development" in result.data

    def test_read_canvas_not_found(self):
        result = read_canvas("/nonexistent/path.canvas")
        assert not result.success
        assert "not found" in result.error.lower()


class TestListCanvases:
    """Tests for canvas_list logic."""

    def test_list_canvases(self, tmp_path):
        (tmp_path / "a.canvas").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")
        (tmp_path / "b.canvas").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")
        (tmp_path / "not_canvas.md").write_text("hello", encoding="utf-8")
        with patch("obsidian_mcp.canvas.canvas_logic.get_vault_path", return_value=tmp_path):
            result = list_canvases("")
        assert result.success
        assert "a.canvas" in result.data
        assert "b.canvas" in result.data
        assert "not_canvas" not in result.data

    def test_list_canvases_subfolder(self, tmp_path):
        sub = tmp_path / "Projects"
        sub.mkdir()
        (sub / "proj.canvas").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")
        with patch("obsidian_mcp.canvas.canvas_logic.get_vault_path", return_value=tmp_path):
            result = list_canvases("Projects")
        assert result.success
        assert "proj.canvas" in result.data

    def test_list_canvases_no_vault(self):
        with patch("obsidian_mcp.canvas.canvas_logic.get_vault_path", return_value=None):
            result = list_canvases("")
        assert not result.success


class TestAddCard:
    """Tests for canvas_add_card logic."""

    def test_add_card(self, tmp_canvas):
        result = add_card(str(tmp_canvas), "New card text")
        assert result.success
        # Verify the card was saved
        data = json.loads(tmp_canvas.read_text(encoding="utf-8"))
        texts = [n.get("text", "") for n in data["nodes"]]
        assert "New card text" in texts

    def test_add_card_to_group(self, tmp_canvas):
        result = add_card(str(tmp_canvas), "Grouped card", group="Development")
        assert result.success

    def test_add_card_to_nonexistent_group(self, tmp_canvas):
        result = add_card(str(tmp_canvas), "Orphan", group="Nonexistent")
        assert not result.success
        assert "not found" in result.error.lower()


class TestAddGroup:
    """Tests for canvas_add_group logic."""

    def test_add_group(self, tmp_canvas):
        result = add_group(str(tmp_canvas), "New Group")
        assert result.success
        data = json.loads(tmp_canvas.read_text(encoding="utf-8"))
        labels = [n.get("label", "") for n in data["nodes"] if n["type"] == "group"]
        assert "New Group" in labels


class TestAddEdge:
    """Tests for canvas_add_edge logic."""

    def test_add_edge(self, tmp_canvas):
        result = add_canvas_edge(str(tmp_canvas), "t4", "t2")
        assert result.success

    def test_add_edge_node_not_found(self, tmp_canvas):
        result = add_canvas_edge(str(tmp_canvas), "nonexistent", "t2")
        assert not result.success

    def test_add_edge_cycle(self, tmp_canvas):
        result = add_canvas_edge(str(tmp_canvas), "t2", "t1")
        assert not result.success
        assert "cycle" in result.error.lower()


class TestUpdateCard:
    """Tests for canvas_update_card logic."""

    def test_update_text(self, tmp_canvas):
        result = update_card(str(tmp_canvas), "t1", text="Updated text")
        assert result.success

    def test_update_color(self, tmp_canvas):
        result = update_card(str(tmp_canvas), "t1", color="2")
        assert result.success

    def test_update_not_found(self, tmp_canvas):
        result = update_card(str(tmp_canvas), "nonexistent", text="x")
        assert not result.success


class TestRemoveCard:
    """Tests for canvas_remove_card logic."""

    def test_remove_card(self, tmp_canvas):
        result = remove_card(str(tmp_canvas), "t4")
        assert result.success
        data = json.loads(tmp_canvas.read_text(encoding="utf-8"))
        ids = [n["id"] for n in data["nodes"]]
        assert "t4" not in ids

    def test_remove_card_not_found(self, tmp_canvas):
        result = remove_card(str(tmp_canvas), "nonexistent")
        assert not result.success


class TestRemoveEdge:
    """Tests for canvas_remove_edge logic."""

    def test_remove_edge(self, tmp_canvas):
        result = remove_canvas_edge(str(tmp_canvas), "e1")
        assert result.success
        data = json.loads(tmp_canvas.read_text(encoding="utf-8"))
        edge_ids = [e["id"] for e in data["edges"]]
        assert "e1" not in edge_ids

    def test_remove_edge_not_found(self, tmp_canvas):
        result = remove_canvas_edge(str(tmp_canvas), "nonexistent")
        assert not result.success
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/canvas/test_canvas_logic.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement canvas logic**

Create `obsidian_mcp/canvas/canvas_logic.py`:

```python
"""
Logic for generic canvas tools.

Provides CRUD operations on any .canvas file without workflow assumptions.
All functions return Result[str].
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config import get_vault_path
from ..result import Result
from ..utils import get_logger

from . import engine
from .models import CanvasFile, Edge, Node

logger = get_logger(__name__)


def _resolve_canvas_path(canvas_path: str) -> Result[str]:
    """Resolve a canvas path relative to vault root.

    Returns Result with the absolute path string on success.
    """
    vault_path = get_vault_path()
    if vault_path is None:
        return Result.fail("Vault path is not configured.")

    abs_path = Path(canvas_path)
    if not abs_path.is_absolute():
        abs_path = vault_path / canvas_path

    if not abs_path.suffix == ".canvas":
        return Result.fail(f"Not a .canvas file: {canvas_path}")

    return Result.ok(str(abs_path))


def _load(canvas_path: str) -> Result[CanvasFile]:
    """Load a canvas with path resolution and error handling."""
    resolved = _resolve_canvas_path(canvas_path)
    if not resolved.success:
        return Result.fail(resolved.error)

    try:
        canvas = engine.load_canvas(resolved.data)
        return Result.ok(canvas)
    except FileNotFoundError:
        return Result.fail(f"Canvas file not found: {canvas_path}")
    except Exception as e:
        return Result.fail(f"Error loading canvas: {e}")


def _save(canvas: CanvasFile) -> Result[str]:
    """Save canvas with error handling."""
    try:
        engine.save_canvas(canvas)
        return Result.ok("saved")
    except Exception as e:
        return Result.fail(f"Error saving canvas: {e}")


def _format_node_summary(node: Node) -> str:
    """Format a node for display."""
    if node.type == "group":
        return f"  [{node.id}] GROUP: {node.label}"
    label = node.text.split("\n")[0][:60] if node.text else "(empty)"
    color = f" color={node.color}" if node.color else ""
    return f"  [{node.id}] {label}{color}"


# ---------------------------------------------------------------------------
# Tool logic functions
# ---------------------------------------------------------------------------


def read_canvas(canvas_path: str) -> Result[str]:
    """Read a canvas and return a human-readable summary."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    groups = engine.find_nodes_by_type(canvas, "group")
    text_nodes = engine.find_nodes_by_type(canvas, "text")

    lines = [f"Canvas: {canvas_path}", f"Nodes: {len(canvas.nodes)} | Edges: {len(canvas.edges)}", ""]

    if groups:
        lines.append("Groups:")
        for g in groups:
            lines.append(f"  [{g.id}] {g.label}")
        lines.append("")

    if text_nodes:
        lines.append("Cards:")
        for n in text_nodes:
            lines.append(_format_node_summary(n))
        lines.append("")

    if canvas.edges:
        lines.append("Edges:")
        for e in canvas.edges:
            lines.append(f"  [{e.id}] {e.from_node} → {e.to_node}")

    return Result.ok("\n".join(lines))


def list_canvases(folder: str) -> Result[str]:
    """List all .canvas files in the vault or a subfolder."""
    vault_path = get_vault_path()
    if vault_path is None:
        return Result.fail("Vault path is not configured.")

    search_path = vault_path / folder if folder else vault_path
    if not search_path.is_dir():
        return Result.fail(f"Folder not found: {folder}")

    canvas_files = sorted(search_path.rglob("*.canvas"))
    if not canvas_files:
        return Result.ok("No .canvas files found.")

    lines = [f"Found {len(canvas_files)} canvas file(s):"]
    for f in canvas_files:
        rel = f.relative_to(vault_path)
        lines.append(f"  {rel}")

    return Result.ok("\n".join(lines))


def add_card(
    canvas_path: str,
    text: str,
    group: str = "",
    color: str = "",
    width: int = 280,
    height: int = 160,
) -> Result[str]:
    """Add a text card to a canvas."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    group_node = None

    if group:
        groups = engine.find_nodes_by_type(canvas, "group")
        group_node = next((g for g in groups if g.label == group), None)
        if group_node is None:
            return Result.fail(f"Group '{group}' not found in canvas.")

    x, y = engine.compute_node_placement(canvas, group_node, [])
    new_node = Node(
        id=engine.generate_node_id(),
        type="text",
        x=x, y=y,
        width=width, height=height,
        text=text,
        color=color,
    )
    engine.add_node(canvas, new_node)

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    logger.info("Added card [%s] to canvas %s", new_node.id, canvas_path)
    return Result.ok(f"Card added: [{new_node.id}] {text[:50]}")


def add_group(canvas_path: str, label: str) -> Result[str]:
    """Add a group to a canvas."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    existing = engine.find_nodes_by_type(canvas, "group")
    # Place new group to the right of existing ones
    x = 0
    if existing:
        rightmost = max(existing, key=lambda g: g.x + g.width)
        x = rightmost.x + rightmost.width + 50

    new_group = Node(
        id=engine.generate_node_id(),
        type="group",
        x=x, y=0,
        width=400, height=800,
        label=label,
    )
    engine.add_node(canvas, new_group)

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    logger.info("Added group [%s] '%s' to canvas %s", new_group.id, label, canvas_path)
    return Result.ok(f"Group added: [{new_group.id}] {label}")


def add_canvas_edge(
    canvas_path: str,
    from_id: str,
    to_id: str,
    label: str = "",
) -> Result[str]:
    """Add an edge between two nodes."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    from_node = engine.find_node(canvas, from_id)
    if from_node is None:
        return Result.fail(f"Source node '{from_id}' not found.")
    to_node = engine.find_node(canvas, to_id)
    if to_node is None:
        return Result.fail(f"Target node '{to_id}' not found.")

    if engine.has_cycle(canvas, from_id, to_id):
        return Result.fail(f"Adding edge {from_id} → {to_id} would create a cycle.")

    from_side, to_side = engine.pick_edge_sides(from_node, to_node)
    new_edge = Edge(
        id=engine.generate_edge_id(),
        from_node=from_id,
        to_node=to_id,
        from_side=from_side,
        to_side=to_side,
        label=label,
    )
    engine.add_edge(canvas, new_edge)

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    return Result.ok(f"Edge added: {from_id} → {to_id}")


def update_card(
    canvas_path: str,
    node_id: str,
    text: str = "",
    color: str = "",
) -> Result[str]:
    """Update text and/or color of a card."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    node = engine.find_node(canvas, node_id)
    if node is None:
        return Result.fail(f"Node '{node_id}' not found.")

    changes = {}
    if text:
        changes["text"] = text
    if color:
        changes["color"] = color

    if not changes:
        return Result.ok("No changes specified.")

    engine.update_node(canvas, node_id, **changes)

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    return Result.ok(f"Card [{node_id}] updated.")


def remove_card(canvas_path: str, node_id: str) -> Result[str]:
    """Remove a card and its connected edges."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    try:
        engine.remove_node(canvas, node_id)
    except ValueError as e:
        return Result.fail(str(e))

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    return Result.ok(f"Card [{node_id}] removed.")


def remove_canvas_edge(canvas_path: str, edge_id: str) -> Result[str]:
    """Remove an edge."""
    load_result = _load(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    try:
        engine.remove_edge(canvas, edge_id)
    except ValueError as e:
        return Result.fail(str(e))

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    return Result.ok(f"Edge [{edge_id}] removed.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/canvas/test_canvas_logic.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add obsidian_mcp/canvas/canvas_logic.py tests/canvas/test_canvas_logic.py
git commit -m "feat(canvas): add generic canvas CRUD logic"
```

---

### Task 4: Generic canvas MCP tools

**Files:**
- Create: `obsidian_mcp/canvas/canvas_tools.py`

- [ ] **Step 1: Implement tool registration**

Create `obsidian_mcp/canvas/canvas_tools.py`:

```python
"""
Generic canvas MCP tools.

Provides CRUD operations on any .canvas file in the vault.
No workflow assumptions — these tools work with any canvas
(mind maps, diagrams, project boards, etc.).
"""

from fastmcp import FastMCP

from ..utils import get_logger
from .canvas_logic import (
    add_canvas_edge,
    add_card,
    add_group,
    list_canvases,
    read_canvas,
    remove_canvas_edge,
    remove_card,
    update_card,
)

logger = get_logger(__name__)


def register_canvas_tools(mcp: FastMCP) -> None:
    """Register generic canvas tools with the MCP server."""

    @mcp.tool()
    def canvas_read(canvas_path: str) -> str:
        """Read a canvas file and return a human-readable summary of its nodes, edges, and groups.

        Args:
            canvas_path: Path to the .canvas file (relative to vault root or absolute)

        Returns:
            Summary of canvas contents
        """
        try:
            return read_canvas(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading canvas: {e}"

    @mcp.tool()
    def canvas_list(folder: str = "") -> str:
        """List all .canvas files in the vault or in a specific folder.

        Args:
            folder: Subfolder to search in (relative to vault root). Empty for entire vault.

        Returns:
            List of .canvas file paths
        """
        try:
            return list_canvases(folder).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error listing canvases: {e}"

    @mcp.tool()
    def canvas_add_card(
        canvas_path: str,
        text: str,
        group: str = "",
        color: str = "",
        width: int = 280,
        height: int = 160,
    ) -> str:
        """Add a text card to a canvas file.

        Args:
            canvas_path: Path to the .canvas file
            text: Card text content
            group: Name of group to place the card in (optional)
            color: Card color as string "0"-"6" (optional)
            width: Card width in pixels (default 280)
            height: Card height in pixels (default 160)

        Returns:
            Confirmation with the new card ID
        """
        try:
            return add_card(canvas_path, text, group, color, width, height).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding card: {e}"

    @mcp.tool()
    def canvas_add_group(canvas_path: str, label: str) -> str:
        """Create a new group/area in a canvas file.

        Args:
            canvas_path: Path to the .canvas file
            label: Group label text

        Returns:
            Confirmation with the new group ID
        """
        try:
            return add_group(canvas_path, label).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding group: {e}"

    @mcp.tool()
    def canvas_add_edge(
        canvas_path: str,
        from_id: str,
        to_id: str,
        label: str = "",
    ) -> str:
        """Connect two nodes with a directional arrow. Rejects if it would create a cycle.

        Args:
            canvas_path: Path to the .canvas file
            from_id: Source node ID
            to_id: Target node ID
            label: Edge label (optional)

        Returns:
            Confirmation of the new edge
        """
        try:
            return add_canvas_edge(canvas_path, from_id, to_id, label).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding edge: {e}"

    @mcp.tool()
    def canvas_update_card(
        canvas_path: str,
        node_id: str,
        text: str = "",
        color: str = "",
    ) -> str:
        """Update the text and/or color of an existing card.

        Args:
            canvas_path: Path to the .canvas file
            node_id: ID of the card to update
            text: New text content (leave empty to keep current)
            color: New color "0"-"6" (leave empty to keep current)

        Returns:
            Confirmation of the update
        """
        try:
            return update_card(canvas_path, node_id, text, color).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error updating card: {e}"

    @mcp.tool()
    def canvas_remove_card(canvas_path: str, node_id: str) -> str:
        """Delete a card and all its connected edges from a canvas.

        Args:
            canvas_path: Path to the .canvas file
            node_id: ID of the card to remove

        Returns:
            Confirmation of removal
        """
        try:
            return remove_card(canvas_path, node_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error removing card: {e}"

    @mcp.tool()
    def canvas_remove_edge(canvas_path: str, edge_id: str) -> str:
        """Delete a connection between two nodes.

        Args:
            canvas_path: Path to the .canvas file
            edge_id: ID of the edge to remove

        Returns:
            Confirmation of removal
        """
        try:
            return remove_canvas_edge(canvas_path, edge_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error removing edge: {e}"
```

- [ ] **Step 2: Verify import works**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
python -c "from obsidian_mcp.canvas.canvas_tools import register_canvas_tools; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add obsidian_mcp/canvas/canvas_tools.py
git commit -m "feat(canvas): add 8 generic canvas MCP tools"
```

---

### Task 5: Workflow logic — task ID generation and normalize

**Files:**
- Create: `obsidian_mcp/canvas/workflow_logic.py`
- Create: `tests/canvas/test_workflow_logic.py`

- [ ] **Step 1: Write tests**

Create `tests/canvas/test_workflow_logic.py`:

```python
"""Tests for canvas workflow logic."""

import json
import pytest
from unittest.mock import patch

from obsidian_mcp.canvas.models import (
    CanvasFile,
    Edge,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
    TASK_ID_RE,
)
from obsidian_mcp.canvas.workflow_logic import (
    extract_task_id,
    extract_task_title,
    generate_group_prefix,
    get_next_task_id,
    is_task_card,
    normalize,
    all_deps_green,
    get_workflow_mode,
    validate_transition,
)


class TestTaskIdParsing:
    """Tests for task ID extraction and generation."""

    def test_extract_task_id(self):
        assert extract_task_id("## DV-01 Build feature\nDescription") == "DV-01"

    def test_extract_task_id_three_letter(self):
        assert extract_task_id("## RSC-12 Research topic") == "RSC-12"

    def test_extract_task_id_no_match(self):
        assert extract_task_id("# Legend\nNot a task") is None

    def test_extract_task_id_empty(self):
        assert extract_task_id("") is None

    def test_extract_task_title(self):
        assert extract_task_title("## DV-01 Build feature\nDescription") == "Build feature"

    def test_is_task_card_true(self):
        node = Node(id="t1", type="text", x=0, y=0, width=280, height=160, text="## DV-01 Task", color="1")
        assert is_task_card(node) is True

    def test_is_task_card_false_legend(self):
        node = Node(id="legend", type="text", x=0, y=0, width=200, height=300, text="# Legend", color="0")
        assert is_task_card(node) is False

    def test_is_task_card_false_group(self):
        node = Node(id="g1", type="group", x=0, y=0, width=400, height=800, label="Dev")
        assert is_task_card(node) is False

    def test_generate_group_prefix_single(self):
        assert generate_group_prefix("Design", []) == "D"

    def test_generate_group_prefix_conflict(self):
        assert generate_group_prefix("Development", ["D"]) == "DV"

    def test_generate_group_prefix_multi_word(self):
        assert generate_group_prefix("Report Writing", []) == "RW"

    def test_generate_group_prefix_research(self):
        prefix = generate_group_prefix("Research", [])
        assert prefix in ("R", "RS")

    def test_get_next_task_id(self, sample_canvas_file):
        # sample has DV-01, DV-02, DV-03, TS-01
        next_id = get_next_task_id(sample_canvas_file, "DV")
        assert next_id == "DV-04"

    def test_get_next_task_id_new_prefix(self, sample_canvas_file):
        next_id = get_next_task_id(sample_canvas_file, "QA")
        assert next_id == "QA-01"


class TestNormalize:
    """Tests for canvas normalization."""

    def test_normalize_assigns_ids(self, tmp_path):
        """Cards without task IDs get IDs assigned."""
        data = {
            "nodes": [
                {"id": "grp", "type": "group", "x": 0, "y": 0, "width": 400, "height": 800, "label": "Development"},
                {"id": "card1", "type": "text", "x": 20, "y": 50, "width": 280, "height": 160, "text": "Build feature\nDescription", "color": "1"},
            ],
            "edges": [],
            "kanvas": {"mode": "strict", "version": "1.0"},
        }
        canvas_path = tmp_path / "test.canvas"
        canvas_path.write_text(json.dumps(data), encoding="utf-8")

        result = normalize(str(canvas_path))
        assert result.success

        loaded = json.loads(canvas_path.read_text(encoding="utf-8"))
        card = next(n for n in loaded["nodes"] if n["id"] == "card1")
        assert "## D-01" in card["text"] or "## DV-01" in card["text"]

    def test_normalize_blocked_states(self, tmp_path):
        """Red card with unmet deps becomes gray; gray with all deps green becomes red."""
        data = {
            "nodes": [
                {"id": "grp", "type": "group", "x": 0, "y": 0, "width": 400, "height": 800, "label": "Dev"},
                {"id": "t1", "type": "text", "x": 20, "y": 50, "width": 280, "height": 160, "text": "## D-01 Done task", "color": "4"},
                {"id": "t2", "type": "text", "x": 20, "y": 250, "width": 280, "height": 160, "text": "## D-02 Blocked task", "color": "0"},
                {"id": "t3", "type": "text", "x": 20, "y": 450, "width": 280, "height": 160, "text": "## D-03 Should block", "color": "1"},
            ],
            "edges": [
                {"id": "e1", "fromNode": "t1", "toNode": "t2", "fromSide": "bottom", "toSide": "top"},
                {"id": "e2", "fromNode": "t2", "toNode": "t3", "fromSide": "bottom", "toSide": "top"},
            ],
            "kanvas": {"mode": "strict", "version": "1.0"},
        }
        canvas_path = tmp_path / "test.canvas"
        canvas_path.write_text(json.dumps(data), encoding="utf-8")

        result = normalize(str(canvas_path))
        assert result.success

        loaded = json.loads(canvas_path.read_text(encoding="utf-8"))
        t2 = next(n for n in loaded["nodes"] if n["id"] == "t2")
        t3 = next(n for n in loaded["nodes"] if n["id"] == "t3")
        # t2 depends on t1 (green) → should become red
        assert t2["color"] == "1"
        # t3 depends on t2 (now red, not green) → should become gray
        assert t3["color"] == "0"

    def test_normalize_doesnt_touch_non_task_cards(self, tmp_path):
        data = {
            "nodes": [
                {"id": "legend", "type": "text", "x": 900, "y": 0, "width": 200, "height": 300, "text": "# Legend\nInfo", "color": "0"},
            ],
            "edges": [],
            "kanvas": {"mode": "strict", "version": "1.0"},
        }
        canvas_path = tmp_path / "test.canvas"
        canvas_path.write_text(json.dumps(data), encoding="utf-8")

        normalize(str(canvas_path))

        loaded = json.loads(canvas_path.read_text(encoding="utf-8"))
        legend = loaded["nodes"][0]
        assert legend["text"] == "# Legend\nInfo"  # unchanged


class TestAllDepsGreen:
    """Tests for dependency satisfaction check."""

    def test_all_deps_green(self, sample_canvas_file):
        from obsidian_mcp.canvas.engine import find_node
        t2 = find_node(sample_canvas_file, "t2")
        # t2 depends on t1 which is green (color "4")
        assert all_deps_green(sample_canvas_file, t2) is True

    def test_not_all_deps_green(self, sample_canvas_file):
        from obsidian_mcp.canvas.engine import find_node
        t3 = find_node(sample_canvas_file, "t3")
        # t3 depends on t1 (green) and t2 (red) → not all green
        assert all_deps_green(sample_canvas_file, t3) is False


class TestValidateTransition:
    """Tests for workflow state transition validation."""

    def test_start_valid(self):
        result = validate_transition(TaskState.TODO, TaskState.DOING, WorkflowMode.STRICT)
        assert result.success

    def test_finish_valid(self):
        result = validate_transition(TaskState.DOING, TaskState.REVIEW, WorkflowMode.STRICT)
        assert result.success

    def test_pause_valid(self):
        result = validate_transition(TaskState.DOING, TaskState.TODO, WorkflowMode.STRICT)
        assert result.success

    def test_approve_strict_rejected(self):
        result = validate_transition(TaskState.PROPOSED, TaskState.TODO, WorkflowMode.STRICT)
        assert not result.success

    def test_approve_relaxed_allowed(self):
        result = validate_transition(TaskState.PROPOSED, TaskState.TODO, WorkflowMode.RELAXED)
        assert result.success

    def test_complete_strict_rejected(self):
        result = validate_transition(TaskState.REVIEW, TaskState.DONE, WorkflowMode.STRICT)
        assert not result.success

    def test_complete_relaxed_allowed(self):
        result = validate_transition(TaskState.REVIEW, TaskState.DONE, WorkflowMode.RELAXED)
        assert result.success

    def test_invalid_transition(self):
        result = validate_transition(TaskState.TODO, TaskState.REVIEW, WorkflowMode.RELAXED)
        assert not result.success


class TestGetWorkflowMode:
    """Tests for reading workflow mode from canvas."""

    def test_strict_mode(self, sample_canvas_file):
        assert get_workflow_mode(sample_canvas_file) == WorkflowMode.STRICT

    def test_no_kanvas_metadata(self):
        canvas = CanvasFile(path="/tmp/t.canvas", nodes=[], edges=[])
        assert get_workflow_mode(canvas) == WorkflowMode.STRICT  # default
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/canvas/test_workflow_logic.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement workflow logic**

Create `obsidian_mcp/canvas/workflow_logic.py`:

```python
"""
Workflow logic for the Kanvas project management system.

Implements the state machine, task ID generation, normalize,
and transition validation. This layer knows about workflow rules
but does not know about MCP tools.
"""

from __future__ import annotations

import re
from typing import Optional

from ..result import Result
from ..utils import get_logger

from . import engine
from .models import (
    CanvasFile,
    KanvasMetadata,
    Node,
    TaskState,
    WorkflowMode,
    TASK_ID_RE,
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


# ---------------------------------------------------------------------------
# Task ID helpers
# ---------------------------------------------------------------------------


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
    """Check if a text node has content that should get a task ID.

    Non-empty text nodes inside groups that don't have IDs yet and aren't
    known non-task cards (legend, etc.) are candidates for ID assignment.
    """
    if node.type != "text":
        return False
    if node.id in _NON_TASK_IDS:
        return False
    if not node.text.strip():
        return False
    # Already has a task ID
    if extract_task_id(node.text) is not None:
        return False
    # Must have a color that indicates it's a task (not colorless)
    if node.color in ("", "0"):
        # Could be a non-task card (legend, note). Only treat as task
        # if it doesn't start with "# " (heading = non-task).
        first_line = node.text.strip().split("\n")[0]
        if first_line.startswith("# "):
            return False
    return True


def generate_group_prefix(label: str, existing_prefixes: list[str]) -> str:
    """Generate a 1-3 letter prefix from a group label.

    Uses initials for multi-word labels, or progressively longer
    prefixes for single-word labels to avoid conflicts.
    """
    words = label.strip().split()
    if len(words) > 1:
        # Multi-word: use initials
        prefix = "".join(w[0].upper() for w in words)[:3]
        if prefix not in existing_prefixes:
            return prefix

    # Single word: try 1, 2, 3 letters
    word = label.strip().upper()
    for length in range(1, min(4, len(word) + 1)):
        prefix = word[:length]
        if prefix not in existing_prefixes:
            return prefix

    # Fallback: use consonants
    consonants = [c for c in word if c not in "AEIOU"]
    if len(consonants) >= 2:
        prefix = consonants[0] + consonants[1]
        if prefix not in existing_prefixes:
            return prefix

    return word[:3]


def get_next_task_id(canvas: CanvasFile, prefix: str) -> str:
    """Get the next available task ID for a given prefix."""
    existing_numbers: list[int] = []
    for node in canvas.nodes:
        task_id = extract_task_id(node.text)
        if task_id and task_id.startswith(prefix + "-"):
            num_str = task_id.split("-")[1]
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


# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------


def all_deps_green(canvas: CanvasFile, node: Node) -> bool:
    """Check if all dependencies of a node are in DONE (green) state."""
    deps = engine.get_dependencies(canvas, node)
    return all(d.color == TaskState.DONE.value for d in deps)


# ---------------------------------------------------------------------------
# Workflow mode
# ---------------------------------------------------------------------------


def get_workflow_mode(canvas: CanvasFile) -> WorkflowMode:
    """Get the workflow mode from canvas metadata. Defaults to STRICT."""
    if canvas.kanvas is not None:
        return canvas.kanvas.mode
    return WorkflowMode.STRICT


# ---------------------------------------------------------------------------
# Transition validation
# ---------------------------------------------------------------------------


def validate_transition(
    from_state: TaskState,
    to_state: TaskState,
    mode: WorkflowMode,
) -> Result[str]:
    """Validate a workflow state transition.

    Returns Result.ok on valid transition, Result.fail with reason on invalid.
    """
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


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------


def normalize(canvas_path: str) -> Result[str]:
    """Normalize a project canvas: assign task IDs, manage blocked states.

    1. Assign IDs to text cards inside groups that don't have one yet.
    2. Update blocked states: red + unmet deps → gray, gray + all deps green → red.

    Returns a summary of changes made.
    """
    try:
        canvas = engine.load_canvas(canvas_path)
    except FileNotFoundError:
        return Result.fail(f"Canvas file not found: {canvas_path}")
    except Exception as e:
        return Result.fail(f"Error loading canvas: {e}")

    changes: list[str] = []

    # --- Phase 1: Assign task IDs ---
    # Collect existing prefixes
    existing_prefixes: list[str] = []
    for node in canvas.nodes:
        tid = extract_task_id(node.text)
        if tid:
            prefix = tid.split("-")[0]
            if prefix not in existing_prefixes:
                existing_prefixes.append(prefix)

    # Build group → prefix mapping
    groups = engine.find_nodes_by_type(canvas, "group")
    group_prefixes: dict[str, str] = {}
    for group in groups:
        # Check if any existing task in this group already has a prefix
        group_nodes = [
            n for n in canvas.nodes
            if n.type == "text" and engine.find_group_for_node(canvas, n) == group
        ]
        existing_group_prefix = None
        for gn in group_nodes:
            tid = extract_task_id(gn.text)
            if tid:
                existing_group_prefix = tid.split("-")[0]
                break

        if existing_group_prefix:
            group_prefixes[group.id] = existing_group_prefix
        else:
            prefix = generate_group_prefix(group.label, existing_prefixes)
            group_prefixes[group.id] = prefix
            existing_prefixes.append(prefix)

    # Assign IDs to cards without them
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
        first_line = node.text.strip().split("\n")[0]
        rest = "\n".join(node.text.strip().split("\n")[1:])
        node.text = f"## {task_id} {first_line}"
        if rest:
            node.text += f"\n{rest}"
        changes.append(f"Assigned {task_id} to card [{node.id}]")
        logger.info("Assigned task ID %s to card [%s]", task_id, node.id)

    # --- Phase 2: Update blocked states ---
    for node in canvas.nodes:
        if not is_task_card(node):
            continue

        deps = engine.get_dependencies(canvas, node)
        if not deps:
            continue

        deps_met = all_deps_green(canvas, node)

        if node.color == TaskState.TODO.value and not deps_met:
            node.color = TaskState.BLOCKED.value
            tid = extract_task_id(node.text)
            changes.append(f"{tid}: red → gray (unmet dependencies)")
            logger.info("Blocked task %s: unmet dependencies", tid)

        elif node.color == TaskState.BLOCKED.value and deps_met:
            node.color = TaskState.TODO.value
            tid = extract_task_id(node.text)
            changes.append(f"{tid}: gray → red (dependencies met)")
            logger.info("Unblocked task %s: all dependencies met", tid)

    # --- Save ---
    engine.save_canvas(canvas)

    if not changes:
        return Result.ok("Canvas is already normalized. No changes needed.")

    summary = f"Normalized canvas ({len(changes)} changes):\n" + "\n".join(f"  - {c}" for c in changes)
    return Result.ok(summary)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/canvas/test_workflow_logic.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add obsidian_mcp/canvas/workflow_logic.py tests/canvas/test_workflow_logic.py
git commit -m "feat(canvas): add workflow logic with state machine, task IDs, and normalize"
```

---

### Task 6: Workflow MCP tools

**Files:**
- Create: `obsidian_mcp/canvas/workflow_tools.py`
- Create: `tests/canvas/test_workflow_tools.py`

- [ ] **Step 1: Write integration tests for key workflow operations**

Create `tests/canvas/test_workflow_tools.py`:

```python
"""Integration tests for workflow tool logic (called via workflow_tools helpers)."""

import json
import pytest
from pathlib import Path

from obsidian_mcp.canvas.workflow_logic import (
    all_deps_green,
    find_task_by_id,
    normalize,
)
from obsidian_mcp.canvas.engine import load_canvas, find_node
from obsidian_mcp.canvas.workflow_tool_logic import (
    get_status,
    show_task,
    get_ready_tasks,
    get_blocked_tasks,
    propose_task,
    propose_group,
    start_task,
    finish_task,
    pause_task,
    approve_task,
    complete_task,
    edit_task,
    add_dependency,
    init_project,
)


@pytest.fixture
def project_canvas(tmp_path) -> Path:
    """Create a project canvas with tasks in various states."""
    data = {
        "nodes": [
            {"id": "grp1", "type": "group", "x": 0, "y": 0, "width": 400, "height": 800, "label": "Development"},
            {"id": "t1", "type": "text", "x": 20, "y": 50, "width": 280, "height": 160, "text": "## DV-01 Build API\nCreate endpoints", "color": "4"},
            {"id": "t2", "type": "text", "x": 20, "y": 250, "width": 280, "height": 160, "text": "## DV-02 Add auth\nAuthentication", "color": "1"},
            {"id": "t3", "type": "text", "x": 20, "y": 450, "width": 280, "height": 160, "text": "## DV-03 Deploy\nDeploy to prod", "color": "0"},
        ],
        "edges": [
            {"id": "e1", "fromNode": "t1", "toNode": "t2", "fromSide": "bottom", "toSide": "top"},
            {"id": "e2", "fromNode": "t2", "toNode": "t3", "fromSide": "bottom", "toSide": "top"},
        ],
        "kanvas": {"mode": "strict", "version": "1.0"},
    }
    path = tmp_path / "Project.canvas"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def relaxed_canvas(tmp_path) -> Path:
    """Create a relaxed-mode project canvas."""
    data = {
        "nodes": [
            {"id": "grp1", "type": "group", "x": 0, "y": 0, "width": 400, "height": 800, "label": "Dev"},
            {"id": "t1", "type": "text", "x": 20, "y": 50, "width": 280, "height": 160, "text": "## D-01 Task one", "color": "6"},
            {"id": "t2", "type": "text", "x": 20, "y": 250, "width": 280, "height": 160, "text": "## D-02 Task two", "color": "5"},
        ],
        "edges": [],
        "kanvas": {"mode": "relaxed", "version": "1.0"},
    }
    path = tmp_path / "Relaxed.canvas"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestReadTools:
    """Tests for read-only workflow tools."""

    def test_get_status(self, project_canvas):
        result = get_status(str(project_canvas))
        assert result.success
        assert "DV-01" in result.data
        assert "Done" in result.data or "done" in result.data.lower()

    def test_show_task(self, project_canvas):
        result = show_task(str(project_canvas), "DV-02")
        assert result.success
        assert "DV-02" in result.data
        assert "auth" in result.data.lower()

    def test_show_task_not_found(self, project_canvas):
        result = show_task(str(project_canvas), "XX-99")
        assert not result.success

    def test_get_ready_tasks(self, project_canvas):
        result = get_ready_tasks(str(project_canvas))
        assert result.success
        assert "DV-02" in result.data

    def test_get_blocked_tasks(self, project_canvas):
        result = get_blocked_tasks(str(project_canvas))
        assert result.success
        assert "DV-03" in result.data


class TestLifecycleTools:
    """Tests for task lifecycle transitions."""

    def test_start_task(self, project_canvas):
        result = start_task(str(project_canvas), "DV-02")
        assert result.success
        canvas = load_canvas(str(project_canvas))
        node = find_task_by_id(canvas, "DV-02")
        assert node.color == "2"  # orange

    def test_start_task_blocked(self, project_canvas):
        result = start_task(str(project_canvas), "DV-03")
        assert not result.success
        assert "blocked" in result.error.lower() or "dependencies" in result.error.lower()

    def test_finish_task(self, project_canvas):
        # First start, then finish
        start_task(str(project_canvas), "DV-02")
        result = finish_task(str(project_canvas), "DV-02")
        assert result.success
        canvas = load_canvas(str(project_canvas))
        node = find_task_by_id(canvas, "DV-02")
        assert node.color == "5"  # cyan

    def test_pause_task(self, project_canvas):
        start_task(str(project_canvas), "DV-02")
        result = pause_task(str(project_canvas), "DV-02")
        assert result.success
        canvas = load_canvas(str(project_canvas))
        node = find_task_by_id(canvas, "DV-02")
        assert node.color == "1"  # red

    def test_approve_strict_fails(self, project_canvas):
        # Add a purple card first
        propose_task(str(project_canvas), "Development", "New task", "Description")
        canvas = load_canvas(str(project_canvas))
        # Find the proposed task
        proposed = [n for n in canvas.nodes if n.color == "6"]
        assert len(proposed) >= 1
        task_id = find_task_by_id(canvas, proposed[0].text.split()[1]) is not None

        result = approve_task(str(project_canvas), extract_proposed_id(str(project_canvas)))
        assert not result.success

    def test_approve_relaxed_works(self, relaxed_canvas):
        result = approve_task(str(relaxed_canvas), "D-01")
        assert result.success
        canvas = load_canvas(str(relaxed_canvas))
        node = find_task_by_id(canvas, "D-01")
        assert node.color == "1"  # red

    def test_complete_relaxed_works(self, relaxed_canvas):
        result = complete_task(str(relaxed_canvas), "D-02")
        assert result.success
        canvas = load_canvas(str(relaxed_canvas))
        node = find_task_by_id(canvas, "D-02")
        assert node.color == "4"  # green


class TestEditTools:
    """Tests for task editing tools."""

    def test_edit_task_in_progress(self, project_canvas):
        start_task(str(project_canvas), "DV-02")
        result = edit_task(str(project_canvas), "DV-02", "Updated description")
        assert result.success

    def test_edit_task_not_in_progress(self, project_canvas):
        result = edit_task(str(project_canvas), "DV-02", "Should fail")
        assert not result.success

    def test_add_dependency(self, project_canvas):
        result = add_dependency(str(project_canvas), "DV-01", "DV-03")
        assert result.success  # DV-01 now also directly blocks DV-03

    def test_add_dependency_cycle(self, project_canvas):
        result = add_dependency(str(project_canvas), "DV-03", "DV-01")
        assert not result.success


class TestProposeTools:
    """Tests for task/group proposal tools."""

    def test_propose_task(self, project_canvas):
        result = propose_task(str(project_canvas), "Development", "New feature", "Build something new")
        assert result.success
        assert "DV-04" in result.data

    def test_propose_task_with_deps(self, project_canvas):
        result = propose_task(
            str(project_canvas), "Development", "Follow-up", "After auth",
            depends_on=["DV-02"],
        )
        assert result.success

    def test_propose_group(self, project_canvas):
        result = propose_group(str(project_canvas), "Testing")
        assert result.success

    def test_propose_task_nonexistent_group(self, project_canvas):
        result = propose_task(str(project_canvas), "Nonexistent", "Task", "Desc")
        assert not result.success


class TestInitProject:
    """Tests for project initialization."""

    def test_init_project(self, tmp_path):
        canvas_path = str(tmp_path / "NewProject.canvas")
        result = init_project(
            canvas_path,
            groups=["Research", "Development"],
            tasks=[
                {"group": "Research", "title": "Gather requirements", "desc": "Research needs"},
                {"group": "Development", "title": "Build MVP", "desc": "First version", "depends_on": ["Gather requirements"]},
            ],
            mode="strict",
        )
        assert result.success

        canvas = load_canvas(canvas_path)
        assert canvas.kanvas is not None
        assert canvas.kanvas.mode.value == "strict"
        groups = [n for n in canvas.nodes if n.type == "group"]
        assert len(groups) == 2
        tasks = [n for n in canvas.nodes if n.color == "6"]
        assert len(tasks) == 2

    def test_init_project_already_exists(self, project_canvas):
        result = init_project(str(project_canvas), groups=["Dev"])
        assert not result.success
        assert "already exists" in result.error.lower()


def extract_proposed_id(canvas_path: str) -> str:
    """Helper to extract the task ID of the first proposed (purple) card."""
    canvas = load_canvas(canvas_path)
    for node in canvas.nodes:
        if node.color == "6":
            from obsidian_mcp.canvas.workflow_logic import extract_task_id
            tid = extract_task_id(node.text)
            if tid:
                return tid
    return "NONE"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/canvas/test_workflow_tools.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'obsidian_mcp.canvas.workflow_tool_logic'`

- [ ] **Step 3: Implement workflow tool logic**

Create `obsidian_mcp/canvas/workflow_tool_logic.py`:

```python
"""
Logic for workflow MCP tools.

Implements project management operations: status, propose, start, finish,
approve, complete, normalize, init_project. All functions return Result[str].
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_project_canvas(canvas_path: str) -> Result[CanvasFile]:
    """Load a canvas and verify it's a project canvas (has kanvas metadata)."""
    try:
        canvas = engine.load_canvas(canvas_path)
    except FileNotFoundError:
        return Result.fail(f"Canvas file not found: {canvas_path}")
    except Exception as e:
        return Result.fail(f"Error loading canvas: {e}")

    if canvas.kanvas is None:
        return Result.fail(
            f"Not a project canvas (no 'kanvas' metadata). "
            f"Use canvas_init_project to initialize, or use generic canvas tools."
        )
    return Result.ok(canvas)


def _save(canvas: CanvasFile) -> Result[str]:
    """Save and normalize."""
    try:
        engine.save_canvas(canvas)
    except Exception as e:
        return Result.fail(f"Error saving canvas: {e}")

    # Run normalize after every write
    normalize(canvas.path)
    return Result.ok("saved")


def _get_state_label(color: str) -> str:
    """Get human-readable label for a color."""
    labels = {
        "0": "Blocked", "1": "To Do", "2": "Doing",
        "4": "Done", "5": "Review", "6": "Proposed",
    }
    return labels.get(color, "Unknown")


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------


def get_status(canvas_path: str) -> Result[str]:
    """Get a board overview: tasks by state, groups, anomalies."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    mode = get_workflow_mode(canvas)

    # Count tasks by state
    state_counts: dict[str, list[str]] = {}
    for node in canvas.nodes:
        if not is_task_card(node):
            continue
        label = _get_state_label(node.color)
        tid = extract_task_id(node.text) or node.id
        state_counts.setdefault(label, []).append(tid)

    groups = engine.find_nodes_by_type(canvas, "group")

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
        return Result.fail(load_result.error)

    canvas = load_result.data
    node = find_task_by_id(canvas, task_id)
    if node is None:
        return Result.fail(f"Task '{task_id}' not found.")

    state = _get_state_label(node.color)
    title = extract_task_title(node.text) or "(no title)"
    group = engine.find_group_for_node(canvas, node)
    group_label = group.label if group else "(none)"

    # Description: everything after the first line
    desc_lines = node.text.strip().split("\n")[1:]
    description = "\n".join(desc_lines).strip() or "(no description)"

    deps = engine.get_dependencies(canvas, node)
    dependents = engine.get_dependents(canvas, node)

    lines = [
        f"Task: {task_id} — {title}",
        f"State: {state}",
        f"Group: {group_label}",
        f"Description: {description}",
    ]

    if deps:
        dep_strs = []
        for d in deps:
            did = extract_task_id(d.text) or d.id
            dep_strs.append(f"{did} ({_get_state_label(d.color)})")
        lines.append(f"Depends on: {', '.join(dep_strs)}")

    if dependents:
        dep_strs = []
        for d in dependents:
            did = extract_task_id(d.text) or d.id
            dep_strs.append(f"{did} ({_get_state_label(d.color)})")
        lines.append(f"Blocks: {', '.join(dep_strs)}")

    return Result.ok("\n".join(lines))


def get_ready_tasks(canvas_path: str) -> Result[str]:
    """Get red tasks with all dependencies met."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    ready = []
    for node in canvas.nodes:
        if not is_task_card(node):
            continue
        if node.color != TaskState.TODO.value:
            continue
        if all_deps_green(canvas, node):
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
        return Result.fail(load_result.error)

    canvas = load_result.data
    blocked = []
    for node in canvas.nodes:
        if not is_task_card(node):
            continue
        if node.color != TaskState.BLOCKED.value:
            continue
        tid = extract_task_id(node.text) or node.id
        deps = engine.get_dependencies(canvas, node)
        unmet = [
            extract_task_id(d.text) or d.id
            for d in deps if d.color != TaskState.DONE.value
        ]
        blocked.append(f"  {tid}: blocked by {', '.join(unmet)}")

    if not blocked:
        return Result.ok("No blocked tasks.")

    return Result.ok(f"Blocked tasks ({len(blocked)}):\n" + "\n".join(blocked))


# ---------------------------------------------------------------------------
# Lifecycle operations
# ---------------------------------------------------------------------------


def _transition_task(
    canvas_path: str,
    task_id: str,
    to_state: TaskState,
    check_deps: bool = False,
) -> Result[str]:
    """Generic task state transition."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    mode = get_workflow_mode(canvas)
    node = find_task_by_id(canvas, task_id)
    if node is None:
        return Result.fail(f"Task '{task_id}' not found.")

    from_state = TaskState(node.color)
    validation = validate_transition(from_state, to_state, mode)
    if not validation.success:
        return Result.fail(validation.error)

    if check_deps and not all_deps_green(canvas, node):
        deps = engine.get_dependencies(canvas, node)
        unmet = [
            extract_task_id(d.text) or d.id
            for d in deps if d.color != TaskState.DONE.value
        ]
        return Result.fail(
            f"Cannot start '{task_id}': blocked by unmet dependencies: {', '.join(unmet)}"
        )

    node.color = to_state.value
    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    logger.info("Task %s: %s → %s", task_id, from_state.name, to_state.name)
    return Result.ok(f"Task {task_id}: {_get_state_label(from_state.value)} → {_get_state_label(to_state.value)}")


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


# ---------------------------------------------------------------------------
# Edit operations
# ---------------------------------------------------------------------------


def edit_task(canvas_path: str, task_id: str, text: str) -> Result[str]:
    """Update a task's description. Must be in-progress (orange), or also cyan in RELAXED mode."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    mode = get_workflow_mode(canvas)
    node = find_task_by_id(canvas, task_id)
    if node is None:
        return Result.fail(f"Task '{task_id}' not found.")

    allowed_states = {TaskState.DOING.value}
    if mode == WorkflowMode.RELAXED:
        allowed_states.add(TaskState.REVIEW.value)

    if node.color not in allowed_states:
        state = _get_state_label(node.color)
        return Result.fail(f"Cannot edit task '{task_id}' in state '{state}'. Must be Doing{' or Review' if mode == WorkflowMode.RELAXED else ''}.")

    # Preserve the task ID header, replace description
    tid = extract_task_id(node.text)
    title = extract_task_title(node.text) or ""
    node.text = f"## {tid} {title}\n{text}"

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    return Result.ok(f"Task {task_id} description updated.")


def add_dependency(canvas_path: str, from_task: str, to_task: str) -> Result[str]:
    """Add a dependency between two tasks. Rejects cycles."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    from_node = find_task_by_id(canvas, from_task)
    if from_node is None:
        return Result.fail(f"Task '{from_task}' not found.")
    to_node = find_task_by_id(canvas, to_task)
    if to_node is None:
        return Result.fail(f"Task '{to_task}' not found.")

    if engine.has_cycle(canvas, from_node.id, to_node.id):
        return Result.fail(f"Adding dependency {from_task} → {to_task} would create a cycle.")

    from_side, to_side = engine.pick_edge_sides(from_node, to_node)
    new_edge = Edge(
        id=engine.generate_edge_id(),
        from_node=from_node.id,
        to_node=to_node.id,
        from_side=from_side,
        to_side=to_side,
    )
    engine.add_edge(canvas, new_edge)

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    return Result.ok(f"Dependency added: {from_task} blocks {to_task}")


# ---------------------------------------------------------------------------
# Propose operations
# ---------------------------------------------------------------------------


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
        return Result.fail(load_result.error)

    canvas = load_result.data
    groups = engine.find_nodes_by_type(canvas, "group")
    group_node = next((g for g in groups if g.label == group), None)
    if group_node is None:
        return Result.fail(f"Group '{group}' not found.")

    # Determine prefix for this group
    existing_prefixes: list[str] = []
    for node in canvas.nodes:
        tid = extract_task_id(node.text)
        if tid:
            p = tid.split("-")[0]
            if p not in existing_prefixes:
                existing_prefixes.append(p)

    # Find existing prefix for this group
    group_prefix = None
    for node in canvas.nodes:
        if node.type != "text":
            continue
        if engine.find_group_for_node(canvas, node) != group_node:
            continue
        tid = extract_task_id(node.text)
        if tid:
            group_prefix = tid.split("-")[0]
            break

    if group_prefix is None:
        group_prefix = generate_group_prefix(group_node.label, existing_prefixes)

    task_id = get_next_task_id(canvas, group_prefix)

    # Resolve dependency nodes
    dep_nodes: list[Node] = []
    if depends_on:
        for dep_ref in depends_on:
            dep_node = find_task_by_id(canvas, dep_ref)
            if dep_node is None:
                return Result.fail(f"Dependency '{dep_ref}' not found.")
            dep_nodes.append(dep_node)

    x, y = engine.compute_node_placement(canvas, group_node, dep_nodes)
    new_node = Node(
        id=engine.generate_node_id(),
        type="text",
        x=x, y=y,
        width=280, height=160,
        text=f"## {task_id} {title}\n{description}",
        color=TaskState.PROPOSED.value,
    )
    engine.add_node(canvas, new_node)

    # Add dependency edges
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

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    logger.info("Proposed task %s in group '%s'", task_id, group)
    return Result.ok(f"Proposed task: {task_id} — {title}")


def propose_group(canvas_path: str, label: str) -> Result[str]:
    """Propose a new group for the project canvas."""
    load_result = _load_project_canvas(canvas_path)
    if not load_result.success:
        return Result.fail(load_result.error)

    canvas = load_result.data
    existing = engine.find_nodes_by_type(canvas, "group")
    x = 0
    if existing:
        rightmost = max(existing, key=lambda g: g.x + g.width)
        x = rightmost.x + rightmost.width + 50

    new_group = Node(
        id=engine.generate_node_id(),
        type="group",
        x=x, y=0,
        width=400, height=800,
        label=label,
    )
    engine.add_node(canvas, new_group)

    save_result = _save(canvas)
    if not save_result.success:
        return save_result

    logger.info("Proposed group '%s'", label)
    return Result.ok(f"Group added: {label}")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


_LEGEND_TEXT = """# Legend
| Color | State |
|-------|-------|
| Purple | Proposed |
| Red | To Do |
| Orange | Doing |
| Cyan | Review |
| Green | Done |
| Gray | Blocked |"""


def init_project(
    canvas_path: str,
    groups: list[str],
    tasks: list[dict] | None = None,
    mode: str = "strict",
) -> Result[str]:
    """Initialize a new project canvas with groups, legend, and optional tasks.

    Args:
        canvas_path: Where to create the .canvas file.
        groups: List of group labels.
        tasks: Optional list of dicts with keys: group, title, desc, depends_on (list of titles).
        mode: Workflow mode ("strict" or "relaxed").
    """
    if Path(canvas_path).exists():
        return Result.fail(f"Canvas already exists: {canvas_path}")

    # Ensure parent directory exists
    Path(canvas_path).parent.mkdir(parents=True, exist_ok=True)

    workflow_mode = WorkflowMode(mode)
    canvas = CanvasFile(
        path=canvas_path,
        nodes=[],
        edges=[],
        kanvas=KanvasMetadata(mode=workflow_mode),
    )

    # Create groups side by side
    group_nodes: dict[str, Node] = {}
    for i, label in enumerate(groups):
        group_node = Node(
            id=engine.generate_node_id(),
            type="group",
            x=i * 450, y=0,
            width=400, height=800,
            label=label,
        )
        engine.add_node(canvas, group_node)
        group_nodes[label] = group_node

    # Add legend to the right
    legend_x = len(groups) * 450
    legend_node = Node(
        id="legend",
        type="text",
        x=legend_x, y=0,
        width=220, height=300,
        text=_LEGEND_TEXT,
        color="0",
    )
    engine.add_node(canvas, legend_node)

    # Build prefix map
    existing_prefixes: list[str] = []
    group_prefix_map: dict[str, str] = {}
    for label in groups:
        prefix = generate_group_prefix(label, existing_prefixes)
        group_prefix_map[label] = prefix
        existing_prefixes.append(prefix)

    # Create tasks
    title_to_node: dict[str, Node] = {}
    if tasks:
        for task_def in tasks:
            group_label = task_def["group"]
            if group_label not in group_nodes:
                return Result.fail(f"Group '{group_label}' not in groups list.")

            prefix = group_prefix_map[group_label]
            task_id = get_next_task_id(canvas, prefix)
            title = task_def["title"]
            desc = task_def.get("desc", "")

            group_node = group_nodes[group_label]
            dep_nodes = []
            for dep_title in task_def.get("depends_on", []):
                dep_title_lower = dep_title.lower()
                dep_node = title_to_node.get(dep_title_lower)
                if dep_node is None:
                    return Result.fail(f"Dependency '{dep_title}' not found (must reference an earlier task title).")
                dep_nodes.append(dep_node)

            x, y = engine.compute_node_placement(canvas, group_node, dep_nodes)
            new_node = Node(
                id=engine.generate_node_id(),
                type="text",
                x=x, y=y,
                width=280, height=160,
                text=f"## {task_id} {title}\n{desc}",
                color=TaskState.PROPOSED.value,
            )
            engine.add_node(canvas, new_node)
            title_to_node[title.lower()] = new_node

            # Add dependency edges
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

    engine.save_canvas(canvas)
    logger.info("Initialized project canvas at %s with %d groups", canvas_path, len(groups))

    task_count = len(tasks) if tasks else 0
    return Result.ok(
        f"Project canvas created: {canvas_path}\n"
        f"Groups: {', '.join(groups)}\n"
        f"Tasks: {task_count} proposed\n"
        f"Mode: {mode}"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/canvas/test_workflow_tools.py -v
```

Expected: All tests PASS. Some tests may need minor adjustments based on exact output format — fix any that fail.

- [ ] **Step 5: Commit**

```bash
git add obsidian_mcp/canvas/workflow_tool_logic.py tests/canvas/test_workflow_tools.py
git commit -m "feat(canvas): add workflow tool logic with lifecycle, propose, and init_project"
```

---

### Task 7: Workflow MCP tool registration

**Files:**
- Create: `obsidian_mcp/canvas/workflow_tools.py`

- [ ] **Step 1: Implement workflow tool registration**

Create `obsidian_mcp/canvas/workflow_tools.py`:

```python
"""
Workflow MCP tools for Kanvas-style project management.

These tools implement the project management workflow on top of Obsidian Canvas:
color-coded task states, dependency tracking, and configurable agent permissions.
"""

from fastmcp import FastMCP

from ..utils import get_logger
from .workflow_logic import normalize
from .workflow_tool_logic import (
    add_dependency,
    approve_task,
    complete_task,
    edit_task,
    finish_task,
    get_blocked_tasks,
    get_ready_tasks,
    get_status,
    init_project,
    pause_task,
    propose_group,
    propose_task,
    show_task,
    start_task,
)

logger = get_logger(__name__)


def register_workflow_tools(mcp: FastMCP) -> None:
    """Register Kanvas workflow tools with the MCP server."""

    # --- Bootstrap ---

    @mcp.tool()
    def canvas_init_project(
        canvas_path: str,
        groups: list[str],
        tasks: list[dict] | None = None,
        mode: str = "strict",
    ) -> str:
        """Create a new project canvas with groups, legend, and optional tasks.

        All tasks are created as purple (proposed) cards. The user reviews
        in Obsidian and approves by setting cards to red.

        Args:
            canvas_path: Path for the new .canvas file (relative to vault or absolute)
            groups: List of group names (e.g., ["Research", "Development", "Testing"])
            tasks: Optional list of task dicts with keys: group, title, desc, depends_on (list of earlier task titles)
            mode: Workflow mode — "strict" (default) or "relaxed"

        Returns:
            Summary of created canvas
        """
        try:
            return init_project(canvas_path, groups, tasks, mode).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error initializing project: {e}"

    # --- Read ---

    @mcp.tool()
    def canvas_status(canvas_path: str) -> str:
        """Get a board overview: tasks grouped by state, groups, and workflow mode.

        Args:
            canvas_path: Path to the project .canvas file

        Returns:
            Board status summary
        """
        try:
            return get_status(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading status: {e}"

    @mcp.tool()
    def canvas_show_task(canvas_path: str, task_id: str) -> str:
        """Show full details for a task: description, state, dependencies, and dependents.

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")

        Returns:
            Task detail summary
        """
        try:
            return show_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error showing task: {e}"

    @mcp.tool()
    def canvas_ready_tasks(canvas_path: str) -> str:
        """List red (To Do) tasks that have all dependencies met and are ready to start.

        Args:
            canvas_path: Path to the project .canvas file

        Returns:
            List of ready tasks
        """
        try:
            return get_ready_tasks(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error getting ready tasks: {e}"

    @mcp.tool()
    def canvas_blocked_tasks(canvas_path: str) -> str:
        """List gray (Blocked) tasks and which dependencies are blocking them.

        Args:
            canvas_path: Path to the project .canvas file

        Returns:
            List of blocked tasks with their blockers
        """
        try:
            return get_blocked_tasks(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error getting blocked tasks: {e}"

    # --- Lifecycle ---

    @mcp.tool()
    def canvas_propose_task(
        canvas_path: str,
        group: str,
        title: str,
        description: str,
        depends_on: list[str] | None = None,
    ) -> str:
        """Propose a new task (creates a purple card). Auto-assigns a task ID.

        Args:
            canvas_path: Path to the project .canvas file
            group: Name of the group to place the task in
            title: Task title
            description: Task description
            depends_on: Optional list of task IDs this task depends on

        Returns:
            Confirmation with the assigned task ID
        """
        try:
            return propose_task(canvas_path, group, title, description, depends_on).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error proposing task: {e}"

    @mcp.tool()
    def canvas_propose_group(canvas_path: str, label: str) -> str:
        """Add a new group to the project canvas.

        Args:
            canvas_path: Path to the project .canvas file
            label: Group label

        Returns:
            Confirmation
        """
        try:
            return propose_group(canvas_path, label).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error proposing group: {e}"

    @mcp.tool()
    def canvas_start_task(canvas_path: str, task_id: str) -> str:
        """Start working on a task: To Do (red) → Doing (orange).

        Validates that all dependencies are green (Done) before allowing the transition.

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")

        Returns:
            Confirmation of state change
        """
        try:
            return start_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error starting task: {e}"

    @mcp.tool()
    def canvas_finish_task(canvas_path: str, task_id: str) -> str:
        """Finish a task and submit for review: Doing (orange) → Review (cyan).

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")

        Returns:
            Confirmation of state change
        """
        try:
            return finish_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error finishing task: {e}"

    @mcp.tool()
    def canvas_pause_task(canvas_path: str, task_id: str) -> str:
        """Pause a task: Doing (orange) → To Do (red).

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")

        Returns:
            Confirmation of state change
        """
        try:
            return pause_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error pausing task: {e}"

    @mcp.tool()
    def canvas_approve_task(canvas_path: str, task_id: str) -> str:
        """Approve a proposed task: Proposed (purple) → To Do (red). RELAXED mode only.

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")

        Returns:
            Confirmation of state change
        """
        try:
            return approve_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error approving task: {e}"

    @mcp.tool()
    def canvas_complete_task(canvas_path: str, task_id: str) -> str:
        """Mark a task as done: Review (cyan) → Done (green). RELAXED mode only.

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")

        Returns:
            Confirmation of state change
        """
        try:
            return complete_task(canvas_path, task_id).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error completing task: {e}"

    # --- Edit ---

    @mcp.tool()
    def canvas_edit_task(canvas_path: str, task_id: str, text: str) -> str:
        """Update a task's description. Task must be in Doing state (orange).
        In RELAXED mode, Review (cyan) tasks can also be edited.

        Args:
            canvas_path: Path to the project .canvas file
            task_id: Task ID (e.g., "DV-01")
            text: New description text (replaces existing description, preserves title)

        Returns:
            Confirmation of update
        """
        try:
            return edit_task(canvas_path, task_id, text).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error editing task: {e}"

    @mcp.tool()
    def canvas_add_dependency(canvas_path: str, from_task: str, to_task: str) -> str:
        """Add a dependency between two tasks. Rejects if it would create a cycle.

        The from_task must be completed (green) before to_task can be started.

        Args:
            canvas_path: Path to the project .canvas file
            from_task: Task ID of the blocker (e.g., "DV-01")
            to_task: Task ID of the blocked task (e.g., "DV-02")

        Returns:
            Confirmation of dependency
        """
        try:
            return add_dependency(canvas_path, from_task, to_task).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error adding dependency: {e}"

    # --- Maintenance ---

    @mcp.tool()
    def canvas_normalize(canvas_path: str) -> str:
        """Normalize the project canvas: assign task IDs to untagged cards and update blocked states.

        This runs automatically on every workflow write operation, but can be called
        explicitly after manual edits in Obsidian.

        Args:
            canvas_path: Path to the project .canvas file

        Returns:
            Summary of changes made
        """
        try:
            return normalize(canvas_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error normalizing canvas: {e}"
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from obsidian_mcp.canvas.workflow_tools import register_workflow_tools; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add obsidian_mcp/canvas/workflow_tools.py
git commit -m "feat(canvas): add 16 workflow MCP tools"
```

---

### Task 8: Server registration and final integration

**Files:**
- Modify: `obsidian_mcp/tools/__init__.py`
- Modify: `obsidian_mcp/server.py`
- Update: `obsidian_mcp/canvas/__init__.py`

- [ ] **Step 1: Update canvas `__init__.py` with tool registration exports**

Update `obsidian_mcp/canvas/__init__.py` to add:

```python
from .canvas_tools import register_canvas_tools
from .workflow_tools import register_workflow_tools
```

And add them to `__all__`.

- [ ] **Step 2: Update `tools/__init__.py`**

Read the current file, then add the canvas imports:

```python
from ..canvas import register_canvas_tools, register_workflow_tools
```

And add to `__all__`:

```python
"register_canvas_tools",
"register_workflow_tools",
```

- [ ] **Step 3: Update `server.py`**

Read the current `create_server()` function. Add these lines after the existing tool registrations:

```python
logger.info("Registering canvas tools...")
register_canvas_tools(mcp)

logger.info("Registering workflow tools...")
register_workflow_tools(mcp)
```

- [ ] **Step 4: Run full test suite**

```bash
python -m pytest tests/canvas/ -v
```

Expected: All canvas tests PASS.

- [ ] **Step 5: Verify server starts**

```bash
python -c "
from obsidian_mcp.server import create_server
server = create_server()
print('Server created OK')
print(f'Tools registered: {len(server._tool_manager._tools)}')
"
```

Expected: Server creates without error, tool count increases by 24 (8 generic + 16 workflow).

- [ ] **Step 6: Commit**

```bash
git add obsidian_mcp/canvas/__init__.py obsidian_mcp/tools/__init__.py obsidian_mcp/server.py
git commit -m "feat(canvas): register canvas and workflow tools in MCP server"
```

---

### Task 9: End-to-end integration test

**Files:**
- Create: `tests/canvas/test_integration.py`

- [ ] **Step 1: Write integration test**

Create `tests/canvas/test_integration.py`:

```python
"""End-to-end integration test for the canvas workflow."""

import json
import pytest
from pathlib import Path

from obsidian_mcp.canvas.engine import load_canvas
from obsidian_mcp.canvas.workflow_logic import extract_task_id, find_task_by_id
from obsidian_mcp.canvas.workflow_tool_logic import (
    approve_task,
    complete_task,
    finish_task,
    get_blocked_tasks,
    get_ready_tasks,
    get_status,
    init_project,
    propose_task,
    start_task,
)


class TestFullWorkflow:
    """Test the complete project lifecycle from init to done."""

    def test_strict_workflow(self, tmp_path):
        """Test full strict workflow: init → propose → start → finish."""
        canvas_path = str(tmp_path / "project.canvas")

        # 1. Init project
        result = init_project(canvas_path, groups=["Backend", "Frontend"])
        assert result.success

        # 2. Check status
        result = get_status(canvas_path)
        assert result.success
        assert "Backend" in result.data

        # 3. Propose tasks
        result = propose_task(canvas_path, "Backend", "Setup database", "Create schema and migrations")
        assert result.success
        assert "B-01" in result.data

        result = propose_task(
            canvas_path, "Backend", "Build API", "REST endpoints",
            depends_on=["B-01"],
        )
        assert result.success
        assert "B-02" in result.data

        # 4. Simulate human approving tasks (set color to red directly)
        canvas = load_canvas(canvas_path)
        for node in canvas.nodes:
            if node.color == "6":  # purple → red
                node.color = "1"
        from obsidian_mcp.canvas.engine import save_canvas
        save_canvas(canvas)

        # 5. Normalize to update blocked states
        from obsidian_mcp.canvas.workflow_logic import normalize
        normalize(canvas_path)

        # 6. Check ready tasks — B-01 should be ready, B-02 blocked
        result = get_ready_tasks(canvas_path)
        assert result.success
        assert "B-01" in result.data

        result = get_blocked_tasks(canvas_path)
        assert result.success
        assert "B-02" in result.data

        # 7. Start B-01
        result = start_task(canvas_path, "B-01")
        assert result.success

        # 8. Finish B-01
        result = finish_task(canvas_path, "B-01")
        assert result.success

        # 9. Simulate human marking B-01 as done
        canvas = load_canvas(canvas_path)
        node = find_task_by_id(canvas, "B-01")
        node.color = "4"  # green
        save_canvas(canvas)
        normalize(canvas_path)

        # 10. B-02 should now be ready
        result = get_ready_tasks(canvas_path)
        assert result.success
        assert "B-02" in result.data

    def test_relaxed_workflow(self, tmp_path):
        """Test relaxed workflow: agent can approve and complete."""
        canvas_path = str(tmp_path / "project.canvas")

        # Init in relaxed mode
        result = init_project(
            canvas_path, groups=["Dev"],
            tasks=[{"group": "Dev", "title": "Quick task", "desc": "Do it fast"}],
            mode="relaxed",
        )
        assert result.success

        # Agent approves
        result = approve_task(canvas_path, "D-01")
        assert result.success

        # Agent starts
        result = start_task(canvas_path, "D-01")
        assert result.success

        # Agent finishes
        result = finish_task(canvas_path, "D-01")
        assert result.success

        # Agent marks done
        result = complete_task(canvas_path, "D-01")
        assert result.success

        # Verify final state
        canvas = load_canvas(canvas_path)
        node = find_task_by_id(canvas, "D-01")
        assert node.color == "4"  # green
```

- [ ] **Step 2: Run integration tests**

```bash
python -m pytest tests/canvas/test_integration.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: All tests PASS, including existing tests (no regressions).

- [ ] **Step 4: Commit**

```bash
git add tests/canvas/test_integration.py
git commit -m "test(canvas): add end-to-end integration tests for workflow lifecycle"
```

---

### Task 10: Final cleanup and documentation

**Files:**
- Modify: `obsidian_mcp/canvas/__init__.py` (final exports)
- Modify: `docs/superpowers/specs/2026-03-28-canvas-integration-design.md` (mark as implemented)

- [ ] **Step 1: Finalize canvas `__init__.py` exports**

Ensure all public APIs are exported. Read the current file and verify completeness.

- [ ] **Step 2: Run linting**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
ruff check obsidian_mcp/canvas/ --fix
ruff format obsidian_mcp/canvas/
ruff check tests/canvas/ --fix
ruff format tests/canvas/
```

Fix any issues.

- [ ] **Step 3: Run full test suite one final time**

```bash
python -m pytest tests/canvas/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 4: Update spec status**

Edit `docs/superpowers/specs/2026-03-28-canvas-integration-design.md`:

Change `**Status:** Draft` to `**Status:** Implemented`

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(canvas): finalize canvas integration module

Complete implementation of canvas management tools:
- 8 generic canvas CRUD tools
- 16 workflow project management tools
- Engine with I/O, queries, mutations, placement
- State machine with strict/relaxed modes
- Normalize with auto-ID and blocked state management
- Full test coverage with integration tests"
```
