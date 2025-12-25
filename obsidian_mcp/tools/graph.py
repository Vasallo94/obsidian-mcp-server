"""
Herramientas de grafos y conexiones para el vault de Obsidian.

Estas herramientas permiten explorar las relaciones entre notas,
encontrar backlinks, buscar por tags y analizar la estructura del grafo.
"""

from typing import Dict, List

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import extract_internal_links, extract_tags_from_content


def register_graph_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de grafos y conexiones en el servidor MCP.
    """

    @mcp.tool()
    def obtener_backlinks(nombre_nota: str) -> str:
        """
        Obtiene todas las notas que enlazan a la nota especificada (backlinks).

        Args:
            nombre_nota: Nombre de la nota (con o sin .md)

        Returns:
            Lista de notas que contienen enlaces a esta nota
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Normalizar nombre (sin extensión para buscar en enlaces)
            nombre_limpio = nombre_nota.replace(".md", "")

            backlinks: List[Dict[str, str]] = []

            for archivo in vault_path.rglob("*.md"):
                # Ignorar la propia nota
                if archivo.stem == nombre_limpio:
                    continue

                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    enlaces = extract_internal_links(contenido)

                    # Verificar si algún enlace apunta a nuestra nota
                    for enlace in enlaces:
                        # Limpiar alias si existe (ej: "Nota|alias")
                        enlace_limpio = enlace.split("|")[0].strip()
                        if enlace_limpio == nombre_limpio:
                            ruta_rel = archivo.relative_to(vault_path)
                            backlinks.append(
                                {
                                    "nota": archivo.stem,
                                    "ruta": str(ruta_rel),
                                }
                            )
                            break  # Ya encontramos el enlace en este archivo

                except Exception:
                    continue

            if not backlinks:
                return f"🔗 No se encontraron backlinks hacia '{nombre_nota}'"

            resultado = f"🔗 **Backlinks hacia '{nombre_nota}'** "
            resultado += f"({len(backlinks)} notas):\n\n"

            for bl in backlinks:
                resultado += f"   • [[{bl['nota']}]] - {bl['ruta']}\n"

            return resultado

        except Exception as e:
            return f"❌ Error al obtener backlinks: {e}"

    @mcp.tool()
    def obtener_notas_por_tag(tag: str) -> str:
        """
        Busca todas las notas que contienen una etiqueta específica.

        Args:
            tag: Etiqueta a buscar (con o sin #)

        Returns:
            Lista de notas que contienen la etiqueta
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Limpiar el # si viene incluido
            tag_limpia = tag.lstrip("#")

            notas_con_tag: List[Dict[str, str]] = []

            for archivo in vault_path.rglob("*.md"):
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    tags = extract_tags_from_content(contenido)

                    if tag_limpia in tags:
                        ruta_rel = archivo.relative_to(vault_path)
                        notas_con_tag.append(
                            {
                                "nota": archivo.stem,
                                "ruta": str(ruta_rel),
                            }
                        )

                except Exception:
                    continue

            if not notas_con_tag:
                return f"🏷️ No se encontraron notas con la etiqueta #{tag_limpia}"

            resultado = f"🏷️ **Notas con #{tag_limpia}** "
            resultado += f"({len(notas_con_tag)} encontradas):\n\n"

            # Agrupar por carpeta
            por_carpeta: Dict[str, List[str]] = {}
            for nota in notas_con_tag:
                carpeta = (
                    str(nota["ruta"]).rsplit("/", 1)[0]
                    if "/" in nota["ruta"]
                    else "Raíz"
                )
                if carpeta not in por_carpeta:
                    por_carpeta[carpeta] = []
                por_carpeta[carpeta].append(nota["nota"])

            for carpeta, notas in sorted(por_carpeta.items()):
                resultado += f"📁 {carpeta}:\n"
                for nota in sorted(notas):
                    resultado += f"   • [[{nota}]]\n"
                resultado += "\n"

            return resultado

        except Exception as e:
            return f"❌ Error al buscar por tag: {e}"

    @mcp.tool()
    def obtener_grafo_local(nombre_nota: str, profundidad: int = 1) -> str:
        """
        Obtiene el grafo local de una nota: enlaces salientes y entrantes.

        Args:
            nombre_nota: Nombre de la nota central
            profundidad: Niveles de profundidad (1 = solo conexiones directas)

        Returns:
            Visualización del grafo local de la nota
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            nombre_limpio = nombre_nota.replace(".md", "")

            # Buscar la nota
            nota_path = None
            for archivo in vault_path.rglob("*.md"):
                if archivo.stem == nombre_limpio:
                    nota_path = archivo
                    break

            if not nota_path:
                return f"❌ No se encontró la nota '{nombre_nota}'"

            # Obtener enlaces salientes
            with open(nota_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            enlaces_salientes = extract_internal_links(contenido)
            # Limpiar aliases
            enlaces_salientes = [e.split("|")[0].strip() for e in enlaces_salientes]
            enlaces_salientes = list(set(enlaces_salientes))

            # Obtener backlinks (enlaces entrantes)
            backlinks = []
            for archivo in vault_path.rglob("*.md"):
                if archivo.stem == nombre_limpio:
                    continue
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        cont = f.read()
                    enlaces = extract_internal_links(cont)
                    for enlace in enlaces:
                        enlace_limpio = enlace.split("|")[0].strip()
                        if enlace_limpio == nombre_limpio:
                            backlinks.append(archivo.stem)
                            break
                except Exception:
                    continue

            # Construir resultado
            resultado = f"🕸️ **Grafo Local de '{nombre_nota}'**\n\n"

            resultado += f"📤 **Enlaces salientes** ({len(enlaces_salientes)}):\n"
            if enlaces_salientes:
                for enlace in sorted(enlaces_salientes)[:15]:
                    resultado += f"   → [[{enlace}]]\n"
                if len(enlaces_salientes) > 15:
                    resultado += f"   ... y {len(enlaces_salientes) - 15} más\n"
            else:
                resultado += "   (ninguno)\n"

            resultado += f"\n📥 **Backlinks** ({len(backlinks)}):\n"
            if backlinks:
                for bl in sorted(backlinks)[:15]:
                    resultado += f"   ← [[{bl}]]\n"
                if len(backlinks) > 15:
                    resultado += f"   ... y {len(backlinks) - 15} más\n"
            else:
                resultado += "   (ninguno)\n"

            # Calc conectividad
            total = len(enlaces_salientes) + len(backlinks)
            resultado += f"\n📊 **Conectividad total**: {total} conexiones"

            return resultado

        except Exception as e:
            return f"❌ Error al obtener grafo: {e}"

    @mcp.tool()
    def encontrar_notas_huerfanas() -> str:
        """
        Encuentra notas huérfanas: sin enlaces entrantes ni salientes.

        Returns:
            Lista de notas que no están conectadas al grafo del vault
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Recopilar todos los enlaces del vault
            enlaces_salientes_por_nota: Dict[str, List[str]] = {}
            todos_los_enlaces: set = set()

            for archivo in vault_path.rglob("*.md"):
                try:
                    with open(archivo, "r", encoding="utf-8") as f:
                        contenido = f.read()

                    enlaces = extract_internal_links(contenido)
                    enlaces_limpios = [e.split("|")[0].strip() for e in enlaces]
                    enlaces_salientes_por_nota[archivo.stem] = enlaces_limpios
                    todos_los_enlaces.update(enlaces_limpios)

                except Exception:
                    continue

            # Encontrar huérfanas
            notas_huerfanas = []
            for archivo in vault_path.rglob("*.md"):
                nombre = archivo.stem

                # Ignorar carpetas de sistema
                if any(x in str(archivo) for x in [".git", ".obsidian", "ZZ_"]):
                    continue

                tiene_salientes = bool(enlaces_salientes_por_nota.get(nombre, []))
                recibe_enlaces = nombre in todos_los_enlaces

                if not tiene_salientes and not recibe_enlaces:
                    ruta_rel = archivo.relative_to(vault_path)
                    notas_huerfanas.append(
                        {
                            "nota": nombre,
                            "ruta": str(ruta_rel),
                        }
                    )

            if not notas_huerfanas:
                return "✅ No hay notas huérfanas. Todas están conectadas al grafo."

            resultado = f"🔍 **Notas Huérfanas** ({len(notas_huerfanas)}):\n\n"
            resultado += "Estas notas no tienen enlaces entrantes ni salientes:\n\n"

            for nota in notas_huerfanas[:30]:
                resultado += f"   • {nota['ruta']}\n"

            if len(notas_huerfanas) > 30:
                resultado += f"\n... y {len(notas_huerfanas) - 30} más"

            return resultado

        except Exception as e:
            return f"❌ Error al buscar huérfanas: {e}"
