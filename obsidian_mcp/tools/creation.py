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
    def crear_nota(
        titulo: str, contenido: str, carpeta: str = "", etiquetas: str = ""
    ) -> str:
        """
        Crea una nueva nota en el vault.

        Args:
            titulo: Título de la nota (se usará como nombre de archivo).
            contenido: Contenido de la nota en Markdown.
            carpeta: Carpeta donde crear la nota (vacío = raíz).
            etiquetas: Etiquetas separadas por comas (ej: "idea,reflexion,personal").

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

            # Preparar contenido con metadatos
            contenido_completo = ""

            # Agregar frontmatter si hay etiquetas
            if etiquetas:
                tags = [tag.strip() for tag in etiquetas.split(",") if tag.strip()]
                contenido_completo += "---\n"
                contenido_completo += f"tags: {tags}\n"
                contenido_completo += f'created: "{datetime.now().isoformat()}"\n'
                contenido_completo += "---\n\n"

            # Agregar el contenido principal
            contenido_completo += contenido

            # Escribir archivo
            with open(nota_path, "w", encoding="utf-8") as f:
                f.write(contenido_completo)

            # Información del resultado
            ruta_relativa = nota_path.relative_to(vault_path)
            resultado = f"✅ Nota creada: **{titulo}**\n"
            resultado += f"📍 Ubicación: {ruta_relativa}\n"
            resultado += f"📊 Tamaño: {len(contenido_completo)} caracteres"

            if etiquetas:
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
