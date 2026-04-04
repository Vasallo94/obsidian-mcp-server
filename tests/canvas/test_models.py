"""Tests for canvas data models."""

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
        data = {
            "id": "b",
            "type": "text",
            "x": 0,
            "y": 0,
            "width": 280,
            "height": 160,
            "text": "hello",
            "color": "2",
        }
        node = Node.from_dict(data)
        assert node.id == "b"
        assert node.color == "2"
        assert node.text == "hello"

    def test_node_from_dict_missing_optional(self):
        data = {
            "id": "c",
            "type": "group",
            "x": 0,
            "y": 0,
            "width": 400,
            "height": 600,
            "label": "Testing",
        }
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
        edge = Edge(
            id="e1", from_node="a", to_node="b", from_side="right", to_side="left"
        )
        d = edge.to_dict()
        assert d["fromNode"] == "a"
        assert d["toNode"] == "b"
        assert d["fromSide"] == "right"

    def test_edge_from_dict(self):
        data = {
            "id": "e2",
            "fromNode": "x",
            "toNode": "y",
            "fromSide": "bottom",
            "toSide": "top",
        }
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
                {
                    "id": "n1",
                    "type": "text",
                    "x": 0,
                    "y": 0,
                    "width": 280,
                    "height": 160,
                    "text": "hello",
                }
            ],
            "edges": [
                {
                    "id": "e1",
                    "fromNode": "n1",
                    "toNode": "n2",
                    "fromSide": "bottom",
                    "toSide": "top",
                }
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
