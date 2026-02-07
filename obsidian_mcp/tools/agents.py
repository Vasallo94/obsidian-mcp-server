"""
Herramientas para la integración de Habilidades (Skills).

Estas herramientas permiten al cliente MCP leer las definiciones y prompts
de las skills almacenadas en la carpeta .agent/skills del vault.

Mejoras v2:
- Parsing estructurado de YAML frontmatter
- Validación de schema con Pydantic
- Caché en memoria para evitar re-lecturas innecesarias
- Soporte para .agent/REGLAS_GLOBALES.md como reglas globales
"""

from __future__ import annotations

from fastmcp import FastMCP


def register_agent_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas y recursos de gestión de skills (agentes).
    """

    @mcp.resource("skills://list")
    def resource_listar_skills() -> str:
        """Recurso que devuelve la lista de skills disponibles."""
        from .agents_logic import list_available_skills

        return list_available_skills().to_display()

    @mcp.tool()
    def listar_agentes() -> str:
        """Lista las skills (agentes) disponibles en el vault."""
        from .agents_logic import list_available_skills

        return list_available_skills().to_display()

    @mcp.tool()
    def obtener_instrucciones_agente(nombre: str) -> str:
        """
        Obtiene el contenido de una Skill específica (SKILL.md).

        Args:
            nombre: El nombre de la carpeta de la skill (ej: 'escritor').
        """
        from .agents_logic import get_agent_instructions

        return get_agent_instructions(nombre).to_display()

    @mcp.tool()
    def obtener_reglas_globales() -> str:
        """
        Obtiene las reglas globales del Agente (.agent/REGLAS_GLOBALES.md).

        ⚠️ OBLIGATORIO PARA AGENTES DE IA: ⚠️
        DEBES leer estas reglas ANTES de realizar cualquier escritura
        o modificación en el vault.
        Contienen restricciones críticas (ej: NO emojis, formatos permitidos).
        """
        from .agents_logic import get_global_rules

        return get_global_rules().to_display()

    @mcp.tool()
    def refrescar_cache_skills() -> str:
        """Invalida y refresca el caché de skills (úsalo tras editar SKILL.md)."""
        from .agents_logic import refresh_skills_cache

        return refresh_skills_cache().to_display()

    @mcp.tool()
    def generar_skill(
        nombre: str,
        descripcion: str,
        instrucciones: str,
        herramientas: str = "",
        ubicacion_defecto: str = "",
    ) -> str:
        """
        Genera una nueva skill con estructura consistente.

        Crea automáticamente el archivo SKILL.md con:
        - Frontmatter YAML correcto
        - Referencia a REGLAS_GLOBALES
        - Sección "REGLA DE ORO DE EDICIÓN"

        Args:
            nombre: Identificador de la skill (ej: "profesor-fisica").
            descripcion: Descripción breve de lo que hace la skill.
            instrucciones: Instrucciones principales en markdown.
            herramientas: Herramientas separadas por comas (ej: "read, edit, web").
            ubicacion_defecto: Carpeta por defecto para notas (ej: "02_Aprendizaje/").
        """
        from .agents_generator import generate_skill

        return generate_skill(
            nombre, descripcion, instrucciones, herramientas, ubicacion_defecto
        ).to_display()

    @mcp.tool()
    def sugerir_skills_para_vault() -> str:
        """
        Analiza el vault y sugiere skills personalizadas.

        Escanea patrones de uso: tags frecuentes, carpetas con más contenido,
        tipos de notas. Devuelve sugerencias de skills basadas en tu vault.
        """
        from .agents_generator import suggest_skills_for_vault

        return suggest_skills_for_vault().to_display()

    @mcp.tool()
    def sincronizar_skills(actualizar: bool = False) -> str:
        """
        Sincroniza y valida las skills existentes.

        Detecta problemas como:
        - Falta de referencia a REGLAS_GLOBALES
        - Falta de sección "REGLA DE ORO DE EDICIÓN"
        - Frontmatter incorrecto

        Args:
            actualizar: Si True, aplica correcciones. Si False, solo reporta.
        """
        from .agents_generator import sync_skills

        return sync_skills(actualizar).to_display()
