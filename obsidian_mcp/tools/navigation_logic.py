"""
Core business logic for navigation tools.

This module contains the actual implementation of navigation operations,
separated from the MCP tool registration to improve testability and
maintain single responsibility.

All functions return Result[str] for consistent error handling.
"""

import json
import re
import secrets
from datetime import date, datetime
from pathlib import Path
from typing import Any

from ..config import get_vault_path
from ..result import Result
from ..utils import (
    check_path_access,
    find_note_by_name,
    get_logger,
    get_note_metadata,
    is_path_forbidden,
    is_path_in_restricted_folder,
    validate_path_within_vault,
)
from ..vault_config import get_vault_config
from .creation_logic import _extract_frontmatter_from_content

logger = get_logger(__name__)

# Line prefixes that mark non-content lines in Markdown
_NON_CONTENT_PREFIXES = frozenset(("#", "-", "*", ">", "---", "[["))
MAX_NOTE_READ_BYTES = 2_000_000
MAX_BATCH_READ_BYTES = 5_000_000


def _json_serial(obj: Any) -> str:
    """JSON serializer for objects not handled by default json module."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def format_search_results(resultados: list, solo_titulos: bool) -> str:
    """Format search results for display.

    Args:
        resultados: List of search result dicts with keys: archivo, linea, coincidencia
        solo_titulos: Whether results are title-only matches

    Returns:
        Formatted string with results grouped by file
    """
    resultado_str = f"Found {len(resultados)} matches:\n\n"

    por_archivo: dict[str, list[dict[str, str]]] = {}
    for r in resultados:
        archivo = r["archivo"]
        if archivo not in por_archivo:
            por_archivo[archivo] = []
        por_archivo[archivo].append(r)

    for archivo, coincidencias in list(por_archivo.items())[:20]:
        resultado_str += f"**{archivo}**\n"
        for c in coincidencias:
            if solo_titulos:
                resultado_str += f"   {c['coincidencia']}\n"
            else:
                resultado_str += f"   L{c['linea']}: {c['coincidencia']}\n"
        resultado_str += "\n"

    if len(por_archivo) > 20:
        resultado_str += f"... and {len(por_archivo) - 20} more files."

    return resultado_str


DEFAULT_LIST_NOTES_LIMIT = 500


def list_notes(  # pylint: disable=too-many-locals,too-many-branches
    carpeta: str = "",
    incluir_subcarpetas: bool = True,
    limit: int = DEFAULT_LIST_NOTES_LIMIT,
    offset: int = 0,
    pattern: str = "",
) -> Result[str]:
    """List notes in the vault or a specific folder, with pagination.

    Issue #5: large vaults overran the response budget (125K+ chars on
    single call). ``limit``/``offset`` cap the output and the footer
    points at the next page.

    Args:
        carpeta: Specific folder to explore (empty = vault root).
        incluir_subcarpetas: Whether to recurse into subfolders.
        limit: Max notes to include in the response. Use 0 for "no limit".
        offset: Start index (after filename sort).
        pattern: Optional glob (e.g. ``"2026-*.md"``) layered over the
            base ``*.md`` discovery.

    Returns:
        Result with a formatted listing plus pagination footer when
        more notes exist beyond ``offset + limit``.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    if limit < 0:
        return Result.fail("limit debe ser >= 0 (0 = sin limite).")
    if offset < 0:
        return Result.fail("offset debe ser >= 0.")

    if carpeta:
        target_path = vault_path / carpeta
        if not target_path.exists():
            return Result.fail(f"Folder does not exist in the vault: {carpeta}")
    else:
        target_path = vault_path

    base_pattern = "**/*.md" if incluir_subcarpetas else "*.md"
    if pattern:
        glob_pattern = (
            f"**/{pattern}"
            if incluir_subcarpetas and not pattern.startswith("**/")
            else pattern
        )
    else:
        glob_pattern = base_pattern

    notas_raw = list(target_path.glob(glob_pattern))

    visibles: list[Path] = []
    notas_filtradas = 0
    for nota in notas_raw:
        is_forbidden, _ = is_path_forbidden(nota, vault_path)
        if is_forbidden:
            notas_filtradas += 1
            continue
        visibles.append(nota)

    total_visibles = len(visibles)

    if total_visibles == 0:
        return Result.ok(f"No notes found in '{carpeta or 'root'}'")

    visibles.sort(key=lambda p: str(p.relative_to(vault_path)))

    end = total_visibles if limit == 0 else min(offset + limit, total_visibles)
    page = visibles[offset:end]

    if not page:
        return Result.ok(
            f"No notes in this page (offset={offset}, limit={limit}). "
            f"Total visibles: {total_visibles}."
        )

    notas_por_carpeta: dict[str, list[dict]] = {}
    for nota in page:
        ruta_relativa = nota.relative_to(vault_path)
        carpeta_padre = (
            str(ruta_relativa.parent) if ruta_relativa.parent != Path(".") else "Root"
        )
        if carpeta_padre not in notas_por_carpeta:
            notas_por_carpeta[carpeta_padre] = []
        notas_por_carpeta[carpeta_padre].append(get_note_metadata(nota))

    header = (
        f"Notes found in the vault ({total_visibles} total, "
        f"showing {offset + 1}-{end}):\n\n"
    )
    resultado = header

    for carpeta_nombre, lista_notas in sorted(notas_por_carpeta.items()):
        resultado += f"{carpeta_nombre} ({len(lista_notas)} notes):\n"
        for nota_meta in sorted(lista_notas, key=lambda x: x["name"]):
            resultado += (
                f"   {nota_meta['name']} "
                f"({nota_meta['size_kb']:.1f}KB, {nota_meta['modified']})\n"
            )
        resultado += "\n"

    if end < total_visibles:
        next_offset = end
        resultado += (
            f"--- Truncated: {total_visibles - end} more notes available. "
            f"Call list_notes(offset={next_offset}, limit={limit}) for the next page."
        )

    return Result.ok(resultado)


def read_note(nombre_archivo: str) -> Result[str]:
    """Read the complete content of a specific note.

    Args:
        nombre_archivo: File name or path (e.g. "Diario/2024-01-01.md")

    Returns:
        Result with formatted string containing metadata and content
    """
    nota_path = find_note_by_name(nombre_archivo)

    if not nota_path:
        return Result.fail(f"Note not found: {nombre_archivo}")

    is_allowed, error = check_path_access(nota_path, operation="read")
    if not is_allowed:
        return Result.fail(error)

    size_bytes = nota_path.stat().st_size
    if size_bytes > MAX_NOTE_READ_BYTES:
        return Result.fail(
            "Note is too large to return safely. Use `notes.info` first and "
            "read a smaller section or split the note."
        )

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    metadata = get_note_metadata(nota_path)

    resultado = f"**{metadata['name']}**\n"
    resultado += f"Location: {metadata['relative_path']}\n"
    resultado += (
        f"Size: {metadata['size_kb']:.1f}KB | Modified: {metadata['modified']}\n"
    )
    resultado += f"{'=' * 50}\n\n"
    resultado += contenido

    return Result.ok(resultado)


def search_notes_by_date(fecha_desde: str, fecha_hasta: str = "") -> Result[str]:
    """Search for notes modified within a date range.

    Args:
        fecha_desde: Start date (YYYY-MM-DD)
        fecha_hasta: End date (YYYY-MM-DD, defaults to today)

    Returns:
        Result with formatted string of matching notes
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    try:
        fecha_inicio = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
    except ValueError:
        return Result.fail(
            "Invalid date format. Use YYYY-MM-DD, for example 2024-01-15."
        )

    if fecha_hasta:
        try:
            fecha_fin = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        except ValueError:
            return Result.fail("Invalid date format. Use YYYY-MM-DD.")
    else:
        fecha_fin = date.today()

    notas_encontradas = []

    for archivo in vault_path.rglob("*.md"):
        is_forbidden_path, _ = is_path_forbidden(archivo, vault_path)
        if is_forbidden_path:
            continue

        fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()

        if fecha_inicio <= fecha_mod <= fecha_fin:
            metadata = get_note_metadata(archivo)
            metadata["fecha"] = fecha_mod.strftime("%Y-%m-%d")
            notas_encontradas.append(metadata)

    if not notas_encontradas:
        return Result.ok(f"No notes modified between {fecha_desde} and {fecha_fin}")

    notas_encontradas.sort(key=lambda x: x["fecha"], reverse=True)

    resultado = (
        f"Notes modified between {fecha_desde} and {fecha_fin} "
        f"({len(notas_encontradas)} found):\n\n"
    )

    for nota in notas_encontradas:
        resultado += f"{nota['name']} ({nota['size_kb']:.1f}KB)\n"
        resultado += f"   {nota['relative_path']} | {nota['fecha']}\n\n"

    return Result.ok(resultado)


def _validate_move_paths(
    origen: str,
    destino: str,
    vault_path: Path,
) -> tuple[bool, str]:
    """Validate origin and destination paths for a move operation.

    Returns:
        (is_valid, error_message) — error_message is empty on success.
    """
    for label, path_str in [("source", origen), ("destination", destino)]:
        is_valid, error = validate_path_within_vault(path_str, vault_path)
        if not is_valid:
            return False, f"Security error ({label}): {error}"

    config = get_vault_config(vault_path)
    private_folders = ["**/Private/", "**/Privado/*"]
    if config and config.private_paths:
        private_folders = config.private_paths

    if is_path_in_restricted_folder(origen, private_folders, vault_path):
        return False, ("Access denied: cannot move files from restricted folders")
    if is_path_in_restricted_folder(destino, private_folders, vault_path):
        return False, ("Access denied: cannot move files into restricted folders")

    return True, ""


def move_note(  # pylint: disable=too-many-locals,too-many-return-statements
    origen: str,
    destino: str,
    crear_carpetas: bool = True,
    update_links: bool = False,
) -> Result[str]:
    """Move or rename a note within the vault.

    Args:
        origen: Current relative path of the note.
        destino: New relative path for the note.
        crear_carpetas: Whether to create destination folders if needed.
        update_links: When True (Issue #7/#11), rewrite every wikilink
            across the vault that points to the old stem so they target
            the new stem instead. Aliases/sections are preserved.

    Returns:
        Result with success or error message. On success, the message
        reports how many wikilinks were touched (or 0 if update_links
        was False) so the agent doesn't have to guess.
    """
    from ..utils.wikilinks import rewrite_wikilinks_in_vault

    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    is_valid, error = _validate_move_paths(origen, destino, vault_path)
    if not is_valid:
        return Result.fail(error)

    path_origen = vault_path / origen
    path_destino = vault_path / destino

    if not path_origen.exists():
        return Result.fail(f"Source file does not exist: {origen}")

    if not path_origen.is_file():
        return Result.fail(f"Source is not a file: {origen}")

    if path_destino.exists():
        return Result.fail(f"Destination file already exists: {destino}")

    if crear_carpetas:
        path_destino.parent.mkdir(parents=True, exist_ok=True)
    elif not path_destino.parent.exists():
        return Result.fail(
            f"Destination folder does not exist: {path_destino.parent.name}"
        )

    old_stem = path_origen.stem
    new_stem = path_destino.stem

    path_origen.rename(path_destino)

    msg = f"File moved/renamed:\nFrom: {origen}\nTo:   {destino}"

    if update_links and old_stem != new_stem:
        total, touched = rewrite_wikilinks_in_vault(
            vault_path, old_target=old_stem, new_target=new_stem
        )
        msg += f"\nLinks updated: {total} references across {len(touched)} files."
    elif not update_links:
        # Issue #11: surface impact even when we didn't rewrite.
        total, touched = rewrite_wikilinks_in_vault(
            vault_path, old_target=old_stem, new_target=new_stem, dry_run=True
        )
        if old_stem != new_stem and total > 0:
            msg += (
                f"\nWarning: {total} wikilinks across {len(touched)} files now point "
                f"to the old stem '{old_stem}'. Re-run with update_links=True to fix."
            )

    return Result.ok(msg)


def _is_content_paragraph(line: str) -> bool:
    """Check if a stripped line is a content paragraph (not markup/headers)."""
    if not line or len(line) <= 50:
        return False
    return not any(line.startswith(prefix) for prefix in _NON_CONTENT_PREFIXES)


def _filter_valid_notes(
    notas: list[Path],
    vault_path: Path,
    excl_folders: list[str],
) -> list[Path]:
    """Filter notes excluding forbidden paths, excluded folders, and tiny files."""
    result = []
    for nota in notas:
        ruta_str = str(nota.relative_to(vault_path))
        if any(excl in ruta_str for excl in excl_folders):
            continue
        if nota.stat().st_size < 200:
            continue
        is_forbidden, _ = is_path_forbidden(nota, vault_path)
        if is_forbidden:
            continue
        result.append(nota)
    return result


def get_random_concept(carpeta: str = "") -> Result[str]:
    """Extract a random concept from the vault as a flashcard.

    Args:
        carpeta: Specific folder to search (empty = entire vault)

    Returns:
        Result with formatted flashcard containing random note excerpt
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    search_path = vault_path / carpeta if carpeta else vault_path
    notas = list(search_path.rglob("*.md"))

    config = get_vault_config(vault_path)
    templates_folder = ""
    if config and config.templates_folder:
        templates_folder = config.templates_folder
    else:
        for item in vault_path.iterdir():
            if item.is_dir() and any(
                t in item.name.lower() for t in ["plantilla", "template"]
            ):
                templates_folder = item.name
                break

    excl_folders = [templates_folder, "System", "Sistema", ".agents", ".github"]
    notas_filtradas = _filter_valid_notes(notas, vault_path, excl_folders)

    if not notas_filtradas:
        return Result.fail("No valid notes found for concept extraction.")

    nota_elegida = secrets.choice(notas_filtradas)
    ruta_relativa = nota_elegida.relative_to(vault_path)

    with open(nota_elegida, "r", encoding="utf-8") as f:
        contenido = f.read()

    titulo_match = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
    titulo = titulo_match.group(1) if titulo_match else nota_elegida.stem

    # Extract content paragraphs
    parrafos = [
        linea.strip()
        for linea in contenido.split("\n")
        if _is_content_paragraph(linea.strip())
    ]

    if parrafos:
        fragmento = secrets.choice(parrafos)
        if len(fragmento) > 300:
            fragmento = fragmento[:300] + "..."
    else:
        fragmento = "(No meaningful text fragment found.)"

    tags_match = re.search(r"tags:\s*\[([^\]]+)\]", contenido)
    tags = tags_match.group(1) if tags_match else ""

    resultado = "**Random Concept**\n\n"
    resultado += f"**{titulo}**\n"
    resultado += f"`{ruta_relativa}`\n"
    if tags:
        resultado += f"Tags: {tags}\n"
    resultado += f"\n---\n\n{fragmento}\n"
    resultado += f'\n---\n*Want to go deeper? Use `notes.read("{ruta_relativa}")`*'

    return Result.ok(resultado)


def read_multiple_notes_logic(rutas: list[str]) -> Result[str]:
    """Read multiple notes in a batch to save LLM roundtrips.

    Args:
        rutas: List of file names or paths.

    Returns:
        JSON string with successful reads and errors.
    """

    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    resultados: dict[str, list[dict[str, Any]]] = {"ok": [], "err": []}

    for ruta in rutas:
        nota_path = find_note_by_name(ruta)
        if not nota_path:
            resultados["err"].append({"path": ruta, "error": "Not found"})
            continue

        is_allowed, error = check_path_access(nota_path, operation="read")
        if not is_allowed:
            resultados["err"].append({"path": ruta, "error": error})
            continue

        try:
            if nota_path.stat().st_size > MAX_NOTE_READ_BYTES:
                resultados["err"].append(
                    {
                        "path": ruta,
                        "error": "Note is too large to include in a batch read.",
                    }
                )
                continue
            with open(nota_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            metadata, cuerpo = _extract_frontmatter_from_content(contenido)

            resultados["ok"].append(
                {
                    "path": str(nota_path.relative_to(vault_path)),
                    "frontmatter": metadata,
                    "content": cuerpo,
                }
            )
        except (OSError, ValueError, KeyError) as e:
            resultados["err"].append({"path": ruta, "error": str(e)})

    json_str = json.dumps(resultados, ensure_ascii=False, default=_json_serial)
    if len(json_str.encode("utf-8")) > MAX_BATCH_READ_BYTES:
        return Result.fail("The response is too large. Request fewer notes at once.")

    return Result.ok(json_str)


def get_notes_info_logic(rutas: list[str]) -> Result[str]:
    """Get metadata for multiple notes without reading full content.

    Args:
        rutas: List of file names or paths.

    Returns:
        JSON string containing array of metadata objects.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Vault path is not configured.")

    infos: list[dict[str, Any]] = []

    for ruta in rutas:
        nota_path = find_note_by_name(ruta)
        if not nota_path:
            infos.append({"path": ruta, "error": "Not found"})
            continue

        is_allowed, error = check_path_access(nota_path, operation="read")
        if not is_allowed:
            infos.append({"path": ruta, "error": error})
            continue

        try:
            metadata = get_note_metadata(nota_path)

            has_frontmatter = False
            with open(nota_path, "r", encoding="utf-8") as f:
                first_lines = f.read(10)
                if first_lines.startswith("---"):
                    has_frontmatter = True

            infos.append(
                {
                    "path": str(nota_path.relative_to(vault_path)),
                    "size_kb": metadata.get("size_kb", 0),
                    "modified": metadata.get("modified", ""),
                    "has_frontmatter": has_frontmatter,
                }
            )
        except (OSError, ValueError) as e:
            infos.append({"path": ruta, "error": str(e)})

    return Result.ok(json.dumps(infos, ensure_ascii=False))
