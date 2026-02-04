"""
Semantic search tools for the Obsidian MCP server.
Provides tools for RAG (Retrieval-Augmented Generation) based knowledge retrieval.
"""

from typing import Any, Dict, Optional

from fastmcp import FastMCP

from ..utils import get_logger

logger = get_logger(__name__)


def register_semantic_tools(mcp: FastMCP) -> None:
    """
    Registers the semantic RAG tools if the required dependencies are available.
    """
    try:
        # Check for core dependencies locally to decide whether to register
        import chromadb  # noqa: F401
        import langchain  # noqa: F401

        @mcp.tool()
        async def preguntar_al_conocimiento(
            pregunta: str, metadata_filter: Optional[Dict[str, Any]] = None
        ) -> str:
            """
            Realiza una búsqueda semántica en todo el vault de Obsidian para responder
            preguntas basadas en el significado y contexto, no solo en palabras clave.
            Útil para recuperar conceptos relacionados, resúmenes o dudas generales.

            Args:
                pregunta: La pregunta o tema sobre el que quieres consultar.
                metadata_filter: Opcional. Filtro de metadatos (ej: {"type": "poesia"}).
            """
            from .semantic_logic import ask_knowledge

            try:
                return ask_knowledge(pregunta, metadata_filter).to_display()
            except Exception as e:
                return f"❌ Error en búsqueda semántica: {e}"

        @mcp.tool()
        async def indexar_vault_semantico(forzar: bool = False) -> str:
            """
            Actualiza el índice semántico del vault. Realiza un rastreo de todas las
            notas para que las nuevas búsquedas semánticas estén actualizadas.

            Args:
                forzar: Si es True, borra el índice anterior y lo crea desde cero.
            """
            from .semantic_logic import index_semantic_vault

            try:
                return index_semantic_vault(forzar).to_display()
            except Exception as e:
                return f"❌ Error al actualizar el índice: {e}"

        @mcp.tool()
        async def encontrar_conexiones_sugeridas(
            threshold: float = 0.70,
            limite: int = 5,
            carpetas_incluir: Optional[list[str]] = None,
            excluir_mocs: bool = True,
            min_palabras: int = 150,
        ) -> str:
            """
            Analiza el vault para encontrar notas que tratan temas muy similares
            pero que NO están enlazadas entre sí.

            Args:
                threshold: Nivel de similitud mínima (0.7 a 1.0). Default 0.82.
                limite: Máximo de sugerencias.
                carpetas_incluir: Lista de carpetas donde buscar (e.g. ["03_Notas"]).
                                  Si se omite, busca en todo excepto exclusiones.
                excluir_mocs: Ignorar MOC, Home, Inbox y sistema. (Default: True).
                min_palabras: Ignorar notas con menos de X palabras. (Default: 150).
            """
            from .semantic_logic import find_suggested_connections

            try:
                return find_suggested_connections(
                    threshold, limite, carpetas_incluir, excluir_mocs, min_palabras
                ).to_display()
            except Exception as e:
                return f"❌ Error al buscar conexiones: {e}"

        logger.info("✅ Herramientas semánticas registradas correctamente")

    except ImportError:
        logger.warning(
            "⚠️ Herramientas semánticas omitidas: Instala dependencias con "
            "'pip install obsidian-mcp-server[rag]'"
        )


def register_agent_tools(_mcp: FastMCP) -> None:
    # Placeholder for agent tools
    pass
