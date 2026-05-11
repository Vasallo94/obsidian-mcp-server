"""Vault profile prompts."""

from __future__ import annotations

from fastmcp import FastMCP

from ..config import get_vault_path
from ..tools.agents_logic import get_cached_skills
from ..vault_config import get_vault_config

SECUNDO_PROFILE = "secundo_selebro"


def register_profile_prompts(mcp: FastMCP) -> None:
    """Register prompts provided by the active vault profile."""
    context = _profile_context()
    if context is None:
        return

    enabled, skills, standards = context

    def prompt_enabled(name: str) -> bool:
        return SECUNDO_PROFILE in enabled or name in enabled

    if prompt_enabled("update_media_item") and "media" in standards:

        @mcp.prompt(name="update_media_item")
        def update_media_item(
            work: str,
            media_type: str = "auto",
            opinion: str = "",
        ) -> str:
            """
            Update a movie, series, or book in the Secundo Selebro media library.

            Args:
                work: Title or free-form description of the work.
                media_type: auto, book, movie, or series.
                opinion: Personal notes to integrate without overwriting.
            """
            return f"""
            Actualiza la biblioteca canónica de Media para: "{work}".
            Tipo indicado: "{media_type}". Opinión/notas del usuario: "{opinion}".

            Reglas obligatorias:
            1. Lee primero `obsidian://standards/media`.
            2. Busca si ya existe nota en `05_Recursos/Media`.
            3. Si falta identificador externo, búscalo antes de enriquecer:
               - películas/series: IMDb ID correcto;
               - libros: ISBN, autor, editorial, año, páginas y portada.
            4. Para películas/series con `imdb_id`, usa el flujo de Cinemeta
               documentado en el vault o el script de sistema disponible.
            5. Completa YAML y `## Resumen` sin sobrescribir contenido humano.
            6. Integra la opinión en `## Notas Personales`.
            7. No sobrescribas `## Subrayados y Anotaciones` ni citas.

            Al terminar, informa qué nota se actualizó, qué identificadores se
            confirmaron y qué campos quedaron pendientes.
            """

    if prompt_enabled("import_kindle_highlights") and "media" in standards:

        @mcp.prompt(name="import_kindle_highlights")
        def import_kindle_highlights(
            clippings_path: str = "/Volumes/Kindle/documents/My Clippings.txt",
        ) -> str:
            """
            Import Kindle highlights into Secundo Selebro media notes.

            Args:
                clippings_path: Path to My Clippings.txt.
            """
            return f"""
            Importa subrayados y notas desde Kindle USB usando:
            `{clippings_path}`.

            No uses el plugin Kindle de Obsidian. El origen autorizado es el
            filesystem local del Kindle.

            Flujo obligatorio:
            1. Lee `obsidian://standards/media`.
            2. Comprueba que existe `{clippings_path}`.
            3. Ejecuta primero dry-run:
               `00_Sistema/Scripts/media_library_maintenance.py kindle --clippings "{clippings_path}"`
            4. Si el dry-run es correcto, ejecuta el mismo comando con `--apply`.
            5. Revisa libros no emparejados y repórtalos.
            6. Ejecutar dos veces la importación no debe duplicar citas.
            """

    if prompt_enabled("audit_vault") and "organizador" in skills:

        @mcp.prompt(name="audit_vault")
        def audit_vault(scope: str = "vault") -> str:
            """Audit vault health using the organizer skill."""
            return f"""
            Audita la salud de "{scope}".

            Flujo obligatorio:
            1. Lee `obsidian://skills/organizador`.
            2. Lee reglas globales.
            3. Revisa tags, frontmatter, duplicados, huérfanas y ubicación.
            4. No borres ni muevas nada sin confirmación explícita.
            5. Devuelve informe con problemas, impacto y acciones propuestas.
            """

    if prompt_enabled("create_moc") and "explorador" in skills:

        @mcp.prompt(name="create_moc")
        def create_moc(topic: str) -> str:
            """Create or update a Map of Content using the explorer skill."""
            return f"""
            Crea o actualiza un MOC sobre: "{topic}".

            Flujo obligatorio:
            1. Lee `obsidian://skills/explorador`.
            2. Busca notas relevantes y conexiones reales.
            3. Usa backlinks/grafo local cuando aporte contexto.
            4. Organiza enlaces por significado, no como lista plana.
            5. Usa plantilla de MOC si existe.
            """

    if prompt_enabled("process_external_resource") and "procesador" in skills:

        @mcp.prompt(name="process_external_resource")
        def process_external_resource(resource: str, source_type: str = "auto") -> str:
            """Process an external resource into the vault."""
            return f"""
            Procesa este recurso externo: "{resource}".
            Tipo indicado: "{source_type}".

            Flujo obligatorio:
            1. Lee `obsidian://skills/procesador`.
            2. Captura metadata mínima y fuente.
            3. Resume sin inventar contenido.
            4. Decide destino final según las reglas de la skill.
            """

    if prompt_enabled("daily_review") and "revision" in skills:

        @mcp.prompt(name="daily_review")
        def daily_review(date: str = "today") -> str:
            """Create a daily review."""
            return f"""
            Genera revisión diaria para: "{date}".

            Lee `obsidian://skills/revision`, resume actividad reciente,
            integra en el diario si existe y no sobrescribas contenido humano.
            """

    if prompt_enabled("weekly_review") and "revision" in skills:

        @mcp.prompt(name="weekly_review")
        def weekly_review(week: str = "current") -> str:
            """Create a weekly review."""
            return f"""
            Genera revisión semanal para: "{week}".

            Lee `obsidian://skills/revision`, revisa diarios/notas recientes,
            sintetiza logros, aprendizajes y próximos objetivos.
            """

    if prompt_enabled("write_runbook") and "registrador" in skills:

        @mcp.prompt(name="write_runbook")
        def write_runbook(procedure: str) -> str:
            """Write an operational runbook."""
            return f"""
            Documenta este procedimiento operativo: "{procedure}".

            Lee `obsidian://skills/registrador`, busca documentación existente
            antes de crear nada, y escribe contexto, procedimiento y verificación.
            """

    if prompt_enabled("write_changelog") and "registrador" in skills:

        @mcp.prompt(name="write_changelog")
        def write_changelog(project: str) -> str:
            """Write a project changelog."""
            return f"""
            Redacta changelog para: "{project}".

            Lee `obsidian://skills/registrador`, agrupa cambios con formato
            Keep a Changelog y enfoca las entradas en impacto para el usuario.
            """

    if prompt_enabled("document_repository") and "documentador" in skills:

        @mcp.prompt(name="document_repository")
        def document_repository(repository_path: str) -> str:
            """Document a source-code repository."""
            return f"""
            Documenta el repositorio: "{repository_path}".

            Lee `obsidian://skills/documentador`, documenta solo lo que existe
            en el código, agrupa por componente y no inventes descripciones.
            """


def _profile_context() -> tuple[set[str], set[str], set[str]] | None:
    vault_path = get_vault_path()
    if not vault_path:
        return None
    config = get_vault_config(vault_path)
    if not config or config.profile.name != SECUNDO_PROFILE:
        return None

    skills = {
        name
        for name, result in get_cached_skills(str(vault_path)).items()
        if result.success and result.data
    }
    standards = set(config.profile.standards)
    return set(config.profile.prompt_sets), skills, standards
