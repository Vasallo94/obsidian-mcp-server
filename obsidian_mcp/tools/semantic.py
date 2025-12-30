"""
Semantic search tools for the Obsidian MCP server.
Provides tools for RAG (Retrieval-Augmented Generation) based knowledge retrieval.
"""

from typing import Any, Dict, Optional

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import get_logger

logger = get_logger(__name__)

# Global service instance
SEMANTIC_SERVICE_INSTANCE = None


def get_semantic_service():
    """Lazy initialization of the SemanticService"""
    global SEMANTIC_SERVICE_INSTANCE  # pylint: disable=global-statement
    if SEMANTIC_SERVICE_INSTANCE is None:
        try:
            # pylint: disable=import-outside-toplevel
            from ..semantic.service import SemanticService

            vault_path = get_vault_path()
            if vault_path:
                SEMANTIC_SERVICE_INSTANCE = SemanticService(str(vault_path))
            else:
                logger.error(
                    "OBSIDIAN_VAULT_PATH not found, cannot initialize SemanticService"
                )
        except ImportError as e:
            logger.error(f"Failed to import SemanticService: {e}")
            return None
    return SEMANTIC_SERVICE_INSTANCE


def register_semantic_tools(mcp: FastMCP) -> None:
    """
    Registers the semantic RAG tools if the required dependencies are available.
    """
    try:
        # Check for core dependencies
        import chromadb  # noqa: F401 # pylint: disable=import-outside-toplevel,unused-import
        import langchain  # noqa: F401 # pylint: disable=import-outside-toplevel,unused-import

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
            service = get_semantic_service()
            if not service:
                return (
                    "Error: El servicio semántico no está disponible o requiere "
                    "dependencias (instala con [rag])."
                )

            # pylint: disable=no-value-for-parameter
            results = service.query(pregunta, metadata_filter=metadata_filter)
            if not results:
                return (
                    "No se encontró información relevante en el vault "
                    "para esta consulta."
                )

            formatted_results = "### Resultados de la búsqueda semántica\n\n"
            for i, res in enumerate(results, 1):
                source_name = res["source"].split("/")[-1]
                meta = res.get("metadata", {})
                meta_str = (
                    f" [Tags: {meta.get('tags', 'N/A')}, "
                    f"Tipo: {meta.get('type', 'N/A')}]"
                    if meta
                    else ""
                )

                formatted_results += (
                    f"**{i}. {source_name}** "
                    f"(Relevancia: {res['relevance']:.2f}){meta_str}\n"
                )
                formatted_results += f"{res['content']}\n\n---\n"

            return formatted_results

        @mcp.tool()
        async def indexar_vault_semantico(forzar: bool = False) -> str:
            """
            Actualiza el índice semántico del vault. Realiza un rastreo de todas las
            notas para que las nuevas búsquedas semánticas estén actualizadas.

            Args:
                forzar: Si es True, borra el índice anterior y lo crea desde cero.
            """
            service = get_semantic_service()
            if not service:
                return "Error: Servicio semántico no disponible."

            success = service.index_vault(force=forzar)
            if success:
                return "✅ Índice semántico actualizado correctamente."
            return "❌ Error al actualizar el índice semántico."

        @mcp.tool()
        async def encontrar_conexiones_sugeridas(
            threshold: float = 0.85, limite: int = 5
        ) -> str:
            """
            Analiza el vault para encontrar notas que tratan temas muy similares
            pero que NO están enlazadas entre sí. Útil para el mantenimiento del vault.

            Args:
                threshold: Nivel de similitud mínima (0.0 a 1.0, por defecto 0.85).
                limite: Número máximo de sugerencias a mostrar.
            """
            service = get_semantic_service()
            if not service:
                return "Error: Servicio semántico no disponible."

            suggestions = service.suggest_connections(threshold=threshold, limit=limite)
            if not suggestions:
                return (
                    "No se encontraron conexiones sugeridas con el "
                    "nivel de similitud actual."
                )

            result = "### 🕸️ Conexiones Sugeridas (Faltan enlaces)\n\n"
            for s in suggestions:
                result += f"- **{s['note_a']}** <--> **{s['note_b']}**\n"
                result += f"  - Motivo: {s['reason']}\n\n"

            result += "\n*Usa `[[Nota]]` para conectarlas manualmente en tu vault.*"
            return result

        logger.info("✅ Herramientas semánticas registradas correctamente")

    except ImportError:
        logger.warning(
            "⚠️ Herramientas semánticas omitidas: Instala dependencias con "
            "'pip install obsidian-mcp-server[rag]'"
        )


def register_agent_tools(_mcp: FastMCP) -> None:
    # This might have been a placeholder or I should check if I need to move it
    pass
