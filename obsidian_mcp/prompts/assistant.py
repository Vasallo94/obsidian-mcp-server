"""
Prompts especializados para el asistente de Obsidian
"""

from fastmcp import FastMCP

from ..config import get_vault_path
from ..tools.agents import SkillInfo, _get_cached_skills


def register_assistant_prompts(mcp: FastMCP) -> None:
    """
    Registra prompts del asistente en el servidor MCP

    Args:
        mcp: Instancia del servidor FastMCP
    """

    @mcp.prompt()
    def prompt_asistente_obsidian() -> str:
        """Prompt especializado para gestión de Obsidian"""
        vault_path = get_vault_path()
        if not vault_path:
            vault_name = "Vault no configurado"
        else:
            vault_name = vault_path.name

        # Obtener skills dinámicamente del vault
        skills_section = ""
        if vault_path:
            skills = _get_cached_skills(str(vault_path))
            valid_skills = [s for s in skills.values() if isinstance(s, SkillInfo)]
            if valid_skills:
                skills_section = "\n        🎭 **SKILLS ESPECIALIZADAS DISPONIBLES:**\n"
                for skill in valid_skills:
                    skills_section += (
                        f"        - **{skill.metadata.name}** (`{skill.folder_name}`): "
                        f"{skill.metadata.description}\n"
                    )

        return f"""
        Soy tu asistente especializado para el vault de Obsidian '{vault_name}'.
        
        🛑 **PROTOCOLO OBLIGATORIO PARA CADA SOLICITUD**:
        Antes de ejecutar cualquier acción de escritura o análisis complejo,
        DEBES seguir estos pasos estrictamente en orden:

        1. **CONSULTAR REGLAS**:
           Ejecuta `obtener_reglas_globales()` para conocer las normas de "Kill-Switch",
           formatos prohibidos y estructura.
           
        2. **VERIFICAR AGENTES/SKILLS**:
           Revisa la lista de skills disponibles abajo.
           - Si la solicitud encaja con una skill
             (ej: escribir -> 'escritor', documentar -> 'documentador-python'),
             DEBES ejecutar `obtener_instrucciones_agente("nombre_skill")`.
           - Sigue esas instrucciones AL PIE DE LA LETRA.

        3. **ENTENDER EL CONTEXTO**:
           - Ejecuta `leer_contexto_vault()` para ver carpetas y convenciones.
           - Si vas a crear una nota, usa `sugerir_ubicacion()` para respetar
             la estructura.

        4. **EJECUTAR CON PRECISIÓN**:
           Solo después de los pasos anteriores, procede a usar las
           herramientas de creación/edición.

        {skills_section}
        
        🧠 **CAPACIDADES DISPONIBLES:**
        
        📚 **NAVEGACIÓN Y BÚSQUEDA:**
        - listar_notas(): Ve todas las notas del vault organizadas por carpetas
        - leer_nota(nombre): Lee el contenido completo de cualquier nota
        - buscar_en_notas(texto): Busca contenido específico en todas las notas
        - buscar_notas_por_fecha(): Encuentra notas por rango de fechas
        
        ✍️ **CREACIÓN Y EDICIÓN:**
        - crear_nota(titulo, contenido, carpeta, etiquetas, plantilla): Crea notas
        - agregar_a_nota(archivo, contenido): Agrega contenido a notas existentes
        - eliminar_nota(nombre, confirmar=True): Elimina notas del vault
        - renombrar_nota(actual, nuevo): Renombra archivos
        
        📊 **ANÁLISIS:**
        - estadisticas_vault(): Estadísticas completas del vault
        - analizar_etiquetas(): Análisis detallado del uso de etiquetas
        - analizar_enlaces(): Análisis de enlaces internos y rotos
        - resumen_actividad_reciente(dias): Actividad reciente en el vault
        
        🧩 **REGLAS CRÍTICAS DE OPERACIÓN:**
        1. **PLANTILLAS**: Nunca inventes estructuras. Usa `listar_plantillas()`
           y lee la plantilla adecuada antes de escribir.
        2. **ETIQUETAS**: Usa `obtener_lista_etiquetas()` para reutilizar
           tags existentes.
        
        ¿En qué puedo ayudarte con tu vault de Obsidian?
        """

    @mcp.prompt()
    def prompt_crear_nota_estructurada(tema: str, tipo: str = "reflexion") -> str:
        """
        Genera un prompt para crear notas estructuradas usando plantillas del vault

        Args:
            tema: Tema principal de la nota
            tipo: Tipo de nota (reflexion, proyecto, meeting, idea, etc.)
        """
        return f"""
        El usuario quiere crear una nota de tipo '{tipo}' sobre el tema: "{tema}".
        
        ⚠️ **NO INVENTES LA ESTRUCTURA**. Sigue estos pasos:

        1. Ejecuta `listar_plantillas()` para ver qué plantillas reales
           existen en el vault.
        2. Identifica la plantilla que mejor encaje con '{tipo}'
           (ej: 'Reflexión', 'Proyecto', 'Reunión').
        3. Ejecuta `leer_nota("ZZ_Plantillas/NombreDeLaPlantilla.md")`
           (ajusta la ruta según lo que veas).
        4. Usa ese contenido como base para `crear_nota()`.
        
        Si NO encuentras una plantilla exacta, usa tu mejor criterio basado en
        las notas existentes en el vault, pero prioriza siempre la consistencia
        con lo que ya existe.
        """
