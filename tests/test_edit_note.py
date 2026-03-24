"""Tests for the redesigned edit_note with old/new partial edit operations."""

import pytest

from obsidian_mcp.tools.creation_logic import edit_note


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    return vault


@pytest.fixture
def sample_note(temp_vault):
    """Create a sample note for editing tests."""
    note = temp_vault / "test_note.md"
    note.write_text(
        "---\ntitle: Test\ncreated: 2026-01-01\n---\n\n# Test Note\n\n"
        "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n",
        encoding="utf-8",
    )
    return note


def _patch_vault(monkeypatch, vault_path):
    """Helper to monkeypatch vault path and find_note_by_name."""
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.get_vault_path",
        lambda: vault_path,
    )
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.find_note_by_name",
        lambda name: vault_path / name if (vault_path / name).exists() else None,
    )


# === Happy Path ===


class TestEditNoteHappyPath:
    """Tests for successful edit operations."""

    def test_single_replace(self, temp_vault, sample_note, monkeypatch):
        """Single old->new replacement."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [{"old": "First paragraph.", "new": "Updated paragraph."}])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "Updated paragraph." in content
        assert "First paragraph." not in content
        assert "Second paragraph." in content  # untouched

    def test_multiple_operations(self, temp_vault, sample_note, monkeypatch):
        """Multiple operations applied atomically."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "Replaced first."},
            {"old": "Third paragraph.", "new": "Replaced third."},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "Replaced first." in content
        assert "Replaced third." in content
        assert "Second paragraph." in content  # untouched

    def test_insert_after_anchor(self, temp_vault, sample_note, monkeypatch):
        """Insert text after an anchor by including anchor in new."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "First paragraph.\n\nInserted paragraph."},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "First paragraph.\n\nInserted paragraph." in content

    def test_delete_fragment(self, temp_vault, sample_note, monkeypatch):
        """Delete a fragment by setting new to empty string."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "Second paragraph.\n\n", "new": ""},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "Second paragraph." not in content

    def test_full_replace(self, temp_vault, sample_note, monkeypatch):
        """Full replace mode with old=''."""
        _patch_vault(monkeypatch, temp_vault)
        new_content = "---\ntitle: Replaced\n---\n\n# New Title\n\nNew body.\n"
        result = edit_note("test_note.md", [{"old": "", "new": new_content}])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "New body." in content
        assert "First paragraph." not in content

    def test_noop_old_equals_new(self, temp_vault, sample_note, monkeypatch):
        """old == new is accepted silently as a no-op."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "First paragraph."},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "First paragraph." in content

    def test_updated_field_set(self, temp_vault, sample_note, monkeypatch):
        """The 'updated' frontmatter field should be set after editing."""
        _patch_vault(monkeypatch, temp_vault)
        edit_note("test_note.md", [{"old": "First paragraph.", "new": "Changed."}])
        content = sample_note.read_text(encoding="utf-8")
        assert "updated:" in content

    def test_success_message_format(self, temp_vault, sample_note, monkeypatch):
        """Success message includes operation count."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "A."},
            {"old": "Third paragraph.", "new": "B."},
        ])
        assert result.success
        assert "2 operaciones" in result.data

    def test_full_replace_message(self, temp_vault, sample_note, monkeypatch):
        """Full replace success message says 'reemplazo total'."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [{"old": "", "new": "---\ntitle: X\n---\n\nBody\n"}])
        assert result.success
        assert "reemplazo total" in result.data


# === Atomic Failure ===


class TestEditNoteAtomicFailure:
    """Tests for atomic failure behavior -- note must remain unchanged."""

    def test_old_not_found(self, temp_vault, sample_note, monkeypatch):
        """Fail if old text is not found in the note."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [{"old": "nonexistent text", "new": "x"}])
        assert not result.success
        assert "No se encontro" in result.error
        assert sample_note.read_text(encoding="utf-8") == original  # unchanged

    def test_old_appears_multiple_times(self, temp_vault, monkeypatch):
        """Fail if old text appears more than once (ambiguity)."""
        note = temp_vault / "dup.md"
        note.write_text("hello world\nhello world\n", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        original = note.read_text(encoding="utf-8")
        result = edit_note("dup.md", [{"old": "hello world", "new": "hi"}])
        assert not result.success
        assert "aparece" in result.error
        assert "2 veces" in result.error
        assert note.read_text(encoding="utf-8") == original

    def test_overlapping_operations(self, temp_vault, sample_note, monkeypatch):
        """Fail if two operations affect overlapping text."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "First paragraph.\n\nSecond", "new": "A"},
            {"old": "Second paragraph.", "new": "B"},
        ])
        assert not result.success
        assert "mismo fragmento" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_full_replace_with_other_ops(self, temp_vault, sample_note, monkeypatch):
        """Fail if full-replace (old='') is combined with other operations."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "", "new": "full content"},
            {"old": "First paragraph.", "new": "x"},
        ])
        assert not result.success
        assert "unica operacion" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_old_empty_new_empty(self, temp_vault, sample_note, monkeypatch):
        """Fail if old='' and new='' (would erase file)."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [{"old": "", "new": ""}])
        assert not result.success
        assert "eliminar_nota" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_empty_operations_list(self, temp_vault, sample_note, monkeypatch):
        """Fail if operations list is empty."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [])
        assert not result.success
        assert "al menos una" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_note_not_found(self, temp_vault, monkeypatch):
        """Fail if note does not exist."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("nonexistent.md", [{"old": "x", "new": "y"}])
        assert not result.success

    def test_batch_fails_atomically(self, temp_vault, sample_note, monkeypatch):
        """If one op in a batch fails, no ops are applied."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "Changed."},  # would succeed
            {"old": "nonexistent text", "new": "x"},  # fails
        ])
        assert not result.success
        assert sample_note.read_text(encoding="utf-8") == original  # nothing changed

    def test_max_operations_exceeded(self, temp_vault, sample_note, monkeypatch):
        """Fail if more than 50 operations are submitted."""
        _patch_vault(monkeypatch, temp_vault)
        ops = [{"old": "First paragraph.", "new": f"v{i}"} for i in range(51)]
        result = edit_note("test_note.md", ops)
        assert not result.success
        assert "50" in result.error


# === Edge Cases ===


class TestEditNoteEdgeCases:
    """Tests for edge cases."""

    def test_empty_note_partial_fails(self, temp_vault, monkeypatch):
        """Partial edit on empty note fails (old not found)."""
        note = temp_vault / "empty.md"
        note.write_text("", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("empty.md", [{"old": "something", "new": "x"}])
        assert not result.success

    def test_empty_note_full_replace_works(self, temp_vault, monkeypatch):
        """Full replace on empty note works."""
        note = temp_vault / "empty.md"
        note.write_text("", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("empty.md", [{"old": "", "new": "---\ntitle: New\n---\n\nContent\n"}])
        assert result.success
        assert "Content" in note.read_text(encoding="utf-8")

    def test_old_with_trailing_whitespace(self, temp_vault, monkeypatch):
        """old with trailing whitespace must match exactly."""
        note = temp_vault / "ws.md"
        note.write_text("hello world  \ngoodbye\n", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        # Exact match including trailing spaces
        result = edit_note("ws.md", [{"old": "hello world  ", "new": "hello world"}])
        assert result.success

    def test_edit_frontmatter_field(self, temp_vault, monkeypatch):
        """Edit a field inside the YAML frontmatter."""
        note = temp_vault / "fm_edit.md"
        note.write_text(
            "---\ntitle: Old Title\ncreated: 2026-01-01\ntags:\n  - draft\n---\n\nBody\n",
            encoding="utf-8",
        )
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("fm_edit.md", [
            {"old": "title: Old Title", "new": "title: New Title"},
        ])
        assert result.success
        content = note.read_text(encoding="utf-8")
        assert "title: New Title" in content
        assert "tags:" in content  # other fields untouched

    def test_user_sets_updated_field(self, temp_vault, monkeypatch):
        """If user operation sets 'updated', system does not override it."""
        note = temp_vault / "fm.md"
        note.write_text(
            "---\ntitle: Test\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nBody\n",
            encoding="utf-8",
        )
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("fm.md", [
            {"old": "updated: 2026-01-01", "new": "updated: 2099-12-31"},
        ])
        assert result.success
        content = note.read_text(encoding="utf-8")
        assert "updated: 2099-12-31" in content
