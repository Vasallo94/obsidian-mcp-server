"""Vault-wide readers skip legacy-encoded notes instead of aborting."""

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.tools.analysis_logic import (
    analyze_links,
    analyze_tags,
    get_vault_stats,
    list_all_tags,
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
    ],
)
def test_vault_reader_skips_non_utf8_note(tmp_path, monkeypatch, operation):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Good.md").write_text("# Good\n\n#tag [[Other]]\n", encoding="utf-8")
    (vault / "Other.md").write_text("# Other\n\n[[Good]]\n", encoding="utf-8")
    (vault / "Legacy.md").write_bytes(b"\xff\xfe")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()
    invalidate_note_cache()

    result = operation()

    assert result.success, result.error
