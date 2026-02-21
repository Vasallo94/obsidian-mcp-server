"""
Herramientas de grafos y conexiones para el vault de Obsidian.

Estas herramientas permiten explorar las relaciones entre notas,
encontrar backlinks, buscar por tags y analizar la estructura del grafo.
"""

from fastmcp import FastMCP

from .graph_logic import (
    find_orphan_notes,
    get_backlinks,
    get_local_graph,
    get_notes_by_tag,
)


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
        try:
            return get_backlinks(nombre_nota).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
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
        try:
            return get_notes_by_tag(tag).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
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
        try:
            return get_local_graph(nombre_nota, profundidad).to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al obtener grafo: {e}"

    @mcp.tool()
    def encontrar_notas_huerfanas() -> str:
        """
        Encuentra notas huérfanas: sin enlaces entrantes ni salientes.

        Returns:
            Lista de notas que no están conectadas al grafo del vault
        """
        try:
            return find_orphan_notes().to_display()
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al buscar huérfanas: {e}"
