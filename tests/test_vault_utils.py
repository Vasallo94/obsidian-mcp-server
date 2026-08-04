"""
Tests for vault utility functions.

These tests cover tag extraction, link extraction, file formatting,
and other shared utilities.
"""

from pathlib import Path

import pytest

from obsidian_mcp.utils import vault as vault_utils
from obsidian_mcp.utils.vault import (
    atomic_write_text,
    extract_internal_links,
    extract_tags_from_content,
    format_file_size,
    sanitize_filename,
)


class TestAtomicWriteText:
    """Tests for crash-safe single-file replacement."""

    def test_replaces_complete_file(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"
        path.write_text("old", encoding="utf-8")
        original_mode = path.stat().st_mode & 0o777

        atomic_write_text(path, "new")

        assert path.read_text(encoding="utf-8") == "new"
        assert path.stat().st_mode & 0o777 == original_mode
        assert not list(tmp_path.glob(".note.md.*.tmp"))

    def test_new_file_is_private(self, tmp_path: Path) -> None:
        path = tmp_path / "note.md"

        atomic_write_text(path, "new")

        assert path.stat().st_mode & 0o777 == 0o600

    def test_invalid_encoding_cleans_up_and_preserves_error(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / "note.md"

        with pytest.raises(LookupError):
            atomic_write_text(path, "content", encoding="no-such-encoding")

        assert not path.exists()
        assert not list(tmp_path.glob(".note.md.*.tmp"))

    def test_replace_failure_preserves_original(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "note.md"
        path.write_text("original", encoding="utf-8")

        def fail_replace(_source: Path, _destination: Path) -> None:
            raise OSError("simulated replace failure")

        monkeypatch.setattr(vault_utils.os, "replace", fail_replace)

        with pytest.raises(OSError, match="simulated replace failure"):
            atomic_write_text(path, "replacement")

        assert path.read_text(encoding="utf-8") == "original"
        assert not list(tmp_path.glob(".note.md.*.tmp"))


class TestExtractTagsFromContent:
    """Tests for tag extraction from note content."""

    def test_extract_inline_tags(self):
        """Should extract #tags from body text."""
        content = "This note is about #python and #programming"
        tags = extract_tags_from_content(content)
        assert "python" in tags
        assert "programming" in tags

    def test_extract_tags_with_hyphens(self):
        """Should extract tags containing hyphens."""
        content = "Working on #machine-learning and #deep-learning"
        tags = extract_tags_from_content(content)
        assert "machine-learning" in tags
        assert "deep-learning" in tags

    def test_extract_tags_from_yaml_frontmatter_array(self):
        """Should extract tags from YAML frontmatter with array format."""
        content = """---
title: Test Note
tags: [python, testing, automation]
---

# Content here
"""
        tags = extract_tags_from_content(content)
        assert "python" in tags
        assert "testing" in tags
        assert "automation" in tags

    def test_combined_frontmatter_and_inline_tags(self):
        """Should extract tags from both frontmatter and body."""
        content = """---
tags: [meta]
---

# Header
Some content with #inline-tag here.
"""
        tags = extract_tags_from_content(content)
        assert "meta" in tags
        assert "inline-tag" in tags

    def test_no_tags_returns_empty(self):
        """Should return empty list when no tags present."""
        content = "This is plain content without any tags."
        tags = extract_tags_from_content(content)
        assert tags == []

    def test_heading_hashes_not_treated_as_tags(self):
        """Should not confuse markdown headings with tags."""
        content = """# This is a heading
## Another heading
Regular text here.
"""
        tags = extract_tags_from_content(content)
        # Headings should not be captured as tags
        assert "This" not in tags
        assert "Another" not in tags

    def test_duplicate_tags_deduplicated(self):
        """Should remove duplicate tags."""
        content = "#python #automation #python"
        tags = extract_tags_from_content(content)
        assert tags.count("python") == 1

    def test_extract_tags_from_yaml_block_list_quoted(self):
        """Should parse a YAML block list of quoted tags (real bug report).

        Regression test for the '#- "media"' bug: notes under
        05_Recursos/Media/* use this exact frontmatter shape, and the old
        line-by-line regex extractor produced a single garbage tag
        literally equal to '- "media"' instead of parsing the YAML list.
        """
        content = """---
title: "Inception"
tags:
  - "media"
  - "media/peliculas"
date: 2024-01-01
---

Body content here.
"""
        tags = extract_tags_from_content(content)
        assert "media" in tags
        assert "media/peliculas" in tags
        # No garbage entries carrying the raw YAML list-item syntax.
        assert not any(t.startswith("-") or '"' in t for t in tags)
        assert len(tags) == 2

    def test_extract_tags_from_yaml_block_list_unquoted(self):
        """Should parse a YAML block list of unquoted tags."""
        content = """---
tags:
  - proyecto
  - obsidian-mcp
---

Body.
"""
        tags = extract_tags_from_content(content)
        assert "proyecto" in tags
        assert "obsidian-mcp" in tags

    def test_extract_tags_from_yaml_frontmatter_string_scalar(self):
        """Should parse a single scalar tag (no list, no array)."""
        content = """---
tags: solo-tag
---

Body.
"""
        tags = extract_tags_from_content(content)
        assert tags == ["solo-tag"]

    def test_inline_tags_ignore_fenced_code_blocks(self):
        """Inline #tag detection must skip fenced code blocks.

        Otherwise pasted changelog/log snippets like '(#80)' get treated
        as tags, producing garbage entries such as '#40'-'#45'.
        """
        content = """Some note about #realtag here.

```
chore(deps): update pyyaml requirement (#80)
chore(deps): bump langsmith from 0.8.3 to 0.8.18 (#84)
```
"""
        tags = extract_tags_from_content(content)
        assert "realtag" in tags
        assert "80" not in tags
        assert "84" not in tags

    def test_inline_tags_ignore_inline_code_spans(self):
        """Inline #tag detection must skip inline code spans."""
        content = "Real #tag1 but not `#notatag` in code span."
        tags = extract_tags_from_content(content)
        assert "tag1" in tags
        assert "notatag" not in tags


class TestExtractInternalLinks:
    """Tests for internal link extraction."""

    def test_extract_simple_wikilinks(self):
        """Should extract [[Link]] format links."""
        content = "See [[Related Note]] and [[Another Note]]"
        links = extract_internal_links(content)
        assert "Related Note" in links
        assert "Another Note" in links

    def test_extract_wikilinks_with_aliases(self):
        """Should extract links with display aliases."""
        content = "Check [[Actual Note|Display Text]] for details"
        links = extract_internal_links(content)
        assert "Actual Note|Display Text" in links

    def test_extract_wikilinks_with_headings(self):
        """Should extract links to specific headings."""
        content = "See [[Note#Section]] for more"
        links = extract_internal_links(content)
        assert "Note#Section" in links

    def test_no_links_returns_empty(self):
        """Should return empty list when no links present."""
        content = "Plain text without any links."
        links = extract_internal_links(content)
        assert not links

    def test_duplicate_links_deduplicated(self):
        """Should remove duplicate links."""
        content = "[[Note]] and [[Note]] again"
        links = extract_internal_links(content)
        assert len(links) == 1
        assert "Note" in links


class TestFormatFileSize:
    """Tests for file size formatting."""

    def test_format_bytes(self):
        """Should format small sizes in bytes."""
        assert format_file_size(500) == "500B"
        assert format_file_size(0) == "0B"

    def test_format_kilobytes(self):
        """Should format KB sizes."""
        assert format_file_size(1024) == "1.0KB"
        assert format_file_size(2560) == "2.5KB"

    def test_format_megabytes(self):
        """Should format MB sizes."""
        assert format_file_size(1024 * 1024) == "1.0MB"
        assert format_file_size(5 * 1024 * 1024) == "5.0MB"

    def test_boundary_values(self):
        """Should handle boundary values correctly."""
        assert format_file_size(1023) == "1023B"
        assert format_file_size(1024) == "1.0KB"


class TestSanitizeFilename:
    """Tests for filename sanitization."""

    def test_adds_md_extension(self):
        """Should add .md extension if missing."""
        assert sanitize_filename("note") == "note.md"

    def test_keeps_existing_extension(self):
        """Should not double-add .md extension."""
        assert sanitize_filename("note.md") == "note.md"

    def test_replaces_forward_slashes(self):
        """Should replace / with -."""
        assert sanitize_filename("path/to/note") == "path-to-note.md"

    def test_replaces_backslashes(self):
        """Should replace \\ with -."""
        assert sanitize_filename("path\\to\\note") == "path-to-note.md"

    def test_replaces_invalid_characters(self):
        """Should replace characters invalid in filenames."""
        assert sanitize_filename("note<>:test") == "note---test.md"
        assert sanitize_filename('file"name') == "file-name.md"
        assert sanitize_filename("what?why*") == "what-why-.md"

    def test_handles_normal_names(self):
        """Should not modify valid filenames."""
        assert sanitize_filename("My Normal Note.md") == "My Normal Note.md"
        assert sanitize_filename("Note with spaces") == "Note with spaces.md"
