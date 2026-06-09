"""Tests for _normalize_frontmatter — deduplication of YAML keys.

Regression: LLM clients sometimes emit YAML with repeated keys
(e.g. two ``created:`` lines). The normalizer re-parses through
yaml round-trip before every disk write to guarantee valid YAML.
"""

import pytest

from obsidian_mcp.tools.creation_logic import (
    _normalize_frontmatter,
    create_note,
    edit_note,
)


# --- Unit tests for _normalize_frontmatter ---


class TestNormalizeFrontmatter:
    def test_duplicate_created_is_deduplicated(self):
        content = (
            "---\n"
            "title: Test\n"
            "created: 2026-06-09\n"
            "type: nota\n"
            "created: '2026-06-09'\n"
            "---\n\n"
            "# Body\n"
        )
        result = _normalize_frontmatter(content)
        assert result.count("created:") == 1
        assert "# Body" in result

    def test_last_value_wins(self):
        content = (
            "---\n"
            "title: First\n"
            "title: Second\n"
            "---\n\n"
            "body\n"
        )
        result = _normalize_frontmatter(content)
        assert result.count("title:") == 1
        assert "Second" in result

    def test_no_frontmatter_unchanged(self):
        content = "# Just a heading\n\nSome text.\n"
        assert _normalize_frontmatter(content) == content

    def test_valid_frontmatter_roundtrips_cleanly(self):
        content = (
            "---\n"
            "title: Clean\n"
            "created: 2026-01-01\n"
            "tags:\n"
            "- one\n"
            "- two\n"
            "---\n\n"
            "body\n"
        )
        result = _normalize_frontmatter(content)
        assert "title:" in result
        assert "created:" in result
        assert "body" in result

    def test_body_preserved_after_normalization(self):
        body = "## Section\n\nParagraph with `code` and **bold**.\n"
        content = (
            "---\n"
            "title: X\n"
            "title: Y\n"
            "---\n\n"
            + body
        )
        result = _normalize_frontmatter(content)
        assert body in result

    def test_invalid_yaml_left_untouched(self):
        content = "---\n: bad yaml [\n---\n\nbody\n"
        assert _normalize_frontmatter(content) == content


# --- Integration tests with create_note ---


@pytest.fixture
def temp_vault(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.get_vault_path",
        lambda: vault,
    )
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.get_vault_config",
        lambda *_args, **_kwargs: None,
    )
    return vault


class TestCreateNoteDeduplicatesFrontmatter:
    def test_embedded_duplicate_created_is_cleaned(self, temp_vault):
        embedded = (
            "---\n"
            "title: Idea\n"
            "created: 2026-06-09\n"
            "type: investigacion\n"
            "status: borrador\n"
            "created: '2026-06-09'\n"
            "tags: [idea]\n"
            "---\n\n"
            "## Body\n"
        )
        result = create_note(
            titulo="Idea",
            contenido=embedded,
            carpeta="notes",
        )
        assert result.success
        content = (temp_vault / "notes" / "Idea.md").read_text(encoding="utf-8")
        assert content.count("created:") == 1


class TestEditNoteDeduplicatesFrontmatter:
    def test_full_replace_deduplicates(self, temp_vault, monkeypatch):
        note = temp_vault / "test.md"
        note.write_text("---\ntitle: Old\n---\n\nbody\n", encoding="utf-8")
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note if note.exists() else None,
        )

        dup_content = (
            "---\n"
            "title: New\n"
            "created: 2026-06-09\n"
            "type: nota\n"
            "created: '2026-06-09'\n"
            "---\n\n"
            "new body\n"
        )
        result = edit_note("test.md", [{"old": "", "new": dup_content}])
        assert result.success
        content = note.read_text(encoding="utf-8")
        assert content.count("created:") == 1

    def test_partial_edit_deduplicates(self, temp_vault, monkeypatch):
        note = temp_vault / "test.md"
        note.write_text(
            "---\ntitle: Test\ncreated: 2026-01-01\ncreated: '2026-01-01'\n---\n\nbody\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "obsidian_mcp.tools.creation_logic.find_note_by_name",
            lambda name: note if note.exists() else None,
        )

        result = edit_note("test.md", [{"old": "body", "new": "changed"}])
        assert result.success
        content = note.read_text(encoding="utf-8")
        assert content.count("created:") == 1
