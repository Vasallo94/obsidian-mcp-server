"""
Core business logic for navigation tools.

This module contains the actual implementation of navigation operations,
separated from the MCP tool registration to improve testability and
maintain single responsibility.

All functions return Result[str] for consistent error handling.
"""

from datetime import date, datetime
from pathlib import Path

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

logger = get_logger(__name__)


def format_search_results(resultados: list, solo_titulos: bool) -> str:
    """Format search results for display.

    Args:
        resultados: List of search result dicts with keys: archivo, linea, coincidencia
        solo_titulos: Whether results are title-only matches

    Returns:
        Formatted string with results grouped by file
    """
    resultado_str = f"Encontradas {len(resultados)} coincidencias:\n\n"

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
        resultado_str += f"... y {len(por_archivo) - 20} archivos mas."

    return resultado_str


def list_notes(carpeta: str = "", incluir_subcarpetas: bool = True) -> Result[str]:
    """List all notes in the vault or a specific folder.

    Args:
        carpeta: Specific folder to explore (empty = vault root)
        incluir_subcarpetas: Whether to include subfolders in search

    Returns:
        Result with formatted string of notes organized by folder
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    if carpeta:
        target_path = vault_path / carpeta
        if not target_path.exists():
            return Result.fail(f"La carpeta '{carpeta}' no existe en el vault")
    else:
        target_path = vault_path

    pattern = "**/*.md" if incluir_subcarpetas else "*.md"
    notas = list(target_path.glob(pattern))

    if not notas:
        return Result.ok(f"No se encontraron notas en '{carpeta or 'raiz'}'")

    notas_por_carpeta: dict[str, list[dict]] = {}
    notas_filtradas = 0
    for nota in notas:
        is_forbidden, _ = is_path_forbidden(nota, vault_path)
        if is_forbidden:
            notas_filtradas += 1
            continue

        ruta_relativa = nota.relative_to(vault_path)
        carpeta_padre = (
            str(ruta_relativa.parent) if ruta_relativa.parent != Path(".") else "Raiz"
        )

        if carpeta_padre not in notas_por_carpeta:
            notas_por_carpeta[carpeta_padre] = []

        metadata = get_note_metadata(nota)
        notas_por_carpeta[carpeta_padre].append(metadata)

    total_visibles = len(notas) - notas_filtradas

    resultado = f"Notas encontradas en el vault ({total_visibles} total):\n\n"

    for carpeta_nombre, lista_notas in sorted(notas_por_carpeta.items()):
        resultado += f"{carpeta_nombre} ({len(lista_notas)} notas):\n"
        for nota_meta in sorted(lista_notas, key=lambda x: x["name"]):
            resultado += (
                f"   {nota_meta['name']} "
                f"({nota_meta['size_kb']:.1f}KB, {nota_meta['modified']})\n"
            )
        resultado += "\n"

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
        return Result.fail(f"No se encontro la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, operation="leer")
    if not is_allowed:
        return Result.fail(error)

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    metadata = get_note_metadata(nota_path)

    resultado = f"**{metadata['name']}**\n"
    resultado += f"Ubicacion: {metadata['relative_path']}\n"
    resultado += (
        f"Tamaño: {metadata['size_kb']:.1f}KB | Modificado: {metadata['modified']}\n"
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
        return Result.fail("La ruta del vault no esta configurada.")

    try:
        fecha_inicio = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
    except ValueError:
        return Result.fail("Formato de fecha invalido. Usa YYYY-MM-DD (ej: 2024-01-15)")

    if fecha_hasta:
        try:
            fecha_fin = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
        except ValueError:
            return Result.fail("Formato de fecha invalido. Usa YYYY-MM-DD")
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
        return Result.ok(
            f"No se encontraron notas modificadas entre {fecha_desde} y {fecha_fin}"
        )

    notas_encontradas.sort(key=lambda x: x["fecha"], reverse=True)

    resultado = (
        f"Notas modificadas entre {fecha_desde} y {fecha_fin} "
        f"({len(notas_encontradas)} encontradas):\n\n"
    )

    for nota in notas_encontradas:
        resultado += f"{nota['name']} ({nota['size_kb']:.1f}KB)\n"
        resultado += f"   {nota['relative_path']} | {nota['fecha']}\n\n"

    return Result.ok(resultado)


def move_note(origen: str, destino: str, crear_carpetas: bool = True) -> Result[str]:
    """Move or rename a note within the vault.

    Args:
        origen: Current relative path of the note
        destino: New relative path for the note
        crear_carpetas: Whether to create destination folders if needed

    Returns:
        Result with success or error message
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("Ruta del vault no configurada")

    is_valid, error = validate_path_within_vault(origen, vault_path)
    if not is_valid:
        return Result.fail(f"Error de seguridad (origen): {error}")

    is_valid, error = validate_path_within_vault(destino, vault_path)
    if not is_valid:
        return Result.fail(f"Error de seguridad (destino): {error}")

    config = get_vault_config(vault_path)
    private_folders = ["**/Private/", "**/Privado/*"]
    if config and config.private_paths:
        private_folders = config.private_paths

    if is_path_in_restricted_folder(origen, private_folders, vault_path):
        return Result.fail(
            "ACCESO DENEGADO: No se permite mover archivos desde carpetas restringidas"
        )

    if is_path_in_restricted_folder(destino, private_folders, vault_path):
        return Result.fail(
            "ACCESO DENEGADO: No se permite mover archivos hacia carpetas restringidas"
        )

    path_origen = vault_path / origen
    path_destino = vault_path / destino

    if not path_origen.exists():
        return Result.fail(f"El archivo origen no existe: {origen}")

    if not path_origen.is_file():
        return Result.fail(f"El origen no es un archivo: {origen}")

    if path_destino.exists():
        return Result.fail(f"El archivo destino ya existe: {destino}")

    if crear_carpetas:
        path_destino.parent.mkdir(parents=True, exist_ok=True)
    elif not path_destino.parent.exists():
        return Result.fail(f"La carpeta destino no existe: {path_destino.parent.name}")

    path_origen.rename(path_destino)

    return Result.ok(f"Archivo movido/renombrado:\nDe: {origen}\nA:  {destino}")


def get_random_concept(carpeta: str = "") -> Result[str]:
    """Extract a random concept from the vault as a flashcard.

    Args:
        carpeta: Specific folder to search (empty = entire vault)

    Returns:
        Result with formatted flashcard containing random note excerpt
    """
    import random
    import re

    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

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

    excl_folders = [templates_folder, "System", "Sistema", ".agent", ".github"]

    notas_filtradas = []
    for nota in notas:
        ruta_str = str(nota.relative_to(vault_path))
        if any(excl in ruta_str for excl in excl_folders):
            continue
        if nota.stat().st_size < 200:
            continue
        is_forbidden, _ = is_path_forbidden(nota, vault_path)
        if is_forbidden:
            continue
        notas_filtradas.append(nota)

    if not notas_filtradas:
        return Result.fail("No se encontraron notas validas para extraer conceptos.")

    nota_elegida = random.choice(notas_filtradas)
    ruta_relativa = nota_elegida.relative_to(vault_path)

    with open(nota_elegida, "r", encoding="utf-8") as f:
        contenido = f.read()

    titulo_match = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
    titulo = titulo_match.group(1) if titulo_match else nota_elegida.stem

    lineas = contenido.split("\n")
    parrafos = []
    for linea in lineas:
        linea_strip = linea.strip()
        if (
            linea_strip
            and not linea_strip.startswith("#")
            and not linea_strip.startswith("-")
            and not linea_strip.startswith("*")
            and not linea_strip.startswith(">")
            and not linea_strip.startswith("---")
            and not linea_strip.startswith("[[")
            and len(linea_strip) > 50
        ):
            parrafos.append(linea_strip)

    if parrafos:
        fragmento = random.choice(parrafos)
        if len(fragmento) > 300:
            fragmento = fragmento[:300] + "..."
    else:
        fragmento = "(No se encontro un fragmento de texto significativo)"

    tags_match = re.search(r"tags:\s*\[([^\]]+)\]", contenido)
    tags = tags_match.group(1) if tags_match else ""

    resultado = "**Concepto Aleatorio**\n\n"
    resultado += f"**{titulo}**\n"
    resultado += f"`{ruta_relativa}`\n"
    if tags:
        resultado += f"Tags: {tags}\n"
    resultado += f"\n---\n\n{fragmento}\n"
    resultado += f'\n---\n*Quieres profundizar? Usa `leer_nota("{ruta_relativa}")`*'

    return Result.ok(resultado)
