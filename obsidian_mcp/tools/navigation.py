"""Navigation tools for the Obsidian vault."""

from pathlib import Path

from fastmcp import Context, FastMCP

from ..config import get_vault_path
from ..utils import get_logger, is_path_forbidden
from .navigation_logic import (
    get_notes_info_logic,
    get_random_concept,
    read_multiple_notes_logic,
)
from .navigation_logic import (
    list_notes as list_notes_logic,
)
from .navigation_logic import (
    move_note as move_note_logic,
)
from .navigation_logic import (
    read_note as read_note_logic,
)
from .navigation_logic import (
    search_notes_by_date as search_notes_by_date_logic,
)
from .registry import register_tool

logger = get_logger(__name__)


def _format_search_results(results: list[dict[str, str]], titles_only: bool) -> str:
    """Format search output."""
    output = f"Found {len(results)} matches:\n\n"

    by_file: dict[str, list[dict[str, str]]] = {}
    for result in results:
        file_name = result["file"]
        if file_name not in by_file:
            by_file[file_name] = []
        by_file[file_name].append(result)

    for file_name, matches in list(by_file.items())[:20]:
        output += f"**{file_name}**\n"
        for match in matches:
            if titles_only:
                output += f"   {match['match']}\n"
            else:
                output += f"   L{match['line']}: {match['match']}\n"
        output += "\n"

    if len(by_file) > 20:
        output += f"... and {len(by_file) - 20} more files."

    return output


def register_navigation_tools(mcp: FastMCP) -> None:  # pylint: disable=too-many-statements
    """Register navigation tools."""

    @register_tool(mcp, "list_notes")
    def list_notes(
        folder: str = "",
        include_subfolders: bool = True,
        limit: int = 500,
        offset: int = 0,
        pattern: str = "",
    ) -> str:
        """
        List Markdown notes in the vault or in a specific folder.

        Args:
            folder: Folder to explore. Empty means the vault root.
            include_subfolders: Whether to include nested folders.
            limit: Max notes per page (0 = no limit). Defaults to 500.
            offset: Start index (after path sort).
            pattern: Optional glob (e.g. "2026-*.md") layered on top of *.md.
        """
        try:
            return list_notes_logic(
                folder, include_subfolders, limit=limit, offset=offset, pattern=pattern
            ).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error listing notes: {e}"

    @register_tool(mcp, "read_note")
    def read_note(note_path: str) -> str:
        """
        Read the full content of a note.

        Args:
            note_path: Note name or path, for example "Daily/2024-01-01.md".
        """
        try:
            return read_note_logic(note_path).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Error reading note: {e}"

    @register_tool(mcp, "search_notes")
    def search_notes(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-nested-blocks
        query: str,
        folder: str = "",
        titles_only: bool = False,
    ) -> str:
        """
        Search note titles or note content with AND semantics.

        Args:
            query: Search text. Multiple words must all be present.
            folder: Folder to search. Empty means the whole vault.
            titles_only: Search only note titles.
        """
        import shutil  # pylint: disable=import-outside-toplevel
        import subprocess  # pylint: disable=import-outside-toplevel # nosec B404

        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "Error: Vault path is not configured."

            if folder:
                search_path = vault_path / folder
                if not search_path.exists():
                    return f"Folder does not exist: {folder}"
            else:
                search_path = vault_path

            terms = [term.strip() for term in query.split() if term.strip()]
            if not terms:
                return "Search query cannot be empty."

            short_term_tip = ""
            short_terms = [term for term in terms if len(term) <= 3]
            if short_terms and not titles_only:
                short_term_tip = (
                    f"Tip: for short terms like '{short_terms[0]}', consider "
                    "`titles_only=True` for better precision.\n\n"
                )

            results: list[dict[str, str]] = []
            matching_files: set[str] = set()
            rg_path = shutil.which("rg")

            if rg_path and not titles_only:
                try:
                    command = [
                        rg_path,
                        "--ignore-case",
                        "--files-with-matches",
                        "--null",
                        "-g",
                        "*.md",
                        terms[0],
                        str(search_path),
                    ]
                    result = subprocess.run(  # pylint: disable=subprocess-run-check # nosec B603
                        command,
                        capture_output=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        raw_paths = result.stdout.decode(
                            "utf-8", errors="ignore"
                        ).split("\0")
                        candidates = [path for path in raw_paths if path]
                        if len(terms) > 1:
                            for candidate in candidates:
                                try:
                                    with open(candidate, "r", encoding="utf-8") as f:
                                        content = f.read().lower()
                                    if all(
                                        term.lower() in content for term in terms[1:]
                                    ):
                                        matching_files.add(candidate)
                                except OSError as e:
                                    logger.debug(
                                        "Could not read candidate '%s': %s",
                                        candidate,
                                        e,
                                    )
                        else:
                            matching_files.update(candidates)
                except OSError as e:
                    logger.warning(
                        "Ripgrep search failed; using Python fallback: %s", e
                    )
                    rg_path = None

            if (not rg_path and not matching_files) or titles_only:
                if titles_only:
                    for item in search_path.rglob("*.md"):
                        is_forbidden, _ = is_path_forbidden(item, vault_path)
                        if is_forbidden:
                            continue
                        name = item.stem.lower()
                        if all(term.lower() in name for term in terms):
                            relative_path = item.relative_to(vault_path)
                            results.append(
                                {
                                    "file": str(relative_path),
                                    "type": "title",
                                    "match": item.stem,
                                }
                            )
                    if results:
                        return _format_search_results(results, titles_only=True)
                    return f"No notes found with title matching '{query}'"

                for item in search_path.rglob("*.md"):
                    is_forbidden, _ = is_path_forbidden(item, vault_path)
                    if is_forbidden:
                        continue
                    try:
                        with open(item, "r", encoding="utf-8") as f:
                            content = f.read().lower()
                        if all(term.lower() in content for term in terms):
                            matching_files.add(str(item))
                    except OSError as e:
                        logger.debug("Could not read file '%s': %s", item, e)

            for file_name in matching_files:
                file_path = Path(file_name)
                if not file_path.is_absolute():
                    file_path = Path(file_name).resolve()

                try:
                    relative_path = file_path.relative_to(vault_path)
                except ValueError:
                    continue

                is_forbidden, _ = is_path_forbidden(file_path, vault_path)
                if is_forbidden:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    for line_number, line in enumerate(lines, 1):
                        line_lower = line.lower()
                        if any(term.lower() in line_lower for term in terms):
                            stripped = line.strip()
                            if len(stripped) <= 3:
                                continue
                            match = (
                                stripped[:100] + "..."
                                if len(stripped) > 100
                                else stripped
                            )
                            results.append(
                                {
                                    "file": str(relative_path),
                                    "line": str(line_number),
                                    "match": match,
                                }
                            )
                            if (
                                len(
                                    [
                                        result
                                        for result in results
                                        if result["file"] == str(relative_path)
                                    ]
                                )
                                >= 2
                            ):
                                break
                except OSError as e:
                    logger.error("Error processing file %s: %s", file_name, e)

            if not results:
                return f"No notes found containing: {', '.join(terms)}"

            return short_term_tip + _format_search_results(results, titles_only=False)

        except OSError as e:
            logger.error("Unexpected search error: %s", e)
            return f"Search error: {e}"

    @register_tool(mcp, "search_notes_by_date")
    def search_notes_by_date(start_date: str, end_date: str = "") -> str:
        """
        Search notes modified in a date range.

        Args:
            start_date: Start date in YYYY-MM-DD format.
            end_date: Optional end date in YYYY-MM-DD format.
        """
        try:
            return search_notes_by_date_logic(start_date, end_date).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Date search error: {e}"

    @register_tool(mcp, "move_note")
    def move_note(source: str, destination: str, create_folders: bool = True) -> str:
        """
        Move or rename a note inside the vault.

        Args:
            source: Current relative note path.
            destination: New relative note path.
            create_folders: Whether to create destination folders.
        """
        try:
            return move_note_logic(source, destination, create_folders).to_display(
                success_prefix="OK"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Move note error: {e}"

    @register_tool(mcp, "random_concept")
    def random_concept(folder: str = "") -> str:
        """
        Return a random concept from the vault as a surprise flashcard.

        Args:
            folder: Folder to search. Empty means the whole vault.
        """
        try:
            return get_random_concept(folder).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Random concept error: {e}"

    @register_tool(mcp, "read_notes")
    async def read_notes(paths: list[str], ctx: Context) -> str:
        """
        Read the content and frontmatter of multiple notes.

        Args:
            paths: Note paths or names to read.
        """
        try:
            total = len(paths)
            if total > 5:
                await ctx.report_progress(0, total, f"Reading {total} notes...")
            result = read_multiple_notes_logic(paths)
            if total > 5:
                await ctx.report_progress(total, total, "Completed")
            return result.to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Read notes error: {e}"

    @register_tool(mcp, "get_note_info")
    def get_note_info(paths: list[str]) -> str:
        """
        Return metadata for multiple notes without loading all content.

        Args:
            paths: Note paths or names.
        """
        try:
            return get_notes_info_logic(paths).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"Get note info error: {e}"
