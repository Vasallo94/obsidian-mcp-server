"""
Herramientas de navegación para el vault de Obsidian
Incluye funciones para listar, leer y buscar notas
"""

from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP

from ..config import get_vault_path, get_vault_settings
from ..utils import (
    check_path_access,
    find_note_by_name,
    get_logger,
    get_note_metadata,
    is_path_forbidden,
    is_path_in_restricted_folder,
    validate_path_within_vault,
)

logger = get_logger(__name__)


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
        Busca texto en las notas del vault

        Args:
            texto: Texto a buscar
            carpeta: Carpeta específica donde buscar (vacío = todo el vault)
            solo_titulos: Si buscar solo en los títulos de las notas
        """
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

            resultados = []
            archivos_revisados = 0

            for archivo_item in search_path.rglob("*.md"):
                archivos_revisados += 1

                # Security: Skip forbidden paths
                is_forbidden_path, _ = is_path_forbidden(archivo_item, vault_path)
                if is_forbidden_path:
                    continue

                try:
                    ruta_relativa = archivo_item.relative_to(vault_path)

                    if solo_titulos:
                        # Buscar solo en el nombre del archivo
                        if texto.lower() in archivo_item.stem.lower():
                            resultados.append(
                                {
                                    "archivo": str(ruta_relativa),
                                    "tipo": "título",
                                    "coincidencia": archivo_item.stem,
                                }
                            )
                    else:
                        # Buscar en todo el contenido
                        with open(archivo_item, "r", encoding="utf-8") as f:
                            contenido = f.read()

                        lineas = contenido.split("\n")
                        for num_linea, linea in enumerate(lineas, 1):
                            if texto.lower() in linea.lower():
                                coincidencia_texto = linea.strip()
                                if len(coincidencia_texto) > 100:
                                    coincidencia_texto = (
                                        coincidencia_texto[:100] + "..."
                                    )

                                resultados.append(
                                    {
                                        "archivo": str(ruta_relativa),
                                        "linea": str(num_linea),
                                        "coincidencia": coincidencia_texto,
                                    }
                                )
                except UnicodeDecodeError:
                    logger.debug(f"Could not decode {archivo_item}: encoding error")
                    continue
                except PermissionError:
                    logger.debug(f"Permission denied reading {archivo_item}")
                    continue
                except Exception as e:
                    logger.warning(f"Error reading {archivo_item}: {e}")
                    continue

            if not resultados:
                busqueda_tipo = "títulos" if solo_titulos else "contenido"
                return (
                    f"🔍 No se encontró '{texto}' en {busqueda_tipo} "
                    f"de {archivos_revisados} notas"
                )

            # Formatear resultados
            busqueda_tipo = "títulos" if solo_titulos else "contenido"
            resultado = (
                f"🔍 Búsqueda de '{texto}' en {busqueda_tipo} "
                f"({len(resultados)} coincidencias):\n\n"
            )

            # Agrupar por archivo
            por_archivo: dict[str, list[dict]] = {}
            for r in resultados:
                archivo_res = r["archivo"]
                if archivo_res not in por_archivo:
                    por_archivo[archivo_res] = []
                por_archivo[archivo_res].append(r)

            for archivo, coincidencias in list(por_archivo.items())[
                :20
            ]:  # Limitar a 20 archivos
                resultado += f"📄 **{archivo}** ({len(coincidencias)} coincidencias):\n"
                for coincidencia in coincidencias[
                    :5
                ]:  # Máximo 5 coincidencias por archivo
                    if solo_titulos:
                        resultado += f"   📌 {coincidencia['coincidencia']}\n"
                    else:
                        resultado += (
                            f"   📍 Línea {coincidencia['linea']}: "
                            f"{coincidencia['coincidencia']}\n"
                        )
                if len(coincidencias) > 5:
                    resultado += (
                        f"   ... y {len(coincidencias) - 5} coincidencias más\n"
                    )
                resultado += "\n"

            if len(por_archivo) > 20:
                resultado += (
                    f"... y {len(por_archivo) - 20} archivos más con coincidencias"
                )

            return resultado

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

            # Security: Check restricted folders with proper path validation
            settings = get_vault_settings()
            restricted_folders = [settings.private_folder]

            if is_path_in_restricted_folder(origen, restricted_folders, vault_path):
                return (
                    "⛔ ACCESO DENEGADO: No se permite mover archivos desde "
                    "carpetas restringidas"
                )

            if is_path_in_restricted_folder(destino, restricted_folders, vault_path):
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
            notas_filtradas = []
            for nota in notas:
                ruta_str = str(nota.relative_to(vault_path))
                # Excluir sistema, plantillas, y archivos de configuración
                if any(
                    excl in ruta_str
                    for excl in [
                        "ZZ_Plantillas",
                        "ZZ_Media",
                        ".agent",
                        ".github",
                        "00_Sistema",
                        "Tags/",
                    ]
                ):
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
