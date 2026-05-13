"""MCP note creation and editing tools."""

import json

from fastmcp import Context, FastMCP

from ..middleware import enrich_response, invalidate_rules_cache
from ..models.tool_inputs import EditOperation
from .creation_logic import (
    append_to_note as append_to_note_logic,
)
from .creation_logic import (
    append_to_section,
    edit_note,
    get_frontmatter_logic,
    manage_tags_logic,
    normalize_edit_operations,
    search_and_replace_global,
    suggest_folder_location,
    update_frontmatter_logic,
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


def _extract_fm(content: str) -> dict:
    """Extract frontmatter dict from content for middleware validation."""
    from .creation_logic import _extract_frontmatter_from_content

    frontmatter, _ = _extract_frontmatter_from_content(content)
    return frontmatter


def _parse_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]


def register_creation_tools(mcp: FastMCP) -> None:  # pylint: disable=too-many-statements
    """Register note creation and editing tools."""

    @register_tool(mcp, "list_templates")
    def list_templates() -> str:
        """List available note templates."""
        try:
            return list_templates_logic().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error listing templates: {e}"

    @register_tool(mcp, "suggest_note_location")
    def suggest_note_location(title: str, content: str, tags: str = "") -> str:
        """Suggest candidate vault folders for a new note."""
        try:
            return suggest_folder_location(title, content, tags)
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error suggesting note location: {e}"

    @register_tool(mcp, "create_note")
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
        """Create a new Markdown note in the vault."""
        try:
            result = create_note_logic(
                title,
                content,
                folder,
                tags,
                template,
                creator,
                description,
            ).to_display(success_prefix="OK")
            return enrich_response(
                tool_name="create_note",
                result=result,
                title=title,
                content=content,
                frontmatter=_extract_fm(content),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error creating note: {e}"

    @register_tool(mcp, "append_to_note")
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
            elif normalized_position in {"end", "start"}:
                result = append_to_note_logic(
                    note_path,
                    content,
                    al_final=normalized_position == "end",
                ).to_display(success_prefix="OK")
            else:
                return "Error: position must be 'end', 'start', or 'section'."

            return enrich_response(
                tool_name="append_to_note",
                result=result,
                content=content,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error appending to note: {e}"

    @register_tool(mcp, "delete_note")
    async def delete_note(note_path: str, ctx: Context) -> str:
        """Delete a note after explicit client confirmation."""
        try:
            result = await ctx.elicit(
                f"Permanently delete '{note_path}'? This cannot be undone.",
                response_type=None,
            )
            if result.action != "accept":
                return "Operation cancelled."
        except Exception:  # pylint: disable=broad-exception-caught
            return (
                "Interactive confirmation is not supported by this client. "
                "The delete operation was cancelled for safety."
            )

        try:
            return delete_note_logic(note_path, confirmar=True).to_display(
                success_prefix="OK"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error deleting note: {e}"

    @register_tool(mcp, "patch_note")
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
                tool_name="patch_note",
                result=result,
                content=combined_new,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error patching note: {e}"

    @register_tool(mcp, "replace_note")
    async def replace_note(note_path: str, content: str, ctx: Context) -> str:
        """Replace the full content of a note after explicit confirmation."""
        try:
            confirmation = await ctx.elicit(
                f"Replace all content in '{note_path}'? This overwrites the note.",
                response_type=None,
            )
            if confirmation.action != "accept":
                return "Operation cancelled."
        except Exception:  # pylint: disable=broad-exception-caught
            return (
                "Interactive confirmation is not supported by this client. "
                "The replace operation was cancelled for safety."
            )

        try:
            edit_result = edit_note(
                note_path, [{"old": "", "new": content}]
            ).to_display(success_prefix="OK")
            if "REGLAS_GLOBALES" in note_path:
                invalidate_rules_cache()
            return enrich_response(
                tool_name="replace_note",
                result=edit_result,
                content=content,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error replacing note: {e}"

    @register_tool(mcp, "preview_replace_in_notes")
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

    @register_tool(mcp, "apply_replace_in_notes")
    async def apply_replace_in_notes(
        search: str,
        replacement: str,
        ctx: Context,
        folder: str = "",
        limit: int = 100,
    ) -> str:
        """Apply a literal search/replace across notes after confirmation."""
        try:
            result = await ctx.elicit(
                f"Replace '{search}' with '{replacement}' in up to {limit} notes"
                f"{f' under {folder}' if folder else ''}?",
                response_type=None,
            )
            if result.action != "accept":
                return "Operation cancelled."
        except Exception:  # pylint: disable=broad-exception-caught
            return (
                "Interactive confirmation is not supported by this client. "
                "Run preview_replace_in_notes first and retry with a client "
                "that supports confirmation."
            )

        try:
            return search_and_replace_global(
                search,
                replacement,
                folder,
                solo_preview=False,
                limite=limit,
            ).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error applying replacement: {e}"

    @register_tool(mcp, "quick_capture")
    def quick_capture(text: str, tags: str = "") -> str:
        """Capture an inbox note in the personal vault profile."""
        try:
            result = quick_capture_logic(text, tags).to_display()
            return enrich_response(
                tool_name="quick_capture",
                result=result,
                title=text[:80],
                content=text,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error creating quick capture: {e}"

    @register_tool(mcp, "get_frontmatter")
    def get_frontmatter(note_path: str) -> str:
        """Return only a note frontmatter block as JSON."""
        try:
            return get_frontmatter_logic(note_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading frontmatter: {e}"

    @register_tool(mcp, "update_frontmatter")
    def update_frontmatter(
        note_path: str,
        frontmatter_updates: str,
        merge: bool = True,
    ) -> str:
        """Update a note frontmatter without changing the note body."""
        try:
            result = update_frontmatter_logic(
                note_path,
                frontmatter_updates,
                merge,
            ).to_display(success_prefix="OK")

            try:
                frontmatter = json.loads(frontmatter_updates)
            except (ValueError, TypeError):
                frontmatter = {}

            return enrich_response(
                tool_name="update_frontmatter",
                result=result,
                frontmatter=frontmatter,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error updating frontmatter: {e}"

    @register_tool(mcp, "update_note_tags")
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
