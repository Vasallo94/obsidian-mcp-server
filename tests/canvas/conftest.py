"""Shared fixtures for canvas tests."""

import json
from pathlib import Path

import pytest

from obsidian_mcp.canvas.models import (
    CanvasFile,
)

SAMPLE_CANVAS_DATA = {
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
            "id": "grp2",
            "type": "group",
            "x": 450,
            "y": 0,
            "width": 400,
            "height": 800,
            "label": "Testing",
        },
        {
            "id": "t1",
            "type": "text",
            "x": 20,
            "y": 50,
            "width": 280,
            "height": 160,
            "text": "## DV-01 Build API\nCreate REST endpoints",
            "color": "4",
        },
        {
            "id": "t2",
            "type": "text",
            "x": 20,
            "y": 250,
            "width": 280,
            "height": 160,
            "text": "## DV-02 Add auth\nAdd authentication",
            "color": "1",
        },
        {
            "id": "t3",
            "type": "text",
            "x": 470,
            "y": 50,
            "width": 280,
            "height": 160,
            "text": "## TS-01 Write tests\nUnit tests for API",
            "color": "0",
        },
        {
            "id": "t4",
            "type": "text",
            "x": 20,
            "y": 450,
            "width": 280,
            "height": 160,
            "text": "## DV-03 Refactor\nClean up code",
            "color": "6",
        },
        {
            "id": "legend",
            "type": "text",
            "x": 900,
            "y": 0,
            "width": 200,
            "height": 300,
            "text": "# Legend\nColors mean things",
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
            "fromNode": "t1",
            "toNode": "t3",
            "fromSide": "right",
            "toSide": "left",
        },
        {
            "id": "e3",
            "fromNode": "t2",
            "toNode": "t3",
            "fromSide": "right",
            "toSide": "left",
        },
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
