"""
Herramientas de creación y edición para el vault de Obsidian.

Estas herramientas permiten crear nuevas notas y modificar las existentes,
facilitando la gestión de contenido del vault desde un cliente MCP.
"""

from fastmcp import FastMCP


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
        from .creation_logic import list_templates

        try:
            return list_templates().to_display()
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
        from .creation_logic import suggest_folder_location

        try:
            return suggest_folder_location(titulo, contenido, etiquetas)
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
        from .creation_logic import create_note

        try:
            return create_note(
                titulo,
                contenido,
                carpeta,
                etiquetas,
                plantilla,
                agente_creador,
                descripcion,
            ).to_display(success_prefix="✅")
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
        from .creation_logic import append_to_note

        try:
            return append_to_note(nombre_archivo, contenido, al_final).to_display(
                success_prefix="✅"
            )
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
        from .creation_logic import delete_note

        try:
            return delete_note(nombre_archivo, confirmar).to_display(success_prefix="✅")
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
        from .creation_logic import edit_note

        try:
            return edit_note(nombre_archivo, nuevo_contenido).to_display(
                success_prefix="✅"
            )
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
        from .creation_logic import search_and_replace_global

        try:
            return search_and_replace_global(
                buscar, reemplazar, carpeta, solo_preview, limite
            ).to_display()
        except Exception as e:
            return f"❌ Error en búsqueda global: {e}"
