"""
Herramientas de contexto para el vault de Obsidian.

Estas herramientas permiten al agente entender la estructura y organización
del vault para tomar mejores decisiones sobre dónde guardar notas y qué etiquetas usar.
"""

from typing import Dict

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import extract_tags_from_content


def register_context_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de contexto en el servidor MCP.
    """

    @mcp.tool()
    def leer_contexto_vault() -> str:
        """
        Lee la estructura general del vault y estadísticas clave para dar
        contexto al agente.
        Devuelve un resumen de carpetas, plantillas y etiquetas comunes.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # 1. Estructura de carpetas (primer nivel y algunos segundos niveles clave)
            estructura = []
            excluidos = {
                ".git",
                ".obsidian",
                ".trash",
                ".gemini",
                ".space",
                ".makemd",
                ".obsidianrag",
            }

            # Buscar carpetas principales
            for item in sorted(vault_path.iterdir()):
                if (
                    item.is_dir()
                    and item.name not in excluidos
                    and not item.name.startswith(".")
                ):
                    subcarpetas = []
                    # Solo listar subcarpetas si no son demasiadas
                    try:
                        for sub in sorted(item.iterdir()):
                            if sub.is_dir() and not sub.name.startswith("."):
                                subcarpetas.append(sub.name)
                    except PermissionError:
                        pass

                    desc = f"📂 {item.name}"
                    if subcarpetas:
                        # Limitar visualización de subcarpetas
                        if len(subcarpetas) > 5:
                            desc += f" (incluye: {', '.join(subcarpetas[:5])}, ...)"
                        else:
                            desc += f" (incluye: {', '.join(subcarpetas)})"
                    estructura.append(desc)

            # 2. Plantillas disponibles
            plantillas = []
            plantillas_path = vault_path / "ZZ_Plantillas"
            if plantillas_path.exists():
                for item in sorted(plantillas_path.glob("*.md")):
                    plantillas.append(item.stem)

            # 3. Etiquetas más comunes (muestreo)
            conteo_etiquetas: Dict[str, int] = {}
            # Analizar un subconjunto reciente o archivos al azar
            # O simplemente usar los archivos en carpetas clave
            limit_files = 100
            count = 0
            for archivo in vault_path.rglob("*.md"):
                if count >= limit_files:
                    break
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        tags = extract_tags_from_content(f.read())
                        for tag in tags:
                            conteo_etiquetas[tag] = conteo_etiquetas.get(tag, 0) + 1
                    count += 1
                except Exception:
                    continue

            top_tags = sorted(
                conteo_etiquetas.items(), key=lambda x: x[1], reverse=True
            )[:20]
            tags_str = ", ".join([f"#{t}" for t, _ in top_tags])

            # Construir reporte
            reporte = "# Contexto del Vault\n\n"

            reporte += "## 📂 Estructura Principal\n"
            reporte += "\n".join(estructura) + "\n\n"

            reporte += "## 📝 Plantillas Disponibles (en ZZ_Plantillas)\n"
            if plantillas:
                reporte += ", ".join(plantillas) + "\n\n"
            else:
                reporte += "No se encontraron plantillas en ZZ_Plantillas.\n\n"

            reporte += "## 🏷️ Etiquetas Comunes (Muestreo)\n"
            if tags_str:
                reporte += tags_str + "\n"
            else:
                reporte += "No se detectaron etiquetas comunes.\n"

            return reporte

        except Exception as e:
            return f"❌ Error al leer contexto: {e}"
