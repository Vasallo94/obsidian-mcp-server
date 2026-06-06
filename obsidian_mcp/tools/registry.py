"""Tool registry metadata and opt-in tool set handling."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from fastmcp import FastMCP

from ..config import get_vault_path
from ..vault_config import get_vault_config

CORE_TOOL_SET = "core"


@dataclass(frozen=True)
class ToolSpec:
    """MCP metadata for a registered tool."""

    title: str
    tool_set: str = CORE_TOOL_SET
    read_only: bool = True
    destructive: bool = False
    idempotent: bool = True
    open_world: bool = False

    def annotations(self) -> dict[str, bool | str]:
        """Return MCP annotations expected by Claude-compatible clients."""
        return {
            "title": self.title,
            "readOnlyHint": self.read_only,
            "destructiveHint": self.destructive,
            "idempotentHint": self.idempotent,
            "openWorldHint": self.open_world,
        }


TOOL_SPECS: dict[str, ToolSpec] = {
    # Core diagnostics and routing
    "vault.health": ToolSpec("Health Check"),
    "vault.diagnose": ToolSpec("Diagnose Vault Setup"),
    "client.roots": ToolSpec("List Client Roots"),
    "route.task": ToolSpec("Route Task"),
    "vault.context": ToolSpec("Read Vault Context"),
    # Core navigation
    "notes.list": ToolSpec("List Notes"),
    "notes.read": ToolSpec("Read Note"),
    "notes.search": ToolSpec("Search Notes"),
    "notes.search_by_date": ToolSpec("Search Notes By Date"),
    "notes.read_many": ToolSpec("Read Multiple Notes"),
    "notes.info": ToolSpec("Get Note Info"),
    "templates.list": ToolSpec("List Templates"),
    "notes.get_frontmatter": ToolSpec("Get Frontmatter"),
    # Core skills/resources
    "skills.list": ToolSpec("List Skills"),
    "skills.read": ToolSpec("Read Skill"),
    "rules.get": ToolSpec("Get Global Rules"),
    "rules.add": ToolSpec(
        "Add Global Rule", "agents_admin", read_only=False, idempotent=False
    ),
    "notes.validate": ToolSpec("Validate Note"),
    # Notes write pack
    "notes.suggest_location": ToolSpec(
        "Suggest Note Location", "notes_write", open_world=False
    ),
    "notes.create": ToolSpec(
        "Create Note", "notes_write", read_only=False, idempotent=False
    ),
    "notes.append": ToolSpec(
        "Append To Note", "notes_write", read_only=False, idempotent=False
    ),
    "notes.patch": ToolSpec(
        "Patch Note", "notes_write", read_only=False, idempotent=False
    ),
    "notes.replace": ToolSpec(
        "Replace Note",
        "notes_write",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "notes.update_frontmatter": ToolSpec(
        "Update Frontmatter", "notes_write", read_only=False, idempotent=False
    ),
    "notes.update_tags": ToolSpec(
        "Update Note Tags", "notes_write", read_only=False, idempotent=False
    ),
    "notes.move": ToolSpec(
        "Move Note", "notes_write", read_only=False, idempotent=False
    ),
    "notes.rename": ToolSpec(
        "Rename Note", "notes_write", read_only=False, idempotent=False
    ),
    "notes.delete": ToolSpec(
        "Delete Note",
        "notes_write",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "notes.preview_replace": ToolSpec("Preview Replace In Notes", "notes_write"),
    "notes.apply_replace": ToolSpec(
        "Apply Replace In Notes",
        "notes_write",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    # Vault analysis pack
    "vault.stats": ToolSpec("Get Vault Stats", "vault_analysis"),
    "tags.canonical": ToolSpec("Get Canonical Tags", "vault_analysis"),
    "tags.analyze": ToolSpec("Analyze Tags", "vault_analysis"),
    "tags.sync_registry": ToolSpec(
        "Sync Tag Registry", "vault_analysis", read_only=False, idempotent=False
    ),
    "tags.list": ToolSpec("List Tags", "vault_analysis"),
    "links.analyze": ToolSpec("Analyze Links", "vault_analysis"),
    "activity.recent": ToolSpec("Summarize Recent Activity", "vault_analysis"),
    "links.backlinks": ToolSpec("Get Backlinks", "vault_analysis"),
    "tags.notes_with": ToolSpec("Get Notes By Tag", "vault_analysis"),
    "links.local_graph": ToolSpec("Get Local Graph", "vault_analysis"),
    "links.find_orphans": ToolSpec("Find Orphan Notes", "vault_analysis"),
    "links.find_broken": ToolSpec("Find Broken Wikilinks", "vault_analysis"),
    "vault.lint": ToolSpec(
        "Lint Vault",
        "vault_analysis",
        read_only=False,  # auto_fix=True writes files
        idempotent=False,
    ),
    # Personal pack
    "inbox.capture": ToolSpec(
        "Quick Capture",
        "secundo_selebro",
        read_only=False,
        idempotent=False,
    ),
    "random.concept": ToolSpec("Random Concept", "secundo_selebro"),
    # Agent administration pack
    "skills.refresh_cache": ToolSpec("Refresh Skills Cache", "agents_admin"),
    "skills.create": ToolSpec(
        "Create Skill", "agents_admin", read_only=False, idempotent=False
    ),
    "skills.suggest": ToolSpec("Suggest Vault Skills", "agents_admin"),
    "skills.sync": ToolSpec(
        "Sync Skills", "agents_admin", read_only=False, idempotent=False
    ),
    # External packs
    "youtube.transcript": ToolSpec(
        "Get YouTube Transcript", "youtube", open_world=True
    ),
    "rag.setup_status": ToolSpec("RAG Setup Status", "obsidianrag", open_world=True),
    "rag.health": ToolSpec("RAG Health", "obsidianrag", open_world=True),
    "rag.ask": ToolSpec("Ask Vault", "obsidianrag", open_world=True),
    "rag.rebuild_index": ToolSpec(
        "Rebuild RAG Index", "obsidianrag", read_only=False, idempotent=False
    ),
    # Legacy semantic pack
    "semantic.search": ToolSpec(
        "Legacy Semantic Search (Deprecated)", "legacy_semantic"
    ),
    "semantic.index": ToolSpec(
        "Legacy Semantic Index (Deprecated)",
        "legacy_semantic",
        read_only=False,
        idempotent=False,
    ),
    "semantic.suggest_connections": ToolSpec(
        "Legacy Semantic Connections (Deprecated)", "legacy_semantic"
    ),
    # Canvas pack
    "canvas.read": ToolSpec("Read Canvas", "canvas"),
    "canvas.list": ToolSpec("List Canvases", "canvas"),
    "canvas.add_card": ToolSpec(
        "Add Canvas Card", "canvas", read_only=False, idempotent=False
    ),
    "canvas.add_group": ToolSpec(
        "Add Canvas Group", "canvas", read_only=False, idempotent=False
    ),
    "canvas.add_edge": ToolSpec(
        "Add Canvas Edge", "canvas", read_only=False, idempotent=False
    ),
    "canvas.update_card": ToolSpec(
        "Update Canvas Card", "canvas", read_only=False, idempotent=False
    ),
    "canvas.move_card": ToolSpec(
        "Move Canvas Node", "canvas", read_only=False, idempotent=True
    ),
    "canvas.remove_card": ToolSpec(
        "Remove Canvas Card",
        "canvas",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "canvas.remove_group": ToolSpec(
        "Remove Canvas Group",
        "canvas",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "canvas.remove_edge": ToolSpec(
        "Remove Canvas Edge",
        "canvas",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    # Kanvas pack
    "kanvas.status": ToolSpec("Kanvas Status", "kanvas"),
    "kanvas.task": ToolSpec("Kanvas Task", "kanvas"),
    "kanvas.ready": ToolSpec("Kanvas Ready Tasks", "kanvas"),
    "kanvas.blocked": ToolSpec("Kanvas Blocked Tasks", "kanvas"),
    "kanvas.start": ToolSpec(
        "Kanvas Start Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.finish": ToolSpec(
        "Kanvas Finish Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.pause": ToolSpec(
        "Kanvas Pause Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.approve": ToolSpec(
        "Kanvas Approve Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.complete": ToolSpec(
        "Kanvas Complete Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.edit_task": ToolSpec(
        "Kanvas Edit Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.add_dependency": ToolSpec(
        "Kanvas Add Dependency", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.propose_task": ToolSpec(
        "Kanvas Propose Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.propose_group": ToolSpec(
        "Kanvas Propose Group", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas.init": ToolSpec("Kanvas Init", "kanvas", read_only=False, idempotent=False),
}


def enabled_tool_sets() -> set[str]:
    """Return enabled tool sets for the active vault."""
    enabled = {CORE_TOOL_SET}
    enabled.update(_tool_sets_from_env())
    vault_path = get_vault_path()
    if not vault_path:
        return enabled

    config = get_vault_config(vault_path)
    if not config:
        return enabled

    enabled.update(config.profile.tool_sets)
    # Backward compatibility while vault profiles migrate prompt_sets -> tool_sets.
    for prompt_set in config.profile.prompt_sets:
        if prompt_set in available_tool_sets():
            enabled.add(prompt_set)
    return enabled


def _tool_sets_from_env() -> set[str]:
    raw_value = os.getenv("OBSIDIAN_MCP_TOOL_SETS", "")
    return {
        item.strip() for item in raw_value.replace(";", ",").split(",") if item.strip()
    }


def available_tool_sets() -> set[str]:
    """Return all declared tool sets."""
    return {spec.tool_set for spec in TOOL_SPECS.values()}


def is_tool_enabled(tool_name: str) -> bool:
    """Return whether a tool should be registered for the active vault."""
    spec = TOOL_SPECS[tool_name]
    return spec.tool_set in enabled_tool_sets()


def register_tool(mcp: FastMCP, tool_name: str) -> Callable:
    """Register a tool only when its tool set is enabled."""
    spec = TOOL_SPECS[tool_name]

    def decorator(fn: Callable) -> Callable:
        if not is_tool_enabled(tool_name):
            return fn
        return mcp.tool(
            name=tool_name,
            title=spec.title,
            annotations=spec.annotations(),
            meta={"tool_set": spec.tool_set},
        )(fn)

    return decorator
