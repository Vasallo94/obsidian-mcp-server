"""
Core business logic for semantic search and RAG tools.

This module encapsulates interactions with the SemanticService.
"""

from typing import Any, Dict, Optional

from ..config import get_vault_path
from ..result import Result
from ..utils import get_logger

logger = get_logger(__name__)

# Global service instance
SEMANTIC_SERVICE_INSTANCE = None


def get_semantic_service():
    """Lazy initialization of the SemanticService."""
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


def ask_knowledge(
    pregunta: str, metadata_filter: Optional[Dict[str, Any]] = None
) -> Result[str]:
    """
    Perform a semantic search in the vault.

    Args:
        pregunta: The question or topic.
        metadata_filter: Optional metadata filter.

    Returns:
        Result with formatted answer/search results.
    """
    service = get_semantic_service()
    if not service:
        return Result.fail(
            "El servicio semántico no está disponible o requiere dependencias."
        )

    try:
        results = service.query(pregunta, metadata_filter=metadata_filter)
        if not results:
            return Result.fail(
                "No se encontró información relevante en el vault para esta consulta."
            )

        formatted_results = "### Resultados de la búsqueda semántica\n\n"
        for i, res in enumerate(results, 1):
            source_name = res["source"].split("/")[-1]
            meta = res.get("metadata", {})
            meta_str = (
                f" [Tags: {meta.get('tags', 'N/A')}, Tipo: {meta.get('type', 'N/A')}]"
                if meta
                else ""
            )
            relevance = res.get("relevance")
            relevance_str = (
                f"(Relevancia: {relevance:.2f})"
                if relevance is not None
                else "(Relevancia: N/D)"
            )

            formatted_results += f"**{i}. {source_name}** {relevance_str}{meta_str}\n"
            formatted_results += f"{res['content']}\n\n---\n"

        return Result.ok(formatted_results)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error en búsqueda semántica: {exc}")


def index_semantic_vault(forzar: bool = False) -> Result[str]:
    """
    Update the semantic index of the vault.

    Args:
        forzar: If True, rebuild index from scratch.

    Returns:
        Result with status report.
    """
    service = get_semantic_service()
    if not service:
        return Result.fail("Servicio semántico no disponible.")

    try:
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
            return Result.ok(result)

        return Result.fail("Error interno al actualizar el índice semántico.")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Excepción al indexar: {exc}")


def find_suggested_connections(
    threshold: float = 0.70,
    limite: int = 5,
    carpetas_incluir: Optional[list[str]] = None,
    excluir_mocs: bool = True,
    min_palabras: int = 150,
) -> Result[str]:
    """
    Analyze vault to find suggested connections between notes.

    Args:
        threshold: Minimum similarity threshold.
        limite: Max suggestions.
        carpetas_incluir: List of folders to include.
        excluir_mocs: Ignore MOCs/system files.
        min_palabras: Minimum word count.

    Returns:
        Result with suggestions report.
    """
    service = get_semantic_service()
    if not service:
        return Result.fail("Servicio semántico no disponible.")

    try:
        suggestions = service.suggest_connections(
            threshold=threshold,
            limit=limite,
            carpetas_incluir=carpetas_incluir,
            excluir_mocs=excluir_mocs,
            min_palabras=min_palabras,
        )
        if not suggestions:
            return Result.ok(
                "No se encontraron conexiones sugeridas con los filtros actuales.\n"
                f"(Threshold: {threshold}, Min Words: {min_palabras}, "
                f"Excluir MOCs: {excluir_mocs})"
            )

        result = "### 🕸️ Conexiones Sugeridas (Faltan enlaces)\n\n"
        for s in suggestions:
            n_a = s["note_a"]
            n_b = s["note_b"]
            sim = s["similarity"]

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
        return Result.ok(result)

    except Exception as exc:  # pylint: disable=broad-exception-caught
        return Result.fail(f"Error al buscar conexiones: {exc}")
