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
        1. Read global rules with `obtener_reglas_globales()`.
        2. Check available skills with `listar_agentes()`.
        3. If a skill matches the task, read it with
           `obtener_instrucciones_agente("skill-name")`.
        4. Read vault context with `leer_contexto_vault()`.
        5. When creating notes, prefer real templates from `listar_plantillas()`
           and `leer_nota()`.

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
        1. Read global rules with `obtener_reglas_globales()`.
        2. List real templates with `listar_plantillas()`.
        3. Read the best matching template with `leer_nota()`.
        4. Use `sugerir_ubicacion()` to choose the destination.
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
        1. Run `listar_plantillas()`.
        2. Choose the closest template by purpose, not just filename.
        3. Read the template with `leer_nota()`.
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
        1. Read global rules with `obtener_reglas_globales()`.
        2. Search notes with `buscar_en_notas()`.
        3. Read the most relevant notes with `leer_nota()`.
        4. Use backlinks or graph tools when relationships matter.
        5. Summarize what you found before proposing edits.

        Do not write to the vault unless the user explicitly asks for a change.
        """
