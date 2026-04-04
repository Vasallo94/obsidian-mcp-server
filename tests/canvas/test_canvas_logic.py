"""Tests for generic canvas tool logic."""

import json
from unittest.mock import patch

from obsidian_mcp.canvas.canvas_logic import (
    add_canvas_edge,
    add_card,
    add_group,
    list_canvases,
    read_canvas,
    remove_canvas_edge,
    remove_card,
    update_card,
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
        with patch(
            "obsidian_mcp.canvas.canvas_logic.get_vault_path", return_value=tmp_path
        ):
            result = list_canvases("")
        assert result.success
        assert "a.canvas" in result.data
        assert "b.canvas" in result.data
        assert "not_canvas" not in result.data

    def test_list_canvases_subfolder(self, tmp_path):
        sub = tmp_path / "Projects"
        sub.mkdir()
        (sub / "proj.canvas").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")
        with patch(
            "obsidian_mcp.canvas.canvas_logic.get_vault_path", return_value=tmp_path
        ):
            result = list_canvases("Projects")
        assert result.success
        assert "proj.canvas" in result.data

    def test_list_canvases_no_vault(self):
        with patch(
            "obsidian_mcp.canvas.canvas_logic.get_vault_path", return_value=None
        ):
            result = list_canvases("")
        assert not result.success


class TestAddCard:
    """Tests for canvas_add_card logic."""

    def test_add_card(self, tmp_canvas):
        result = add_card(str(tmp_canvas), "New card text")
        assert result.success
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
