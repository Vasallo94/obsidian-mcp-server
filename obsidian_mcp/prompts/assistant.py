"""
Prompts especializados para el asistente de Obsidian
"""

from fastmcp import FastMCP

from ..config import get_vault_path


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

        return f"""
        Soy tu asistente especializado para el vault de Obsidian '{vault_name}'.
        
        🧠 **CAPACIDADES DISPONIBLES:**
        
        📚 **NAVEGACIÓN Y BÚSQUEDA:**
        - listar_notas(): Ve todas las notas del vault organizadas por carpetas
        - leer_nota(nombre): Lee el contenido completo de cualquier nota
        - buscar_en_notas(texto): Busca contenido específico en todas las notas
        - buscar_notas_por_fecha(): Encuentra notas por rango de fechas
        
        ✍️ **CREACIÓN Y EDICIÓN:**
        - crear_nota(titulo, contenido, carpeta, etiquetas): Crea nuevas notas
        - agregar_a_nota(archivo, contenido): Agrega contenido a notas existentes
        - eliminar_nota(nombre, confirmar=True): Elimina notas del vault
        - renombrar_nota(actual, nuevo): Renombra archivos
        
        📊 **ANÁLISIS:**
        - estadisticas_vault(): Estadísticas completas del vault
        - analizar_etiquetas(): Análisis detallado del uso de etiquetas
        - analizar_enlaces(): Análisis de enlaces internos y rotos
        - resumen_actividad_reciente(dias): Actividad reciente en el vault
        
        🧩 **LÓGICA DE ETIQUETADO INTELIGENTE (Smart Tagging):**
        Antes de crear cualquier nota con etiquetas o sugerir tags:
        1. Consulta SIEMPRE las etiquetas existentes con `analizar_etiquetas()` o
           `obtener_lista_etiquetas()`.
        2. **Prioriza** usar etiquetas que ya existen si semánticamente encajan.
        3. Si y SOLO si ninguna etiqueta existente sirve, puedes crear nuevas.
        4. **Límite estricto**: Máximo 3 etiquetas NUEVAS por nota.

        💡 **SUGERENCIAS DE USO:**
        • "Muéstrame mis notas más recientes"
        • "Busca todas las referencias a 'inteligencia artificial'"
        • "Crea una nota sobre lo que he aprendido hoy"
        • "¿Cuáles son mis temas más frecuentes?"
        • "Analiza los enlaces rotos en mi vault"
        • "Dame estadísticas de mi productividad"
        
        ¿En qué puedo ayudarte con tu vault de Obsidian?
        """

    @mcp.prompt()
    def prompt_crear_nota_estructurada(tema: str, tipo: str = "reflexion") -> str:
        """
        Genera un prompt para crear notas estructuradas según el tipo

        Args:
            tema: Tema principal de la nota
            tipo: Tipo de nota (reflexion, proyecto, meeting, idea, etc.)
        """
        templates = {
            "reflexion": f"""
            Crea una nota de reflexión sobre "{tema}" con la siguiente estructura:
            
            # Reflexión: {tema}
            
            ## 🤔 Pregunta Principal
            [¿Qué pregunta estoy explorando?]
            
            ## 💭 Pensamientos Iniciales
            [Mis primeras ideas sobre el tema]
            
            ## 🔍 Análisis
            [Exploración más profunda]
            
            ## 🎯 Conclusiones
            [¿Qué he aprendido?]
            
            ## 🔗 Conexiones
            [Enlaces con otras ideas o notas]
            
            ## 📚 Referencias
            [Fuentes, libros, artículos relacionados]
            """,
            "proyecto": f"""
            Crea una nota de proyecto para "{tema}" con la siguiente estructura:
            
            # Proyecto: {tema}
            
            ## 🎯 Objetivo
            [¿Qué quiero lograr?]
            
            ## 📋 Tareas
            - [ ] [Primera tarea]
            - [ ] [Segunda tarea]
            
            ## 📅 Timeline
            - **Inicio**: [fecha]
            - **Hitos importantes**: 
            - **Finalización**: [fecha]
            
            ## 📊 Recursos Necesarios
            [Herramientas, personas, materiales]
            
            ## 🚧 Obstáculos Potenciales
            [¿Qué podría salir mal?]
            
            ## ✅ Criterios de Éxito
            [¿Cómo sabré que he terminado?]
            """,
            "meeting": f"""
            Crea una nota de reunión sobre "{tema}" con la siguiente estructura:
            
            # Reunión: {tema}
            
            ## 📅 Información
            - **Fecha**: [fecha]
            - **Duración**: [tiempo]
            - **Participantes**: [lista]
            - **Tipo**: [presencial/virtual]
            
            ## 🎯 Agenda
            1. [Punto 1]
            2. [Punto 2]
            3. [Punto 3]
            
            ## 📝 Notas
            [Apuntes durante la reunión]
            
            ## ✅ Acuerdos
            [Decisiones tomadas]
            
            ## 📋 Acciones
            - [ ] [Acción 1] - Responsable: [nombre] - Fecha: [fecha]
            - [ ] [Acción 2] - Responsable: [nombre] - Fecha: [fecha]
            
            ## 🔄 Seguimiento
            [Próximos pasos]
            """,
            "idea": f"""
            Crea una nota de idea sobre "{tema}" con la siguiente estructura:
            
            # 💡 Idea: {tema}
            
            ## ⚡ La Idea
            [Descripción concisa de la idea]
            
            ## 🌟 ¿Por qué es interesante?
            [Qué la hace especial o valiosa]
            
            ## 🛠️ ¿Cómo podría implementarse?
            [Pasos prácticos para llevarla a cabo]
            
            ## 🎯 Aplicaciones Potenciales
            [Dónde o cómo se podría usar]
            
            ## 🔗 Ideas Relacionadas
            [Conexiones con otras ideas]
            
            ## 📈 Próximos Pasos
            - [ ] [Acción inmediata]
            - [ ] [Investigar más sobre...]
            - [ ] [Probar con...]
            """,
        }

        return templates.get(tipo.lower(), templates["reflexion"])
