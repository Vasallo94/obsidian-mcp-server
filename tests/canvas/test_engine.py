"""Tests for canvas engine — I/O and queries."""

import json
from pathlib import Path

import pytest

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
            path=path,
            nodes=[],
            edges=[],
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
        new_node = Node(
            id="new1", type="text", x=0, y=0, width=280, height=160, text="New card"
        )
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
        edge_ids = [e.id for e in sample_canvas_file.edges]
        assert "e1" not in edge_ids  # t1 → t2
        assert "e3" not in edge_ids  # t2 → t3
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
