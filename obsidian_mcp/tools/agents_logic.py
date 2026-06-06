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
    skills_path = vault_path / ".agents" / "skills"

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
                f"ℹ️ No se encontraron skills en {vault_path}/.agents/skills/"
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

        new_rules_path = vault_path / ".agents" / "REGLAS_GLOBALES.md"
        legacy_rules_path = vault_path / ".github" / "copilot-instructions.md"

        rules_path = None
        if new_rules_path.exists():
            rules_path = new_rules_path
        elif legacy_rules_path.exists():
            rules_path = legacy_rules_path

        if not rules_path:
            return Result.ok(
                "ℹ️ No se encontraron reglas globales (.agents/REGLAS_GLOBALES.md)."
            )

        contenido = rules_path.read_text(encoding="utf-8")
        location = "📍 " + str(rules_path.relative_to(vault_path))

        return Result.ok(f"📜 **Reglas Globales** {location}\n\n{contenido}")

    except OSError as e:
        return Result.fail(f"Error: {e}")


def add_global_rule(rule_text: str) -> Result[str]:
    """Append a human-readable rule to the vault's global rules file.

    Lets an agent register a rule the user dictated (e.g. "no hard-wrap of
    markdown") without giving it raw file access to ``.agents/`` (AFP issue
    #52). The rule is appended as a bullet to the prose body of
    REGLAS_GLOBALES.md; the machine-readable ``validations`` frontmatter is
    left untouched. Caller is responsible for human confirmation.

    Args:
        rule_text: The rule to register. Bullet/number prefixes are optional.

    Returns:
        Result with a confirmation message and the file location.
    """
    from ..middleware import invalidate_rules_cache

    cleaned = rule_text.strip()
    if not cleaned:
        return Result.fail("La regla está vacía.")

    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # Normalize to a single bullet item unless the user already formatted it.
    bullet = cleaned
    if not re.match(r"^([-*]|\d+[.)])\s", cleaned):
        bullet = f"- {cleaned}"

    rules_path = vault_path / ".agents" / "REGLAS_GLOBALES.md"

    try:
        if rules_path.exists():
            existing = rules_path.read_text(encoding="utf-8")
            separator = "" if existing.endswith("\n") else "\n"
            rules_path.write_text(f"{existing}{separator}{bullet}\n", encoding="utf-8")
        else:
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            rules_path.write_text(
                f"# Reglas Globales del Vault\n\n{bullet}\n",
                encoding="utf-8",
            )
    except OSError as e:
        return Result.fail(f"No se pudo escribir el fichero de reglas: {e}")

    invalidate_rules_cache()

    location = str(rules_path.relative_to(vault_path))
    return Result.ok(f"Regla añadida a {location}:\n{bullet}")


def refresh_skills_cache() -> Result[str]:
    """Invalidate and refresh existing skills cache."""
    invalidate_skills_cache()
    return Result.ok(
        "✅ Caché de skills invalidado. La próxima consulta recargará las skills."
    )


def validate_note_logic(
    title: str = "",
    content: str = "",
    mode: str = "create",
) -> Result[str]:
    """Run vault rules against arbitrary content without writing.

    Lets agents lint a note before calling create_note / patch_note so they
    can fix violations in-context instead of round-tripping through a write.

    Args:
        title: Note title (used by rules with scope='title').
        content: Full note body, optionally including YAML frontmatter.
        mode: One of 'create', 'edit', 'append'. Determines which rules apply.

    Returns:
        Result with a JSON summary {valid, mode, violations[]}.
    """
    import json

    from ..middleware import load_vault_rules, run_validations
    from .creation_logic import _extract_frontmatter_from_content

    if mode not in {"create", "edit", "append"}:
        return Result.fail(
            f"mode debe ser uno de: create, edit, append (recibido: '{mode}')."
        )

    frontmatter, body = _extract_frontmatter_from_content(content)
    rules = load_vault_rules()
    warnings = run_validations(
        rules,
        mode=mode,
        title=title,
        content=body if frontmatter else content,
        frontmatter=frontmatter,
    )

    payload: dict[str, Any] = {
        "valid": not warnings,
        "mode": mode,
        "violations": warnings,
    }
    return Result.ok(json.dumps(payload, ensure_ascii=False, indent=2))
