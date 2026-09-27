"""MCP note creation and editing tools."""

import json
from time import perf_counter

from fastmcp import FastMCP

from ..config import get_vault_path
from ..messages import ERRORS
from ..middleware import enrich_response, invalidate_rules_cache
from ..models.tool_inputs import EditOperation
from ..utils import find_note_by_name
from .creation_logic import (
    _extract_frontmatter_from_content,
    append_to_section,
    edit_note,
    get_frontmatter_logic,
    inbox_capture_frontmatter,
    manage_tags_logic,
    normalize_edit_operations,
    note_relative_path,
    resolve_create_folder,
    search_and_replace_global,
    suggest_folder_location,
    update_frontmatter_logic,
)
from .creation_logic import (
    append_to_note as append_to_note_logic,
)
from .creation_logic import (
    create_note as create_note_logic,
)
from .creation_logic import (
    delete_note as delete_note_logic,
)
from .creation_logic import (
    list_templates as list_templates_logic,
)
from .creation_logic import (
    quick_capture as quick_capture_logic,
)
from .registry import register_tool


def _with_duration(result: str, started_at: float) -> str:
    """Append elapsed time context for synchronous write operations."""
    return f"{result}\n- Duración: {perf_counter() - started_at:.2f}s"


def _extract_fm(content: str) -> dict:
    """Extract frontmatter dict from content for middleware validation."""
    frontmatter, _ = _extract_frontmatter_from_content(content)
    return frontmatter


def _vault_rel_path(note_path: str) -> str:
    """Vault-relative path of an existing note, for path-filtered vault rules."""
    vault_path = get_vault_path()
    found = find_note_by_name(note_path)
    if not vault_path or found is None:
        return ""
    try:
        return found.resolve().relative_to(vault_path.resolve()).as_posix()
    except ValueError:
        return ""


def _parse_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def register_creation_tools(mcp: FastMCP) -> None:  # pylint: disable=too-many-statements
    """Register note creation and editing tools."""

    @register_tool(mcp, "templates.list")
    def list_templates() -> str:
        """List available note templates."""
        try:
            return list_templates_logic().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error listing templates: {e}"

    @register_tool(mcp, "notes.suggest_location")
    def suggest_note_location(title: str, content: str, tags: str = "") -> str:
        """Suggest candidate vault folders for a new note."""
        try:
            return suggest_folder_location(title, content, tags)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error suggesting note location: {e}"

    @register_tool(mcp, "notes.create")
    def create_note(
        title: str,
        content: str,
        *,
        folder: str = "",
        tags: str = "",
        template: str = "",
        creator: str = "",
        description: str = "",
    ) -> str:
        """Create a new Markdown note in the vault.

        Paths are vault-relative. `folder` is a path relative to the vault root
        (e.g. "Projects/AFP"); missing parent folders are created automatically.
        Leave `folder` empty to auto-suggest a location (falls back to the vault
        root). The `.md` extension is added if omitted. Does not require
        confirmation, so this never overwrites an existing note: if one already
        exists at the target path, creation fails instead of replacing it (use
        notes.replace with confirm=True to overwrite).

        Args:
            title: Note title; also the filename (sanitized).
            content: Markdown body, optionally with YAML frontmatter.
            folder: Vault-relative target folder; parents auto-created.
            tags: Comma-separated tags.
            template: Template file name to apply.
            creator: Name of the creating agent.
            description: Short description for template placeholders.
        """
        try:
            folder = resolve_create_folder(title, content, tags, folder)
            logic_result = create_note_logic(
                title,
                content,
                folder,
                tags,
                template,
                creator,
                description,
            )
            result = logic_result.to_display(success_prefix="OK")
            if not logic_result.success:
                return result
            # Validate what was actually written (template + injected fields),
            # not just the `content` argument.
            note_path = note_relative_path(folder, title).as_posix()
            vault_path = get_vault_path()
            written = (
                (vault_path / note_path).read_text(encoding="utf-8")
                if vault_path
                else content
            )
            written_fm, written_body = _extract_frontmatter_from_content(written)
            return enrich_response(
                tool_name="notes.create",
                result=result,
                title=title,
                content=written_body if written_fm else written,
                frontmatter=written_fm,
                path=note_path,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error creating note: {e}"

    @register_tool(mcp, "notes.append")
    def append_to_note(
        note_path: str,
        content: str,
        position: str = "end",
        section: str = "",
        create_section: bool = True,
    ) -> str:
        """Append, prepend, or insert content into a section of a note."""
        try:
            normalized_position = position.strip().lower()
            if normalized_position == "section":
                if not section:
                    return "Error: section is required when position='section'."
                result = append_to_section(
                    note_path, section, content, create_section
                ).to_display(success_prefix="OK")
            elif normalized_position in {"end", "start", "append"}:
                if normalized_position == "append":
                    normalized_position = "end"
                result = append_to_note_logic(
                    note_path,
                    content,
                    al_final=normalized_position == "end",
                ).to_display(success_prefix="OK")
            else:
                return "Error: position must be 'end', 'append', 'start', or 'section'."

            return enrich_response(
                tool_name="notes.append",
                result=result,
                content=content,
                path=_vault_rel_path(note_path),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error appending to note: {e}"

    @register_tool(mcp, "notes.delete")
    def delete_note(note_path: str, confirm: bool = False) -> str:
        """Delete a note from the vault. Destructive: requires confirm=True.

        Pass confirm=True to proceed. The host shows its own permission prompt
        before the call runs, so that is the human approval surface; this gate
        just prevents accidental deletes.
        """
        if not confirm:
            return ERRORS.WRITE_REQUIRES_CONFIRM

        try:
            started_at = perf_counter()
            result = delete_note_logic(note_path, confirmar=True).to_display(
                success_prefix="OK"
            )
            return _with_duration(result, started_at)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error deleting note: {e}"

    @register_tool(mcp, "notes.patch")
    def patch_note(note_path: str, operations: list[EditOperation]) -> str:
        """Patch a note with atomic exact-match replacements.

        Each operation uses `old` for the unique text to replace and `new` for
        the replacement text. Common aliases (`oldText`/`newText` and
        `old_text`/`new_text`) are accepted for client compatibility.
        """
        try:
            normalized_result = normalize_edit_operations(operations)
            if not normalized_result.success:
                return f"Error: {normalized_result.error}"
            normalized_operations = normalized_result.data or []

            if any(operation["old"] == "" for operation in normalized_operations):
                return (
                    "Error: patch_note does not allow full-note replacement. "
                    "Use replace_note for that destructive operation."
                )

            result = edit_note(note_path, normalized_operations).to_display(
                success_prefix="OK"
            )
            if "REGLAS_GLOBALES" in note_path:
                invalidate_rules_cache()
            combined_new = "\n".join(
                operation["new"] for operation in normalized_operations
            )
            return enrich_response(
                tool_name="notes.patch",
                result=result,
                content=combined_new,
                path=_vault_rel_path(note_path),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error patching note: {e}"

    @register_tool(mcp, "notes.replace")
    def replace_note(note_path: str, content: str, confirm: bool = False) -> str:
        """Overwrite the full content of a note. Destructive: requires confirm=True.

        Pass confirm=True to proceed. The host shows its own permission prompt
        before the call runs, so that is the human approval surface; this gate
        just prevents accidental overwrites.
        """
        if not confirm:
            return ERRORS.WRITE_REQUIRES_CONFIRM

        try:
            started_at = perf_counter()
            edit_result = edit_note(
                note_path, [{"old": "", "new": content}]
            ).to_display(success_prefix="OK")
            if "REGLAS_GLOBALES" in note_path:
                invalidate_rules_cache()
            replaced_fm, replaced_body = _extract_frontmatter_from_content(content)
            result = enrich_response(
                tool_name="notes.replace",
                result=edit_result,
                content=replaced_body if replaced_fm else content,
                frontmatter=replaced_fm,
                path=_vault_rel_path(note_path),
            )
            return _with_duration(result, started_at)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error replacing note: {e}"

    @register_tool(mcp, "notes.preview_replace")
    def preview_replace_in_notes(
        search: str,
        replacement: str,
        folder: str = "",
        limit: int = 100,
    ) -> str:
        """Preview a literal search/replace across notes without writing files."""
        try:
            return search_and_replace_global(
                search,
                replacement,
                folder,
                solo_preview=True,
                limite=limit,
            ).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error previewing replacement: {e}"

    @register_tool(mcp, "notes.apply_replace")
    def apply_replace_in_notes(
        search: str,
        replacement: str,
        folder: str = "",
        limit: int = 100,
        confirm: bool = False,
    ) -> str:
        """Apply a literal search/replace across notes. Destructive: requires confirm=True.

        Preview first with preview_replace_in_notes, then pass confirm=True to
        write. The host shows its own permission prompt before the call runs.
        """
        if not confirm:
            return ERRORS.WRITE_REQUIRES_CONFIRM

        try:
            started_at = perf_counter()
            result = search_and_replace_global(
                search,
                replacement,
                folder,
                solo_preview=False,
                limite=limit,
            ).to_display()
            return _with_duration(result, started_at)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error applying replacement: {e}"

    @register_tool(mcp, "inbox.capture")
    def quick_capture(text: str, tags: str = "") -> str:
        """Capture an inbox note in the personal vault profile."""
        try:
            result = quick_capture_logic(text, tags).to_display()
            return enrich_response(
                tool_name="inbox.capture",
                result=result,
                title=text[:80],
                content=text,
                frontmatter=inbox_capture_frontmatter(tags),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error creating quick capture: {e}"

    @register_tool(mcp, "notes.get_frontmatter")
    def get_frontmatter(note_path: str) -> str:
        """Return only a note frontmatter block as JSON."""
        try:
            return get_frontmatter_logic(note_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading frontmatter: {e}"

    @register_tool(mcp, "notes.update_frontmatter")
    def update_frontmatter(
        note_path: str,
        frontmatter_updates: str,
        merge: bool = True,
    ) -> str:
        """Update a note frontmatter without changing the note body."""
        try:
            logic_result = update_frontmatter_logic(
                note_path,
                frontmatter_updates,
                merge,
            )
            result = logic_result.to_display(success_prefix="OK")
            if not logic_result.success:
                return result

            try:
                frontmatter = json.loads(frontmatter_updates)
            except (ValueError, TypeError):
                frontmatter = {}

            return enrich_response(
                tool_name="notes.update_frontmatter",
                result=result,
                frontmatter=frontmatter,
                path=_vault_rel_path(note_path),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error updating frontmatter: {e}"

    @register_tool(mcp, "notes.update_tags")
    def update_note_tags(note_path: str, operation: str, tags: str = "") -> str:
        """Add, remove, or set YAML tags on a note."""
        try:
            normalized_operation = operation.strip().lower()
            if normalized_operation in {"add", "remove"}:
                return manage_tags_logic(
                    note_path,
                    normalized_operation,
                    tags,
                ).to_display(success_prefix="OK")
            if normalized_operation == "set":
                tags_json = json.dumps(
                    {"tags": _parse_tags(tags)},
                    ensure_ascii=False,
                )
                result = update_frontmatter_logic(note_path, tags_json, merge=True)
                return result.to_display(success_prefix="OK")

            return "Error: operation must be 'add', 'remove', or 'set'."
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error updating note tags: {e}"
