"""
Herramientas de contexto para el vault de Obsidian.

Estas herramientas permiten al agente entender la estructura y organización
del vault para tomar mejores decisiones sobre dónde guardar notas y qué etiquetas usar.
"""

from fastmcp import FastMCP

from .context_logic import (
    build_vault_health_report,
    diagnose_vault_setup_report,
    read_vault_context,
    route_task_request,
)


def register_context_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de contexto en el servidor MCP.
    """

    @mcp.tool()
    def leer_contexto_vault() -> str:
        """
        Lee la estructura general del vault y estadísticas clave.

        ⚠️ OBLIGATORIO PARA AGENTES DE IA: ⚠️
        Esta debe ser SIEMPRE la PRIMERA herramienta que ejecutes al comenzar
        cualquier tarea con el vault. Te informa de:
        1. Estructura de carpetas válida.
        2. Plantillas disponibles.
        3. Estado de la configuración de Agentes (.agents).

        Devuelve un resumen de carpetas, plantillas y etiquetas comunes.
        """
        try:
            return read_vault_context().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al leer contexto: {e}"

    @mcp.tool()
    def health_check() -> str:
        """
        Validate the active vault and MCP profile configuration.

        Checks vault path, .agents/vault.yaml, templates, skills, standards,
        and local docs declared by the active profile.
        """
        try:
            return build_vault_health_report().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error running health check: {e}"

    @mcp.tool()
    def diagnose_vault_setup() -> str:
        """
        Diagnose vault setup issues and return actionable recommendations.
        """
        try:
            return diagnose_vault_setup_report().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error diagnosing vault setup: {e}"

    @mcp.tool()
    def route_task(request: str) -> str:
        """
        Recommend which prompt, skill, resources, and tools to use for a task.

        Args:
            request: User request or task description to route.
        """
        try:
            return route_task_request(request).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error routing task: {e}"
