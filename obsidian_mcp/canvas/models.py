"""
Data models for Obsidian Canvas files.

Defines the core structures used to represent canvas elements (nodes, edges),
canvas files, and the Kanvas workflow metadata (task states, workflow modes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import ClassVar, Optional


class TaskState(str, Enum):
    """Color-coded task states for the Kanvas workflow."""

    BLOCKED = "0"  # gray
    TODO = "1"  # red
    DOING = "2"  # orange
    DONE = "4"  # green
    REVIEW = "5"  # cyan
    PROPOSED = "6"  # purple


class WorkflowMode(str, Enum):
    """Agent permission level for workflow operations."""

    STRICT = "strict"  # agent can't approve/complete
    RELAXED = "relaxed"  # agent can approve and complete


# Regex to extract task ID from card text: "## XX-NN Title"
TASK_ID_RE = re.compile(r"^##\s+([A-Z]{1,3})-(\d{2})\s+(.*)$", re.MULTILINE)


@dataclass
class Node:  # pylint: disable=too-many-instance-attributes
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
    _OPTIONAL_FIELDS: ClassVar[set[str]] = {"text", "label", "color", "file", "url"}

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

    _OPTIONAL_FIELDS: ClassVar[set[str]] = {"label"}

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
        """Serialize to dict format."""
        return {"mode": self.mode.value, "version": self.version}

    @classmethod
    def from_dict(cls, data: dict) -> KanvasMetadata:
        """Deserialize from dict format."""
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
