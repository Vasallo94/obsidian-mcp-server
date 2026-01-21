"""
Herramientas de contexto para el vault de Obsidian.

Estas herramientas permiten al agente entender la estructura y organización
del vault para tomar mejores decisiones sobre dónde guardar notas y qué etiquetas usar.
"""

from fastmcp import FastMCP


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
        3. Estado de la configuración de Agentes (.agent).

        Devuelve un resumen de carpetas, plantillas y etiquetas comunes.
        """
        from .context_logic import read_vault_context

        try:
            result = read_vault_context()
            return result.data if result.success else f"❌ {result.error}"
        except Exception as e:
            return f"❌ Error al leer contexto: {e}"
