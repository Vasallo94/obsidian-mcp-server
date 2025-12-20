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

        return "📂 Sugerencia: `01_Inbox` (Categoría general)"

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
            if not carpeta:
                # Intento de sugerencia automática si no se especifica
                res_sug = _get_sugerencia_ubicacion(titulo, contenido, etiquetas)
                # Extrae el path de vuelta entre backticks: 📂 Sugerencia: `path`
                import re

                match = re.search(r"`([^`]+)`", res_sug)
                carpeta_sugerida = match.group(1) if match else "01_Inbox"
                carpeta = carpeta_sugerida

            carpeta_path = vault_path / carpeta
            carpeta_path.mkdir(parents=True, exist_ok=True)
            nota_path = carpeta_path / nombre_archivo

            if not nota_path.suffix == ".md":
                nota_path = nota_path.with_suffix(".md")

            # Verificar si ya existe
            if nota_path.exists():
                return f"❌ Ya existe una nota con el nombre '{nombre_archivo}'"

            # Preparar contenido final
            contenido_final = ""
            ahora = datetime.now().strftime("%Y-%m-%d")

            # Lógica de inyección de metadatos del agente
            creator_metadata = ""
            if agente_creador:
                creator_metadata = f"agente_creador: {agente_creador}\n"

            # Si se usa plantilla
            if plantilla:
                plantilla_path = vault_path / "ZZ_Plantillas" / plantilla
                if not plantilla.endswith(".md"):
                    plantilla_path = plantilla_path.with_suffix(".md")

                if plantilla_path.exists():
                    with open(plantilla_path, "r", encoding="utf-8") as f:
                        plantilla_content = f.read()

                    # Reemplazos básicos
                    plantilla_content = plantilla_content.replace("{{title}}", titulo)
                    plantilla_content = plantilla_content.replace("{{titulo}}", titulo)
                    plantilla_content = plantilla_content.replace("{{date}}", ahora)
                    plantilla_content = plantilla_content.replace("{{fecha}}", ahora)

                    contenido_final = plantilla_content
                    # Si hay contenido adicional, añadirlo al final
                    if contenido:
                        if contenido_final.endswith("\n\n"):
                            contenido_final += contenido
                        else:
                            contenido_final += f"\n\n{contenido}"
                else:
                    return f"❌ No se encontró la plantilla '{plantilla}'"
            else:
                # Sin plantilla, crear frontmatter básico
                tags_list = [t.strip() for t in etiquetas.split(",") if t.strip()]
                contenido_final = "---\n"
                contenido_final += f'title: "{titulo}"\n'
                contenido_final += f"tags: {tags_list}\n"
                contenido_final += f'created: "{ahora}"\n'
                if creator_metadata:
                    contenido_final += creator_metadata
                contenido_final += "---\n\n"
                contenido_final += f"# {titulo}\n\n"
                contenido_final += contenido

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

            ruta_relativa = nota_path.relative_to(vault_path)

            # Eliminar archivo
            nota_path.unlink()

            return f"✅ Nota eliminada: {ruta_relativa}"

        except Exception as e:
            return f"❌ Error al eliminar nota: {e}"
