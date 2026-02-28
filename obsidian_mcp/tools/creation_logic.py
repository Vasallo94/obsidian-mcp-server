"""
Core business logic for creation tools.

This module contains the actual implementation of note creation operations,
separated from the MCP tool registration to improve testability and
maintain single responsibility.

All functions return Result[str] for consistent error handling.
"""

# pylint: disable=too-many-lines

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from ..config import get_vault_path
from ..result import Result
from ..utils import (
    check_path_access,
    find_note_by_name,
    get_logger,
    sanitize_filename,
)
from ..vault_config import get_vault_config


def _json_serial(obj: Any) -> str:
    """JSON serializer for objects not handled by default json module."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


logger = get_logger(__name__)


def _process_date_placeholders(content: str, date_obj: datetime | None = None) -> str:
    """
    Process date placeholders in content.

    Supports formats:
    - {{date}} or {{fecha}} -> YYYY-MM-DD
    - {{date:FORMAT}} -> Custom Moment.js-style format
    """
    if date_obj is None:
        date_obj = datetime.now()

    format_map = [
        ("YYYY", "%Y"),
        ("YY", "%y"),
        ("MMMM", "%B"),
        ("MMM", "%b"),
        ("MM", "%m"),
        ("M", "%-m" if hasattr(datetime, "strftime") else "%m"),
        ("dddd", "%A"),
        ("ddd", "%a"),
        ("DD", "%d"),
        ("D", "%-d" if hasattr(datetime, "strftime") else "%d"),
        ("HH", "%H"),
        ("mm", "%M"),
        ("ss", "%S"),
    ]

    meses_es = {
        "January": "Enero",
        "February": "Febrero",
        "March": "Marzo",
        "April": "Abril",
        "May": "Mayo",
        "June": "Junio",
        "July": "Julio",
        "August": "Agosto",
        "September": "Septiembre",
        "October": "Octubre",
        "November": "Noviembre",
        "December": "Diciembre",
        "Jan": "Ene",
        "Feb": "Feb",
        "Mar": "Mar",
        "Apr": "Abr",
        "Jun": "Jun",
        "Jul": "Jul",
        "Aug": "Ago",
        "Sep": "Sep",
        "Oct": "Oct",
        "Nov": "Nov",
        "Dec": "Dic",
    }
    dias_es = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
        "Mon": "Lun",
        "Tue": "Mar",
        "Wed": "Mié",
        "Thu": "Jue",
        "Fri": "Vie",
        "Sat": "Sáb",
        "Sun": "Dom",
    }

    def convert_format(moment_format: str) -> str:
        result = moment_format
        for moment, strftime in format_map:
            result = result.replace(moment, strftime)
        try:
            formatted = date_obj.strftime(result)
            for en, es in meses_es.items():
                formatted = formatted.replace(en, es)
            for en, es in dias_es.items():
                formatted = formatted.replace(en, es)
            return formatted
        except ValueError:
            return moment_format

    pattern_with_format = re.compile(r"\{\{(?:date|fecha):([^}]+)\}\}")

    def replace_with_format(match: re.Match) -> str:
        formato = match.group(1)
        return convert_format(formato)

    content = pattern_with_format.sub(replace_with_format, content)
    simple_date = date_obj.strftime("%Y-%m-%d")
    content = re.sub(r"\{\{(?:date|fecha)\}\}", simple_date, content)

    content = re.sub(
        r'(created:\s*["\']?)YYYY-MM-DD(["\']?)',
        rf"\g<1>{simple_date}\g<2>",
        content,
    )
    content = re.sub(
        r'(updated:\s*["\']?)YYYY-MM-DD(["\']?)',
        rf"\g<1>{simple_date}\g<2>",
        content,
    )

    return content


def _extract_frontmatter_from_content(contenido: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter from content if it exists."""
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
    match = frontmatter_pattern.match(contenido)
    if not match:
        return {}, contenido

    try:
        yaml_content = match.group(1)
        metadata = yaml.safe_load(yaml_content) or {}
        if not isinstance(metadata, dict):
            return {}, contenido
        contenido_limpio = contenido[match.end() :]
        return metadata, contenido_limpio.lstrip()
    except yaml.YAMLError:
        return {}, contenido


def _build_frontmatter(
    titulo: str,
    ahora: str,
    tags_list: list[str],
    agente_creador: str = "",
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    """Build YAML frontmatter block combining metadata."""
    metadata: dict[str, Any] = {}

    if extra_metadata:
        metadata.update(extra_metadata)

    metadata["title"] = titulo
    metadata["created"] = ahora

    existing_tags = metadata.get("tags", [])
    if isinstance(existing_tags, str):
        existing_tags = [t.strip() for t in existing_tags.split(",") if t.strip()]
    elif not isinstance(existing_tags, list):
        existing_tags = []

    all_tags = list(existing_tags)
    for tag in tags_list:
        if tag not in all_tags:
            all_tags.append(tag)

    if all_tags:
        metadata["tags"] = all_tags

    if agente_creador:
        metadata["agente_creador"] = agente_creador

    yaml_content = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    return f"---\n{yaml_content}---\n\n"


def append_to_note(
    nombre_archivo: str,
    contenido: str,
    al_final: bool = True,
) -> Result[str]:
    """Append content to an existing note.

    Args:
        nombre_archivo: Name of the file to modify.
        contenido: Content to append.
        al_final: If True, append at end; if False, prepend.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontro la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido_actual = f.read()

    if al_final:
        sep = "\n\n" if not contenido_actual.endswith("\n\n") else ""
        nuevo_contenido = contenido_actual + sep + contenido
    else:
        nuevo_contenido = contenido + "\n\n" + contenido_actual

    with open(nota_path, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

    ruta_relativa = nota_path.relative_to(vault_path)
    posicion = "final" if al_final else "inicio"
    return Result.ok(f"Contenido agregado al {posicion} de {ruta_relativa}")


def delete_note(nombre_archivo: str, confirmar: bool = False) -> Result[str]:
    """Delete a note from the vault (requires confirmation).

    Args:
        nombre_archivo: Name of the file to delete.
        confirmar: Must be True to confirm deletion.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    if not confirmar:
        return Result.fail("Para eliminar una nota, debes confirmar con confirmar=True")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontro la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "eliminar")
    if not is_allowed:
        return Result.fail(error)

    ruta_relativa = nota_path.relative_to(vault_path)
    nota_path.unlink()

    return Result.ok(f"Nota eliminada: {ruta_relativa}")


def edit_note(nombre_archivo: str, nuevo_contenido: str) -> Result[str]:
    """Edit an existing note, replacing all its content.

    Args:
        nombre_archivo: Name or path of the note to edit.
        nuevo_contenido: The complete new content (including YAML frontmatter).

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontro la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "editar")
    if not is_allowed:
        return Result.fail(error)

    contenido_procesado = _process_date_placeholders(nuevo_contenido)

    ahora = datetime.now().strftime("%Y-%m-%d")
    if contenido_procesado.startswith("---"):
        if re.search(r"^updated:", contenido_procesado, re.MULTILINE):
            contenido_procesado = re.sub(
                r'^(updated:\s*["\']?)[^"\'\n]+(["\']?)$',
                rf"\g<1>{ahora}\g<2>",
                contenido_procesado,
                count=1,
                flags=re.MULTILINE,
            )
        else:
            if re.search(r"^created:", contenido_procesado, re.MULTILINE):
                contenido_procesado = re.sub(
                    r"^(created:\s*.+)$",
                    rf"\1\nupdated: {ahora}",
                    contenido_procesado,
                    count=1,
                    flags=re.MULTILINE,
                )
            else:
                contenido_procesado = contenido_procesado.replace(
                    "\n---\n", f"\nupdated: {ahora}\n---\n", 1
                )

    with open(nota_path, "w", encoding="utf-8") as f:
        f.write(contenido_procesado)

    ruta_relativa = nota_path.relative_to(vault_path)
    return Result.ok(f"Nota editada correctamente: {ruta_relativa}")


def suggest_folder_location(titulo: str, contenido: str, etiquetas: str = "") -> str:
    """Helper to suggest location based on semantics and keywords."""

    # 1. Try Semantic Suggestion (multi-candidate)
    # Import inside try to gracefully degrade when RAG optional deps are missing.
    try:
        from ..semantic.service import (
            SemanticService,  # pylint: disable=import-outside-toplevel # noqa: PLC0415
        )

        vault_path = get_vault_path()
        if vault_path:
            service = SemanticService(str(vault_path))

            # Combine distinct terms for better retrieval
            # Limit content to first 1000 chars to avoid huge queries
            query = f"{titulo} {etiquetas} {contenido[:1000]}"
            suggestions = service.suggest_folder(query, limit=5, top_k=3)

            if suggestions:
                # Format multi-candidate response
                lines = [
                    "📂 **Sugerencias basadas en contenido similar:**\n",
                    "(Evalúa estas opciones y propón la mejor al usuario)\n",
                ]
                for i, s in enumerate(suggestions, 1):
                    conf_pct = int(s["confidence"] * 100)
                    conf_bar = "█" * (conf_pct // 10) + "░" * (10 - conf_pct // 10)
                    notes_str = (
                        ", ".join(s["similar_notes"]) if s["similar_notes"] else "—"
                    )
                    lines.append(
                        f"{i}. `{s['folder']}`\n"
                        f"   Confianza: {conf_bar} {conf_pct}% "
                        f"({s['votes']} votos)\n"
                        f"   Notas similares: {notes_str}"
                    )

                # Add guidance for the LLM
                top_conf = suggestions[0]["confidence"]
                if top_conf >= 0.6:
                    pct = int(top_conf * 100)
                    lines.append(
                        f"\n💡 La opción 1 tiene alta confianza ({pct}%). "
                        "Puedes sugerirla al usuario."
                    )
                elif top_conf >= 0.4:
                    lines.append(
                        "\n⚠️ Confianza moderada. Muestra las opciones al "
                        "usuario para que decida."
                    )
                else:
                    lines.append(
                        "\n⚠️ Baja confianza. Pregunta al usuario dónde "
                        "prefiere ubicar la nota."
                    )

                return "\n".join(lines)

    except (ImportError, OSError) as e:
        logger.debug("Semantic suggestion unavailable, using heuristic: %s", e)

    texto = (titulo + " " + contenido + " " + etiquetas).lower()

    # IA / Machine Learning
    if any(
        k in texto
        for k in [
            "ia",
            "inteligencia artificial",
            "mcp",
            "llm",
            "gpt",
            "claude",
            "agente",
            "embedding",
            "rag",
            "machine learning",
            "ml",
            "modelo",
        ]
    ):
        return "📂 Sugerencia: `02_Aprendizaje/IA`"

    # Lógica simple de categorización basada en la estructura del vault
    if any(k in texto for k in ["poema", "poesía", "verso", "rima"]):
        return "📂 Sugerencia: `03_Creaciones/Poemas`"
    elif any(k in texto for k in ["reflexión", "pienso", "creo", "opinión"]):
        return "📂 Sugerencia: `03_Creaciones/Reflexiones`"
    elif any(
        k in texto
        for k in [
            "código",
            "python",
            "sql",
            "config",
            "bash",
            "script",
            "git",
            "docker",
        ]
    ):
        return "📂 Sugerencia: `02_Aprendizaje/Programación`"
    elif any(
        k in texto
        for k in [
            "sistema",
            "linux",
            "ssh",
            "nas",
            "red",
            "networking",
            "homelab",
        ]
    ):
        return "📂 Sugerencia: `02_Aprendizaje/Sistemas`"
    elif any(k in texto for k in ["filosofía", "ética", "aristóteles", "dualismo"]):
        return "📂 Sugerencia: `02_Aprendizaje/Filosofía`"
    elif any(k in texto for k in ["psicología", "cognitivo", "mente", "ego"]):
        return "📂 Sugerencia: `02_Aprendizaje/Psicología`"

    # Default fallback - scan for inbox-like folders or use root
    try:
        vault_path = get_vault_path()
        if vault_path:
            for item in Path(vault_path).iterdir():
                if item.is_dir() and any(
                    t in item.name.lower() for t in ["inbox", "bandeja", "entrada"]
                ):
                    return f"📂 Sugerencia: `{item.name}` (Categoría general)"
    except OSError as e:
        logger.debug("Error al buscar carpeta inbox en vault: %s", e)

    return "📂 Sugerencia: Ubicación a confirmar con el usuario"


def create_note(
    titulo: str,
    contenido: str,
    carpeta: str = "",
    etiquetas: str = "",
    plantilla: str = "",
    agente_creador: str = "",
    descripcion: str = "",
) -> Result[str]:
    """Create a new note in the vault.

    Args:
        titulo: Title of the note.
        contenido: Content of the note.
        carpeta: Target folder (empty = root or auto-suggested).
        etiquetas: Comma-separated tags.
        plantilla: Name of the template file to use.
        agente_creador: Name of the creating agent.
        descripcion: Brief description for placeholders.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # Preparar nombre de archivo
    nombre_archivo = sanitize_filename(titulo)

    # Determinar ruta (si no hay carpeta, usar ubicación sugerida)
    config = get_vault_config(vault_path)

    if not carpeta:
        # Intento de sugerencia automática si no se especifica
        res_sug = suggest_folder_location(titulo, contenido, etiquetas)
        # Extrae el path de vuelta entre backticks: 📂 Sugerencia: `path`
        match = re.search(r"`([^`]+)`", res_sug)
        if match:
            carpeta = match.group(1)
        else:
            # Fallback to vault root
            carpeta = ""

    carpeta_path = vault_path / carpeta
    carpeta_path.mkdir(parents=True, exist_ok=True)
    nota_path = carpeta_path / nombre_archivo

    if not nota_path.suffix == ".md":
        nota_path = nota_path.with_suffix(".md")

    # Security: Validate path access (within vault + not forbidden)
    is_allowed, error = check_path_access(nota_path, vault_path, "crear nota en")
    if not is_allowed:
        return Result.fail(error)

    # Verificar si ya existe
    if nota_path.exists():
        return Result.fail(f"Ya existe una nota con el nombre '{nombre_archivo}'")

    # Preparar contenido final
    contenido_final = ""
    ahora = datetime.now().strftime("%Y-%m-%d")

    # Si se usa plantilla
    if plantilla:
        # Get templates folder
        templates_folder = None
        if config and config.templates_folder:
            templates_folder = config.templates_folder
        else:
            for item in vault_path.iterdir():
                if item.is_dir() and any(
                    t in item.name.lower() for t in ["plantilla", "template"]
                ):
                    templates_folder = item.name
                    break

        if not templates_folder:
            return Result.fail(
                "No se detectó carpeta de plantillas.\n\n"
                "💡 Crea `.agents/vault.yaml` con:\n"
                "```yaml\n"
                'templates_folder: "TuCarpetaDePlantillas"\n'
                "```"
            )

        plantilla_path = vault_path / templates_folder / plantilla
        if not plantilla.endswith(".md"):
            plantilla_path = plantilla_path.with_suffix(".md")

        if plantilla_path.exists():
            with open(plantilla_path, "r", encoding="utf-8") as f:
                plantilla_content = f.read()

            # Reemplazos de título
            plantilla_content = plantilla_content.replace("{{title}}", titulo)
            plantilla_content = plantilla_content.replace("{{titulo}}", titulo)

            # Reemplazos de descripción
            plantilla_content = plantilla_content.replace(
                "{{description}}", descripcion
            )
            plantilla_content = plantilla_content.replace(
                "{{descripcion}}", descripcion
            )

            # Reemplazos de hora (HH:mm)
            hora_actual = datetime.now().strftime("%H:%M")
            plantilla_content = plantilla_content.replace("{{time}}", hora_actual)
            plantilla_content = plantilla_content.replace("{{hora}}", hora_actual)

            # Reemplazos de carpeta
            carpeta_final = carpeta if carpeta else ""
            plantilla_content = plantilla_content.replace("{{folder}}", carpeta_final)
            plantilla_content = plantilla_content.replace("{{carpeta}}", carpeta_final)

            # Reemplazos de etiquetas
            plantilla_content = plantilla_content.replace("{{tags}}", etiquetas)
            plantilla_content = plantilla_content.replace("{{etiquetas}}", etiquetas)

            # Procesar todas las fechas con formatos
            plantilla_content = _process_date_placeholders(plantilla_content)

            contenido_final = plantilla_content
            # Si hay contenido adicional, añadirlo al final
            if contenido:
                # Extraer frontmatter del contenido si existe
                # para evitar duplicación con la plantilla
                _, contenido_limpio = _extract_frontmatter_from_content(contenido)
                if contenido_final.endswith("\n\n"):
                    contenido_final += contenido_limpio
                else:
                    contenido_final += f"\n\n{contenido_limpio}"
        else:
            return Result.fail(f"No se encontró la plantilla '{plantilla}'")
    else:
        # Sin plantilla: detectar si el contenido ya tiene frontmatter
        tags_list = [t.strip() for t in etiquetas.split(",") if t.strip()]

        # Extraer frontmatter del contenido si existe
        extra_metadata, contenido_limpio = _extract_frontmatter_from_content(contenido)

        # Construir frontmatter unificado
        frontmatter = _build_frontmatter(
            titulo=titulo,
            ahora=ahora,
            tags_list=tags_list,
            agente_creador=agente_creador,
            extra_metadata=extra_metadata if extra_metadata else None,
        )

        contenido_final = frontmatter

        # Añadir título si el contenido limpio no empieza con un heading
        if not contenido_limpio.lstrip().startswith("#"):
            contenido_final += f"# {titulo}\n\n"

        contenido_final += contenido_limpio

    # Procesar cualquier placeholder de fecha restante en el contenido
    contenido_final = _process_date_placeholders(contenido_final)

    # Escribir archivo
    with open(nota_path, "w", encoding="utf-8") as f:
        f.write(contenido_final)

    ruta_relativa = nota_path.relative_to(vault_path)
    resultado = f"Nota creada: **{titulo}**\n"
    resultado += f"📍 Ubicación: {ruta_relativa}\n"
    if plantilla:
        resultado += f"📝 Plantilla usada: {plantilla}\n"
    if agente_creador:
        resultado += f"🤖 Agente: {agente_creador}\n"

    return Result.ok(resultado)


def list_templates() -> Result[str]:
    """List available templates in the vault.

    Returns:
        Result with formatted list of templates.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    config = get_vault_config(vault_path)

    # Determine templates folder from config or auto-detect
    templates_folder = None
    if config and config.templates_folder:
        templates_folder = config.templates_folder
    else:
        # Auto-detect: look for folders with "plantilla" or "template"
        for item in vault_path.iterdir():
            if item.is_dir() and any(
                t in item.name.lower() for t in ["plantilla", "template"]
            ):
                templates_folder = item.name
                break

    if not templates_folder:
        return Result.fail(
            "No se detectó carpeta de plantillas en el vault.\n\n"
            "💡 **Solución**: Crea `.agents/vault.yaml` con:\n"
            "```yaml\n"
            'templates_folder: "NombreDeTuCarpetaDePlantillas"\n'
            "```"
        )

    templates_path = vault_path / templates_folder
    if not templates_path.exists():
        return Result.fail(f"No se encontró la carpeta '{templates_folder}'")

    plantillas = []
    for item in sorted(templates_path.glob("*.md")):
        plantillas.append(item.name)

    if not plantillas:
        return Result.ok(f"ℹ️ No hay plantillas disponibles en {templates_folder}")

    return Result.ok(
        "📝 **Plantillas disponibles:**\n" + "\n".join([f"- {p}" for p in plantillas])
    )


def search_and_replace_global(
    buscar: str,
    reemplazar: str,
    carpeta: str = "",
    solo_preview: bool = True,
    limite: int = 100,
) -> Result[str]:
    """Search and replace text in all notes.

    Args:
        buscar: Text/Pattern to search (literal).
        reemplazar: Replacement text.
        carpeta: Specific folder to search (empty = whole vault).
        solo_preview: If True, only show preview of changes.
        limite: Max files to process.

    Returns:
        Result with summary of changes.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    if not buscar:
        return Result.fail("Debes especificar un texto a buscar.")

    # Determinar carpeta de búsqueda
    if carpeta:
        search_path = vault_path / carpeta
        if not search_path.exists():
            return Result.fail(f"La carpeta '{carpeta}' no existe.")
    else:
        search_path = vault_path

    # Carpetas excluidas por seguridad
    config = get_vault_config(vault_path)
    excluded = [".git", ".obsidian", ".trash", "node_modules"]
    if config and config.excluded_folders:
        excluded.extend(config.excluded_folders)

    # Buscar archivos .md
    archivos_afectados: list[dict[str, Any]] = []
    archivos_procesados = 0

    for md_file in search_path.rglob("*.md"):
        # Saltar carpetas excluidas
        if any(excl in md_file.parts for excl in excluded):
            continue

        # Verificar acceso usando función centralizada
        is_allowed, _ = check_path_access(md_file, vault_path, "buscar en")
        if not is_allowed:
            continue

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                contenido = f.read()

            if buscar in contenido:
                ocurrencias = contenido.count(buscar)
                ruta_rel = md_file.relative_to(vault_path)
                archivos_afectados.append(
                    {
                        "path": md_file,
                        "ruta_rel": str(ruta_rel),
                        "ocurrencias": ocurrencias,
                        "contenido_original": contenido,
                    }
                )

                archivos_procesados += 1
                if archivos_procesados >= limite:
                    break

        except OSError as e:
            logger.debug("No se pudo leer '%s' para busqueda: %s", md_file, e)
            continue

    if not archivos_afectados:
        return Result.ok(f"ℹ️ No se encontró '{buscar}' en ninguna nota.")

    # Modo preview
    if solo_preview:
        resultado = f"🔍 **Preview de búsqueda**: `{buscar}`\n"
        resultado += f"📊 Se encontraron **{len(archivos_afectados)}** "
        total_ocurrencias = sum(a["ocurrencias"] for a in archivos_afectados)
        resultado += f"archivos con {total_ocurrencias} ocurrencias totales.\n\n"
        resultado += "**Archivos afectados:**\n"
        for arch in archivos_afectados[:20]:  # Limitar output
            resultado += f"- `{arch['ruta_rel']}` ({arch['ocurrencias']} ocurrencias)\n"
        if len(archivos_afectados) > 20:
            resultado += f"- ... y {len(archivos_afectados) - 20} archivos más\n"
        resultado += "\n⚠️ Ejecuta con `solo_preview=False` para aplicar los cambios."
        return Result.ok(resultado)

    # Modo ejecución
    archivos_modificados = 0
    total_reemplazos = 0

    for arch in archivos_afectados:
        try:
            nuevo_contenido = arch["contenido_original"].replace(buscar, reemplazar)
            with open(arch["path"], "w", encoding="utf-8") as f:
                f.write(nuevo_contenido)
            archivos_modificados += 1
            total_reemplazos += arch["ocurrencias"]
        except OSError as e:
            logger.warning("No se pudo escribir reemplazo en '%s': %s", arch["path"], e)
            continue

    resultado = "✅ **Reemplazo completado**\n"
    resultado += f"- Archivos modificados: {archivos_modificados}\n"
    resultado += f"- Reemplazos realizados: {total_reemplazos}\n"
    resultado += f"- `{buscar}` → `{reemplazar}`"
    return Result.ok(resultado)


def quick_capture(texto: str, etiquetas: str = "") -> Result[str]:
    """Capture an idea quickly to Inbox with minimal friction.

    Args:
        texto: The content to capture.
        etiquetas: Optional comma-separated tags.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # 1. Find Inbox folder by auto-detection
    inbox_folder = None
    inbox_candidates = ["00_Bandeja", "Inbox", "01_Inbox", "Bandeja", "inbox"]

    for candidate in inbox_candidates:
        candidate_path = vault_path / candidate
        if candidate_path.exists() and candidate_path.is_dir():
            inbox_folder = candidate
            break

    if not inbox_folder:
        # Fallback: create in root
        inbox_folder = ""

    # 2. Generate title with timestamp
    ahora = datetime.now()
    titulo = ahora.strftime("Captura %Y-%m-%d %H:%M")

    # 3. Try to use "Idea" template if exists
    plantilla = ""
    templates_folder = None
    config = get_vault_config(vault_path)
    if config and config.templates_folder:
        templates_folder = config.templates_folder
    else:
        for item in vault_path.iterdir():
            if item.is_dir() and any(
                t in item.name.lower() for t in ["plantilla", "template"]
            ):
                templates_folder = item.name
                break

    if templates_folder:
        idea_template = vault_path / templates_folder / "Idea.md"
        if idea_template.exists():
            plantilla = "Idea.md"

    # 4. Create the note
    return create_note(
        titulo=titulo,
        contenido=texto,
        carpeta=inbox_folder,
        etiquetas=etiquetas,
        plantilla=plantilla,
    )


def append_to_section(
    nombre_archivo: str,
    seccion: str,
    contenido: str,
    crear_si_no_existe: bool = True,
) -> Result[str]:
    """Append content to a specific section of a note.

    Args:
        nombre_archivo: Name of the file to modify.
        seccion: Section heading to find (e.g., "Recursos", "## Ideas").
        contenido: Content to insert.
        crear_si_no_existe: If True, create the section if not found.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido_actual = f.read()

    # Normalize section name (remove leading # if present)
    seccion_limpia = seccion.lstrip("#").strip()

    # Find section heading at any level (##, ###, ####, etc.)
    # Pattern matches: ## Section, ### Section, etc.
    pattern = rf"^(#{{1,6}})\s+{re.escape(seccion_limpia)}\s*$"
    match = re.search(pattern, contenido_actual, re.MULTILINE | re.IGNORECASE)

    if match:
        # Found the section
        section_start = match.end()
        section_level = len(match.group(1))  # Number of # characters

        # Find the next heading of equal or higher level (fewer or equal #)
        next_heading_pattern = rf"^#{{{1},{section_level}}}\s+\S"
        remaining_content = contenido_actual[section_start:]
        next_match = re.search(next_heading_pattern, remaining_content, re.MULTILINE)

        if next_match:
            # Insert before next heading
            insert_pos = section_start + next_match.start()
            # Ensure proper spacing
            nuevo_contenido = (
                contenido_actual[:insert_pos].rstrip()
                + "\n\n"
                + contenido
                + "\n\n"
                + contenido_actual[insert_pos:].lstrip()
            )
        else:
            # No next heading, append at end of file
            nuevo_contenido = contenido_actual.rstrip() + "\n\n" + contenido + "\n"

    elif crear_si_no_existe:
        # Section not found, create it at end
        nuevo_contenido = (
            contenido_actual.rstrip() + f"\n\n## {seccion_limpia}\n\n{contenido}\n"
        )
    else:
        return Result.fail(
            f"No se encontró la sección '{seccion}' en la nota. "
            "Usa crear_si_no_existe=True para crearla."
        )

    with open(nota_path, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

    ruta_relativa = nota_path.relative_to(vault_path)
    return Result.ok(
        f"Contenido añadido a sección '{seccion_limpia}' de {ruta_relativa}"
    )


def get_frontmatter_logic(nombre_archivo: str) -> Result[str]:
    """Retrieve only the frontmatter of a note as JSON.

    Args:
        nombre_archivo: Name of the file.

    Returns:
        Result containing the frontmatter as a JSON string.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "leer")
    if not is_allowed:
        return Result.fail(error)

    try:
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        metadata, _ = _extract_frontmatter_from_content(contenido)
        return Result.ok(
            json.dumps(metadata, indent=2, ensure_ascii=False, default=_json_serial)
        )
    except OSError as e:
        return Result.fail(f"Error al leer frontmatter: {e}")


def update_frontmatter_logic(
    nombre_archivo: str,
    frontmatter_updates: str,
    merge: bool = True,
) -> Result[str]:
    """Update the frontmatter of a note without altering the body.

    Args:
        nombre_archivo: Name of the file.
        frontmatter_updates: JSON string containing the dictionary of updates.
        merge: If True, merges with existing frontmatter. If False, replaces it.

    Returns:
        Result with success message.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    try:
        updates_dict = json.loads(frontmatter_updates)
    except json.JSONDecodeError:
        return Result.fail("frontmatter_updates debe ser un JSON string válido.")

    try:
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        metadata, cuerpo = _extract_frontmatter_from_content(contenido)

        if merge:
            metadata.update(updates_dict)
        else:
            metadata = updates_dict

        yaml_content = yaml.dump(
            metadata,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        nuevo_contenido = f"---\n{yaml_content}---\n{cuerpo}"

        with open(nota_path, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)

        ruta_rel = nota_path.relative_to(vault_path)
        return Result.ok(f"Frontmatter actualizado exitosamente en {ruta_rel}")
    except OSError as e:
        return Result.fail(f"Error al actualizar frontmatter: {e}")


def manage_tags_logic(
    nombre_archivo: str,
    operation: str,
    tags: str,
) -> Result[str]:
    """Add, remove, or list tags in a note's frontmatter.

    Args:
        nombre_archivo: Name of the file.
        operation: 'add', 'remove', or 'list'.
        tags: Comma-separated tags to add/remove (empty for list).

    Returns:
        Result with success message or tag list.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontró la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
    if not is_allowed:
        return Result.fail(error)

    try:
        with open(nota_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        metadata, cuerpo = _extract_frontmatter_from_content(contenido)
        existing_tags = metadata.get("tags", [])

        # Normalize existing tags to a list of strings
        if isinstance(existing_tags, str):
            tags_list = [t.strip() for t in existing_tags.split(",") if t.strip()]
        elif isinstance(existing_tags, list):
            tags_list = [str(t).strip() for t in existing_tags if str(t).strip()]
        else:
            tags_list = []

        if operation == "list":
            tags_str = ", ".join(tags_list) if tags_list else "(sin etiquetas)"
            return Result.ok(f"Etiquetas en {nombre_archivo}: {tags_str}")

        input_tags = [t.strip() for t in tags.split(",") if t.strip()]

        if operation == "add":
            for t in input_tags:
                if t not in tags_list:
                    tags_list.append(t)
        elif operation == "remove":
            tags_list = [t for t in tags_list if t not in input_tags]
        else:
            return Result.fail("Operación no válida. Usa 'add', 'remove', o 'list'.")

        metadata["tags"] = tags_list

        yaml_content = yaml.dump(
            metadata,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        nuevo_contenido = f"---\n{yaml_content}---\n{cuerpo}"

        with open(nota_path, "w", encoding="utf-8") as f:
            f.write(nuevo_contenido)

        ruta_rel = nota_path.relative_to(vault_path)
        return Result.ok(
            f"Etiquetas ({operation}) actualizadas exitosamente en {ruta_rel}"
        )
    except OSError as e:
        return Result.fail(f"Error al gestionar etiquetas: {e}")
