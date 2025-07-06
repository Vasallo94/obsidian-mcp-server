"""
Herramientas de navegación para el vault de Obsidian
Incluye funciones para listar, leer y buscar notas
"""

from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import find_note_by_name, get_note_metadata


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
            notas_por_carpeta = {}
            for nota in notas:
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

            # Formatear resultado
            resultado = f"📚 Notas encontradas en el vault ({len(notas)} total):\n\n"

            for carpeta_nombre, lista_notas in sorted(notas_por_carpeta.items()):
                resultado += f"📁 {carpeta_nombre} ({len(lista_notas)} notas):\n"
                for nota in sorted(lista_notas, key=lambda x: x["name"]):
                    resultado += f"   📄 {nota['name']} ({nota['size_kb']:.1f}KB, {nota['modified']})\n"
                resultado += "\n"

            return resultado

        except Exception as e:
            return f"❌ Error al listar notas: {e}"

    @mcp.tool()
    def leer_nota(nombre_archivo: str) -> str:
        """
        Lee el contenido completo de una nota específica

        Args:
            nombre_archivo: Nombre del archivo (puede incluir ruta, ej: "Diario/2024-01-01.md")
        """
        try:
            nota_path = find_note_by_name(nombre_archivo)

            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_archivo}'"

            # Leer contenido
            with open(nota_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            # Obtener metadata
            metadata = get_note_metadata(nota_path)

            resultado = f"📄 **{metadata['name']}**\n"
            resultado += f"📍 Ubicación: {metadata['relative_path']}\n"
            resultado += f"📊 Tamaño: {metadata['size_kb']:.1f}KB | Modificado: {metadata['modified']}\n"
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

            for archivo_path in search_path.rglob("*.md"):
                archivos_revisados += 1
                try:
                    ruta_relativa = archivo_path.relative_to(vault_path)

                    if solo_titulos:
                        # Buscar solo en el nombre del archivo
                        if texto.lower() in archivo_path.stem.lower():
                            resultados.append(
                                {
                                    "archivo": str(ruta_relativa),
                                    "tipo": "título",
                                    "coincidencia": archivo_path.stem,
                                }
                            )
                    else:
                        # Buscar en todo el contenido
                        with open(archivo_path, "r", encoding="utf-8") as f:
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
                                        "linea": num_linea,
                                        "coincidencia": coincidencia_texto,
                                    }
                                )
                except Exception:
                    continue

            if not resultados:
                busqueda_tipo = "títulos" if solo_titulos else "contenido"
                return f"🔍 No se encontró '{texto}' en {busqueda_tipo} de {archivos_revisados} notas"

            # Formatear resultados
            busqueda_tipo = "títulos" if solo_titulos else "contenido"
            resultado = f"🔍 Búsqueda de '{texto}' en {busqueda_tipo} ({len(resultados)} coincidencias):\n\n"

            # Agrupar por archivo
            por_archivo: dict[str, list[dict[str, str | int]]] = {}
            for r in resultados:
                archivo: str = r["archivo"]
                if archivo not in por_archivo:
                    por_archivo[archivo] = []
                por_archivo[archivo].append(r)

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
                        resultado += f"   📍 Línea {coincidencia['linea']}: {coincidencia['coincidencia']}\n"
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
                fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()

                if fecha_inicio <= fecha_mod <= fecha_fin:
                    metadata = get_note_metadata(archivo)
                    metadata["fecha"] = fecha_mod.strftime("%Y-%m-%d")
                    notas_encontradas.append(metadata)

            if not notas_encontradas:
                return f"📅 No se encontraron notas modificadas entre {fecha_desde} y {fecha_fin}"

            # Ordenar por fecha (más recientes primero)
            notas_encontradas.sort(key=lambda x: x["fecha"], reverse=True)

            resultado = f"📅 Notas modificadas entre {fecha_desde} y {fecha_fin} ({len(notas_encontradas)} encontradas):\n\n"

            for nota in notas_encontradas:
                resultado += f"📄 {nota['name']} ({nota['size_kb']:.1f}KB)\n"
                resultado += f"   📍 {nota['relative_path']} | 📅 {nota['fecha']}\n\n"

            return resultado

        except ValueError:
            return "❌ Formato de fecha inválido. Usa YYYY-MM-DD (ej: 2024-01-15)"
        except Exception as e:
            return f"❌ Error al buscar por fecha: {e}"
