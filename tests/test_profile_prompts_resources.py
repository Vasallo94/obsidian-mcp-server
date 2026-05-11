import asyncio
import shlex
from pathlib import Path

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.server import create_server
from obsidian_mcp.tools.agents_logic import invalidate_skills_cache
from obsidian_mcp.tools.obsidianrag import (
    build_obsidianrag_setup_resource,
    check_rag_health,
)
from obsidian_mcp.vault_config import invalidate_vault_config_cache


@pytest.fixture(autouse=True)
def clear_config_caches():
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()
    yield
    reset_settings()
    invalidate_vault_config_cache()
    invalidate_skills_cache()


def test_core_prompts_register_without_vault_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    mcp = create_server()

    prompt_names = {prompt.name for prompt in asyncio.run(mcp.list_prompts())}
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}

    assert {
        "assistant_overview",
        "create_structured_note",
        "use_vault_template",
        "explore_vault_context",
    }.issubset(prompt_names)
    assert "create_mermaid_diagram" not in prompt_names
    assert "update_media_item" not in prompt_names
    assert "prompt_actualizar_media" not in prompt_names
    assert all(not name.startswith("prompt_") for name in prompt_names)
    assert "ask_vault" not in tool_names
    assert "rag_health" not in tool_names
    assert "preguntar_al_conocimiento" not in tool_names


def test_profile_and_pack_prompts_register_from_vault_config(tmp_path, monkeypatch):
    _write_vault_profile(tmp_path)
    _write_skill(tmp_path, "organizador")
    _write_skill(tmp_path, "explorador")
    _write_skill(tmp_path, "procesador")
    _write_skill(tmp_path, "revision")
    _write_skill(tmp_path, "registrador")
    _write_skill(tmp_path, "documentador")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    mcp = create_server()
    prompt_names = {prompt.name for prompt in asyncio.run(mcp.list_prompts())}

    assert "create_mermaid_diagram" in prompt_names
    assert "fix_obsidian_mermaid" in prompt_names
    assert "update_media_item" in prompt_names
    assert "import_kindle_highlights" in prompt_names
    assert "audit_vault" in prompt_names
    assert "create_moc" in prompt_names
    assert "process_external_resource" in prompt_names
    assert "daily_review" in prompt_names
    assert "weekly_review" in prompt_names
    assert "write_runbook" in prompt_names
    assert "write_changelog" in prompt_names
    assert "document_repository" in prompt_names


def test_profile_resources_register_and_read_declared_standard(tmp_path, monkeypatch):
    _write_vault_profile(tmp_path)
    _write_skill(tmp_path, "organizador")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    mcp = create_server()
    resources = {str(resource.uri) for resource in asyncio.run(mcp.list_resources())}
    templates = {
        template.uri_template for template in asyncio.run(mcp.list_resource_templates())
    }
    standard = asyncio.run(mcp.read_resource("obsidian://standards/media"))
    local_doc = asyncio.run(mcp.read_resource("obsidian://local_docs/index"))
    capabilities = asyncio.run(mcp.read_resource("obsidian://capabilities"))
    catalog = asyncio.run(mcp.read_resource("obsidian://skills/catalog"))

    assert "obsidian://capabilities" in resources
    assert "obsidian://profile" in resources
    assert "obsidian://skills/list" in resources
    assert "obsidian://skills/catalog" in resources
    assert "obsidian://skills/{name}" in templates
    assert "obsidian://standards/{name}" in templates
    assert "obsidian://local_docs/{name}" in templates
    assert "Media Standard" in str(standard)
    assert "Local Index" in str(local_doc)
    assert "health_check" in str(capabilities)
    assert "when_to_use" in str(catalog)


def test_diagnostic_tools_are_registered_and_report_profile(tmp_path, monkeypatch):
    _write_vault_profile(tmp_path)
    _write_skill(tmp_path, "organizador")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    mcp = create_server()
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    health_tool = asyncio.run(mcp.get_tool("health_check"))
    diagnosis_tool = asyncio.run(mcp.get_tool("diagnose_vault_setup"))
    route_tool = asyncio.run(mcp.get_tool("route_task"))
    health = asyncio.run(health_tool.run({}))
    diagnosis = asyncio.run(diagnosis_tool.run({}))
    route = asyncio.run(
        route_tool.run({"request": "Busca una nota que recuerdo sobre RAG"})
    )
    media_search_route = asyncio.run(
        route_tool.run({"request": "Busca una película sobre una modelo y asesinatos"})
    )

    assert "health_check" in tool_names
    assert "diagnose_vault_setup" in tool_names
    assert "route_task" in tool_names
    assert "profile_configured" in str(health)
    assert "integration:obsidianrag:path" in str(health)
    assert "No setup issues detected" in str(diagnosis)
    assert "ObsidianRAG" in str(route)
    assert "Recommended prompt: `explore_vault_context`" in str(media_search_route)
    assert "ObsidianRAG" in str(media_search_route)


def test_obsidianrag_pack_registers_resources_and_tools(tmp_path, monkeypatch):
    _write_vault_profile(tmp_path, extra_tool_sets=["obsidianrag"])
    _write_skill(tmp_path, "explorador")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    mcp = create_server()
    tool_names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    resources = {str(resource.uri) for resource in asyncio.run(mcp.list_resources())}
    setup = asyncio.run(mcp.read_resource("obsidian://integrations/obsidianrag/setup"))
    config = asyncio.run(
        mcp.read_resource("obsidian://integrations/obsidianrag/config")
    )
    capabilities = asyncio.run(mcp.read_resource("obsidian://capabilities"))

    assert "ask_vault" in tool_names
    assert "rag_health" in tool_names
    assert "rebuild_rag_index" in tool_names
    assert "rag_setup_status" in tool_names
    assert "obsidian://integrations/obsidianrag/setup" in resources
    assert "obsidian://integrations/obsidianrag/config" in resources
    assert "ObsidianRAG" in str(setup)
    assert "Ollama" in str(setup)
    assert "obsidianrag serve" in str(setup)
    assert "api_url" in str(config)
    assert "ask_vault" in str(capabilities)


def test_obsidianrag_rejects_non_loopback_api_url(tmp_path, monkeypatch):
    _write_vault_profile(tmp_path, extra_tool_sets=["obsidianrag"])
    config_path = tmp_path / ".agents" / "vault.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "http://127.0.0.1:8000", "https://example.com"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    health = check_rag_health()

    assert not health.success
    assert "loopback" in (health.error or "")


def test_obsidianrag_setup_uses_shell_safe_paths(tmp_path, monkeypatch):
    vault_path = tmp_path / "Vault With Spaces"
    vault_path.mkdir()
    _write_vault_profile(vault_path, extra_tool_sets=["obsidianrag"])
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault_path))

    setup = build_obsidianrag_setup_resource()

    assert "User Consent" in setup
    assert "uv run obsidianrag serve --vault" in setup
    assert shlex.quote(str(vault_path)) in setup


def _write_vault_profile(vault: Path, extra_tool_sets: list[str] | None = None) -> None:
    standard_path = vault / "Standards" / "Media.md"
    standard_path.parent.mkdir(parents=True)
    standard_path.write_text("# Media Standard\n", encoding="utf-8")
    (vault / "Templates").mkdir()
    (vault / "README.md").write_text("# Local Index\n", encoding="utf-8")
    integration_path = vault / "External" / "ObsidianRAG"
    integration_path.mkdir(parents=True)
    agents_path = vault / ".agents"
    agents_path.mkdir()
    prompt_sets = "\n".join(
        f'    - "{prompt_set}"' for prompt_set in ["mermaid", "secundo_selebro"]
    )
    tool_sets = "\n".join(
        f'    - "{tool_set}"'
        for tool_set in [
            "notes_write",
            "vault_analysis",
            "secundo_selebro",
            "agents_admin",
            "youtube",
            *(extra_tool_sets or []),
        ]
    )
    (agents_path / "vault.yaml").write_text(
        f"""
version: "1.0"
templates_folder: "Templates"
profile:
  name: "secundo_selebro"
  prompt_sets:
{prompt_sets}
  tool_sets:
{tool_sets}
  standards:
    media: "Standards/Media.md"
  local_docs:
    index: "README.md"
  integrations:
    obsidianrag:
      project_path: "External/ObsidianRAG"
      api_url: "http://127.0.0.1:8000"
""".strip(),
        encoding="utf-8",
    )


def _write_skill(vault: Path, name: str) -> None:
    skill_path = vault / ".agents" / "skills" / name
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text(
        f"""
---
name: {name}
description: Skill for {name}
tools:
  - obsidian-mcp
---

# {name}

## Cuándo usar esta skill
- Use when routing tests need {name}.

Use this skill for tests.
""".strip(),
        encoding="utf-8",
    )
