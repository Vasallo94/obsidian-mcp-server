"""Tests for list_notes pagination, filtering, and limits (Issue #5)."""

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.tools.navigation_logic import list_notes


@pytest.fixture
def populated_vault(tmp_path, monkeypatch):
    """Vault with 25 notes across two folders for pagination tests."""
    vault = tmp_path / "vault"
    (vault / "a").mkdir(parents=True)
    (vault / "b").mkdir(parents=True)
    for i in range(15):
        (vault / "a" / f"note-{i:02d}.md").write_text(
            f"# Note {i}\nbody\n", encoding="utf-8"
        )
    for i in range(10):
        (vault / "b" / f"note-{i:02d}.md").write_text(
            f"# B Note {i}\nbody\n", encoding="utf-8"
        )
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault))
    reset_settings()
    return vault


class TestListNotesPagination:
    def test_default_returns_all_when_below_limit(self, populated_vault):
        result = list_notes()
        assert result.success
        assert "25 total" in result.data
        assert "showing 1-25" in result.data
        assert "Truncated" not in result.data

    def test_limit_caps_results(self, populated_vault):
        result = list_notes(limit=10)
        assert result.success
        assert "25 total" in result.data
        assert "showing 1-10" in result.data
        assert "15 more notes available" in result.data
        assert "offset=10" in result.data

    def test_offset_skips_initial_results(self, populated_vault):
        result = list_notes(offset=20, limit=10)
        assert result.success
        assert "showing 21-25" in result.data
        assert "Truncated" not in result.data

    def test_limit_zero_means_no_limit(self, populated_vault):
        result = list_notes(limit=0)
        assert result.success
        assert "25 total" in result.data
        assert "Truncated" not in result.data

    def test_folder_filter(self, populated_vault):
        result = list_notes(carpeta="a")
        assert result.success
        assert "15 total" in result.data

    def test_pattern_filter(self, populated_vault):
        """Issue #5: glob pattern to narrow results."""
        result = list_notes(pattern="note-0?.md")
        assert result.success
        # note-00..note-09 in both folders = 20 matches, but folder b only has 0-9 (10),
        # folder a has 0-9 (10) = 20 total.
        assert "20 total" in result.data

    def test_pattern_and_folder_combined(self, populated_vault):
        result = list_notes(carpeta="b", pattern="note-0?.md")
        assert result.success
        assert "10 total" in result.data

    def test_negative_limit_rejected(self, populated_vault):
        result = list_notes(limit=-1)
        assert not result.success
        assert "limit" in (result.error or "")

    def test_negative_offset_rejected(self, populated_vault):
        result = list_notes(offset=-5)
        assert not result.success
        assert "offset" in (result.error or "")

    def test_offset_past_end_returns_empty_page_message(self, populated_vault):
        result = list_notes(offset=100, limit=10)
        assert result.success
        assert "No notes in this page" in result.data
        assert "Total visibles: 25" in result.data

    def test_nonexistent_folder(self, populated_vault):
        result = list_notes(carpeta="zzz")
        assert not result.success
        assert "does not exist" in (result.error or "")
