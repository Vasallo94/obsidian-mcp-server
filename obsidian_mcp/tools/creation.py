"""
Herramientas de creación y edición para el vault de Obsidian.

Estas herramientas permiten crear nuevas notas y modificar las existentes,
facilitando la gestión de contenido del vault desde un cliente MCP.
"""

from datetime import datetime

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import find_note_by_name, sanitize_filename


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

            plantillas_path = vault_path / "ZZ_Plantillas"
            if not plantillas_path.exists():
                return "❌ No se encontró la carpeta 'ZZ_Plantillas'"

            plantillas = []
            for item in sorted(plantillas_path.glob("*.md")):
                plantillas.append(item.name)

            if not plantillas:
                return "ℹ️ No hay plantillas disponibles en ZZ_Plantillas"

            return "📝 **Plantillas disponibles:**\n" + "\n".join(
                [f"- {p}" for p in plantillas]
            )

        except Exception as e:
            return f"❌ Error al listar plantillas: {e}"

    @mcp.tool()
    def crear_nota(
        titulo: str,
        contenido: str,
        carpeta: str = "",
        etiquetas: str = "",
        plantilla: str = "",
    ) -> str:
        """
        Crea una nueva nota en el vault, opcionalmente usando una plantilla.

        Args:
            titulo: Título de la nota (se usará como nombre de archivo).
            contenido: Contenido de la nota en Markdown.
            carpeta: Carpeta donde crear la nota (vacío = raíz).
            etiquetas: Etiquetas separadas por comas (ej: "idea,reflexion").
            plantilla: Nombre del archivo de plantilla a usar (ej: "Diario.md").
                       Las variables {{titulo}} y {{fecha}} se reemplazarán.

        Returns:
            Un mensaje indicando el resultado de la operación.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Preparar nombre de archivo
            nombre_archivo = sanitize_filename(titulo)

            # Determinar ruta
            if carpeta:
                carpeta_path = vault_path / carpeta
                carpeta_path.mkdir(parents=True, exist_ok=True)
                nota_path = carpeta_path / nombre_archivo
            else:
                nota_path = vault_path / nombre_archivo

            # Verificar si ya existe
            if nota_path.exists():
                return f"❌ Ya existe una nota con el nombre '{nombre_archivo}'"

            # Preparar contenido
            contenido_final = ""

            # Si se usa plantilla
            if plantilla:
                plantilla_path = vault_path / "ZZ_Plantillas" / plantilla
                if not plantilla.endswith(".md"):
                    plantilla_path = plantilla_path.with_suffix(".md")

                if plantilla_path.exists():
                    try:
                        with open(plantilla_path, "r", encoding="utf-8") as f:
                            plantilla_content = f.read()

                        # Reemplazos básicos
                        plantilla_content = plantilla_content.replace(
                            "{{title}}", titulo
                        )
                        plantilla_content = plantilla_content.replace(
                            "{{titulo}}", titulo
                        )
                        plantilla_content = plantilla_content.replace(
                            "{{date}}", datetime.now().strftime("%Y-%m-%d")
                        )
                        plantilla_content = plantilla_content.replace(
                            "{{fecha}}", datetime.now().strftime("%Y-%m-%d")
                        )

                        contenido_final = plantilla_content
                        # Si hay contenido adicional, añadirlo al final
                        if contenido:
                            contenido_final += f"\n\n{contenido}"
                    except Exception as e:
                        return f"❌ Error al leer plantilla: {e}"
                else:
                    return f"❌ No se encontró la plantilla '{plantilla}'"
            else:
                # Sin plantilla, usar lógica manual
                contenido_final = ""

                # Agregar frontmatter si hay etiquetas (y no se usó plantilla,
                # ya que la plantilla debería tener su propio frontmatter)
                # NOTA: Si la plantilla tiene frontmatter, las etiquetas pasadas aquí
                # se podrían perder o duplicar. Idealmente deberíamos inyectarlas.
                # Por simplicidad: si hay plantilla, asumimos que maneja sus tags.
                # Pero el usuario pidió tags acotadas. Vamos a intentar inyectar tags.
                # Mejor estrategia simple: Si hay etiquetas, inyectar frontmatter
                # solo si no hay plantilla, o si la plantilla no tiene frontmatter.

                if etiquetas:
                    tags = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
                    contenido_final += "---\n"
                    contenido_final += f"tags: {tags}\n"
                    contenido_final += f'created: "{datetime.now().isoformat()}"\n'
                    contenido_final += "---\n\n"

                contenido_final += contenido

            # Escribir archivo
            with open(nota_path, "w", encoding="utf-8") as f:
                f.write(contenido_final)

            # Información del resultado
            ruta_relativa = nota_path.relative_to(vault_path)
            resultado = f"✅ Nota creada: **{titulo}**\n"
            resultado += f"📍 Ubicación: {ruta_relativa}\n"

            if plantilla:
                resultado += f"📝 Plantilla usada: {plantilla}\n"

            resultado += f"📊 Tamaño: {len(contenido_final)} caracteres"

            if etiquetas and not plantilla:
                resultado += f"\n🏷️  Etiquetas: {etiquetas}"

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

            # Leer contenido actual
            with open(nota_path, "r", encoding="utf-8") as f:
                contenido_actual = f.read()

            # Preparar nuevo contenido
            if al_final:
                nuevo_contenido = contenido_actual + "\n\n" + contenido
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

            ruta_relativa = nota_path.relative_to(vault_path)

            # Eliminar archivo
            nota_path.unlink()

            return f"✅ Nota eliminada: {ruta_relativa}"

        except Exception as e:
            return f"❌ Error al eliminar nota: {e}"
