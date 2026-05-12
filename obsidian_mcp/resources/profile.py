"""Profile, skill, and standard MCP resources."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from ..config import get_vault_path
from ..tools.agents_logic import get_agent_instructions, get_cached_skills
from ..tools.obsidianrag import (
    build_obsidianrag_config_resource,
    build_obsidianrag_setup_resource,
)
from ..tools.registry import available_tool_sets, enabled_tool_sets
from ..utils.security import check_path_access
from ..vault_config import get_vault_config


def register_profile_resources(mcp: FastMCP) -> None:
    """Register profile-specific MCP resources."""

    @mcp.resource("obsidian://capabilities")
    def capabilities_resource() -> str:
        """Return discoverable MCP capabilities for the active vault."""
        vault_path = get_vault_path()
        config = get_vault_config(vault_path) if vault_path else None
        profile = config.profile if config else None
        skills_count = 0
        if vault_path:
            skills_count = sum(
                1
                for result in get_cached_skills(str(vault_path)).values()
                if result.success and result.data
            )

        payload: dict[str, Any] = {
            "core_prompts": [
                "assistant_overview",
                "create_structured_note",
                "use_vault_template",
                "explore_vault_context",
            ],
            "optional_prompt_packs": {
                "enabled": profile.prompt_sets if profile else [],
                "available": ["mermaid"],
            },
            "tool_sets": {
                "enabled": sorted(enabled_tool_sets()),
                "available": sorted(available_tool_sets()),
            },
            "profile": {
                "name": profile.name if profile else None,
                "standards": sorted(profile.standards) if profile else [],
                "local_docs": sorted(profile.local_docs) if profile else [],
                "integrations": sorted(profile.integrations) if profile else [],
                "skills_count": skills_count,
            },
            "resources": [
                "obsidian://profile",
                "obsidian://skills/list",
                "obsidian://skills/catalog",
                "obsidian://skills/{name}",
                "obsidian://standards/{name}",
                "obsidian://local_docs/{name}",
            ],
            "diagnostics": [
                "health_check",
                "diagnose_vault_setup",
                "list_client_roots",
                "route_task",
            ],
            "client_capabilities": {
                "roots": {
                    "tool": "list_client_roots",
                    "purpose": (
                        "Inspect roots advertised by the MCP client so agents can "
                        "confirm workspace/vault access before setup work."
                    ),
                }
            },
            "obsidianrag_tools": (
                ["rag_setup_status", "rag_health", "ask_vault", "rebuild_rag_index"]
                if _is_tool_set_enabled("obsidianrag")
                else []
            ),
        }
        if _is_tool_set_enabled("obsidianrag"):
            payload["resources"].extend(
                [
                    "obsidian://integrations/obsidianrag/setup",
                    "obsidian://integrations/obsidianrag/config",
                ]
            )
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @mcp.resource("obsidian://profile")
    def profile_resource() -> str:
        """Return a safe summary of the active vault profile."""
        vault_path = get_vault_path()
        if not vault_path:
            return json.dumps({"profile": None, "error": "Vault is not configured"})

        config = get_vault_config(vault_path)
        profile = config.profile if config else None
        payload = {
            "vault": vault_path.name,
            "profile": profile.name if profile else None,
            "prompt_sets": profile.prompt_sets if profile else [],
            "tool_sets": sorted(enabled_tool_sets()),
            "standards": sorted(profile.standards) if profile else [],
            "local_docs": sorted(profile.local_docs) if profile else [],
            "integrations": sorted(profile.integrations) if profile else [],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @mcp.resource("obsidian://skills/list")
    def skills_list_resource() -> str:
        """List valid skills declared under .agents/skills."""
        vault_path = get_vault_path()
        if not vault_path:
            return json.dumps({"skills": [], "error": "Vault is not configured"})

        skills = get_cached_skills(str(vault_path))
        valid_skills = []
        invalid_skills = []
        for folder, result in sorted(skills.items()):
            if result.success and result.data:
                valid_skills.append(
                    {
                        "name": result.data.metadata.name,
                        "folder": folder,
                        "description": result.data.metadata.description,
                        "tools": result.data.metadata.tools or [],
                    }
                )
            else:
                invalid_skills.append({"folder": folder, "error": result.error})

        return json.dumps(
            {"skills": valid_skills, "invalid_skills": invalid_skills},
            ensure_ascii=False,
            indent=2,
        )

    @mcp.resource("obsidian://skills/catalog")
    def skills_catalog_resource() -> str:
        """Return a richer skill catalog with use-case hints."""
        vault_path = get_vault_path()
        if not vault_path:
            return json.dumps({"skills": [], "error": "Vault is not configured"})

        catalog = []
        for folder, result in sorted(get_cached_skills(str(vault_path)).items()):
            if not result.success or not result.data:
                continue
            skill = result.data
            catalog.append(
                {
                    "name": skill.metadata.name,
                    "folder": folder,
                    "description": skill.metadata.description,
                    "tools": skill.metadata.tools or [],
                    "when_to_use": _extract_skill_section(
                        skill.body, ["cuándo usar", "cuando usar", "when to use"]
                    ),
                    "when_not_to_use": _extract_skill_section(
                        skill.body,
                        ["cuándo no usar", "cuando no usar", "when not to use"],
                    ),
                }
            )

        return json.dumps({"skills": catalog}, ensure_ascii=False, indent=2)

    @mcp.resource("obsidian://skills/{name}")
    def skill_resource(name: str) -> str:
        """Return a specific skill by folder name."""
        return get_agent_instructions(name).to_display()

    @mcp.resource("obsidian://standards/{name}")
    def standard_resource(name: str) -> str:
        """Return a named standard declared in the vault profile."""
        vault_path = get_vault_path()
        if not vault_path:
            return "❌ Error: Vault is not configured."

        config = get_vault_config(vault_path)
        if not config or name not in config.profile.standards:
            available = sorted(config.profile.standards) if config else []
            return f"❌ Error: Standard '{name}' not found. Available: {available}"

        return _read_declared_file(
            vault_path, config.profile.standards[name], "Standard"
        )

    @mcp.resource("obsidian://local_docs/{name}")
    def local_doc_resource(name: str) -> str:
        """Return a named local document declared in the vault profile."""
        vault_path = get_vault_path()
        if not vault_path:
            return "❌ Error: Vault is not configured."

        config = get_vault_config(vault_path)
        if not config or name not in config.profile.local_docs:
            available = sorted(config.profile.local_docs) if config else []
            return f"❌ Error: Local doc '{name}' not found. Available: {available}"

        return _read_declared_file(
            vault_path, config.profile.local_docs[name], "Local doc"
        )

    if _is_tool_set_enabled("obsidianrag"):

        @mcp.resource("obsidian://integrations/obsidianrag/setup")
        def obsidianrag_setup_resource() -> str:
            """Return the guided ObsidianRAG setup playbook."""
            return build_obsidianrag_setup_resource()

        @mcp.resource("obsidian://integrations/obsidianrag/config")
        def obsidianrag_config_resource() -> str:
            """Return the safe ObsidianRAG integration config."""
            return build_obsidianrag_config_resource()


def _read_declared_file(vault_path: Path, relative_value: str, label: str) -> str:
    relative_path = Path(relative_value)
    target_path = vault_path / relative_path
    allowed, error = check_path_access(target_path, vault_path, "read")
    if not allowed:
        return error
    if not target_path.exists() or not target_path.is_file():
        return f"❌ Error: {label} file does not exist: {relative_path}"
    return target_path.read_text(encoding="utf-8")


def _is_tool_set_enabled(tool_set: str) -> bool:
    return tool_set in enabled_tool_sets()


def _extract_skill_section(body: str, headings: list[str]) -> list[str]:
    lines = body.splitlines()
    capture = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip().casefold()
            if capture:
                break
            capture = any(heading in heading_text for heading in headings)
            continue
        if not capture:
            continue
        if stripped.startswith("- "):
            items.append(stripped.removeprefix("- ").strip())
        elif stripped and len(items) < 3 and not stripped.startswith(">"):
            items.append(stripped)
        if len(items) >= 6:
            break
    return items
