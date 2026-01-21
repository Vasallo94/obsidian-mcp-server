"""
Herramientas de grafos y conexiones para el vault de Obsidian.

Estas herramientas permiten explorar las relaciones entre notas,
encontrar backlinks, buscar por tags y analizar la estructura del grafo.
"""

from fastmcp import FastMCP


def register_graph_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de grafos y conexiones en el servidor MCP.
    """

    @mcp.tool()
    def obtener_backlinks(nombre_nota: str) -> str:
        """
        Obtiene todas las notas que enlazan a la nota especificada (backlinks).

        Args:
            nombre_nota: Nombre de la nota (con o sin .md)

        Returns:
            Lista de notas que contienen enlaces a esta nota
        """
        from .graph_logic import get_backlinks

        try:
            result = get_backlinks(nombre_nota)
            return result.data if result.success else f"❌ {result.error}"
        except Exception as e:
            return f"❌ Error al obtener backlinks: {e}"

    @mcp.tool()
    def obtener_notas_por_tag(tag: str) -> str:
        """
        Busca todas las notas que contienen una etiqueta específica.

        Args:
            tag: Etiqueta a buscar (con o sin #)

        Returns:
            Lista de notas que contienen la etiqueta
        """
        from .graph_logic import get_notes_by_tag

        try:
            result = get_notes_by_tag(tag)
            return result.data if result.success else f"❌ {result.error}"
        except Exception as e:
            return f"❌ Error al buscar por tag: {e}"

    @mcp.tool()
    def obtener_grafo_local(nombre_nota: str, profundidad: int = 1) -> str:
        """
        Obtiene el grafo local de una nota: enlaces salientes y entrantes.

        Args:
            nombre_nota: Nombre de la nota central
            profundidad: Niveles de profundidad (1 = solo conexiones directas)

        Returns:
            Visualización del grafo local de la nota
        """
        from .graph_logic import get_local_graph

        try:
            result = get_local_graph(nombre_nota, profundidad)
            return result.data if result.success else f"❌ {result.error}"
        except Exception as e:
            return f"❌ Error al obtener grafo: {e}"

    @mcp.tool()
    def encontrar_notas_huerfanas() -> str:
        """
        Encuentra notas huérfanas: sin enlaces entrantes ni salientes.

        Returns:
            Lista de notas que no están conectadas al grafo del vault
        """
        from .graph_logic import find_orphan_notes

        try:
            result = find_orphan_notes()
            return result.data if result.success else f"❌ {result.error}"
        except Exception as e:
            return f"❌ Error al buscar huérfanas: {e}"
