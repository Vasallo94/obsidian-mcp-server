"""
Herramientas para la integración de Habilidades (Skills).

Estas herramientas permiten al cliente MCP leer las definiciones y prompts
de las skills almacenadas en la carpeta .agent/skills del vault.

Mejoras v2:
- Parsing estructurado de YAML frontmatter
- Validación de schema con Pydantic
- Caché en memoria para evitar re-lecturas innecesarias
- Soporte para .agent/REGLAS_GLOBALES.md como reglas globales
"""

from __future__ import annotations

from fastmcp import FastMCP


def register_agent_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas y recursos de gestión de skills (agentes).
    """

    @mcp.resource("skills://list")
    def resource_listar_skills() -> str:
        """Recurso que devuelve la lista de skills disponibles."""
        from .agents_logic import list_available_skills

        result = list_available_skills()
        return result.data if result.success else f"❌ {result.error}"

    @mcp.tool()
    def listar_agentes() -> str:
        """Lista las skills (agentes) disponibles en el vault."""
        from .agents_logic import list_available_skills

        result = list_available_skills()
        return result.data if result.success else f"❌ {result.error}"

    @mcp.tool()
    def obtener_instrucciones_agente(nombre: str) -> str:
        """
        Obtiene el contenido de una Skill específica (SKILL.md).

        Args:
            nombre: El nombre de la carpeta de la skill (ej: 'escritor').
        """
        from .agents_logic import get_agent_instructions

        result = get_agent_instructions(nombre)
        return result.data if result.success else f"❌ {result.error}"

    @mcp.tool()
    def obtener_reglas_globales() -> str:
        """
        Obtiene las reglas globales del Agente (.agent/REGLAS_GLOBALES.md).

        ⚠️ OBLIGATORIO PARA AGENTES DE IA: ⚠️
        DEBES leer estas reglas ANTES de realizar cualquier escritura
        o modificación en el vault.
        Contienen restricciones críticas (ej: NO emojis, formatos permitidos).
        """
        from .agents_logic import get_global_rules

        result = get_global_rules()
        return result.data if result.success else f"❌ {result.error}"

    @mcp.tool()
    def refrescar_cache_skills() -> str:
        """Invalida y refresca el caché de skills (úsalo tras editar SKILL.md)."""
        from .agents_logic import refresh_skills_cache

        result = refresh_skills_cache()
        return result.data if result.success else f"❌ {result.error}"
