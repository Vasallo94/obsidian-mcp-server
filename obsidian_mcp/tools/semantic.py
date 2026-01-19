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
        import chromadb  # noqa: F401 # pylint: disable=import-outside-toplevel,unused-import # type: ignore
        import langchain  # noqa: F401 # pylint: disable=import-outside-toplevel,unused-import # type: ignore

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

            stats = service.index_vault(force=forzar)

            if stats.get("success"):
                mode = "completo" if not stats.get("is_incremental") else "incremental"
                result = f"✅ Índice semántico actualizado correctamente ({mode}).\n\n"
                result += "📊 **Estadísticas:**\n"
                result += f"- Documentos procesados: {stats.get('docs_processed', 0)}\n"

                if stats.get("is_incremental"):
                    result += f"- Nuevos: {stats.get('docs_new', 0)}\n"
                    result += f"- Modificados: {stats.get('docs_modified', 0)}\n"
                    result += f"- Eliminados: {stats.get('docs_deleted', 0)}\n"

                result += f"- Tiempo: {stats.get('time_seconds', 0):.2f}s"
                return result

            return "❌ Error al actualizar el índice semántico."

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
            service = get_semantic_service()
            if not service:
                return "Error: Servicio semántico no disponible."

            suggestions = service.suggest_connections(
                threshold=threshold,
                limit=limite,
                carpetas_incluir=carpetas_incluir,
                excluir_mocs=excluir_mocs,
                min_palabras=min_palabras,
            )
            if not suggestions:
                return (
                    "No se encontraron conexiones sugeridas con los filtros actuales.\n"
                    f"(Threshold: {threshold}, Min Words: {min_palabras}, "
                    f"Excluir MOCs: {excluir_mocs})"
                )

            result = "### 🕸️ Conexiones Sugeridas (Faltan enlaces)\n\n"
            for s in suggestions:
                n_a = s["note_a"]
                n_b = s["note_b"]
                sim = s["similarity"]
                # Formato visual rico
                result += f"#### 🔗 {n_a} ↔ {n_b} (Similitud: {sim:.2f})\n"
                result += (
                    f"- **Ubicación**: `{s['folder_a']}` ↔ `{s['folder_b']}`\n"
                    f"- **Extensión**: {s['words_a']} words ↔ {s['words_b']} words\n"
                    f"- **Contexto sugerido**:\n"
                    f"  - *{n_a}*: {s['section_a']}\n"
                    f"  - *{n_b}*: {s['section_b']}\n"
                    f"- **Razón**: {s['reason']}\n\n"
                )

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
