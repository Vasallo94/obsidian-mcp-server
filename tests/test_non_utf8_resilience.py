"""Vault-wide readers skip legacy-encoded notes instead of aborting."""

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.tools import analysis_logic
from obsidian_mcp.tools.analysis_logic import (
    analyze_links,
    analyze_tags,
    get_vault_stats,
    list_all_tags,
    sync_tag_registry,
)
from obsidian_mcp.tools.graph_logic import (
    find_orphan_notes,
    get_backlinks,
    get_local_graph,
    get_notes_by_tag,
)
from obsidian_mcp.utils import invalidate_note_cache


@pytest.mark.parametrize(
    "operation",
    [
        get_vault_stats,
        analyze_tags,
        list_all_tags,
        analyze_links,
        lambda: get_backlinks("Good"),
        lambda: get_notes_by_tag("tag"),
        lambda: get_local_graph("Good"),
        find_orphan_notes,
        lambda: sync_tag_registry(False),
    ],
)
def test_vault_reader_skips_non_utf8_note(tmp_path, monkeypatch, operation):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Good.md").write_text("# Good\n\n#tag [[Other]]\n", encoding="utf-8")
    (vault / "Other.md").write_text("# Other\n\n[[Good]]\n", encoding="utf-8")
    (vault / "Legacy.md").write_bytes(b"\xff\xfe")
    (vault / "Registro de Tags del Vault.md").write_text(
        "# Tags\n\n- `tag`\n", encoding="utf-8"
    )
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()
    invalidate_note_cache()

    result = operation()

    assert result.success, result.error
    assert "Archivos ilegibles omitidos: 1" in (result.data or "")


def test_incomplete_tag_scan_does_not_update_registry(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Good.md").write_text("# Good\n\n#new\n", encoding="utf-8")
    (vault / "Legacy.md").write_bytes(b"\xff\xfe")
    registry = vault / "Registro de Tags del Vault.md"
    original = "# Tags\n\n- `old`\n\n## Estadísticas\n\nold table\n"
    registry.write_text(original, encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()

    result = sync_tag_registry(True)

    assert result.success
    assert registry.read_text(encoding="utf-8") == original
    assert "Registro no actualizado" in (result.data or "")


def test_stats_and_orphans_disclose_skipped_note(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Good.md").write_text("# Good\n\n[[Other]]\n", encoding="utf-8")
    (vault / "Other.md").write_text("# Other\n\n[[Good]]\n", encoding="utf-8")
    (vault / "Legacy.md").write_bytes(b"\xff\xfe")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()
    invalidate_note_cache()

    stats = get_vault_stats()
    orphans = find_orphan_notes()

    assert stats.success and orphans.success
    assert "Archivos Markdown: 3" in (stats.data or "")
    assert "Notas analizadas: 2" in (stats.data or "")
    assert "Archivos ilegibles omitidos: 1" in (stats.data or "")
    assert "Legacy.md" not in (orphans.data or "")
    assert "Archivos ilegibles omitidos: 1" in (orphans.data or "")


def test_non_utf8_central_note_returns_failure(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Legacy.md").write_bytes(b"\xff\xfe")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()
    invalidate_note_cache()

    result = get_local_graph("Legacy")

    assert not result.success
    assert "nota central" in (result.error or "")


def test_processing_unicode_error_is_not_reported_as_success(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Good.md").write_text("# Good\n", encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()

    def fail_processing(_content):
        raise UnicodeDecodeError("utf-8", b"x", 0, 1, "processor bug")

    monkeypatch.setattr(analysis_logic, "extract_internal_links", fail_processing)

    with pytest.raises(UnicodeDecodeError):
        analyze_links()
