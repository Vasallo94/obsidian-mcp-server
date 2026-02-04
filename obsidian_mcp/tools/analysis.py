"""
Herramientas de análisis y estadísticas para el vault de Obsidian.

Estas herramientas permiten generar estadísticas y análisis del vault,
facilitando la gestión y organización desde un cliente MCP.
"""

from fastmcp import FastMCP


def register_analysis_tools(mcp: FastMCP) -> None:
    """
    Registra todas las herramientas de análisis en el servidor MCP.

    Args:
        mcp: Instancia del servidor FastMCP.
    """

    @mcp.tool()
    def estadisticas_vault() -> str:
        """Genera estadísticas completas del vault de Obsidian"""
        from .analysis_logic import get_vault_stats

        try:
            return get_vault_stats().to_display()
        except Exception as e:
            return f"❌ Error al generar estadísticas: {e}"

    @mcp.tool()
    def obtener_tags_canonicas() -> str:
        """
        Obtiene la lista de tags oficiales/canónicas definidas en el
        archivo 'Registro de Tags del Vault.md'.

        Returns:
            Lista de tags categorizadas según el registro oficial.
        """
        from .analysis_logic import get_canonical_tags

        try:
            return get_canonical_tags().to_display()
        except Exception as e:
            return f"❌ Error al obtener tags canónicas: {e}"

    @mcp.tool()
    def analizar_etiquetas() -> str:
        """Analiza el uso de etiquetas en el vault."""
        from .analysis_logic import analyze_tags

        try:
            return analyze_tags().to_display()
        except Exception as e:
            return f"❌ Error al analizar etiquetas: {e}"

    @mcp.tool()
    def sincronizar_registro_tags(actualizar: bool = False) -> str:
        """
        Sincroniza el uso de tags en el vault con el registro oficial.

        Args:
            actualizar: Si es True, intenta actualizar la tabla de
                       estadísticas en el archivo de registro.
        """
        from .analysis_logic import sync_tag_registry

        try:
            return sync_tag_registry(actualizar).to_display()
        except Exception as e:
            return f"❌ Error en sincronización: {e}"

    @mcp.tool()
    def obtener_lista_etiquetas() -> str:
        """
        Obtiene una lista simple de las etiquetas existentes en el vault.
        Útil para ver qué etiquetas ya existen antes de crear nuevas.

        Returns:
            Lista de etiquetas formateada como string.
        """
        from .analysis_logic import list_all_tags

        try:
            return list_all_tags().to_display()
        except Exception as e:
            return f"❌ Error al obtener lista de etiquetas: {e}"

    @mcp.tool()
    def analizar_enlaces() -> str:
        """Analiza los enlaces internos en el vault"""
        from .analysis_logic import analyze_links

        try:
            return analyze_links().to_display()
        except Exception as e:
            return f"❌ Error al analizar enlaces: {e}"

    @mcp.tool()
    def resumen_actividad_reciente(dias: int = 7) -> str:
        """
        Genera un resumen de la actividad reciente en el vault

        Args:
            dias: Número de días hacia atrás para analizar (por defecto 7)
        """
        from .analysis_logic import get_recent_activity

        try:
            return get_recent_activity(dias).to_display()
        except Exception as e:
            return f"❌ Error al generar resumen de actividad: {e}"
