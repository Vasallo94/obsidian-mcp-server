"""
Tests for the Result type and response models.

These tests cover core data structures used throughout the codebase.
"""

import pytest

from obsidian_mcp.models.responses import (
    BacklinkResult,
    ConnectionSuggestion,
    NoteMetadata,
    SearchResult,
    SemanticSearchResult,
    TagAnalysis,
    VaultStats,
)
from obsidian_mcp.result import Result


class TestResultType:
    """Tests for the generic Result type."""

    def test_ok_creates_successful_result(self):
        """Result.ok should create a successful result with data."""
        result = Result.ok("success data")
        assert result.success is True
        assert result.data == "success data"
        assert result.error is None

    def test_fail_creates_failed_result(self):
        """Result.fail should create a failed result with error."""
        result = Result.fail("something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "something went wrong"

    def test_bool_returns_success_status(self):
        """Result should be truthy when successful, falsy when failed."""
        assert bool(Result.ok("data")) is True
        assert bool(Result.fail("error")) is False

    def test_unwrap_returns_data_on_success(self):
        """unwrap should return data when result is successful."""
        result = Result.ok(42)
        assert result.unwrap() == 42

    def test_unwrap_raises_on_failure(self):
        """unwrap should raise ValueError when result is failed."""
        result = Result.fail("error message")
        with pytest.raises(ValueError, match="Cannot unwrap failed Result"):
            result.unwrap()

    def test_unwrap_or_returns_data_on_success(self):
        """unwrap_or should return data when successful."""
        result = Result.ok("actual")
        assert result.unwrap_or("default") == "actual"

    def test_unwrap_or_returns_default_on_failure(self):
        """unwrap_or should return default when failed."""
        result = Result.fail("error")
        assert result.unwrap_or("default") == "default"

    def test_map_error_returns_formatted_error(self):
        """map_error should format error with prefix."""
        result = Result.fail("file not found")
        assert result.map_error("❌") == "❌ file not found"
        assert result.map_error("ERROR:") == "ERROR: file not found"

    def test_map_error_returns_empty_on_success(self):
        """map_error should return empty string on success."""
        result = Result.ok("data")
        assert result.map_error() == ""

    def test_to_display_on_success(self):
        """to_display should return data string on success."""
        result = Result.ok("Note created")
        assert result.to_display() == "Note created"
        assert result.to_display(success_prefix="✅") == "✅ Note created"

    def test_to_display_on_failure(self):
        """to_display should return formatted error on failure."""
        result = Result.fail("Invalid path")
        assert result.to_display() == "❌ Invalid path"
        assert result.to_display(error_prefix="Error:") == "Error: Invalid path"

    def test_result_with_complex_data(self):
        """Result should work with complex data types."""
        data = {"notes": ["note1.md", "note2.md"], "count": 2}
        result = Result.ok(data)
        assert result.unwrap() == data
        assert result.unwrap()["count"] == 2


class TestNoteMetadata:
    """Tests for NoteMetadata model."""

    def test_create_valid_metadata(self):
        """Should create valid note metadata."""
        meta = NoteMetadata(
            name="Test Note.md",
            stem="Test Note",
            relative_path="folder/Test Note.md",
            size_kb=1.5,
            modified="2024-01-15T10:30:00",
            created="2024-01-10T08:00:00",
        )
        assert meta.name == "Test Note.md"
        assert meta.stem == "Test Note"
        assert meta.size_kb == 1.5

    def test_size_must_be_non_negative(self):
        """size_kb should not accept negative values."""
        with pytest.raises(ValueError):
            NoteMetadata(
                name="test.md",
                stem="test",
                relative_path="test.md",
                size_kb=-1.0,
                modified="2024-01-15",
                created="2024-01-10",
            )


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_create_search_result(self):
        """Should create a valid search result."""
        result = SearchResult(
            archivo="notes/idea.md",
            linea="15",
            tipo="content",
            coincidencia="matching text here",
        )
        assert result.archivo == "notes/idea.md"
        assert result.linea == "15"

    def test_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        result = SearchResult(
            archivo="test.md",
            coincidencia="match",
        )
        assert result.linea is None
        assert result.tipo is None


class TestVaultStats:
    """Tests for VaultStats model."""

    def test_create_vault_stats(self):
        """Should create valid vault statistics."""
        stats = VaultStats(
            vault_name="MyVault",
            vault_path="/path/to/vault",
            total_files=150,
            markdown_files=120,
            folders=25,
            last_scan="2024-01-15T12:00:00Z",
        )
        assert stats.vault_name == "MyVault"
        assert stats.markdown_files == 120
        assert stats.error is None

    def test_stats_with_error(self):
        """Should accept error message when scan fails."""
        stats = VaultStats(
            vault_name="MyVault",
            vault_path="/path/to/vault",
            total_files=0,
            markdown_files=0,
            folders=0,
            last_scan="2024-01-15T12:00:00Z",
            error="Permission denied",
        )
        assert stats.error == "Permission denied"


class TestTagAnalysis:
    """Tests for TagAnalysis model."""

    def test_create_tag_analysis(self):
        """Should create valid tag analysis."""
        analysis = TagAnalysis(
            tag="python",
            count=15,
            files=["note1.md", "note2.md"],
        )
        assert analysis.tag == "python"
        assert analysis.count == 15
        assert len(analysis.files) == 2

    def test_empty_files_list(self):
        """Should accept empty files list."""
        analysis = TagAnalysis(tag="unused", count=0)
        assert analysis.files == []


class TestBacklinkResult:
    """Tests for BacklinkResult model."""

    def test_create_backlink_result(self):
        """Should create valid backlink result."""
        result = BacklinkResult(
            source_note="Main Concept.md",
            linking_notes=["Related.md", "Another.md"],
            count=2,
        )
        assert result.source_note == "Main Concept.md"
        assert result.count == 2


class TestSemanticSearchResult:
    """Tests for SemanticSearchResult model."""

    def test_create_semantic_result(self):
        """Should create valid semantic search result."""
        result = SemanticSearchResult(
            content="Some relevant text about the topic",
            source="knowledge/topic.md",
            relevance=0.85,
        )
        assert result.content == "Some relevant text about the topic"
        assert result.relevance == 0.85
        assert result.metadata == {}
        assert result.links == []

    def test_semantic_result_with_links(self):
        """Should accept linked context."""
        result = SemanticSearchResult(
            content="Text with links",
            source="note.md",
            relevance=0.7,
            links=["[[Related]]", "[[Other]]"],
            linked_context=["Context from Related", "Context from Other"],
        )
        assert len(result.links) == 2
        assert len(result.linked_context) == 2


class TestConnectionSuggestion:
    """Tests for ConnectionSuggestion model."""

    def test_create_connection_suggestion(self):
        """Should create valid connection suggestion."""
        suggestion = ConnectionSuggestion(
            note_a="Python Basics.md",
            note_b="Programming Concepts.md",
            similarity=0.82,
            folder_a="02_Learning",
            folder_b="02_Learning",
            words_a=500,
            words_b=350,
            section_a="## Introduction",
            section_b="## Overview",
            reason="Both discuss fundamental programming concepts",
        )
        assert suggestion.similarity == 0.82
        assert "programming" in suggestion.reason.lower()

    def test_similarity_bounds(self):
        """Similarity should be between 0 and 1."""
        with pytest.raises(ValueError):
            ConnectionSuggestion(
                note_a="a.md",
                note_b="b.md",
                similarity=1.5,  # Invalid: > 1
                folder_a="",
                folder_b="",
                words_a=100,
                words_b=100,
                section_a="",
                section_b="",
                reason="",
            )
