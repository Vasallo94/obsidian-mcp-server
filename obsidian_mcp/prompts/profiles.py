"""Vault profile prompts."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import get_vault_path
from ..tools.agents_logic import get_cached_skills
from ..vault_config import get_vault_config

SECUNDO_PROFILE = "secundo_selebro"


def register_profile_prompts(mcp: FastMCP) -> None:
    """Register prompts provided by the active vault profile."""
    context = _profile_context()
    if context is None:
        return

    enabled, skills, standards = context

    def prompt_enabled(name: str) -> bool:
        return SECUNDO_PROFILE in enabled or name in enabled

    if prompt_enabled("update_media_item") and "media" in standards:

        @mcp.prompt(name="update_media_item")
        def update_media_item(
            work: str,
            media_type: str = "auto",
            opinion: str = "",
        ) -> str:
            """
            Update a movie, series, or book in the active vault media library.

            Args:
                work: Title or free-form description of the work.
                media_type: auto, book, movie, or series.
                opinion: Personal notes to integrate without overwriting.
            """
            return f"""
            Update the canonical Media library for: "{work}".
            Requested type: "{media_type}". User opinion/notes: "{opinion}".

            Required workflow:
            1. Read `obsidian://standards/media` first.
            2. Search for an existing note under `05_Recursos/Media`.
            3. If the external identifier is missing, resolve it before enrichment:
               - movies/series: correct IMDb ID;
               - books: ISBN, author, publisher, year, pages, and cover.
            4. For movies/series with `imdb_id`, use the Cinemeta workflow
               documented in the vault or the available system script.
            5. Complete YAML and `## Resumen` without overwriting human content.
            6. Integrate the opinion into `## Notas Personales`.
            7. Do not overwrite `## Subrayados y Anotaciones` or quotes.

            When done, report which note was updated, which identifiers were
            confirmed, and which fields still need manual review.
            """

    if prompt_enabled("import_kindle_highlights") and "media" in standards:

        @mcp.prompt(name="import_kindle_highlights")
        def import_kindle_highlights(
            clippings_path: str = "/Volumes/Kindle/documents/My Clippings.txt",
        ) -> str:
            """
            Import Kindle highlights into the active vault media notes.

            Args:
                clippings_path: Path to My Clippings.txt.
            """
            return f"""
            Import highlights and notes from Kindle USB using:
            `{clippings_path}`.

            Do not use the Obsidian Kindle plugin. The authorized source is the
            Kindle's local filesystem.

            Required workflow:
            1. Read `obsidian://standards/media`.
            2. Check that `{clippings_path}` exists.
            3. Run a dry-run first:
               `00_Sistema/Scripts/media_library_maintenance.py kindle --clippings "{clippings_path}"`
            4. If the dry-run is clean, run the same command with `--apply`.
            5. Review and report unmatched books.
            6. Running the import twice must not duplicate quotes.
            """

    if prompt_enabled("audit_vault") and "organizador" in skills:

        @mcp.prompt(name="audit_vault")
        def audit_vault(scope: str = "vault") -> str:
            """Audit vault health using the organizer skill."""
            return f"""
            Audit the health of "{scope}".

            Required workflow:
            1. Read `obsidian://skills/organizador`.
            2. Read global rules.
            3. Review tags, frontmatter, duplicates, orphan notes, and placement.
            4. Do not delete or move anything without explicit confirmation.
            5. Return a report with issues, impact, and proposed actions.
            """

    if prompt_enabled("create_moc") and "explorador" in skills:

        @mcp.prompt(name="create_moc")
        def create_moc(topic: str) -> str:
            """Create or update a Map of Content using the explorer skill."""
            return f"""
            Create or update a MOC about: "{topic}".

            Required workflow:
            1. Read `obsidian://skills/explorador`.
            2. Search for relevant notes and real connections.
            3. Use backlinks/local graph when they add context.
            4. Organize links by meaning, not as a flat list.
            5. Use a MOC template if one exists.
            """

    if prompt_enabled("process_external_resource") and "procesador" in skills:

        @mcp.prompt(name="process_external_resource")
        def process_external_resource(resource: str, source_type: str = "auto") -> str:
            """Process an external resource into the vault."""
            return f"""
            Process this external resource: "{resource}".
            Requested type: "{source_type}".

            Required workflow:
            1. Read `obsidian://skills/procesador`.
            2. Capture minimal metadata and source.
            3. Summarize without inventing content.
            4. Choose the final destination according to the skill rules.
            """

    if prompt_enabled("daily_review") and "revision" in skills:

        @mcp.prompt(name="daily_review")
        def daily_review(date: str = "today") -> str:
            """Create a daily review."""
            return f"""
            Create a daily review for: "{date}".

            Read `obsidian://skills/revision`, summarize recent activity,
            integrate into the daily note if it exists, and do not overwrite
            human content.
            """

    if prompt_enabled("weekly_review") and "revision" in skills:

        @mcp.prompt(name="weekly_review")
        def weekly_review(week: str = "current") -> str:
            """Create a weekly review."""
            return f"""
            Create a weekly review for: "{week}".

            Read `obsidian://skills/revision`, review recent daily notes/notes,
            and synthesize wins, lessons, and next objectives.
            """

    if prompt_enabled("write_runbook") and "registrador" in skills:

        @mcp.prompt(name="write_runbook")
        def write_runbook(procedure: str) -> str:
            """Write an operational runbook."""
            return f"""
            Document this operational procedure: "{procedure}".

            Read `obsidian://skills/registrador`, search for existing
            documentation before creating anything, and write context, procedure,
            and verification steps.
            """

    if prompt_enabled("write_changelog") and "registrador" in skills:

        @mcp.prompt(name="write_changelog")
        def write_changelog(project: str) -> str:
            """Write a project changelog."""
            return f"""
            Write a changelog for: "{project}".

            Read `obsidian://skills/registrador`, group changes using Keep a
            Changelog style, and focus entries on user impact.
            """

    if prompt_enabled("document_repository") and "documentador" in skills:

        @mcp.prompt(name="document_repository")
        def document_repository(repository_path: str) -> str:
            """Document a source-code repository."""
            return f"""
            Document the repository: "{repository_path}".

            Read `obsidian://skills/documentador`, document only what exists
            in the code, group by component, and do not invent descriptions.
            """


def _profile_context() -> tuple[set[str], set[str], set[str]] | None:
    vault_path = get_vault_path()
    if not vault_path:
        return None
    config = get_vault_config(vault_path)
    if not config or config.profile.name != SECUNDO_PROFILE:
        return None

    skills = {
        name
        for name, result in get_cached_skills(str(vault_path)).items()
        if result.success and result.data
    }
    standards = set(config.profile.standards)
    return set(config.profile.prompt_sets), skills, standards
