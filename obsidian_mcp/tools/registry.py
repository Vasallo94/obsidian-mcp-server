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
    "health_check": ToolSpec("Health Check"),
    "diagnose_vault_setup": ToolSpec("Diagnose Vault Setup"),
    "list_client_roots": ToolSpec("List Client Roots"),
    "route_task": ToolSpec("Route Task"),
    "read_vault_context": ToolSpec("Read Vault Context"),
    # Core navigation
    "list_notes": ToolSpec("List Notes"),
    "read_note": ToolSpec("Read Note"),
    "search_notes": ToolSpec("Search Notes"),
    "search_notes_by_date": ToolSpec("Search Notes By Date"),
    "read_notes": ToolSpec("Read Multiple Notes"),
    "get_note_info": ToolSpec("Get Note Info"),
    "list_templates": ToolSpec("List Templates"),
    "get_frontmatter": ToolSpec("Get Frontmatter"),
    # Core skills/resources
    "list_skills": ToolSpec("List Skills"),
    "read_skill": ToolSpec("Read Skill"),
    "get_global_rules": ToolSpec("Get Global Rules"),
    "validate_note": ToolSpec("Validate Note"),
    # Notes write pack
    "suggest_note_location": ToolSpec(
        "Suggest Note Location", "notes_write", open_world=False
    ),
    "create_note": ToolSpec(
        "Create Note", "notes_write", read_only=False, idempotent=False
    ),
    "append_to_note": ToolSpec(
        "Append To Note", "notes_write", read_only=False, idempotent=False
    ),
    "patch_note": ToolSpec(
        "Patch Note", "notes_write", read_only=False, idempotent=False
    ),
    "replace_note": ToolSpec(
        "Replace Note",
        "notes_write",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "update_frontmatter": ToolSpec(
        "Update Frontmatter", "notes_write", read_only=False, idempotent=False
    ),
    "update_note_tags": ToolSpec(
        "Update Note Tags", "notes_write", read_only=False, idempotent=False
    ),
    "move_note": ToolSpec(
        "Move Note", "notes_write", read_only=False, idempotent=False
    ),
    "rename_note": ToolSpec(
        "Rename Note", "notes_write", read_only=False, idempotent=False
    ),
    "delete_note": ToolSpec(
        "Delete Note",
        "notes_write",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "preview_replace_in_notes": ToolSpec("Preview Replace In Notes", "notes_write"),
    "apply_replace_in_notes": ToolSpec(
        "Apply Replace In Notes",
        "notes_write",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    # Vault analysis pack
    "get_vault_stats": ToolSpec("Get Vault Stats", "vault_analysis"),
    "get_canonical_tags": ToolSpec("Get Canonical Tags", "vault_analysis"),
    "analyze_tags": ToolSpec("Analyze Tags", "vault_analysis"),
    "sync_tag_registry": ToolSpec(
        "Sync Tag Registry", "vault_analysis", read_only=False, idempotent=False
    ),
    "list_tags": ToolSpec("List Tags", "vault_analysis"),
    "analyze_links": ToolSpec("Analyze Links", "vault_analysis"),
    "summarize_recent_activity": ToolSpec(
        "Summarize Recent Activity", "vault_analysis"
    ),
    "get_backlinks": ToolSpec("Get Backlinks", "vault_analysis"),
    "get_notes_by_tag": ToolSpec("Get Notes By Tag", "vault_analysis"),
    "get_local_graph": ToolSpec("Get Local Graph", "vault_analysis"),
    "find_orphan_notes": ToolSpec("Find Orphan Notes", "vault_analysis"),
    "find_broken_wikilinks": ToolSpec("Find Broken Wikilinks", "vault_analysis"),
    # Personal pack
    "quick_capture": ToolSpec(
        "Quick Capture",
        "secundo_selebro",
        read_only=False,
        idempotent=False,
    ),
    "random_concept": ToolSpec("Random Concept", "secundo_selebro"),
    # Agent administration pack
    "refresh_skills_cache": ToolSpec("Refresh Skills Cache", "agents_admin"),
    "create_skill": ToolSpec(
        "Create Skill", "agents_admin", read_only=False, idempotent=False
    ),
    "suggest_vault_skills": ToolSpec("Suggest Vault Skills", "agents_admin"),
    "sync_skills": ToolSpec(
        "Sync Skills", "agents_admin", read_only=False, idempotent=False
    ),
    # External packs
    "get_youtube_transcript": ToolSpec(
        "Get YouTube Transcript", "youtube", open_world=True
    ),
    "rag_setup_status": ToolSpec("RAG Setup Status", "obsidianrag", open_world=True),
    "rag_health": ToolSpec("RAG Health", "obsidianrag", open_world=True),
    "ask_vault": ToolSpec("Ask Vault", "obsidianrag", open_world=True),
    "rebuild_rag_index": ToolSpec(
        "Rebuild RAG Index", "obsidianrag", read_only=False, idempotent=False
    ),
    # Legacy semantic pack
    "semantic_search": ToolSpec(
        "Legacy Semantic Search (Deprecated)", "legacy_semantic"
    ),
    "index_vault_semantic": ToolSpec(
        "Legacy Semantic Index (Deprecated)",
        "legacy_semantic",
        read_only=False,
        idempotent=False,
    ),
    "suggest_semantic_connections": ToolSpec(
        "Legacy Semantic Connections (Deprecated)", "legacy_semantic"
    ),
    # Canvas pack
    "canvas_read": ToolSpec("Read Canvas", "canvas"),
    "canvas_list": ToolSpec("List Canvases", "canvas"),
    "canvas_add_card": ToolSpec(
        "Add Canvas Card", "canvas", read_only=False, idempotent=False
    ),
    "canvas_add_group": ToolSpec(
        "Add Canvas Group", "canvas", read_only=False, idempotent=False
    ),
    "canvas_add_edge": ToolSpec(
        "Add Canvas Edge", "canvas", read_only=False, idempotent=False
    ),
    "canvas_update_card": ToolSpec(
        "Update Canvas Card", "canvas", read_only=False, idempotent=False
    ),
    "canvas_remove_card": ToolSpec(
        "Remove Canvas Card",
        "canvas",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    "canvas_remove_edge": ToolSpec(
        "Remove Canvas Edge",
        "canvas",
        read_only=False,
        destructive=True,
        idempotent=False,
    ),
    # Kanvas pack
    "kanvas_status": ToolSpec("Kanvas Status", "kanvas"),
    "kanvas_task": ToolSpec("Kanvas Task", "kanvas"),
    "kanvas_ready": ToolSpec("Kanvas Ready Tasks", "kanvas"),
    "kanvas_blocked": ToolSpec("Kanvas Blocked Tasks", "kanvas"),
    "kanvas_start": ToolSpec(
        "Kanvas Start Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_finish": ToolSpec(
        "Kanvas Finish Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_pause": ToolSpec(
        "Kanvas Pause Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_approve": ToolSpec(
        "Kanvas Approve Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_complete": ToolSpec(
        "Kanvas Complete Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_edit_task": ToolSpec(
        "Kanvas Edit Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_add_dependency": ToolSpec(
        "Kanvas Add Dependency", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_propose_task": ToolSpec(
        "Kanvas Propose Task", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_propose_group": ToolSpec(
        "Kanvas Propose Group", "kanvas", read_only=False, idempotent=False
    ),
    "kanvas_init": ToolSpec("Kanvas Init", "kanvas", read_only=False, idempotent=False),
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
