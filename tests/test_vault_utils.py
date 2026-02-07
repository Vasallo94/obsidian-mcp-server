"""
Tests for vault utility functions.

These tests cover tag extraction, link extraction, file formatting,
and other shared utilities.
"""

from obsidian_mcp.utils.vault import (
    extract_internal_links,
    extract_tags_from_content,
    format_file_size,
    sanitize_filename,
)


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
        assert links == []

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
