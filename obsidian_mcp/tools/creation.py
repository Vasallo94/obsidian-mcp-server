"""
Herramientas de creación y edición para el vault de Obsidian.

Estas herramientas permiten crear nuevas notas y modificar las existentes,
facilitando la gestión de contenido del vault desde un cliente MCP.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import (
    check_path_access,
    find_note_by_name,
    is_path_in_restricted_folder,
    sanitize_filename,
    validate_path_within_vault,
)
from ..vault_config import get_vault_config


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


def _get_sugerencia_ubicacion(titulo: str, contenido: str, etiquetas: str = "") -> str:
    """Helper para sugerir ubicación basado en palabras clave."""
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
        from ..config import get_vault_path

        vault_path = get_vault_path()
        if vault_path:
            for item in Path(vault_path).iterdir():
                if item.is_dir() and any(
                    t in item.name.lower() for t in ["inbox", "bandeja", "entrada"]
                ):
                    return f"📂 Sugerencia: `{item.name}` (Categoría general)"
    except Exception:
        pass

    return "📂 Sugerencia: Ubicación a confirmar con el usuario"


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
                return (
                    "⚠️ No se detectó carpeta de plantillas en el vault.\n\n"
                    "💡 **Solución**: Crea `.agent/vault.yaml` con:\n"
                    "```yaml\n"
                    'templates_folder: "NombreDeTuCarpetaDePlantillas"\n'
                    "```"
                )

            templates_path = vault_path / templates_folder
            if not templates_path.exists():
                return f"❌ No se encontró la carpeta '{templates_folder}'"

            plantillas = []
            for item in sorted(templates_path.glob("*.md")):
                plantillas.append(item.name)

            if not plantillas:
                return f"ℹ️ No hay plantillas disponibles en {templates_folder}"

            return "📝 **Plantillas disponibles:**\n" + "\n".join(
                [f"- {p}" for p in plantillas]
            )

        except Exception as e:
            return f"❌ Error al listar plantillas: {e}"

    @mcp.tool()
    def sugerir_ubicacion(titulo: str, contenido: str, etiquetas: str = "") -> str:
        """
        Sugiere carpetas candidatas para una nota nueva según su contenido y tags.

        ⚠️ IMPORTANTE PARA AGENTES DE IA: ⚠️
        Esta herramienta devuelve SUGERENCIAS PROBABILÍSTICAS, no respuestas
        definitivas. Debes:
        1. Evaluar las opciones junto con el contexto del usuario.
        2. Considerar la confianza (confidence) de cada sugerencia.
        3. Proponer la mejor opción al usuario, explicando tu razonamiento.
        4. Si ninguna sugerencia tiene alta confianza (>0.5), preguntar al usuario.

        La sugerencia se basa en notas similares ya existentes en el vault.
        No es infalible: el usuario puede tener una mejor idea de dónde ubicarla.

        Args:
            titulo: Título de la nota.
            contenido: Fragmento o contenido total de la nota.
            etiquetas: Etiquetas enviadas o planeadas.

        Returns:
            Lista de carpetas sugeridas con confianza, o fallback a reglas.
        """
        try:
            # 1. Try Semantic Suggestion (multi-candidate)
            try:
                from ..semantic.service import SemanticService

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
                            conf_bar = "█" * (conf_pct // 10) + "░" * (
                                10 - conf_pct // 10
                            )
                            notes_str = (
                                ", ".join(s["similar_notes"])
                                if s["similar_notes"]
                                else "—"
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

            except Exception:
                pass  # Silent fallback to regex/keywords

            # 2. Fallback to Keyword/Regex logic
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
        descripcion: str = "",
    ) -> str:
        """
        Crea una nueva nota en el vault.

        ⚠️ ADVERTENCIA CRÍTICA PARA AGENTES DE IA: ⚠️
        1. NO uses herramientas genéricas de sistema de archivos (como write_file).
           SIEMPRE usa esta herramienta para crear notas en el vault.
        2. ANTES de ejecutar esta acción, DEBES haber leído las reglas globales
           con `leer_contexto_vault` y `obtener_reglas_globales`.
        3. Verifica si existe una SKILL aplicable (ej: investigador, escritor)
           y sigue sus instrucciones específicas.

        Args:
            titulo: Título de la nota.
            contenido: Contenido de la nota.
            carpeta: Carpeta donde crear la nota (vacío = raíz).
            etiquetas: Etiquetas separadas por comas.
            plantilla: Nombre del archivo de plantilla (ej: "Diario.md").
            agente_creador: Si se creó usando un agente específico (ej: "escritor").
            descripcion: Descripción breve de la nota (para placeholder
                {{description}}).
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Preparar nombre de archivo
            nombre_archivo = sanitize_filename(titulo)

            # Determinar ruta (si no hay carpeta, usar ubicación sugerida)
            config = get_vault_config(vault_path)

            if not carpeta:
                # Intento de sugerencia automática si no se especifica
                res_sug = _get_sugerencia_ubicacion(titulo, contenido, etiquetas)
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

            # Security: Validate path is within vault (prevent path traversal)
            is_valid, error = validate_path_within_vault(nota_path, vault_path)
            if not is_valid:
                return f"⛔ Error de seguridad: {error}"

            # Security: Prevent creating notes in restricted folders
            private_paths = []
            if config and config.private_paths:
                private_paths = config.private_paths
            else:
                private_paths = ["**/Privado/*", "**/Private/*"]
            if is_path_in_restricted_folder(nota_path, private_paths, vault_path):
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
                    return (
                        "⚠️ No se detectó carpeta de plantillas.\n\n"
                        "💡 Crea `.agent/vault.yaml` con:\n"
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
                    plantilla_content = plantilla_content.replace(
                        "{{time}}", hora_actual
                    )
                    plantilla_content = plantilla_content.replace(
                        "{{hora}}", hora_actual
                    )

                    # Reemplazos de carpeta
                    carpeta_final = carpeta if carpeta else ""
                    plantilla_content = plantilla_content.replace(
                        "{{folder}}", carpeta_final
                    )
                    plantilla_content = plantilla_content.replace(
                        "{{carpeta}}", carpeta_final
                    )

                    # Reemplazos de etiquetas
                    plantilla_content = plantilla_content.replace("{{tags}}", etiquetas)
                    plantilla_content = plantilla_content.replace(
                        "{{etiquetas}}", etiquetas
                    )

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

        ⚠️ ADVERTENCIA CRÍTICA PARA AGENTES DE IA: ⚠️
        1. NO uses herramientas genéricas de sistema de archivos.
        2. ANTES de ejecutar, DEBES leer la nota original con `leer_nota`.
        3. DEBES respetar las Reglas Globales (sin emojis en títulos,
           frontmatter válido).
        4. El nuevo contenido debe ser TOTAL (no diffs).

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

            # Security: Check restricted folders via vault config
            config = get_vault_config(vault_path)
            private_folders = ["**/Private/", "**/Privado/*"]
            if config and config.private_paths:
                private_folders = config.private_paths

            if is_path_in_restricted_folder(nota_path, private_folders, vault_path):
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

    @mcp.tool()
    def buscar_y_reemplazar_global(
        buscar: str,
        reemplazar: str,
        carpeta: str = "",
        solo_preview: bool = True,
        limite: int = 100,
    ) -> str:
        """
        Busca y reemplaza texto en todas las notas del vault.
        Útil para corregir enlaces rotos, renombrar tags, o actualizar rutas.

        Args:
            buscar: Texto o patrón a buscar (texto literal, no regex).
            reemplazar: Texto de reemplazo.
            carpeta: Carpeta específica donde buscar (vacío = todo el vault).
            solo_preview: Si True, solo muestra qué cambiaría sin modificar.
            limite: Máximo de archivos a procesar (seguridad).

        Returns:
            Resumen de archivos afectados y cambios realizados.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            if not buscar:
                return "❌ Debes especificar un texto a buscar."

            # Determinar carpeta de búsqueda
            if carpeta:
                search_path = vault_path / carpeta
                if not search_path.exists():
                    return f"❌ La carpeta '{carpeta}' no existe."
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

                # Verificar acceso
                is_valid, _ = validate_path_within_vault(md_file, vault_path)
                if not is_valid:
                    continue

                # Verificar si está en carpeta privada
                private_paths = ["**/Privado/*", "**/Private/*"]
                if config and config.private_paths:
                    private_paths = config.private_paths
                if is_path_in_restricted_folder(md_file, private_paths, vault_path):
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

                except Exception:
                    continue

            if not archivos_afectados:
                return f"ℹ️ No se encontró '{buscar}' en ninguna nota."

            # Modo preview
            if solo_preview:
                resultado = f"🔍 **Preview de búsqueda**: `{buscar}`\n"
                resultado += f"📊 Se encontraron **{len(archivos_afectados)}** "
                total_ocurrencias = sum(a["ocurrencias"] for a in archivos_afectados)
                resultado += (
                    f"archivos con {total_ocurrencias} ocurrencias totales.\n\n"
                )
                resultado += "**Archivos afectados:**\n"
                for arch in archivos_afectados[:20]:  # Limitar output
                    resultado += (
                        f"- `{arch['ruta_rel']}` ({arch['ocurrencias']} ocurrencias)\n"
                    )
                if len(archivos_afectados) > 20:
                    resultado += (
                        f"- ... y {len(archivos_afectados) - 20} archivos más\n"
                    )
                resultado += (
                    "\n⚠️ Ejecuta con `solo_preview=False` para aplicar los cambios."
                )
                return resultado

            # Modo ejecución
            archivos_modificados = 0
            total_reemplazos = 0

            for arch in archivos_afectados:
                try:
                    nuevo_contenido = arch["contenido_original"].replace(
                        buscar, reemplazar
                    )
                    with open(arch["path"], "w", encoding="utf-8") as f:
                        f.write(nuevo_contenido)
                    archivos_modificados += 1
                    total_reemplazos += arch["ocurrencias"]
                except Exception:
                    continue

            resultado = "✅ **Reemplazo completado**\n"
            resultado += f"- Archivos modificados: {archivos_modificados}\n"
            resultado += f"- Reemplazos realizados: {total_reemplazos}\n"
            resultado += f"- `{buscar}` → `{reemplazar}`"
            return resultado

        except Exception as e:
            return f"❌ Error en búsqueda global: {e}"
