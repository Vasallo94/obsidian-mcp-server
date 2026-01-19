"""
Herramientas de navegación para el vault de Obsidian
Incluye funciones para listar, leer y buscar notas
"""

from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP

from ..config import get_vault_path
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


def _formatear_resultados(resultados: list, solo_titulos: bool) -> str:
    """Helper para formatear la salida de búsqueda"""
    resultado_str = f"🔍 Encontradas {len(resultados)} coincidencias:\n\n"

    por_archivo: dict[str, list[dict[str, str]]] = {}
    for r in resultados:
        archivo = r["archivo"]
        if archivo not in por_archivo:
            por_archivo[archivo] = []
        por_archivo[archivo].append(r)

    for archivo, coincidencias in list(por_archivo.items())[:20]:
        resultado_str += f"📄 **{archivo}**\n"
        for c in coincidencias:
            if solo_titulos:
                resultado_str += f"   📌 {c['coincidencia']}\n"
            else:
                resultado_str += f"   📍 L{c['linea']}: {c['coincidencia']}\n"
        resultado_str += "\n"

    if len(por_archivo) > 20:
        resultado_str += f"... y {len(por_archivo) - 20} archivos más."

    return resultado_str


def register_navigation_tools(mcp: FastMCP) -> None:
    """
    Registra todas las herramientas de navegación en el servidor MCP

    Args:
        mcp: Instancia del servidor FastMCP
    """

    @mcp.tool()
    def listar_notas(carpeta: str = "", incluir_subcarpetas: bool = True) -> str:
        """
        Lista todas las notas (.md) en el vault o en una carpeta específica

        Args:
            carpeta: Carpeta específica a explorar (vacío = raíz del vault)
            incluir_subcarpetas: Si incluir subcarpetas en la búsqueda
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            if carpeta:
                target_path = vault_path / carpeta
                if not target_path.exists():
                    return f"❌ La carpeta '{carpeta}' no existe en el vault"
            else:
                target_path = vault_path

            # Buscar archivos markdown
            pattern = "**/*.md" if incluir_subcarpetas else "*.md"
            notas = list(target_path.glob(pattern))

            if not notas:
                return f"📂 No se encontraron notas en '{carpeta or 'raíz'}'"

            # Organizar por carpetas
            notas_por_carpeta: dict[str, list[dict]] = {}
            notas_filtradas = 0
            for nota in notas:
                # Security: Skip forbidden paths
                is_forbidden, _ = is_path_forbidden(nota, vault_path)
                if is_forbidden:
                    notas_filtradas += 1
                    continue

                ruta_relativa = nota.relative_to(vault_path)
                carpeta_padre = (
                    str(ruta_relativa.parent)
                    if ruta_relativa.parent != Path(".")
                    else "📄 Raíz"
                )

                if carpeta_padre not in notas_por_carpeta:
                    notas_por_carpeta[carpeta_padre] = []

                metadata = get_note_metadata(nota)
                notas_por_carpeta[carpeta_padre].append(metadata)

            total_visibles = len(notas) - notas_filtradas

            # Formatear resultado
            resultado = (
                f"📚 Notas encontradas en el vault ({total_visibles} total):\n\n"
            )

            for carpeta_nombre, lista_notas in sorted(notas_por_carpeta.items()):
                resultado += f"📁 {carpeta_nombre} ({len(lista_notas)} notas):\n"
                for nota_meta in sorted(lista_notas, key=lambda x: x["name"]):
                    resultado += (
                        f"   📄 {nota_meta['name']} "
                        f"({nota_meta['size_kb']:.1f}KB, {nota_meta['modified']})\n"
                    )
                resultado += "\n"

            return resultado

        except Exception as e:
            return f"❌ Error al listar notas: {e}"

    @mcp.tool()
    def leer_nota(nombre_archivo: str) -> str:
        """
        Lee el contenido completo de una nota específica

        Args:
            nombre_archivo: Nombre del archivo (ej: "Diario/2024-01-01.md")
        """
        try:
            nota_path = find_note_by_name(nombre_archivo)

            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"

            # Security: Check access to this path
            is_allowed, error = check_path_access(nota_path, operation="leer")
            if not is_allowed:
                return error

            # Leer contenido
            with open(nota_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            # Obtener metadata
            metadata = get_note_metadata(nota_path)

            resultado = f"📄 **{metadata['name']}**\n"
            resultado += f"📍 Ubicación: {metadata['relative_path']}\n"
            resultado += (
                f"📊 Tamaño: {metadata['size_kb']:.1f}KB | "
                f"Modificado: {metadata['modified']}\n"
            )
            resultado += f"{'=' * 50}\n\n"
            resultado += contenido

            return resultado

        except Exception as e:
            return f"❌ Error al leer nota: {e}"

    @mcp.tool()
    def buscar_en_notas(
        texto: str, carpeta: str = "", solo_titulos: bool = False
    ) -> str:
        """
        Busca texto en las notas del vault usando búsqueda inteligente (ripgrep o fallback Python).
        Soporta múltiples términos: "nas ssh" buscará notas que contengan "nas" Y "ssh".

        Args:
            texto: Texto a buscar (puede incluir múltiples palabras)
            carpeta: Carpeta específica donde buscar (vacío = todo el vault)
            solo_titulos: Si buscar solo en los títulos de las notas
        """
        import shutil
        import subprocess

        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            if carpeta:
                search_path = vault_path / carpeta
                if not search_path.exists():
                    return f"❌ La carpeta '{carpeta}' no existe"
            else:
                search_path = vault_path

            # Preparar términos de búsqueda (AND logic)
            terminos = [t.strip() for t in texto.split() if t.strip()]
            if not terminos:
                return "❌ Debes proporcionar texto para buscar."

            resultados = []
            archivos_coincidentes = set()
            rg_path = shutil.which("rg")

            # --- ESTRATEGIA: HÍBRIDA (RG + Python) ---
            # 1. Usar ripgrep para encontrar archivos con el PRIMER término
            #    (filtro rápido)
            # 2. Verificar el resto de términos en Python (lógica robusta)
            if rg_path and not solo_titulos:
                try:
                    # Buscar el primer término con rg (solo .md)
                    cmd = [
                        rg_path,
                        "--ignore-case",
                        "--files-with-matches",
                        "--null",
                        "-g",
                        "*.md",
                        terminos[0],
                        str(search_path),
                    ]

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        check=False,  # No lanzar error si no encuentra nada (retcode 1)
                    )

                    if result.returncode == 0:
                        paths_raw = result.stdout.decode(
                            "utf-8", errors="ignore"
                        ).split("\0")
                        candidatos = [p for p in paths_raw if p]

                        # Si hay más términos, filtrarlos en Python
                        # (más seguro que pipear rg)
                        if len(terminos) > 1:
                            for cand in candidatos:
                                try:
                                    with open(cand, "r", encoding="utf-8") as f:
                                        contenido = f.read().lower()
                                    # Verificar RESTO de términos
                                    if all(
                                        t.lower() in contenido for t in terminos[1:]
                                    ):
                                        archivos_coincidentes.add(cand)
                                except Exception:
                                    pass
                        else:
                            # Solo había un término, todos son válidos
                            for cand in candidatos:
                                archivos_coincidentes.add(cand)

                except Exception as e:
                    logger.warning(f"Error en fase RG, cayendo a Python puro: {e}")
                    rg_path = None  # Forzar fallback

            # --- ESTRATEGIA 2: PYTHON PURO (Fallback o Títulos) ---
            if (not rg_path and not archivos_coincidentes) or solo_titulos:
                # (Mantener lógica original para solo_titulos o fallback total)
                # Si es solo títulos, buscar solo en nombres
                if solo_titulos:
                    for archivo_item in search_path.rglob("*.md"):
                        # Security: Skip forbidden paths
                        is_forbidden_path, _ = is_path_forbidden(
                            archivo_item, vault_path
                        )
                        if is_forbidden_path:
                            continue

                        # Verificar si TODOS los términos están en el nombre
                        nombre_lower = archivo_item.stem.lower()
                        if all(t.lower() in nombre_lower for t in terminos):
                            ruta_relativa = archivo_item.relative_to(vault_path)
                            resultados.append(
                                {
                                    "archivo": str(ruta_relativa),
                                    "tipo": "título",
                                    "coincidencia": archivo_item.stem,
                                }
                            )
                    # Salir rápido si solo buscamos títulos
                    if resultados:
                        return _formatear_resultados(resultados, solo_titulos=True)
                    else:
                        return f"🔍 No se encontraron notas con el título '{texto}'"

                # Si es contenido (Fallback Python)
                else:
                    for archivo_item in search_path.rglob("*.md"):
                        # Security
                        is_forbidden_path, _ = is_path_forbidden(
                            archivo_item, vault_path
                        )
                        if is_forbidden_path:
                            continue

                        try:
                            # Leer archivo
                            with open(archivo_item, "r", encoding="utf-8") as f:
                                contenido = f.read().lower()

                            # Verificar AND logic
                            if all(t.lower() in contenido for t in terminos):
                                archivos_coincidentes.add(str(archivo_item))

                        except Exception:
                            continue

            # --- PROCESAR RESULTADOS DE CONTENIDO ---
            # Si tenemos archivos candidatos (de rg o python), extraemos el contexto
            # Esto es necesario porque rg -l no da el contexto, y queremos mostrarlo

            for archivo_str in archivos_coincidentes:
                archivo_path = Path(archivo_str)
                # Asegurar path absoluto si viene de rg relativo (depende de cwd)
                if not archivo_path.is_absolute():
                    # rg devuelve paths absolutos si input es absoluto,
                    # pero por seguridad:
                    archivo_path = Path(archivo_str).resolve()

                try:
                    # Recalcular relativo para display
                    try:
                        ruta_relativa = archivo_path.relative_to(vault_path)
                    except ValueError:
                        # Si rg devolvió path extraño
                        continue

                    # Security check (redundante pero seguro)
                    is_forbidden_path, _ = is_path_forbidden(archivo_path, vault_path)
                    if is_forbidden_path:
                        continue

                    with open(archivo_path, "r", encoding="utf-8") as f:
                        lineas = f.readlines()

                    # Buscar la MEJOR línea de coincidencia (la que tenga más términos)
                    for num, linea in enumerate(lineas, 1):
                        linea_lower = linea.lower()
                        # Solo mostramos líneas que tengan AL MENOS UNO de los términos
                        # (Ya sabemos que el archivo tiene todos)
                        if any(t.lower() in linea_lower for t in terminos):
                            if len(linea.strip()) > 3:  # Ignorar líneas muy cortas
                                co = (
                                    linea.strip()[:100] + "..."
                                    if len(linea.strip()) > 100
                                    else linea.strip()
                                )
                                resultados.append(
                                    {
                                        "archivo": str(ruta_relativa),
                                        "linea": str(num),
                                        "coincidencia": co,
                                    }
                                )
                                # Límite: solo 3 líneas por archivo para no saturar
                                if (
                                    len(
                                        [
                                            r
                                            for r in resultados
                                            if r["archivo"] == str(ruta_relativa)
                                        ]
                                    )
                                    >= 3
                                ):
                                    break

                except Exception as e:
                    logger.error(f"Error procesando archivo {archivo_str}: {e}")
                    continue

            if not resultados:
                return (
                    f"🔍 No se encontraron notas que contengan: {', '.join(terminos)}"
                )

            return _formatear_resultados(resultados, solo_titulos=False)

        except Exception as e:
            return f"❌ Error en búsqueda: {e}"

    @mcp.tool()
    def buscar_notas_por_fecha(fecha_desde: str, fecha_hasta: str = "") -> str:
        """
        Busca notas modificadas en un rango de fechas

        Args:
            fecha_desde: Fecha de inicio (YYYY-MM-DD)
            fecha_hasta: Fecha de fin (YYYY-MM-DD, opcional, por defecto hoy)
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Parsear fechas
            fecha_inicio = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            if fecha_hasta:
                fecha_fin = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
            else:
                fecha_fin = date.today()

            notas_encontradas = []

            for archivo in vault_path.rglob("*.md"):
                # Security: Skip forbidden paths
                is_forbidden_path, _ = is_path_forbidden(archivo, vault_path)
                if is_forbidden_path:
                    continue

                fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()

                if fecha_inicio <= fecha_mod <= fecha_fin:
                    metadata = get_note_metadata(archivo)
                    metadata["fecha"] = fecha_mod.strftime("%Y-%m-%d")
                    notas_encontradas.append(metadata)

            if not notas_encontradas:
                return (
                    f"📅 No se encontraron notas modificadas entre "
                    f"{fecha_desde} y {fecha_fin}"
                )

            # Ordenar por fecha (más recientes primero)
            notas_encontradas.sort(key=lambda x: x["fecha"], reverse=True)

            resultado = (
                f"📅 Notas modificadas entre {fecha_desde} y {fecha_fin} "
                f"({len(notas_encontradas)} encontradas):\n\n"
            )

            for nota in notas_encontradas:
                resultado += f"📄 {nota['name']} ({nota['size_kb']:.1f}KB)\n"
                resultado += f"   📍 {nota['relative_path']} | 📅 {nota['fecha']}\n\n"

            return resultado

        except ValueError:
            return "❌ Formato de fecha inválido. Usa YYYY-MM-DD (ej: 2024-01-15)"
        except Exception as e:
            return f"❌ Error al buscar por fecha: {e}"

    @mcp.tool()
    def mover_nota(origen: str, destino: str, crear_carpetas: bool = True) -> str:
        """
        Mueve o renombra una nota dentro del vault.

        Args:
            origen: Ruta relativa actual de la nota (ej: "Sin titulo.md")
            destino: Ruta relativa nueva de la nota (ej: "01_Inbox/Nueva Nota.md")
            crear_carpetas: Si crear las carpetas destino si no existen (True)

        Returns:
            Mensaje de éxito o error.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: Ruta del vault no configurada"

            # Security: Validate paths are within vault (prevent path traversal)
            is_valid, error = validate_path_within_vault(origen, vault_path)
            if not is_valid:
                return f"⛔ Error de seguridad (origen): {error}"

            is_valid, error = validate_path_within_vault(destino, vault_path)
            if not is_valid:
                return f"⛔ Error de seguridad (destino): {error}"

            # Security: Check restricted folders via vault config
            config = get_vault_config(vault_path)
            private_folders = ["**/Private/", "**/Privado/*"]
            if config and config.private_paths:
                private_folders = config.private_paths

            if is_path_in_restricted_folder(origen, private_folders, vault_path):
                return (
                    "⛔ ACCESO DENEGADO: No se permite mover archivos desde "
                    "carpetas restringidas"
                )

            if is_path_in_restricted_folder(destino, private_folders, vault_path):
                return (
                    "⛔ ACCESO DENEGADO: No se permite mover archivos hacia "
                    "carpetas restringidas"
                )

            path_origen = vault_path / origen
            path_destino = vault_path / destino

            # Verificar origen
            if not path_origen.exists():
                return f"❌ El archivo origen no existe: {origen}"

            if not path_origen.is_file():
                return f"❌ El origen no es un archivo: {origen}"

            # Verificar destino
            if path_destino.exists():
                return f"❌ El archivo destino ya existe: {destino}"

            # Crear carpetas si es necesario
            if crear_carpetas:
                path_destino.parent.mkdir(parents=True, exist_ok=True)
            elif not path_destino.parent.exists():
                return f"❌ La carpeta destino no existe: {path_destino.parent.name}"

            # Mover archivo
            path_origen.rename(path_destino)

            return f"✅ Archivo movido/renombrado:\nDe: {origen}\nA:  {destino}"

        except Exception as e:
            return f"❌ Error al mover nota: {e}"

    @mcp.tool()
    def concepto_aleatorio(carpeta: str = "") -> str:
        """
        Extrae un concepto aleatorio del vault como flashcard sorpresa.
        Útil para reforzar conocimiento o descubrir notas olvidadas.

        Args:
            carpeta: Carpeta específica donde buscar (vacío = todo el vault)
        """
        import random
        import re

        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            search_path = vault_path / carpeta if carpeta else vault_path

            # Buscar todas las notas markdown
            notas = list(search_path.rglob("*.md"))

            # Filtrar notas del sistema y plantillas
            config = get_vault_config(vault_path)
            templates_folder = ""
            if config and config.templates_folder:
                templates_folder = config.templates_folder
            else:
                # Auto-detect
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
                # Excluir sistema, plantillas, y archivos de configuración
                if any(excl in ruta_str for excl in excl_folders):
                    continue
                # Excluir archivos muy pequeños (< 200 bytes)
                if nota.stat().st_size < 200:
                    continue
                # Security check
                is_forbidden, _ = is_path_forbidden(nota, vault_path)
                if is_forbidden:
                    continue
                notas_filtradas.append(nota)

            if not notas_filtradas:
                return "📭 No se encontraron notas válidas para extraer conceptos."

            # Seleccionar nota aleatoria
            nota_elegida = random.choice(notas_filtradas)
            ruta_relativa = nota_elegida.relative_to(vault_path)

            # Leer contenido
            with open(nota_elegida, "r", encoding="utf-8") as f:
                contenido = f.read()

            # Extraer título (primer H1)
            titulo_match = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
            titulo = titulo_match.group(1) if titulo_match else nota_elegida.stem

            # Extraer un fragmento significativo
            # Buscar párrafos (líneas no vacías que no son headers ni listas)
            lineas = contenido.split("\n")
            parrafos = []
            for linea in lineas:
                linea_strip = linea.strip()
                # Saltar headers, listas, links, frontmatter, líneas vacías
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
                fragmento = "(No se encontró un fragmento de texto significativo)"

            # Tags si existen
            tags_match = re.search(r"tags:\s*\[([^\]]+)\]", contenido)
            tags = tags_match.group(1) if tags_match else ""

            # Formatear respuesta
            resultado = "🎲 **Concepto Aleatorio**\n\n"
            resultado += f"📄 **{titulo}**\n"
            resultado += f"📍 `{ruta_relativa}`\n"
            if tags:
                resultado += f"🏷️ {tags}\n"
            resultado += f"\n---\n\n{fragmento}\n"
            resultado += (
                f'\n---\n💡 *¿Quieres profundizar? Usa `leer_nota("{ruta_relativa}")`*'
            )

            return resultado

        except Exception as e:
            return f"❌ Error: {e}"
