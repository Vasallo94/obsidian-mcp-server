"""
Semantic search tools for the Obsidian MCP server.
Provides tools for RAG (Retrieval-Augmented Generation) based knowledge retrieval.
"""

import asyncio
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import get_logger
from ..vault_config import get_vault_config

logger = get_logger(__name__)


def register_semantic_tools(mcp: FastMCP) -> None:
    """
    Registers legacy in-process semantic RAG tools only when explicitly enabled.
    """
    if "legacy_semantic" not in _enabled_prompt_sets():
        logger.info(
            "Legacy semantic tools omitted. Enable prompt set 'legacy_semantic' "
            "or use the ObsidianRAG pack for RAG."
        )
        return

    try:
        # Check for core dependencies locally to decide whether to register
        # pylint: disable-next=import-outside-toplevel,unused-import
        import chromadb  # noqa: F401

        # pylint: disable-next=import-outside-toplevel,unused-import
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
            # pylint: disable-next=import-outside-toplevel
            from .semantic_logic import ask_knowledge

            try:
                return ask_knowledge(pregunta, metadata_filter).to_display()
            except Exception as e:  # pylint: disable=broad-exception-caught
                return f"❌ Error en búsqueda semántica: {e}"

        @mcp.tool()
        async def indexar_vault_semantico(ctx, forzar: bool = False) -> str:
            """
            Actualiza el índice semántico del vault. Realiza un rastreo de todas las
            notas para que las nuevas búsquedas semánticas estén actualizadas.

            Args:
                forzar: Si es True, borra el índice anterior y lo crea desde cero.
            """
            # pylint: disable-next=import-outside-toplevel
            from .semantic_logic import index_semantic_vault

            try:
                await ctx.report_progress(0, 1, "Indexando vault semántico...")
                result = await asyncio.to_thread(index_semantic_vault, forzar)
                await ctx.report_progress(1, 1, "Indexación completada")
                return result.to_display()
            except Exception as e:  # pylint: disable=broad-exception-caught
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
            # pylint: disable-next=import-outside-toplevel
            from .semantic_logic import find_suggested_connections

            try:
                return find_suggested_connections(
                    threshold, limite, carpetas_incluir, excluir_mocs, min_palabras
                ).to_display()
            except ValueError as e:
                return f"❌ Error al buscar conexiones: {e}"

        logger.info("✅ Herramientas semánticas registradas correctamente")

    except ImportError:
        logger.warning(
            "⚠️ Herramientas semánticas omitidas: Instala dependencias con "
            "'pip install obsidian-mcp-server[rag]'"
        )


def _enabled_prompt_sets() -> set[str]:
    vault_path = get_vault_path()
    if not vault_path:
        return set()
    config = get_vault_config(vault_path)
    if not config:
        return set()
    return set(config.profile.prompt_sets)


def register_agent_tools(_mcp: FastMCP) -> None:
    # Placeholder for agent tools
    pass
