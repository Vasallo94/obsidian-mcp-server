"""
Herramientas de creación y edición para el vault de Obsidian.

Estas herramientas permiten crear nuevas notas y modificar las existentes,
facilitando la gestión de contenido del vault desde un cliente MCP.
"""

import re
from datetime import datetime
from typing import Any

import yaml
from fastmcp import FastMCP

from ..config import get_vault_path, get_vault_settings
from ..utils import (
    check_path_access,
    find_note_by_name,
    is_path_in_restricted_folder,
    sanitize_filename,
    validate_path_within_vault,
)


def _process_date_placeholders(content: str, date_obj: datetime | None = None) -> str:
    """
    Procesa placeholders de fecha en el contenido.

    Soporta formatos:
    - {{date}} o {{fecha}} -> YYYY-MM-DD
    - {{date:FORMATO}} -> Formato personalizado estilo Moment.js/Obsidian

    Formatos soportados (subset de Moment.js):
    - YYYY: Año 4 dígitos (2026)
    - YY: Año 2 dígitos (26)
    - MM: Mes 2 dígitos (01-12)
    - M: Mes sin padding (1-12)
    - MMMM: Mes nombre completo (Enero)
    - MMM: Mes abreviado (Ene)
    - DD: Día 2 dígitos (01-31)
    - D: Día sin padding (1-31)
    - dddd: Día de semana completo (Lunes)
    - ddd: Día de semana abreviado (Lun)
    - HH: Hora 24h (00-23)
    - mm: Minutos (00-59)
    - ss: Segundos (00-59)

    Args:
        content: Contenido con placeholders de fecha.
        date_obj: Objeto datetime a usar (por defecto: ahora).

    Returns:
        Contenido con fechas reemplazadas.
    """
    if date_obj is None:
        date_obj = datetime.now()

    # Mapeo de formatos Moment.js -> strftime
    # Orden importa: más específicos primero
    FORMAT_MAP = [
        ("YYYY", "%Y"),
        ("YY", "%y"),
        ("MMMM", "%B"),  # Nombre completo del mes
        ("MMM", "%b"),  # Nombre abreviado
        ("MM", "%m"),
        ("M", "%-m" if hasattr(datetime, "strftime") else "%m"),  # Sin padding
        ("dddd", "%A"),  # Día de semana completo
        ("ddd", "%a"),  # Día de semana abreviado
        ("DD", "%d"),
        ("D", "%-d" if hasattr(datetime, "strftime") else "%d"),  # Sin padding
        ("HH", "%H"),
        ("mm", "%M"),
        ("ss", "%S"),
    ]

    # Nombres de meses y días en español
    MESES_ES = {
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
    DIAS_ES = {
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
        """Convierte formato Moment.js a strftime y formatea."""
        result = moment_format
        for moment, strftime in FORMAT_MAP:
            result = result.replace(moment, strftime)

        # Formatear con strftime
        try:
            formatted = date_obj.strftime(result)
            # Traducir meses y días al español
            for en, es in MESES_ES.items():
                formatted = formatted.replace(en, es)
            for en, es in DIAS_ES.items():
                formatted = formatted.replace(en, es)
            return formatted
        except ValueError:
            return moment_format  # Si falla, devolver original

    # Patrón para {{date:FORMATO}} o {{fecha:FORMATO}}
    pattern_with_format = re.compile(r"\{\{(?:date|fecha):([^}]+)\}\}")

    def replace_with_format(match: re.Match) -> str:
        formato = match.group(1)
        return convert_format(formato)

    content = pattern_with_format.sub(replace_with_format, content)

    # Patrón para {{date}} o {{fecha}} sin formato -> YYYY-MM-DD
    simple_date = date_obj.strftime("%Y-%m-%d")
    content = re.sub(r"\{\{(?:date|fecha)\}\}", simple_date, content)

    # También reemplazar placeholders literales YYYY-MM-DD (de templates mal escritos)
    # Solo si están en contexto de metadata (cerca de "created:" o "updated:")
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
    """
    Extrae el frontmatter YAML del contenido si existe.

    Args:
        contenido: Contenido que puede incluir frontmatter YAML al inicio.

    Returns:
        Tupla con (diccionario de metadatos, contenido sin frontmatter).
        Si no hay frontmatter, retorna ({}, contenido original).
    """
    # Patrón para detectar frontmatter YAML al inicio del contenido
    # Debe empezar con --- y terminar con ---
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)

    match = frontmatter_pattern.match(contenido)
    if not match:
        return {}, contenido

    try:
        yaml_content = match.group(1)
        metadata = yaml.safe_load(yaml_content) or {}
        if not isinstance(metadata, dict):
            # Si el YAML no es un diccionario, ignorarlo
            return {}, contenido

        # Contenido sin el frontmatter
        contenido_limpio = contenido[match.end() :]
        return metadata, contenido_limpio.lstrip()
    except yaml.YAMLError:
        # Si hay error parseando YAML, retornar contenido original
        return {}, contenido


def _build_frontmatter(
    titulo: str,
    ahora: str,
    tags_list: list[str],
    agente_creador: str = "",
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    """
    Construye el bloque frontmatter YAML combinando metadatos.

    Args:
        titulo: Título de la nota.
        ahora: Fecha actual en formato YYYY-MM-DD.
        tags_list: Lista de etiquetas.
        agente_creador: Nombre del agente creador (opcional).
        extra_metadata: Metadatos adicionales del contenido original.

    Returns:
        String con el frontmatter YAML formateado.
    """
    metadata: dict[str, Any] = {}

    # Si hay metadatos extra del contenido, empezar con ellos
    if extra_metadata:
        metadata.update(extra_metadata)

    # Sobreescribir/añadir campos obligatorios
    metadata["title"] = titulo
    metadata["created"] = ahora

    # Combinar tags: los del contenido original + los pasados explícitamente
    existing_tags = metadata.get("tags", [])
    if isinstance(existing_tags, str):
        # Convertir string a lista si es necesario
        existing_tags = [t.strip() for t in existing_tags.split(",") if t.strip()]
    elif not isinstance(existing_tags, list):
        existing_tags = []

    # Combinar sin duplicados, manteniendo orden
    all_tags = list(existing_tags)
    for tag in tags_list:
        if tag not in all_tags:
            all_tags.append(tag)

    if all_tags:
        metadata["tags"] = all_tags

    if agente_creador:
        metadata["agente_creador"] = agente_creador

    # Generar YAML
    yaml_content = yaml.dump(
        metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    )

    return f"---\n{yaml_content}---\n\n"


def register_creation_tools(mcp: FastMCP) -> None:
    """
    Registra todas las herramientas de creación en el servidor MCP.

    Args:
        mcp: Instancia del servidor FastMCP.
    """

    @mcp.tool()
    def listar_plantillas() -> str:
        """
        Lista las plantillas disponibles en la carpeta ZZ_Plantillas.

        Returns:
            Lista de nombres de plantillas disponibles.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            settings = get_vault_settings()
            plantillas_path = vault_path / settings.templates_folder
            if not plantillas_path.exists():
                return f"❌ No se encontró la carpeta '{settings.templates_folder}'"

            plantillas = []
            for item in sorted(plantillas_path.glob("*.md")):
                plantillas.append(item.name)

            if not plantillas:
                return f"ℹ️ No hay plantillas disponibles en {settings.templates_folder}"

            return "📝 **Plantillas disponibles:**\n" + "\n".join(
                [f"- {p}" for p in plantillas]
            )

        except Exception as e:
            return f"❌ Error al listar plantillas: {e}"

    def _get_sugerencia_ubicacion(
        titulo: str, contenido: str, etiquetas: str = ""
    ) -> str:
        """Helper para sugerir ubicación."""
        texto = (titulo + " " + contenido + " " + etiquetas).lower()

        # Lógica simple de categorización basada en la estructura del vault
        if any(k in texto for k in ["poema", "poesía", "verso", "rima"]):
            return "📂 Sugerencia: `03_Creaciones/Poemas`"
        elif any(k in texto for k in ["reflexión", "pienso", "creo", "opinión"]):
            return "📂 Sugerencia: `03_Creaciones/Reflexiones`"
        elif any(k in texto for k in ["código", "python", "sql", "mcp", "config"]):
            return "📂 Sugerencia: `02_Aprendizaje/Programación`"
        elif any(k in texto for k in ["filosofía", "ética", "aristóteles", "dualismo"]):
            return "📂 Sugerencia: `02_Aprendizaje/Filosofía`"
        elif any(k in texto for k in ["psicología", "cognitivo", "mente", "ego"]):
            return "📂 Sugerencia: `02_Aprendizaje/Psicología`"

        settings = get_vault_settings()
        return f"📂 Sugerencia: `{settings.inbox_folder}` (Categoría general)"

    @mcp.tool()
    def sugerir_ubicacion(titulo: str, contenido: str, etiquetas: str = "") -> str:
        """
        Sugiere la mejor carpeta para una nota nueva según su contenido y tags.

        Args:
            titulo: Título de la nota.
            contenido: Fragmento o contenido total de la nota.
            etiquetas: Etiquetas enviadas o planeadas.
        """
        try:
            return _get_sugerencia_ubicacion(titulo, contenido, etiquetas)
        except Exception as e:
            return f"❌ Error al sugerir ubicación: {e}"

    @mcp.tool()
    def crear_nota(
        titulo: str,
        contenido: str,
        carpeta: str = "",
        etiquetas: str = "",
        plantilla: str = "",
        agente_creador: str = "",
    ) -> str:
        """
        Crea una nueva nota en el vault.
        IMPORTANTE: Se prefiere el uso de plantillas para mantener la consistencia.

        Args:
            titulo: Título de la nota.
            contenido: Contenido de la nota.
            carpeta: Carpeta donde crear la nota (vacío = raíz).
            etiquetas: Etiquetas separadas por comas.
            plantilla: Nombre del archivo de plantilla (ej: "Diario.md").
            agente_creador: Si se creó usando un agente específico (ej: "escritor").
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Preparar nombre de archivo
            nombre_archivo = sanitize_filename(titulo)

            # Determinar ruta (si no hay carpeta, sugerir una o usar Inbox)
            settings = get_vault_settings()
            if not carpeta:
                # Intento de sugerencia automática si no se especifica
                res_sug = _get_sugerencia_ubicacion(titulo, contenido, etiquetas)
                # Extrae el path de vuelta entre backticks: 📂 Sugerencia: `path`
                match = re.search(r"`([^`]+)`", res_sug)
                carpeta_sugerida = match.group(1) if match else settings.inbox_folder
                carpeta = carpeta_sugerida

            carpeta_path = vault_path / carpeta
            carpeta_path.mkdir(parents=True, exist_ok=True)
            nota_path = carpeta_path / nombre_archivo

            if not nota_path.suffix == ".md":
                nota_path = nota_path.with_suffix(".md")

            # Security: Validate path is within vault (prevent path traversal)
            is_valid, error = validate_path_within_vault(nota_path, vault_path)
            if not is_valid:
                return f"⛔ Error de seguridad: {error}"

            # Security: Prevent creating notes in restricted folders
            restricted_folders = [settings.private_folder]
            if is_path_in_restricted_folder(nota_path, restricted_folders, vault_path):
                return (
                    "⛔ ACCESO DENEGADO: No se permite crear notas en "
                    "carpetas restringidas"
                )

            # Verificar si ya existe
            if nota_path.exists():
                return f"❌ Ya existe una nota con el nombre '{nombre_archivo}'"

            # Preparar contenido final
            contenido_final = ""
            ahora = datetime.now().strftime("%Y-%m-%d")

            # Si se usa plantilla
            if plantilla:
                plantilla_path = vault_path / settings.templates_folder / plantilla
                if not plantilla.endswith(".md"):
                    plantilla_path = plantilla_path.with_suffix(".md")

                if plantilla_path.exists():
                    with open(plantilla_path, "r", encoding="utf-8") as f:
                        plantilla_content = f.read()

                    # Reemplazos de título
                    plantilla_content = plantilla_content.replace("{{title}}", titulo)
                    plantilla_content = plantilla_content.replace("{{titulo}}", titulo)

                    # Procesar todas las fechas con formatos
                    plantilla_content = _process_date_placeholders(plantilla_content)

                    contenido_final = plantilla_content
                    # Si hay contenido adicional, añadirlo al final
                    if contenido:
                        # Extraer frontmatter del contenido si existe
                        # para evitar duplicación con la plantilla
                        _, contenido_limpio = _extract_frontmatter_from_content(
                            contenido
                        )
                        if contenido_final.endswith("\n\n"):
                            contenido_final += contenido_limpio
                        else:
                            contenido_final += f"\n\n{contenido_limpio}"
                else:
                    return f"❌ No se encontró la plantilla '{plantilla}'"
            else:
                # Sin plantilla: detectar si el contenido ya tiene frontmatter
                tags_list = [t.strip() for t in etiquetas.split(",") if t.strip()]

                # Extraer frontmatter del contenido si existe
                extra_metadata, contenido_limpio = _extract_frontmatter_from_content(
                    contenido
                )

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
            resultado = f"✅ Nota creada: **{titulo}**\n"
            resultado += f"📍 Ubicación: {ruta_relativa}\n"
            if plantilla:
                resultado += f"📝 Plantilla usada: {plantilla}\n"
            if agente_creador:
                resultado += f"🤖 Agente: {agente_creador}\n"

            return resultado

        except Exception as e:
            return f"❌ Error al crear nota: {e}"

    @mcp.tool()
    def agregar_a_nota(
        nombre_archivo: str, contenido: str, al_final: bool = True
    ) -> str:
        """
        Agrega contenido a una nota existente.

        Args:
            nombre_archivo: Nombre del archivo a modificar.
            contenido: Contenido a agregar.
            al_final: Si agregar al final (True) o al principio (False) de la nota.

        Returns:
            Un mensaje indicando el resultado de la operación.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            nota_path = find_note_by_name(nombre_archivo)
            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"

            # Security: Check access to this path
            is_allowed, error = check_path_access(nota_path, vault_path, "modificar")
            if not is_allowed:
                return error

            # Leer contenido actual
            with open(nota_path, "r", encoding="utf-8") as f:
                contenido_actual = f.read()

            # Preparar nuevo contenido
            if al_final:
                sep = "\n\n" if not contenido_actual.endswith("\n\n") else ""
                nuevo_contenido = contenido_actual + sep + contenido
            else:
                nuevo_contenido = contenido + "\n\n" + contenido_actual

            # Escribir archivo
            with open(nota_path, "w", encoding="utf-8") as f:
                f.write(nuevo_contenido)

            ruta_relativa = nota_path.relative_to(vault_path)
            posicion = "final" if al_final else "inicio"
            return f"✅ Contenido agregado al {posicion} de {ruta_relativa}"

        except Exception as e:
            return f"❌ Error al agregar contenido: {e}"

    @mcp.tool()
    def eliminar_nota(nombre_archivo: str, confirmar: bool = False) -> str:
        """
        Elimina una nota del vault (requiere confirmación).

        Args:
            nombre_archivo: Nombre del archivo a eliminar.
            confirmar: Confirmación para eliminar (debe ser True).

        Returns:
            Un mensaje indicando el resultado de la operación.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            if not confirmar:
                return "❌ Para eliminar una nota, debes confirmar con confirmar=True"

            nota_path = find_note_by_name(nombre_archivo)
            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"

            # Security: Check access to this path
            is_allowed, error = check_path_access(nota_path, vault_path, "eliminar")
            if not is_allowed:
                return error

            ruta_relativa = nota_path.relative_to(vault_path)

            # Eliminar archivo
            nota_path.unlink()

            return f"✅ Nota eliminada: {ruta_relativa}"

        except Exception as e:
            return f"❌ Error al eliminar nota: {e}"

    @mcp.tool()
    def editar_nota(nombre_archivo: str, nuevo_contenido: str) -> str:
        """
        Edita una nota existente, reemplazando todo su contenido.
        Útil para mejorar, añadir secciones, corregir frontmatter o reformatear notas.

        IMPORTANTE: El agente DEBE leer la nota primero con leer_nota()
        antes de editarla para asegurarse de preservar el contenido
        que no desea modificar.

        Args:
            nombre_archivo: Nombre o ruta de la nota a editar (ej: "Mi Nota.md")
            nuevo_contenido: El contenido completo actualizado
                             (incluye frontmatter YAML)

        Returns:
            Mensaje de confirmación o error
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            nota_path = find_note_by_name(nombre_archivo)
            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"

            # Security: Validate path is within vault
            is_valid, error = validate_path_within_vault(nota_path, vault_path)
            if not is_valid:
                return f"⛔ Error de seguridad: {error}"

            # Security: Check restricted folders with proper path validation
            settings = get_vault_settings()
            restricted_folders = [settings.private_folder]
            if is_path_in_restricted_folder(nota_path, restricted_folders, vault_path):
                return (
                    "⛔ ACCESO DENEGADO: No se permite editar archivos en "
                    "carpetas restringidas"
                )

            # Process date placeholders
            contenido_procesado = _process_date_placeholders(nuevo_contenido)

            # Auto-inject or update 'updated' field in frontmatter
            ahora = datetime.now().strftime("%Y-%m-%d")
            if contenido_procesado.startswith("---"):
                # Tiene frontmatter, intentar actualizar 'updated'
                if re.search(r"^updated:", contenido_procesado, re.MULTILINE):
                    # Reemplazar valor existente
                    contenido_procesado = re.sub(
                        r'^(updated:\s*["\']?)[^"\'\n]+(["\']?)$',
                        rf"\g<1>{ahora}\g<2>",
                        contenido_procesado,
                        count=1,
                        flags=re.MULTILINE,
                    )
                else:
                    # Añadir 'updated' después de 'created' o al final del frontmatter
                    if re.search(r"^created:", contenido_procesado, re.MULTILINE):
                        contenido_procesado = re.sub(
                            r"^(created:\s*.+)$",
                            rf"\1\nupdated: {ahora}",
                            contenido_procesado,
                            count=1,
                            flags=re.MULTILINE,
                        )
                    else:
                        # Añadir antes del cierre del frontmatter
                        contenido_procesado = contenido_procesado.replace(
                            "\n---\n", f"\nupdated: {ahora}\n---\n", 1
                        )

            # Guardar el nuevo contenido
            with open(nota_path, "w", encoding="utf-8") as f:
                f.write(contenido_procesado)

            ruta_relativa = nota_path.relative_to(vault_path)
            return f"✅ Nota editada correctamente: {ruta_relativa}"

        except Exception as e:
            return f"❌ Error al editar nota: {e}"
