"""Public core prompts for generic Obsidian workflows."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import get_vault_path
from ..tools.agents_logic import get_cached_skills


def register_core_prompts(mcp: FastMCP) -> None:
    """Register prompts that are always safe for public use."""

    @mcp.prompt(name="assistant_overview")
    def assistant_overview() -> str:
        """Overview prompt for working with an Obsidian vault."""
        vault_path = get_vault_path()
        vault_name = vault_path.name if vault_path else "unconfigured vault"
        skills_section = ""

        if vault_path:
            skills = get_cached_skills(str(vault_path))
            valid_skills = [
                result.data
                for result in skills.values()
                if result.success and result.data
            ]
            if valid_skills:
                skills_section = "\nAvailable vault skills:\n"
                for skill in valid_skills:
                    skills_section += (
                        f"- {skill.metadata.name} ({skill.folder_name}): "
                        f"{skill.metadata.description}\n"
                    )

        return f"""
        You are an Obsidian assistant for the vault "{vault_name}".

        Before writing or making complex changes:
        1. Read global rules with `rules.get()`.
        2. Check available skills with `skills.list()`.
        3. If a skill matches the task, read it with
           `skills.read("skill-name")`.
        4. Read vault context with `vault.context()`.
        5. When creating notes, prefer real templates from `templates.list()`
           and `notes.read()`.

        Reuse existing tags and conventions. Do not invent a structure when
        the vault already has a matching template, standard, or skill.

        {skills_section}
        """

    @mcp.prompt(name="create_structured_note")
    def create_structured_note(topic: str, note_type: str = "note") -> str:
        """
        Create a structured note from vault templates.

        Args:
            topic: Main note topic.
            note_type: Desired note type.
        """
        return f"""
        Create a structured Obsidian note about "{topic}".
        Desired note type: "{note_type}".

        Required flow:
        1. Read global rules with `rules.get()`.
        2. List real templates with `templates.list()`.
        3. Read the best matching template with `notes.read()`.
        4. Use `notes.suggest_location()` to choose the destination.
        5. Create the note without inventing frontmatter fields that conflict
           with the template or vault conventions.

        If no exact template exists, infer the closest structure from nearby
        notes and explain the assumption in your final response.
        """

    @mcp.prompt(name="use_vault_template")
    def use_vault_template(template_goal: str) -> str:
        """
        Find and use an existing vault template.

        Args:
            template_goal: What the user wants the template for.
        """
        return f"""
        The user needs a vault template for: "{template_goal}".

        Required flow:
        1. Run `templates.list()`.
        2. Choose the closest template by purpose, not just filename.
        3. Read the template with `notes.read()`.
        4. Explain which template you chose and why.
        5. Use the template exactly as the structural base for any new note.
        """

    @mcp.prompt(name="explore_vault_context")
    def explore_vault_context(query: str) -> str:
        """
        Explore relevant vault context before answering or editing.

        Args:
            query: Topic or task to explore.
        """
        return f"""
        Explore the vault context for: "{query}".

        Required flow:
        1. Read global rules with `rules.get()`.
        2. Search notes with `notes.search()`.
        3. Read the most relevant notes with `notes.read()`.
        4. Use backlinks or graph tools when relationships matter.
        5. Summarize what you found before proposing edits.

        Do not write to the vault unless the user explicitly asks for a change.
        """

    @mcp.prompt(name="bootstrap_vault_config")
    def bootstrap_vault_config() -> str:
        """
        Inspect an unknown vault and generate its .agents/vault.yaml.

        Any agent or harness can run this once against a vault to derive a
        declarative taxonomy, so tools and skills stop hardcoding folder
        names. Inference happens here, once; at runtime the MCP only reads.
        """
        vault_path = get_vault_path()
        vault_name = vault_path.name if vault_path else "the configured vault"
        return f"""
        Goal: create (or update) `.agents/vault.yaml` for **{vault_name}** by
        inspecting how this vault is actually organised. Do NOT invent a
        layout — derive it from what exists.

        Steps:
        1. List the top-level folders and read the vault stats
           (`vault.stats` / `vault.context`).
        2. Sample frontmatter across folders: which `type:` values appear,
           and in which folders do they concentrate. Read a handful of notes
           per top-level folder with `notes.read()`.
        3. Read `.agents/REGLAS_GLOBALES.md` if it exists — its allowed `type`
           values and location table are the source of truth; prefer them
           over inference when they disagree.
        4. Map each semantic role below to the real folder that plays it. Omit
           a role if the vault has no such folder. Roles are a stable
           vocabulary skills rely on; folders are vault-specific:
             inbox, system, journal, knowledge, creations, projects, media,
             personal, templates
        5. Locate named documents the tools need, especially the tag registry
           (a note titled like "Registro de Tags del Vault"), and record its
           real path under `profile.local_docs.tag_registry`.

        Write this shape (all keys optional; keep any existing keys intact):

        ```yaml
        taxonomy:
          roles:
            inbox: "<folder>"
            knowledge: "<folder>"
            creations: "<folder>"
            projects: "<folder>"
            # ...only roles that exist
          types: [<the type values this vault actually uses>]
        profile:
          local_docs:
            tag_registry: "<path to the tag registry note>"
        ```

        Validation before you finish:
        - Every folder you reference must exist (check each path).
        - `types` must match REGLAS_GLOBALES if that file defines them.
        - After writing, call `vault.health` and confirm it passes.

        Deliverable: write the file, then produce a short markdown report of
        what you inferred (roles → folders, type vocabulary, tag registry
        path, and anything ambiguous you had to guess). Commit both the
        `vault.yaml` and the report, and push.
        """
