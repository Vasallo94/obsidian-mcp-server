"""Tests for the shared wikilink scanning/rewriting engine."""

import pytest

from obsidian_mcp.utils.wikilinks import (
    parse_wikilink,
    rewrite_wikilinks_in_content,
    rewrite_wikilinks_in_vault,
    scan_broken_wikilinks,
)


@pytest.fixture
def vault(tmp_path):
    """Vault with cross-referenced notes for wikilink tests."""
    v = tmp_path / "vault"
    v.mkdir()
    (v / "A.md").write_text(
        "# A\nlink to [[B]] and [[C|alias]] and [[B#Section]]\n",
        encoding="utf-8",
    )
    (v / "B.md").write_text(
        "# B\nlink to [[A]] and ![[image.png]] and [[Missing Target]]\n",
        encoding="utf-8",
    )
    (v / "folder").mkdir()
    (v / "folder" / "C.md").write_text("# C\nbody\n", encoding="utf-8")
    return v


class TestParseWikilink:
    def test_bare_target(self):
        assert parse_wikilink("Note") == ("Note", None, None)

    def test_alias(self):
        assert parse_wikilink("Note|alias") == ("Note", None, "alias")

    def test_section(self):
        assert parse_wikilink("Note#Section") == ("Note", "Section", None)

    def test_section_and_alias(self):
        assert parse_wikilink("Note#Section|alias") == (
            "Note",
            "Section",
            "alias",
        )

    def test_whitespace_is_stripped(self):
        assert parse_wikilink("  Note  |  alias  ") == ("Note", None, "alias")


class TestScanBrokenWikilinks:
    def test_finds_missing_target(self, vault):
        broken = scan_broken_wikilinks(vault)
        targets = [b.occurrence.target for b in broken]
        assert "Missing Target" in targets
        assert "B" not in targets  # exists
        assert "C" not in targets  # exists in folder/

    def test_excludes_image_embeds(self, vault):
        broken = scan_broken_wikilinks(vault)
        assert all(b.occurrence.target != "image.png" for b in broken)

    def test_section_anchors_resolve_to_note(self, vault):
        """[[B#Section]] resolves if B.md exists, even if no Section heading."""
        broken = scan_broken_wikilinks(vault)
        assert all(b.occurrence.target != "B" for b in broken)

    def test_records_source_file_and_line(self, vault):
        broken = scan_broken_wikilinks(vault)
        miss = next(b for b in broken if b.occurrence.target == "Missing Target")
        assert miss.occurrence.source.name == "B.md"
        assert miss.occurrence.line_no == 2

    def test_suggests_close_matches(self, vault):
        # Add a near-miss target name to provoke a suggestion.
        (vault / "Missing Targets.md").write_text("# x\n", encoding="utf-8")
        broken = scan_broken_wikilinks(vault)
        miss = next(b for b in broken if b.occurrence.target == "Missing Target")
        assert "Missing Targets" in miss.suggestions


class TestRewriteWikilinksInContent:
    def test_simple_replace(self):
        new, count = rewrite_wikilinks_in_content(
            "see [[Old Name]] today",
            old_target="Old Name",
            new_target="New Name",
        )
        assert count == 1
        assert new == "see [[New Name]] today"

    def test_preserves_alias(self):
        new, _ = rewrite_wikilinks_in_content(
            "[[Old|click here]]", old_target="Old", new_target="New"
        )
        assert new == "[[New|click here]]"

    def test_preserves_section(self):
        new, _ = rewrite_wikilinks_in_content(
            "[[Old#Intro]]", old_target="Old", new_target="New"
        )
        assert new == "[[New#Intro]]"

    def test_preserves_section_and_alias(self):
        new, _ = rewrite_wikilinks_in_content(
            "[[Old#Intro|see here]]", old_target="Old", new_target="New"
        )
        assert new == "[[New#Intro|see here]]"

    def test_ignores_unrelated_links(self):
        new, count = rewrite_wikilinks_in_content(
            "[[Other]] and [[Old]] and [[Third]]",
            old_target="Old",
            new_target="Renamed",
        )
        assert count == 1
        assert new == "[[Other]] and [[Renamed]] and [[Third]]"

    def test_ignores_image_embeds(self):
        new, count = rewrite_wikilinks_in_content(
            "![[Old.png]] and [[Old]]",
            old_target="Old",
            new_target="New",
        )
        # Only the non-embed link is rewritten.
        assert count == 1
        assert "![[Old.png]]" in new
        assert "[[New]]" in new

    def test_old_equals_new_is_noop(self):
        new, count = rewrite_wikilinks_in_content(
            "[[Same]]", old_target="Same", new_target="Same"
        )
        assert count == 0
        assert new == "[[Same]]"


class TestRewriteWikilinksInVault:
    def test_updates_all_references(self, vault):
        # B is referenced from A
        total, touched = rewrite_wikilinks_in_vault(
            vault, old_target="B", new_target="Beta"
        )
        assert total >= 1
        assert any(p.name == "A.md" for p in touched)
        assert "[[Beta]]" in (vault / "A.md").read_text(encoding="utf-8")
        assert "[[Beta#Section]]" in (vault / "A.md").read_text(encoding="utf-8")

    def test_dry_run_does_not_write(self, vault):
        original_a = (vault / "A.md").read_text(encoding="utf-8")
        total, touched = rewrite_wikilinks_in_vault(
            vault, old_target="B", new_target="Beta", dry_run=True
        )
        assert total >= 1
        assert touched
        # File contents unchanged.
        assert (vault / "A.md").read_text(encoding="utf-8") == original_a

    def test_no_match_returns_zero(self, vault):
        total, touched = rewrite_wikilinks_in_vault(
            vault, old_target="NonExistent", new_target="X"
        )
        assert total == 0
        assert not touched
