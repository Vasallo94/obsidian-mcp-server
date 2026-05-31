"""End-to-end integration tests for canvas and workflow tools.

Exercises the full stack from MCP tool registration through to file I/O,
calling logic functions directly without going through the MCP protocol.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from obsidian_mcp.canvas.canvas_logic import add_card, read_canvas
from obsidian_mcp.canvas.workflow_tool_logic import (
    approve_task,
    complete_task,
    finish_task,
    get_status,
    init_project,
    propose_task,
    start_task,
)


class TestProjectLifecycle:
    """End-to-end tests for project canvas lifecycle operations."""

    def test_init_and_read(self, tmp_path):
        """Init a project canvas and verify it can be read back."""
        canvas_path = str(tmp_path / "project.canvas")
        result = init_project(canvas_path, groups=["Planning", "Dev"], mode="relaxed")

        assert result.success is True
        assert Path(canvas_path).exists()

        status_result = get_status(canvas_path)
        assert status_result.success is True
        assert "Mode: relaxed" in status_result.data

    def test_propose_and_approve_task(self, tmp_path):
        """Propose a task then approve it, verifying state transitions."""
        canvas_path = str(tmp_path / "project.canvas")
        init_project(canvas_path, groups=["Planning", "Dev"], mode="relaxed")

        propose_result = propose_task(
            canvas_path,
            group="Planning",
            title="Research",
            description="Do research",
        )
        assert propose_result.success is True
        assert "Proposed task:" in propose_result.data

        # Extract task ID: split on ": " then on " —" → first part
        task_id = propose_result.data.split(": ")[1].split(" —")[0]

        approve_result = approve_task(canvas_path, task_id)
        assert approve_result.success is True
        assert "→ To Do" in approve_result.data

    def test_start_finish_complete_cycle(self, tmp_path):
        """Full task lifecycle: propose → approve → start → finish → complete."""
        canvas_path = str(tmp_path / "project.canvas")
        init_project(canvas_path, groups=["Planning", "Dev"], mode="relaxed")

        propose_result = propose_task(
            canvas_path,
            group="Planning",
            title="Build feature",
            description="Implement the feature",
        )
        task_id = propose_result.data.split(": ")[1].split(" —")[0]

        approve_result = approve_task(canvas_path, task_id)
        assert approve_result.success is True

        start_result = start_task(canvas_path, task_id)
        assert start_result.success is True
        assert "→ Doing" in start_result.data

        finish_result = finish_task(canvas_path, task_id)
        assert finish_result.success is True
        assert "→ Review" in finish_result.data

        complete_result = complete_task(canvas_path, task_id)
        assert complete_result.success is True
        assert "→ Done" in complete_result.data

    def test_canvas_crud(self, tmp_path):
        """Add a card to a generic canvas and read it back."""
        canvas_path = tmp_path / "generic.canvas"
        canvas_path.write_text(json.dumps({"nodes": [], "edges": []}), encoding="utf-8")

        add_result = add_card(str(canvas_path), "Hello world")
        assert add_result.success is True

        read_result = read_canvas(str(canvas_path))
        assert read_result.success is True

    def test_server_has_canvas_tools(self, monkeypatch):
        """Verify the MCP server registers all expected canvas and kanvas tools."""
        from obsidian_mcp.server import create_server

        monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "canvas,kanvas")
        with patch(
            "obsidian_mcp.server.validate_configuration", return_value=(True, "")
        ):
            mcp = create_server()

        tool_names = [t.name for t in asyncio.run(mcp.list_tools())]

        canvas_tools = [
            "canvas.read",
            "canvas.list",
            "canvas.add_card",
            "canvas.add_group",
            "canvas.add_edge",
            "canvas.update_card",
            "canvas.remove_card",
            "canvas.remove_edge",
        ]
        for tool in canvas_tools:
            assert tool in tool_names, f"Missing canvas tool: {tool}"

        kanvas_tools = [
            "kanvas.status",
            "kanvas.task",
            "kanvas.ready",
            "kanvas.blocked",
            "kanvas.start",
            "kanvas.finish",
            "kanvas.pause",
            "kanvas.approve",
            "kanvas.complete",
            "kanvas.edit_task",
            "kanvas.add_dependency",
            "kanvas.propose_task",
            "kanvas.propose_group",
            "kanvas.init",
        ]
        for tool in kanvas_tools:
            assert tool in tool_names, f"Missing kanvas tool: {tool}"
