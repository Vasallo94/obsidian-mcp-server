"""Integration tests for workflow tool logic (called via workflow_tools helpers)."""

import json
from pathlib import Path

import pytest

from obsidian_mcp.canvas.engine import load_canvas
from obsidian_mcp.canvas.workflow_logic import (
    find_task_by_id,
)
from obsidian_mcp.canvas.workflow_tool_logic import (
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


@pytest.fixture
def project_canvas(tmp_path) -> Path:
    """Create a project canvas with tasks in various states."""
    data = {
        "nodes": [
            {
                "id": "grp1",
                "type": "group",
                "x": 0,
                "y": 0,
                "width": 400,
                "height": 800,
                "label": "Development",
            },
            {
                "id": "t1",
                "type": "text",
                "x": 20,
                "y": 50,
                "width": 280,
                "height": 160,
                "text": "## DV-01 Build API\nCreate endpoints",
                "color": "4",
            },
            {
                "id": "t2",
                "type": "text",
                "x": 20,
                "y": 250,
                "width": 280,
                "height": 160,
                "text": "## DV-02 Add auth\nAuthentication",
                "color": "1",
            },
            {
                "id": "t3",
                "type": "text",
                "x": 20,
                "y": 450,
                "width": 280,
                "height": 160,
                "text": "## DV-03 Deploy\nDeploy to prod",
                "color": "0",
            },
        ],
        "edges": [
            {
                "id": "e1",
                "fromNode": "t1",
                "toNode": "t2",
                "fromSide": "bottom",
                "toSide": "top",
            },
            {
                "id": "e2",
                "fromNode": "t2",
                "toNode": "t3",
                "fromSide": "bottom",
                "toSide": "top",
            },
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
            {
                "id": "grp1",
                "type": "group",
                "x": 0,
                "y": 0,
                "width": 400,
                "height": 800,
                "label": "Dev",
            },
            {
                "id": "t1",
                "type": "text",
                "x": 20,
                "y": 50,
                "width": 280,
                "height": 160,
                "text": "## D-01 Task one",
                "color": "6",
            },
            {
                "id": "t2",
                "type": "text",
                "x": 20,
                "y": 250,
                "width": 280,
                "height": 160,
                "text": "## D-02 Task two",
                "color": "5",
            },
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
        assert (
            "blocked" in result.error.lower() or "dependencies" in result.error.lower()
        )

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
        result = approve_task(
            str(project_canvas), extract_proposed_id(str(project_canvas))
        )
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
        result = propose_task(
            str(project_canvas), "Development", "New feature", "Build something new"
        )
        assert result.success
        assert "DV-04" in result.data

    def test_propose_task_with_deps(self, project_canvas):
        result = propose_task(
            str(project_canvas),
            "Development",
            "Follow-up",
            "After auth",
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
                {
                    "group": "Research",
                    "title": "Gather requirements",
                    "desc": "Research needs",
                },
                {
                    "group": "Development",
                    "title": "Build MVP",
                    "desc": "First version",
                    "depends_on": ["Gather requirements"],
                },
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
