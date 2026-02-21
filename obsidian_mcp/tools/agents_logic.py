"""
Core business logic for agent skills management.

This module handles parsing, caching, and retrieving agent skills and global rules.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from ..config import get_vault_path
from ..result import Result

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


def parse_skill_file(skill_path: Path) -> Result[SkillInfo]:
    """
    Parsea un archivo SKILL.md extrayendo metadata y cuerpo.

    Retorna Result[SkillInfo] si es válido, o Result.fail con el error.
    """
    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError as e:
        return Result.fail(f"Error leyendo archivo: {e}")

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return Result.fail("El archivo no tiene YAML frontmatter válido (---...---)")

    yaml_raw = match.group(1)
    body = content[match.end() :]

    try:
        yaml_data = yaml.safe_load(yaml_raw)
    except yaml.YAMLError as e:
        return Result.fail(f"Error parseando YAML: {e}")

    if not isinstance(yaml_data, dict):
        return Result.fail("El frontmatter no es un diccionario válido")

    try:
        metadata = SkillMetadata(**yaml_data)
    except ValidationError as e:
        errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        return Result.fail(f"Schema inválido: {errors}")

    return Result.ok(
        SkillInfo(
            folder_name=skill_path.parent.name,
            metadata=metadata,
            body=body.strip(),
        )
    )


# ============================================================================
# Caché de Skills
# ============================================================================


@lru_cache(maxsize=1)
def get_cached_skills(vault_path_str: str) -> dict[str, Result[SkillInfo]]:
    """
    Escanea y cachea todas las skills del vault.
    El caché se invalida si cambia vault_path_str.
    """
    vault_path = Path(vault_path_str)
    skills_path = vault_path / ".agent" / "skills"

    if not skills_path.exists():
        return {}

    results: dict[str, Result[SkillInfo]] = {}
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                results[skill_dir.name] = parse_skill_file(skill_file)

    return results


def invalidate_skills_cache() -> None:
    """Invalida el caché de skills (útil tras crear/editar skills)."""
    get_cached_skills.cache_clear()


# ============================================================================
# Business Logic Functions
# ============================================================================


def list_available_skills() -> Result[str]:
    """List available skills (agents) in the vault."""
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        skills = get_cached_skills(str(vault_path))

        if not skills:
            return Result.ok(
                f"ℹ️ No se encontraron skills en {vault_path}/.agent/skills/"
            )

        # Construir respuesta estructurada
        valid_skills: list[dict[str, Any]] = []
        invalid_skills: list[str] = []

        for name, result in sorted(skills.items()):
            if result.success and result.data:
                valid_skills.append(
                    {
                        "name": result.data.metadata.name,
                        "folder": name,
                        "description": result.data.metadata.description,
                        "tools": result.data.metadata.tools or [],
                    }
                )
            else:
                invalid_skills.append(f"⚠️ {name}: {result.error}")

        output_parts = ["🤖 **Skills Disponibles:**\n"]

        for skill in valid_skills:
            output_parts.append(
                f"- **{skill['name']}** (`{skill['folder']}`)\n"
                f"  _{skill['description']}_"
            )

        if invalid_skills:
            output_parts.append("\n**Skills con errores:**")
            output_parts.extend(invalid_skills)

        return Result.ok("\n".join(output_parts))

    except (OSError, ValueError) as e:
        return Result.fail(f"Error: {e}")


def get_agent_instructions(nombre: str) -> Result[str]:
    """Get the content of a specific Skill (SKILL.md)."""
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        skills = get_cached_skills(str(vault_path))

        if nombre not in skills:
            available = ", ".join(sorted(skills.keys())) or "ninguna"
            return Result.fail(
                f"Skill '{nombre}' no encontrada. Disponibles: {available}"
            )

        result = skills[nombre]

        if not result.success or not result.data:
            return Result.fail(f"Error en skill '{nombre}': {result.error}")

        skill_info = result.data

        # Construir respuesta con metadata estructurada + cuerpo
        header = (
            f"📄 **Skill: {skill_info.metadata.name}**\n\n"
            f"**Descripción**: {skill_info.metadata.description}\n"
        )
        if skill_info.metadata.tools:
            header += f"**Herramientas**: {', '.join(skill_info.metadata.tools)}\n"

        return Result.ok(f"{header}\n---\n\n{skill_info.body}")

    except (OSError, ValueError) as e:
        return Result.fail(f"Error: {e}")


def get_global_rules() -> Result[str]:
    """Get global rules from the Agent configuration."""
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("La ruta del vault no está configurada.")

        new_rules_path = vault_path / ".agent" / "REGLAS_GLOBALES.md"
        legacy_rules_path = vault_path / ".github" / "copilot-instructions.md"

        rules_path = None
        if new_rules_path.exists():
            rules_path = new_rules_path
        elif legacy_rules_path.exists():
            rules_path = legacy_rules_path

        if not rules_path:
            return Result.ok(
                "ℹ️ No se encontraron reglas globales (.agent/REGLAS_GLOBALES.md)."
            )

        contenido = rules_path.read_text(encoding="utf-8")
        location = "📍 " + str(rules_path.relative_to(vault_path))

        return Result.ok(f"📜 **Reglas Globales** {location}\n\n{contenido}")

    except OSError as e:
        return Result.fail(f"Error: {e}")


def refresh_skills_cache() -> Result[str]:
    """Invalidate and refresh existing skills cache."""
    invalidate_skills_cache()
    return Result.ok(
        "✅ Caché de skills invalidado. La próxima consulta recargará las skills."
    )
