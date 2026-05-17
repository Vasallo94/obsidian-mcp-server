"""End-to-end tests for the wikilink-hygiene tools (Issues #6, #7, #11)."""

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.tools.analysis_logic import find_broken_wikilinks
from obsidian_mcp.tools.navigation_logic import move_note


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    v.mkdir()
    (v / "A.md").write_text(
        "# A\n[[B]] and [[C|cee]] and [[Missing]]\n",
        encoding="utf-8",
    )
    (v / "B.md").write_text("# B\n[[A]] [[Missing#sec]]\n", encoding="utf-8")
    (v / "C.md").write_text("# C\nbody\n", encoding="utf-8")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    reset_settings()
    return v


class TestFindBrokenWikilinks:
    """Issue #6."""

    def test_reports_broken_links_with_source_and_line(self, vault):
        result = find_broken_wikilinks()
        assert result.success
        text = result.data
        assert "Missing" in text
        assert "A.md" in text
        assert "B.md" in text
        # Format: "  L<n>: [[Missing]]" -- line number must be present
        assert "L2" in text

    def test_no_broken_links_returns_ok(self, tmp_path, monkeypatch):
        v = tmp_path / "clean"
        v.mkdir()
        (v / "x.md").write_text("# x\n[[y]]\n", encoding="utf-8")
        (v / "y.md").write_text("# y\n[[x]]\n", encoding="utf-8")
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
        reset_settings()
        result = find_broken_wikilinks()
        assert result.success
        assert "No se encontraron" in result.data

    def test_suggestions_for_typo(self, vault):
        # Add a near-stem so the fuzzy matcher has something to suggest.
        (vault / "Missing Note.md").write_text("# m\n", encoding="utf-8")
        result = find_broken_wikilinks()
        assert "Missing Note" in result.data

    def test_limit_caps_results(self, vault):
        result = find_broken_wikilinks(limit=1)
        assert result.success
        assert "mas" in result.data or "más" in result.data or "1 (" in result.data


class TestMoveNoteUpdateLinks:
    """Issues #7 and #11."""

    def test_update_links_rewrites_references(self, vault):
        """Moving B.md to Beta.md with update_links=True rewrites [[B]] -> [[Beta]]."""
        result = move_note("B.md", "Beta.md", update_links=True)
        assert result.success
        a_content = (vault / "A.md").read_text(encoding="utf-8")
        assert "[[Beta]]" in a_content
        assert "[[B]]" not in a_content
        assert "Links updated:" in result.data

    def test_warns_when_links_left_stale(self, vault):
        """Issue #11: default move surfaces unresolved references count."""
        result = move_note("B.md", "Beta.md", update_links=False)
        assert result.success
        # A.md references [[B]]; the move leaves it stale.
        assert "old stem 'B'" in result.data
        assert "Re-run with update_links=True" in result.data

    def test_preserves_alias_when_renaming(self, vault):
        result = move_note("C.md", "Charlie.md", update_links=True)
        assert result.success
        a_content = (vault / "A.md").read_text(encoding="utf-8")
        assert "[[Charlie|cee]]" in a_content

    def test_no_warning_when_no_references(self, vault):
        # D.md has no incoming references.
        (vault / "D.md").write_text("# D\nstandalone\n", encoding="utf-8")
        result = move_note("D.md", "DD.md", update_links=False)
        assert result.success
        assert "old stem" not in result.data
        assert "Re-run" not in result.data
