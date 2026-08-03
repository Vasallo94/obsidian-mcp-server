"""Regression tests for the shared vault filesystem boundary."""

import json
from pathlib import Path

from obsidian_mcp.canvas import canvas_logic, workflow_tool_logic
from obsidian_mcp.result import Result
from obsidian_mcp.tools import agents_generator, creation_logic, obsidianrag
from obsidian_mcp.utils import security


def test_canvas_resolvers_reject_absolute_paths_outside_vault(
    tmp_path: Path, monkeypatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.canvas"
    outside.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(canvas_logic, "get_vault_path", lambda: vault)
    monkeypatch.setattr(workflow_tool_logic, "get_vault_path", lambda: vault)

    assert not canvas_logic.read_canvas(str(outside)).success
    assert not workflow_tool_logic.init_project(str(outside), groups=[]).success


def test_create_note_rejects_traversal_before_creating_directories(
    tmp_path: Path, monkeypatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    monkeypatch.setattr(creation_logic, "get_vault_path", lambda: vault)
    monkeypatch.setattr(creation_logic, "get_vault_config", lambda _vault: None)

    result = creation_logic.create_note("escape", "content", carpeta="../outside")

    assert not result.success
    assert not outside.exists()


def test_skill_create_rejects_traversal(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(agents_generator, "get_vault_path", lambda: vault)

    result = agents_generator.generate_skill("../../escape", "desc", "instructions")

    assert not result.success
    assert not (tmp_path / "escape").exists()


def test_forbidden_patterns_merge_project_and_vault_files(
    tmp_path: Path, monkeypatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".forbidden_paths").write_text("Private/*\n", encoding="utf-8")
    monkeypatch.setattr(security, "get_vault_path", lambda: vault)

    patterns = security.load_forbidden_patterns(force_reload=True)

    assert "Private/*" in patterns
    assert "**/secrets.md" in patterns


def test_safe_iterator_skips_protected_files(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    private = vault / "Private"
    private.mkdir(parents=True)
    (vault / "public.md").write_text("public", encoding="utf-8")
    (private / "secret.md").write_text("secret", encoding="utf-8")
    (vault / ".forbidden_paths").write_text("Private/*\n", encoding="utf-8")
    monkeypatch.setattr(security, "get_vault_path", lambda: vault)
    security.load_forbidden_patterns(force_reload=True)

    files = list(security.iter_safe_vault_files(vault))

    assert files == [vault / "public.md"]


def test_safe_iterator_skips_symlink_escape(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    link = vault / "linked.md"
    try:
        link.symlink_to(outside)
    except OSError:
        return
    monkeypatch.setattr(security, "get_vault_path", lambda: vault)
    security.load_forbidden_patterns(force_reload=True)

    assert not list(security.iter_safe_vault_files(vault))


def test_obsidianrag_resources_do_not_expose_secret_env(monkeypatch) -> None:
    config = {
        "vault_path": "/vault",
        "project_path": "/project",
        "api_url": "http://127.0.0.1:8000",
        "docs": None,
        "env": {
            "OBSIDIANRAG_LLM_MODEL": "local-model",
            "OPENAI_API_KEY": "top-secret",
            "SERVICE_TOKEN": "token-value",
        },
    }
    monkeypatch.setattr(
        obsidianrag, "_get_integration_config", lambda: Result.ok(config)
    )

    resource = obsidianrag.build_obsidianrag_config_resource()
    setup = obsidianrag.build_obsidianrag_setup_resource()

    assert "env" not in json.loads(resource)
    assert "top-secret" not in setup
    assert "token-value" not in setup
    assert "OBSIDIANRAG_LLM_MODEL" in setup
