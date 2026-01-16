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

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fastmcp import FastMCP
from pydantic import BaseModel, ValidationError

from ..config import get_vault_path

# ============================================================================
# Schema de Skill (Pydantic)
# ============================================================================


class SkillMetadata(BaseModel):
    """Schema para validar el frontmatter YAML de una Skill."""

    name: str
    description: str
    tools: list[str] | None = None


class SkillInfo(BaseModel):
    """Información completa de una skill, incluyendo metadata y contenido."""

    folder_name: str
    metadata: SkillMetadata
    body: str  # Contenido Markdown sin el frontmatter


# ============================================================================
# Parsing de SKILL.md
# ============================================================================

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_skill_file(skill_path: Path) -> SkillInfo | str:
    """
    Parsea un archivo SKILL.md extrayendo metadata y cuerpo.

    Retorna un SkillInfo si es válido, o un string con el error.
    """
    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error leyendo archivo: {e}"

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return "El archivo no tiene YAML frontmatter válido (---...---)"

    yaml_raw = match.group(1)
    body = content[match.end() :]

    try:
        yaml_data = yaml.safe_load(yaml_raw)
    except yaml.YAMLError as e:
        return f"Error parseando YAML: {e}"

    if not isinstance(yaml_data, dict):
        return "El frontmatter no es un diccionario válido"

    try:
        metadata = SkillMetadata(**yaml_data)
    except ValidationError as e:
        errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        return f"Schema inválido: {errors}"

    return SkillInfo(
        folder_name=skill_path.parent.name,
        metadata=metadata,
        body=body.strip(),
    )


# ============================================================================
# Caché de Skills
# ============================================================================


@lru_cache(maxsize=1)
def _get_cached_skills(vault_path_str: str) -> dict[str, SkillInfo | str]:
    """
    Escanea y cachea todas las skills del vault.
    El caché se invalida si cambia vault_path_str.
    """
    vault_path = Path(vault_path_str)
    skills_path = vault_path / ".agent" / "skills"

    if not skills_path.exists():
        return {}

    results: dict[str, SkillInfo | str] = {}
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                results[skill_dir.name] = parse_skill_file(skill_file)

    return results


def invalidate_skills_cache() -> None:
    """Invalida el caché de skills (útil tras crear/editar skills)."""
    _get_cached_skills.cache_clear()


# ============================================================================
# Registro de Herramientas MCP
# ============================================================================


def register_agent_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas y recursos de gestión de skills (agentes).
    """

    @mcp.resource("skills://list")
    def resource_listar_skills() -> str:
        """Recurso que devuelve la lista de skills disponibles."""
        return listar_skills_logic()

    @mcp.tool()
    def listar_agentes() -> str:
        """Lista las skills (agentes) disponibles en el vault."""
        return listar_skills_logic()

    def listar_skills_logic() -> str:
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            skills = _get_cached_skills(str(vault_path))

            if not skills:
                return f"ℹ️ No se encontraron skills en {vault_path}/.agent/skills/"

            # Construir respuesta estructurada
            valid_skills: list[dict[str, Any]] = []
            invalid_skills: list[str] = []

            for name, result in sorted(skills.items()):
                if isinstance(result, SkillInfo):
                    valid_skills.append(
                        {
                            "name": result.metadata.name,
                            "folder": name,
                            "description": result.metadata.description,
                            "tools": result.metadata.tools or [],
                        }
                    )
                else:
                    invalid_skills.append(f"⚠️ {name}: {result}")

            output_parts = ["🤖 **Skills Disponibles:**\n"]

            for skill in valid_skills:
                output_parts.append(
                    f"- **{skill['name']}** (`{skill['folder']}`)\n"
                    f"  _{skill['description']}_"
                )

            if invalid_skills:
                output_parts.append("\n**Skills con errores:**")
                output_parts.extend(invalid_skills)

            return "\n".join(output_parts)

        except Exception as e:
            return f"❌ Error: {e}"

    @mcp.tool()
    def obtener_instrucciones_agente(nombre: str) -> str:
        """
        Obtiene el contenido de una Skill específica (SKILL.md).

        Args:
            nombre: El nombre de la carpeta de la skill (ej: 'escritor').
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            skills = _get_cached_skills(str(vault_path))

            if nombre not in skills:
                available = ", ".join(sorted(skills.keys())) or "ninguna"
                return f"❌ Skill '{nombre}' no encontrada. Disponibles: {available}"

            result = skills[nombre]

            if isinstance(result, str):
                return f"❌ Error en skill '{nombre}': {result}"

            # Construir respuesta con metadata estructurada + cuerpo
            header = (
                f"📄 **Skill: {result.metadata.name}**\n\n"
                f"**Descripción**: {result.metadata.description}\n"
            )
            if result.metadata.tools:
                header += f"**Herramientas**: {', '.join(result.metadata.tools)}\n"

            return f"{header}\n---\n\n{result.body}"

        except Exception as e:
            return f"❌ Error: {e}"

    @mcp.tool()
    def obtener_reglas_globales() -> str:
        """Obtiene las reglas globales (si existen)."""
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            # Nueva ubicación preferida: .agent/REGLAS_GLOBALES.md
            new_rules_path = vault_path / ".agent" / "REGLAS_GLOBALES.md"

            # Fallback a ubicación legacy
            legacy_rules_path = vault_path / ".github" / "copilot-instructions.md"

            rules_path = None
            if new_rules_path.exists():
                rules_path = new_rules_path
            elif legacy_rules_path.exists():
                rules_path = legacy_rules_path

            if not rules_path:
                return (
                    "ℹ️ No se encontraron reglas globales (.agent/REGLAS_GLOBALES.md)."
                )

            contenido = rules_path.read_text(encoding="utf-8")
            location = "📍 " + str(rules_path.relative_to(vault_path))

            return f"📜 **Reglas Globales** {location}\n\n{contenido}"

        except Exception as e:
            return f"❌ Error: {e}"

    @mcp.tool()
    def refrescar_cache_skills() -> str:
        """Invalida y refresca el caché de skills (úsalo tras editar SKILL.md)."""
        invalidate_skills_cache()
        return (
            "✅ Caché de skills invalidado. La próxima consulta recargará las skills."
        )
