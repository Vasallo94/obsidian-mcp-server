"""
Skill Generator - Logic for creating and managing skills.

This module contains functions to:
1. Generate new skills with consistent templates
2. Suggest skills based on vault patterns
3. Synchronize and validate existing skills
"""

from datetime import datetime
from textwrap import dedent

from ..config import get_vault_path
from ..result import Result

# Template for new skills
SKILL_TEMPLATE = dedent("""
    ---
    name: {name}
    description: >
      {description}
    tools: [{tools}]
    updated: {date}
    ---

    # {title}

    {description}

    ## Cuándo usar esta skill
    {when_to_use}

    ## Antes de Crear Notas

    > [!CAUTION]
    > **OBLIGATORIO**: Lee y aplica [[.agent/REGLAS_GLOBALES]]
    > antes de crear cualquier nota.

    **Ubicación por defecto:** `{default_location}`

    ## Instrucciones

    {instructions}

    ## REGLA DE ORO DE EDICIÓN
    Cuando uses `editar_nota`, el `nuevo_contenido` debe ser el **ARCHIVO COMPLETO**.
    - **NUNCA** dupliques el bloque YAML.
    - **REEMPLAZA** la metadata anterior con la nueva.
    - Asegura que solo exista un título `#` principal.
""").strip()


def generate_skill(
    nombre: str,
    descripcion: str,
    instrucciones: str,
    herramientas: str = "",
    ubicacion_defecto: str = "",
) -> Result[str]:
    """Generate a new skill with consistent structure.

    Args:
        nombre: Skill identifier (e.g., "profesor-fisica").
        descripcion: Brief description of what the skill does.
        instrucciones: Main instructions in markdown.
        herramientas: Comma-separated tools (e.g., "read, edit, web").
        ubicacion_defecto: Default folder for notes created by this skill.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # Validate name
    nombre_limpio = nombre.lower().strip().replace(" ", "-")
    if not nombre_limpio:
        return Result.fail("El nombre de la skill no puede estar vacío.")

    # Check if skill already exists
    skills_path = vault_path / ".agent" / "skills"
    skill_path = skills_path / nombre_limpio
    skill_file = skill_path / "SKILL.md"

    if skill_file.exists():
        return Result.fail(
            f"Ya existe una skill llamada '{nombre_limpio}'. "
            "Usa `editar_nota` para modificarla."
        )

    # Prepare template values
    tools_list = (
        herramientas.strip() if herramientas else "read, edit, search, obsidian-mcp"
    )

    # Generate human-readable title
    titulo = nombre_limpio.replace("-", " ").title()

    # Auto-generate "when to use" based on description
    when_to_use = (
        f"- Cuando el usuario necesite: {descripcion.lower()}\n"
        "- Cuando se mencione este tema o contexto específico."
    )

    # Default location
    ubicacion = ubicacion_defecto if ubicacion_defecto else "02_Aprendizaje/"

    # Build skill content
    fecha = datetime.now().strftime("%Y-%m-%d")
    skill_content = SKILL_TEMPLATE.format(
        name=nombre_limpio,
        description=descripcion,
        tools=tools_list,
        date=fecha,
        title=titulo,
        when_to_use=when_to_use,
        default_location=ubicacion,
        instructions=instrucciones,
    )

    # Create skill directory and file
    skill_path.mkdir(parents=True, exist_ok=True)
    skill_file.write_text(skill_content, encoding="utf-8")

    return Result.ok(
        f"Skill creada: **{titulo}**\n"
        f"📍 Ubicación: `.agent/skills/{nombre_limpio}/SKILL.md`\n\n"
        "La skill ya está disponible. Usa `listar_agentes()` para verla."
    )


def suggest_skills_for_vault() -> Result[str]:
    """Analyze vault and suggest personalized skills.

    Returns:
        Result with suggestions or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    # Collect statistics
    tag_counts: dict[str, int] = {}
    folder_counts: dict[str, int] = {}
    total_notes = 0

    # Excluded folders
    excluded = {".git", ".obsidian", ".trash", ".agent", "node_modules"}

    for md_file in vault_path.rglob("*.md"):
        # Skip excluded
        if any(excl in md_file.parts for excl in excluded):
            continue

        total_notes += 1

        # Count by top-level folder
        try:
            rel_path = md_file.relative_to(vault_path)
            if len(rel_path.parts) > 1:
                top_folder = rel_path.parts[0]
                folder_counts[top_folder] = folder_counts.get(top_folder, 0) + 1
        except ValueError:
            pass

        # Extract tags from content
        try:
            content = md_file.read_text(encoding="utf-8")
            import re

            # Inline tags
            inline_tags = re.findall(r"#([a-zA-ZáéíóúñÁÉÍÓÚÑ][a-zA-Z0-9_-]*)", content)
            for tag in inline_tags:
                tag_lower = tag.lower()
                tag_counts[tag_lower] = tag_counts.get(tag_lower, 0) + 1

            # YAML tags
            if content.startswith("---"):
                yaml_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
                if yaml_match:
                    yaml_section = yaml_match.group(1)
                    tags_match = re.search(r"tags:\s*\[([^\]]+)\]", yaml_section)
                    if tags_match:
                        yaml_tags = [
                            t.strip().lower() for t in tags_match.group(1).split(",")
                        ]
                        for tag in yaml_tags:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        except Exception:  # nosec B112
            continue

    # Analyze patterns and suggest skills

    # Sort by frequency
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_folders = sorted(folder_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Generate suggestions based on patterns
    skill_ideas = _generate_skill_ideas(top_tags, top_folders)

    # Build output
    output = f"📊 **Análisis del Vault** ({total_notes} notas)\n\n"

    output += "📁 **Carpetas con más contenido:**\n"
    for folder, count in top_folders[:5]:
        output += f"- `{folder}/` ({count} notas)\n"

    output += "\n🏷️ **Tags más frecuentes:**\n"
    for tag, count in top_tags[:10]:
        output += f"- #{tag} ({count})\n"

    if skill_ideas:
        output += "\n💡 **Skills sugeridas:**\n\n"
        for i, idea in enumerate(skill_ideas, 1):
            output += (
                f"{i}. **{idea['name']}**\n"
                f"   {idea['description']}\n"
                f"   _Basado en: {idea['based_on']}_\n\n"
            )
        output += (
            "¿Quieres que genere alguna de estas skills? "
            "Usa `generar_skill(nombre, descripcion, instrucciones)`."
        )
    else:
        output += (
            "\n💡 No detecté patrones claros para sugerir skills automáticamente. "
            "Puedes crear una manualmente con `generar_skill()`."
        )

    return Result.ok(output)


def _generate_skill_ideas(
    top_tags: list[tuple[str, int]],
    top_folders: list[tuple[str, int]],
) -> list[dict[str, str]]:
    """Generate skill ideas based on detected patterns."""
    ideas: list[dict[str, str]] = []

    # Tag-based suggestions
    tag_skill_map = {
        "física": {
            "name": "profesor-fisica",
            "description": "Explica conceptos de física con fórmulas LaTeX y diagramas",
        },
        "python": {
            "name": "pythonista",
            "description": "Genera código Python limpio y documentado",
        },
        "poesía": {
            "name": "poeta",
            "description": "Crea poesía siguiendo tu estilo personal",
        },
        "poema": {
            "name": "poeta",
            "description": "Crea poesía siguiendo tu estilo personal",
        },
        "ia": {
            "name": "experto-ia",
            "description": "Explica conceptos de IA/ML de forma clara",
        },
        "reflexión": {
            "name": "filosofo",
            "description": "Guía reflexiones profundas y ensayos filosóficos",
        },
        "diario": {
            "name": "compañero-diario",
            "description": "Ayuda con entradas de diario y reflexión personal",
        },
    }

    seen_skills: set[str] = set()

    for tag, count in top_tags:
        if count >= 5 and tag in tag_skill_map:
            skill = tag_skill_map[tag]
            if skill["name"] not in seen_skills:
                ideas.append(
                    {
                        "name": skill["name"],
                        "description": skill["description"],
                        "based_on": f"#{tag} ({count} usos)",
                    }
                )
                seen_skills.add(skill["name"])

    return ideas[:5]  # Limit to 5 suggestions


def sync_skills(actualizar: bool = False) -> Result[str]:
    """Synchronize and validate existing skills.

    Args:
        actualizar: If True, apply fixes. If False, only report.

    Returns:
        Result with sync report or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no está configurada.")

    skills_path = vault_path / ".agent" / "skills"
    if not skills_path.exists():
        return Result.fail("No existe la carpeta `.agent/skills/`.")

    issues: list[dict[str, str | bool]] = []
    fixed: list[str] = []

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            issues.append(
                {
                    "skill": skill_dir.name,
                    "issue": "Falta archivo SKILL.md",
                    "fixable": False,
                }
            )
            continue

        content = skill_file.read_text(encoding="utf-8")

        # Check for REGLAS_GLOBALES reference
        if "REGLAS_GLOBALES" not in content:
            issues.append(
                {
                    "skill": skill_dir.name,
                    "issue": "Falta referencia a REGLAS_GLOBALES",
                    "fixable": True,
                }
            )
            if actualizar:
                # Add the caution block after the first heading
                import re

                new_content = re.sub(
                    r"(^# .+\n)",
                    r"\1\n> [!CAUTION]\n> **OBLIGATORIO**: Lee y aplica "
                    r"[[.agent/REGLAS_GLOBALES]] antes de crear notas.\n\n",
                    content,
                    count=1,
                    flags=re.MULTILINE,
                )
                skill_file.write_text(new_content, encoding="utf-8")
                fixed.append(skill_dir.name)

        # Check for REGLA DE ORO
        if "REGLA DE ORO" not in content:
            issues.append(
                {
                    "skill": skill_dir.name,
                    "issue": "Falta sección 'REGLA DE ORO DE EDICIÓN'",
                    "fixable": True,
                }
            )
            if actualizar:
                # Append the golden rule
                golden_rule = dedent("""

                    ## REGLA DE ORO DE EDICIÓN
                    Cuando uses `editar_nota`, el `nuevo_contenido`
                    debe ser el **ARCHIVO COMPLETO**.
                    - **NUNCA** dupliques el bloque YAML.
                    - **REEMPLAZA** la metadata anterior.
                """).strip()
                skill_file.write_text(content + "\n\n" + golden_rule, encoding="utf-8")
                if skill_dir.name not in fixed:
                    fixed.append(skill_dir.name)

    # Build report
    if not issues:
        return Result.ok("✅ Todas las skills están sincronizadas correctamente.")

    output = f"📋 **Reporte de sincronización** ({len(issues)} problemas)\n\n"

    for issue in issues:
        status = "🔧" if issue.get("fixable") else "⚠️"
        output += f"{status} **{issue['skill']}**: {issue['issue']}\n"

    if actualizar and fixed:
        output += f"\n✅ Corregidas: {', '.join(fixed)}"
    elif not actualizar and any(i.get("fixable") for i in issues):
        output += (
            "\n💡 Ejecuta `sincronizar_skills(actualizar=True)` "
            "para aplicar correcciones."
        )

    return Result.ok(output)
