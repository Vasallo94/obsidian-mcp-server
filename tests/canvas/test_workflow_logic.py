"""Tests for canvas workflow logic."""

import json

from obsidian_mcp.canvas.models import (
    CanvasFile,
    Node,
    TaskState,
    WorkflowMode,
)
from obsidian_mcp.canvas.workflow_logic import (
    all_deps_green,
    extract_task_id,
    extract_task_title,
    generate_group_prefix,
    get_next_task_id,
    get_workflow_mode,
    is_task_card,
    normalize,
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
        assert (
            extract_task_title("## DV-01 Build feature\nDescription") == "Build feature"
        )

    def test_is_task_card_true(self):
        node = Node(
            id="t1",
            type="text",
            x=0,
            y=0,
            width=280,
            height=160,
            text="## DV-01 Task",
            color="1",
        )
        assert is_task_card(node) is True

    def test_is_task_card_false_legend(self):
        node = Node(
            id="legend",
            type="text",
            x=0,
            y=0,
            width=200,
            height=300,
            text="# Legend",
            color="0",
        )
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
                {
                    "id": "grp",
                    "type": "group",
                    "x": 0,
                    "y": 0,
                    "width": 400,
                    "height": 800,
                    "label": "Development",
                },
                {
                    "id": "card1",
                    "type": "text",
                    "x": 20,
                    "y": 50,
                    "width": 280,
                    "height": 160,
                    "text": "Build feature\nDescription",
                    "color": "1",
                },
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
                {
                    "id": "grp",
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
                    "text": "## D-01 Done task",
                    "color": "4",
                },
                {
                    "id": "t2",
                    "type": "text",
                    "x": 20,
                    "y": 250,
                    "width": 280,
                    "height": 160,
                    "text": "## D-02 Blocked task",
                    "color": "0",
                },
                {
                    "id": "t3",
                    "type": "text",
                    "x": 20,
                    "y": 450,
                    "width": 280,
                    "height": 160,
                    "text": "## D-03 Should block",
                    "color": "1",
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
                {
                    "id": "legend",
                    "type": "text",
                    "x": 900,
                    "y": 0,
                    "width": 200,
                    "height": 300,
                    "text": "# Legend\nInfo",
                    "color": "0",
                },
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
        result = validate_transition(
            TaskState.TODO, TaskState.DOING, WorkflowMode.STRICT
        )
        assert result.success

    def test_finish_valid(self):
        result = validate_transition(
            TaskState.DOING, TaskState.REVIEW, WorkflowMode.STRICT
        )
        assert result.success

    def test_pause_valid(self):
        result = validate_transition(
            TaskState.DOING, TaskState.TODO, WorkflowMode.STRICT
        )
        assert result.success

    def test_approve_strict_rejected(self):
        result = validate_transition(
            TaskState.PROPOSED, TaskState.TODO, WorkflowMode.STRICT
        )
        assert not result.success

    def test_approve_relaxed_allowed(self):
        result = validate_transition(
            TaskState.PROPOSED, TaskState.TODO, WorkflowMode.RELAXED
        )
        assert result.success

    def test_complete_strict_rejected(self):
        result = validate_transition(
            TaskState.REVIEW, TaskState.DONE, WorkflowMode.STRICT
        )
        assert not result.success

    def test_complete_relaxed_allowed(self):
        result = validate_transition(
            TaskState.REVIEW, TaskState.DONE, WorkflowMode.RELAXED
        )
        assert result.success

    def test_invalid_transition(self):
        result = validate_transition(
            TaskState.TODO, TaskState.REVIEW, WorkflowMode.RELAXED
        )
        assert not result.success


class TestGetWorkflowMode:
    """Tests for reading workflow mode from canvas."""

    def test_strict_mode(self, sample_canvas_file):
        assert get_workflow_mode(sample_canvas_file) == WorkflowMode.STRICT

    def test_no_kanvas_metadata(self):
        canvas = CanvasFile(path="/tmp/t.canvas", nodes=[], edges=[])
        assert get_workflow_mode(canvas) == WorkflowMode.STRICT  # default
