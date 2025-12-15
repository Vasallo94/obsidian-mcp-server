"""
Herramientas de análisis y estadísticas para el vault de Obsidian
Incluye funciones para generar estadísticas y análisis del vault
"""

from datetime import datetime

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import extract_internal_links, extract_tags_from_content


def register_analysis_tools(mcp: FastMCP) -> None:
    """
    Registra todas las herramientas de análisis en el servidor MCP

    Args:
        mcp: Instancia del servidor FastMCP
    """

    @mcp.tool()
    def estadisticas_vault() -> str:
        """
        Genera estadísticas completas del vault de Obsidian
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            vault_name = vault_path.name

            # Contadores
            total_notas = 0
            total_palabras = 0
            total_caracteres = 0
            carpetas = set()
            etiquetas = set()
            enlaces_internos = set()

            # Análisis por fecha
            por_fecha = {}

            for archivo in vault_path.rglob("*.md"):
                total_notas += 1

                # Carpeta
                carpeta_padre = archivo.parent.relative_to(vault_path)
                if str(carpeta_padre) != ".":
                    carpetas.add(str(carpeta_padre))

                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    # Contar palabras y caracteres
                    palabras = len(contenido.split())
                    total_palabras += palabras
                    total_caracteres += len(contenido)

                    # Buscar etiquetas y enlaces
                    etiquetas.update(extract_tags_from_content(contenido))
                    enlaces_internos.update(extract_internal_links(contenido))

                    # Fecha de modificación
                    fecha_mod = datetime.fromtimestamp(archivo.stat().st_mtime).date()
                    fecha_str = fecha_mod.strftime("%Y-%m")
                    por_fecha[fecha_str] = por_fecha.get(fecha_str, 0) + 1

                except Exception:
                    continue

            # Formatear estadísticas
            resultado = f"📊 **Estadísticas del Vault '{vault_name}'**\n\n"

            resultado += "📚 **Contenido:**\n"
            resultado += f"   • Total de notas: {total_notas:,}\n"
            resultado += f"   • Total de palabras: {total_palabras:,}\n"
            resultado += f"   • Total de caracteres: {total_caracteres:,}\n"
            promedio_palabras = total_palabras / max(total_notas, 1)
            resultado += (
                f"   • Promedio de palabras por nota: {promedio_palabras:.0f}\n\n"
            )

            resultado += "📁 **Organización:**\n"
            resultado += f"   • Carpetas: {len(carpetas)}\n"
            for carpeta in sorted(carpetas):
                resultado += f"     - {carpeta}\n"
            resultado += "\n"

            resultado += "🏷️ **Etiquetas más usadas:**\n"
            if etiquetas:
                # Mostrar primeras 10 etiquetas (alfabéticamente)
                for tag in sorted(list(etiquetas)[:10]):
                    resultado += f"   • #{tag}\n"
                if len(etiquetas) > 10:
                    resultado += f"   ... y {len(etiquetas) - 10} etiquetas más\n"
            else:
                resultado += "   • No se encontraron etiquetas\n"
            resultado += "\n"

            resultado += f"🔗 **Enlaces internos únicos:** {len(enlaces_internos)}\n\n"

            resultado += "📅 **Actividad por mes (últimos 6 meses):**\n"
            fechas_ordenadas = sorted(list(por_fecha.keys()))[-6:]
            for fecha in fechas_ordenadas:
                resultado += f"   • {fecha}: {por_fecha[fecha]} notas\n"

            return resultado

        except Exception as e:
            return f"❌ Error al generar estadísticas: {e}"

    @mcp.tool()
    def analizar_etiquetas() -> str:
        """
        Analiza el uso de etiquetas en el vault
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Contador de etiquetas con frecuencia
            conteo_etiquetas = {}
            archivos_con_etiquetas = []

            for archivo in vault_path.rglob("*.md"):
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    etiquetas = extract_tags_from_content(contenido)
                    if etiquetas:
                        archivos_con_etiquetas.append(archivo.name)
                        for tag in etiquetas:
                            conteo_etiquetas[tag] = conteo_etiquetas.get(tag, 0) + 1

                except Exception:
                    continue

            if not conteo_etiquetas:
                return "🏷️ No se encontraron etiquetas en el vault"

            # Ordenar por frecuencia
            etiquetas_ordenadas = sorted(
                conteo_etiquetas.items(), key=lambda x: x[1], reverse=True
            )

            resultado = "🏷️ **Análisis de Etiquetas**\n\n"
            resultado += "📊 **Resumen:**\n"
            resultado += f"   • Total de etiquetas únicas: {len(conteo_etiquetas)}\n"
            resultado += f"   • Archivos con etiquetas: {len(archivos_con_etiquetas)}\n"
            resultado += f"   • Total de usos: {sum(conteo_etiquetas.values())}\n\n"

            resultado += "🔝 **Etiquetas más frecuentes:**\n"
            for tag, count in etiquetas_ordenadas[:15]:
                resultado += f"   • #{tag}: {count} usos\n"

            if len(etiquetas_ordenadas) > 15:
                resultado += f"   ... y {len(etiquetas_ordenadas) - 15} etiquetas más\n"

            return resultado

        except Exception as e:
            return f"❌ Error al analizar etiquetas: {e}"

    @mcp.tool()
    def obtener_lista_etiquetas() -> str:
        """
        Obtiene una lista simple de las etiquetas existentes en el vault.
        Útil para ver qué etiquetas ya existen antes de crear nuevas.

        Returns:
            Lista de etiquetas formateada como string.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            etiquetas_set = set()

            # Recorrer archivos para extraer etiquetas
            # Recorrer archivos para extraer etiquetas
            # Limitamos a recientes si es necesario, pero rglog es rápido.
            for archivo in vault_path.rglob("*.md"):
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()
                        tags = extract_tags_from_content(contenido)
                        etiquetas_set.update(tags)
                except Exception:
                    continue

            if not etiquetas_set:
                return "ℹ️ No se encontraron etiquetas."

            lista_ordenada = sorted(list(etiquetas_set))
            return "🏷️ **Etiquetas existentes:**\n" + ", ".join(lista_ordenada)

        except Exception as e:
            return f"❌ Error al obtener lista de etiquetas: {e}"

    @mcp.tool()
    def analizar_enlaces() -> str:
        """
        Analiza los enlaces internos en el vault
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            enlaces_por_archivo = {}
            todos_los_enlaces = {}
            archivos_existentes = {f.stem for f in vault_path.rglob("*.md")}

            for archivo in vault_path.rglob("*.md"):
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    enlaces = extract_internal_links(contenido)
                    if enlaces:
                        enlaces_por_archivo[archivo.name] = enlaces
                        for enlace in enlaces:
                            todos_los_enlaces[enlace] = (
                                todos_los_enlaces.get(enlace, 0) + 1
                            )

                except Exception:
                    continue

            if not todos_los_enlaces:
                return "🔗 No se encontraron enlaces internos en el vault"

            # Analizar enlaces rotos
            enlaces_rotos = []
            for enlace in todos_los_enlaces:
                # Limpiar el enlace (remover alias si existe)
                enlace_limpio = enlace.split("|")[0].strip()
                if enlace_limpio not in archivos_existentes:
                    enlaces_rotos.append(enlace)

            # Ordenar por frecuencia
            enlaces_ordenados = sorted(
                todos_los_enlaces.items(), key=lambda x: x[1], reverse=True
            )

            resultado = "🔗 **Análisis de Enlaces Internos**\n\n"
            resultado += "📊 **Resumen:**\n"
            resultado += f"   • Total de enlaces únicos: {len(todos_los_enlaces)}\n"
            resultado += f"   • Archivos con enlaces: {len(enlaces_por_archivo)}\n"
            resultado += (
                f"   • Total de referencias: {sum(todos_los_enlaces.values())}\n"
            )
            resultado += f"   • Enlaces rotos: {len(enlaces_rotos)}\n\n"

            resultado += "🔝 **Enlaces más referenciados:**\n"
            for enlace, count in enlaces_ordenados[:10]:
                resultado += f"   • [[{enlace}]]: {count} referencias\n"

            if enlaces_rotos:
                resultado += "\n⚠️ **Enlaces rotos encontrados:**\n"
                for enlace in enlaces_rotos[:10]:
                    resultado += f"   • [[{enlace}]]\n"
                if len(enlaces_rotos) > 10:
                    resultado += (
                        f"   ... y {len(enlaces_rotos) - 10} enlaces rotos más\n"
                    )

            return resultado

        except Exception as e:
            return f"❌ Error al analizar enlaces: {e}"

    @mcp.tool()
    def resumen_actividad_reciente(dias: int = 7) -> str:
        """
        Genera un resumen de la actividad reciente en el vault

        Args:
            dias: Número de días hacia atrás para analizar (por defecto 7)
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            from datetime import datetime, timedelta

            fecha_limite = datetime.now() - timedelta(days=dias)

            archivos_recientes = []
            archivos_modificados = []

            for archivo in vault_path.rglob("*.md"):
                stats = archivo.stat()
                fecha_creacion = datetime.fromtimestamp(stats.st_ctime)
                fecha_modificacion = datetime.fromtimestamp(stats.st_mtime)

                if fecha_creacion >= fecha_limite:
                    archivos_recientes.append(
                        {
                            "nombre": archivo.name,
                            "fecha": fecha_creacion.strftime("%Y-%m-%d %H:%M"),
                            "tipo": "creado",
                        }
                    )
                elif fecha_modificacion >= fecha_limite:
                    archivos_modificados.append(
                        {
                            "nombre": archivo.name,
                            "fecha": fecha_modificacion.strftime("%Y-%m-%d %H:%M"),
                            "tipo": "modificado",
                        }
                    )

            # Ordenar por fecha
            archivos_recientes.sort(key=lambda x: x["fecha"], reverse=True)
            archivos_modificados.sort(key=lambda x: x["fecha"], reverse=True)

            resultado = f"📅 **Actividad Reciente (últimos {dias} días)**\n\n"

            if archivos_recientes:
                resultado += f"✨ **Archivos creados ({len(archivos_recientes)}):**\n"
                for archivo in archivos_recientes[:10]:
                    resultado += f"   • {archivo['nombre']} - {archivo['fecha']}\n"
                if len(archivos_recientes) > 10:
                    resultado += (
                        f"   ... y {len(archivos_recientes) - 10} archivos más\n"
                    )
                resultado += "\n"

            if archivos_modificados:
                resultado += (
                    f"📝 **Archivos modificados ({len(archivos_modificados)}):**\n"
                )
                for archivo in archivos_modificados[:10]:
                    resultado += f"   • {archivo['nombre']} - {archivo['fecha']}\n"
                if len(archivos_modificados) > 10:
                    resultado += (
                        f"   ... y {len(archivos_modificados) - 10} archivos más\n"
                    )

            if not archivos_recientes and not archivos_modificados:
                resultado += (
                    f"😴 No hay actividad registrada en los últimos {dias} días"
                )

            return resultado

        except Exception as e:
            return f"❌ Error al generar resumen de actividad: {e}"
