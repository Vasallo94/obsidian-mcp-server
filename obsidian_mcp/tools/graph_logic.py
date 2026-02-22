"""
Core business logic for graph tools.

This module contains the logic for exploring connections between notes,
finding backlinks, searching tags, and analyzing graph structure.
"""

from pathlib import Path
from typing import Dict, List

from ..config import get_vault_path
from ..result import Result
from ..utils import extract_internal_links, extract_tags_from_content, get_logger

logger = get_logger(__name__)


def get_backlinks(nombre_nota: str) -> Result[str]:
    """
    Get all notes that link to the specified note.

    Args:
        nombre_nota: Name of the note (with or without .md)

    Returns:
        Result with list of backlinks.
    """
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        # Normalize name
        nombre_limpio = nombre_nota.replace(".md", "")

        backlinks: List[Dict[str, str]] = []

        for archivo in vault_path.rglob("*.md"):
            # Ignore self
            if archivo.stem == nombre_limpio:
                continue

            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    contenido = f.read()

                enlaces = extract_internal_links(contenido)

                for enlace in enlaces:
                    enlace_limpio = enlace.split("|")[0].strip()
                    if enlace_limpio == nombre_limpio:
                        ruta_rel = archivo.relative_to(vault_path)
                        backlinks.append(
                            {
                                "nota": archivo.stem,
                                "ruta": str(ruta_rel),
                            }
                        )
                        break
            except OSError as e:
                logger.debug("No se pudo leer '%s': %s", archivo, e)
                continue

        if not backlinks:
            return Result.ok(f"🔗 No se encontraron backlinks hacia '{nombre_nota}'")

        resultado = (
            f"🔗 **Backlinks hacia '{nombre_nota}'** ({len(backlinks)} notas):\n\n"
        )
        for bl in backlinks:
            resultado += f"   • [[{bl['nota']}]] - {bl['ruta']}\n"

        return Result.ok(resultado)

    except OSError as e:
        return Result.fail(f"Error al obtener backlinks: {e}")


def get_notes_by_tag(tag: str) -> Result[str]:
    """
    Find all notes containing a specific tag.

    Args:
        tag: Tag to search for (with or without #)

    Returns:
        Result with list of notes.
    """
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        tag_limpia = tag.lstrip("#")
        notas_con_tag: List[Dict[str, str]] = []

        for archivo in vault_path.rglob("*.md"):
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    contenido = f.read()
                tags = extract_tags_from_content(contenido)
                if tag_limpia in tags:
                    ruta_rel = archivo.relative_to(vault_path)
                    notas_con_tag.append(
                        {
                            "nota": archivo.stem,
                            "ruta": str(ruta_rel),
                        }
                    )
            except OSError as e:
                logger.debug("No se pudo leer '%s': %s", archivo, e)
                continue

        if not notas_con_tag:
            return Result.ok(f"🏷️ No se encontraron notas con la etiqueta #{tag_limpia}")

        resultado = (
            f"🏷️ **Notas con #{tag_limpia}** ({len(notas_con_tag)} encontradas):\n\n"
        )

        por_carpeta: Dict[str, List[str]] = {}
        for nota in notas_con_tag:
            carpeta = (
                str(nota["ruta"]).rsplit("/", 1)[0] if "/" in nota["ruta"] else "Raíz"
            )
            if carpeta not in por_carpeta:
                por_carpeta[carpeta] = []
            por_carpeta[carpeta].append(nota["nota"])

        for carpeta, notas in sorted(por_carpeta.items()):
            resultado += f"📁 {carpeta}:\n"
            for nombre_nota in sorted(notas):
                resultado += f"   • [[{nombre_nota}]]\n"
            resultado += "\n"

        return Result.ok(resultado)

    except OSError as e:
        return Result.fail(f"Error al buscar por tag: {e}")


def _find_backlinks(vault_path: Path, nombre_limpio: str) -> list[str]:
    """Scan vault for notes that link to the given note name."""
    backlinks = []
    for archivo in vault_path.rglob("*.md"):
        if archivo.stem == nombre_limpio:
            continue
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                cont = f.read()
            enlaces = extract_internal_links(cont)
            for enlace in enlaces:
                if enlace.split("|")[0].strip() == nombre_limpio:
                    backlinks.append(archivo.stem)
                    break
        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
    return backlinks


def _format_link_section(
    title: str,
    items: list[str],
    arrow: str,
    limit: int = 15,
) -> str:
    """Format a list of links into a display section."""
    result = f"{title} ({len(items)}):\n"
    if not items:
        return result + "   (ninguno)\n"
    for item in sorted(items)[:limit]:
        result += f"   {arrow} [[{item}]]\n"
    if len(items) > limit:
        result += f"   ... y {len(items) - limit} más\n"
    return result


def get_local_graph(nombre_nota: str, profundidad: int = 1) -> Result[str]:
    """
    Get local graph for a note: outgoing and incoming links.

    Args:
        nombre_nota: Name of the central note.
        profundidad: Depth levels (1 = direct connections only).

    Returns:
        Result with graph visualization.
    """
    try:
        if profundidad > 1:
            logger.warning(
                "get_local_graph currently only fully supports profundidad=1. "
                "Returning direct connections."
            )

        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        nombre_limpio = nombre_nota.replace(".md", "")

        # Find note
        nota_path = None
        for archivo in vault_path.rglob("*.md"):
            if archivo.stem == nombre_limpio:
                nota_path = archivo
                break

        if not nota_path:
            return Result.fail(f"No se encontró la nota '{nombre_nota}'")

        # Get outgoing links
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        raw_links = extract_internal_links(contenido)
        enlaces_salientes = list({e.split("|")[0].strip() for e in raw_links})

        # Get backlinks
        backlinks = _find_backlinks(vault_path, nombre_limpio)

        # Format result
        resultado = f"🕸️ **Grafo Local de '{nombre_nota}'**\n\n"
        resultado += _format_link_section(
            "📤 **Enlaces salientes**",
            enlaces_salientes,
            "→",
        )
        resultado += "\n"
        resultado += _format_link_section("📥 **Backlinks**", backlinks, "←")

        total = len(enlaces_salientes) + len(backlinks)
        resultado += f"\n📊 **Conectividad total**: {total} conexiones"

        return Result.ok(resultado)

    except OSError as e:
        return Result.fail(f"Error al obtener grafo local: {e}")


def find_orphan_notes() -> Result[str]:
    """
    Find orphan notes: those without incoming or outgoing links.

    Returns:
        Result with list of orphan notes.
    """
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        enlaces_salientes_por_nota: Dict[str, List[str]] = {}
        todos_los_enlaces: set = set()

        for archivo in vault_path.rglob("*.md"):
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    contenido = f.read()
                enlaces = extract_internal_links(contenido)
                enlaces_limpios = [e.split("|")[0].strip() for e in enlaces]
                enlaces_salientes_por_nota[archivo.stem] = enlaces_limpios
                todos_los_enlaces.update(enlaces_limpios)
            except OSError as e:
                logger.debug("No se pudo leer '%s': %s", archivo, e)
                continue

        notas_huerfanas = []
        for archivo in vault_path.rglob("*.md"):
            nombre = archivo.stem
            if any(x in str(archivo) for x in [".git", ".obsidian", "ZZ_"]):
                continue

            tiene_salientes = bool(enlaces_salientes_por_nota.get(nombre, []))
            recibe_enlaces = nombre in todos_los_enlaces

            if not tiene_salientes and not recibe_enlaces:
                ruta_rel = archivo.relative_to(vault_path)
                notas_huerfanas.append(
                    {
                        "nota": nombre,
                        "ruta": str(ruta_rel),
                    }
                )

        if not notas_huerfanas:
            return Result.ok(
                "✅ No hay notas huérfanas. Todas están conectadas al grafo."
            )

        resultado = f"🔍 **Notas Huérfanas** ({len(notas_huerfanas)}):\n\n"
        resultado += "Estas notas no tienen enlaces entrantes ni salientes:\n\n"
        for nota in notas_huerfanas[:30]:
            resultado += f"   • {nota['ruta']}\n"
        if len(notas_huerfanas) > 30:
            resultado += f"\n... y {len(notas_huerfanas) - 30} más"

        return Result.ok(resultado)

    except OSError as e:
        return Result.fail(f"Error al encontrar notas huerfanas: {e}")
