"""Regression tests for the shared vault filesystem boundary."""

import json
from pathlib import Path

from obsidian_mcp.canvas import canvas_logic, workflow_tool_logic
from obsidian_mcp.result import Result
from obsidian_mcp.tools import (
    agents_generator,
    creation_logic,
    navigation_logic,
    obsidianrag,
)
from obsidian_mcp.utils import security
from obsidian_mcp.utils import vault as vault_utils


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


def test_packaged_boundary_excludes_trash_notes(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    trash = vault / ".trash"
    trash.mkdir(parents=True)
    (trash / "nested").mkdir()
    (vault / ".trashcan").mkdir()
    (vault / ".git").mkdir()
    (vault / ".obsidian").mkdir()
    (vault / "visible.md").write_text("visible", encoding="utf-8")
    (trash / "deleted.md").write_text("deleted", encoding="utf-8")
    (trash / "nested" / "deleted.md").write_text("deleted", encoding="utf-8")
    (vault / ".trashcan" / "normal.md").write_text("normal", encoding="utf-8")
    (vault / ".trash-file.md").write_text("normal", encoding="utf-8")
    (vault / ".git" / "tracked.md").write_text("hidden", encoding="utf-8")
    (vault / ".obsidian" / "plugin.md").write_text("hidden", encoding="utf-8")
    monkeypatch.setattr(security, "get_vault_path", lambda: vault)
    monkeypatch.setattr(navigation_logic, "get_vault_path", lambda: vault)
    security.load_forbidden_patterns(force_reload=True, vault_path=vault)

    visible = {
        path.relative_to(vault).as_posix()
        for path in security.iter_safe_vault_files(vault)
    }

    assert visible == {".trash-file.md", ".trashcan/normal.md", "visible.md"}
    for protected in [
        trash,
        trash / "deleted.md",
        trash / "nested" / "deleted.md",
        vault / ".git",
        vault / ".obsidian",
    ]:
        assert security.is_path_forbidden(protected, vault)[0]
    assert security.resolve_vault_path(".trash", vault)[0] is None
    listed = navigation_logic.list_notes()
    assert listed.success
    assert "visible.md" in (listed.data or "")
    assert "deleted.md" not in (listed.data or "")
    assert "tracked.md" not in (listed.data or "")
    assert "plugin.md" not in (listed.data or "")


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


def test_skill_create_accepts_safe_unicode_name(tmp_path: Path, monkeypatch) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(agents_generator, "get_vault_path", lambda: vault)

    result = agents_generator.generate_skill("revisión-notas", "desc", "instructions")

    assert result.success
    assert (vault / ".agents" / "skills" / "revisión-notas" / "SKILL.md").is_file()


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


def test_exact_forbidden_directory_protects_only_its_descendants(
    tmp_path: Path, monkeypatch
) -> None:
    vault = tmp_path / "vault"
    protected = vault / "Sensitive" / "nested"
    allowed = vault / "SensitiveBackup"
    protected.mkdir(parents=True)
    allowed.mkdir()
    (protected / "secret.md").write_text("secret", encoding="utf-8")
    (allowed / "public.md").write_text("public", encoding="utf-8")
    (vault / ".forbidden_paths").write_text("Sensitive\n", encoding="utf-8")
    monkeypatch.setattr(security, "get_vault_path", lambda: vault)
    security.load_forbidden_patterns(force_reload=True, vault_path=vault)

    assert security.is_path_forbidden(vault / "Sensitive", vault)[0]
    assert security.is_path_forbidden(protected / "secret.md", vault)[0]
    assert not security.is_path_forbidden(allowed / "public.md", vault)[0]
    assert security.resolve_vault_path("Sensitive/nested/secret.md", vault)[0] is None
    assert list(security.iter_safe_vault_files(vault)) == [allowed / "public.md"]


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


def test_safe_iterator_supports_symlinked_vault_root(tmp_path: Path) -> None:
    real_vault = tmp_path / "real-vault"
    real_vault.mkdir()
    note = real_vault / "note.md"
    note.write_text("public", encoding="utf-8")
    linked_vault = tmp_path / "linked-vault"
    try:
        linked_vault.symlink_to(real_vault, target_is_directory=True)
    except OSError:
        return

    assert list(security.iter_safe_vault_files(linked_vault)) == [note]


def test_normalized_traversal_cannot_bypass_forbidden_pattern(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    private = vault / "Private"
    private.mkdir(parents=True)
    secret = private / "secret.md"
    secret.write_text("secret", encoding="utf-8")
    (vault / ".forbidden_paths").write_text("Private/*\n", encoding="utf-8")
    security.load_forbidden_patterns(force_reload=True, vault_path=vault)

    allowed, _ = security.check_path_access(
        vault / "unused" / ".." / "Private" / "secret.md", vault
    )

    assert not allowed


def test_symlink_to_protected_file_is_denied(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    private = vault / "Private"
    private.mkdir(parents=True)
    secret = private / "secret.md"
    secret.write_text("secret", encoding="utf-8")
    alias = vault / "alias.md"
    (vault / ".forbidden_paths").write_text("Private/*\n", encoding="utf-8")
    try:
        alias.symlink_to(secret)
    except OSError:
        return

    assert not security.check_path_access(alias, vault)[0]


def test_list_notes_includes_safe_internal_file_symlink(
    tmp_path: Path, monkeypatch
) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    target = vault / "target.md"
    target.write_text("public", encoding="utf-8")
    alias = vault / "alias.md"
    try:
        alias.symlink_to(target)
    except OSError:
        return
    monkeypatch.setattr(navigation_logic, "get_vault_path", lambda: vault)
    monkeypatch.setattr(vault_utils, "get_vault_path", lambda: vault)

    result = navigation_logic.list_notes()

    assert result.success
    assert "alias.md" in (result.data or "")


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
            "DATABASE_URL": "postgres://user:pass@localhost/db",
            "ANTHROPIC_APIKEY": "api-key",
            "GH_TOKENS": "tokens",
            "PASSWORDS": "passwords",
            "CREDS": "credentials",
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
    assert "postgres://" not in setup
    assert "api-key" not in setup
    assert "tokens" not in setup
    assert "passwords" not in setup
    assert "credentials" not in setup
    assert "OPENAI_API_KEY" in setup
    assert "DATABASE_URL" in setup
    assert "OBSIDIANRAG_LLM_MODEL" in setup


def test_obsidianrag_rejects_loopback_url_with_credentials() -> None:
    assert not obsidianrag._is_loopback_http_url(  # pylint: disable=protected-access
        "http://user:pass@localhost:8000"
    )


def test_note_cache_is_scoped_to_vault(tmp_path: Path, monkeypatch) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "same.md").write_text("first", encoding="utf-8")
    (second / "same.md").write_text("second", encoding="utf-8")
    active_vault = first
    monkeypatch.setattr(vault_utils, "get_vault_path", lambda: active_vault)
    vault_utils.invalidate_note_cache()

    assert vault_utils.find_note_by_name("same") == first / "same.md"
    active_vault = second
    assert vault_utils.find_note_by_name("same") == second / "same.md"
