"""
Core business logic for context tools.

This module contains the implementation of context gathering operations,
separated from the MCP tool registration.
"""

from pathlib import Path
from typing import Dict, Optional, TypedDict

from ..config import get_vault_path
from ..result import Result
from ..utils import extract_tags_from_content, get_logger
from ..vault_config import VaultConfig, get_vault_config
from .agents_logic import get_cached_skills
from .registry import enabled_tool_sets

logger = get_logger(__name__)


def _collect_folder_structure(vault_path: Path) -> list[str]:
    """Collect top-level folder structure with immediate subfolders."""
    excluded = {
        ".git",
        ".obsidian",
        ".trash",
        ".gemini",
        ".space",
        ".makemd",
        ".obsidianrag",
        ".agents",
    }
    structure = []

    for item in sorted(vault_path.iterdir()):
        if not item.is_dir() or item.name in excluded or item.name.startswith("."):
            continue

        subfolders = []
        try:
            for sub in sorted(item.iterdir()):
                if sub.is_dir() and not sub.name.startswith("."):
                    subfolders.append(sub.name)
        except PermissionError:
            pass

        desc = f"📂 {item.name}"
        if subfolders:
            names = ", ".join(subfolders[:5])
            if len(subfolders) > 5:
                desc += f" (includes: {names}, ...)"
            else:
                desc += f" (includes: {names})"
        structure.append(desc)

    return structure


def _collect_templates(
    vault_path: Path,
    config: Optional[VaultConfig],
) -> tuple[Optional[str], list[str]]:
    """Find template folder and list available templates."""
    templates_folder: Optional[str] = None

    if config and config.templates_folder:
        templates_folder = config.templates_folder
    else:
        for item in vault_path.iterdir():
            if item.is_dir() and any(
                t in item.name.lower() for t in ["plantilla", "template", "templates"]
            ):
                templates_folder = item.name
                break

    templates: list[str] = []
    if templates_folder:
        plantillas_path = vault_path / templates_folder
        if plantillas_path.exists():
            templates = [item.stem for item in sorted(plantillas_path.glob("*.md"))]

    return templates_folder, templates


def _collect_common_tags(vault_path: Path) -> str:
    """Sample up to 100 notes and return top 20 tags as a formatted string."""
    counts: Dict[str, int] = {}
    count = 0

    for archivo in vault_path.rglob("*.md"):
        if count >= 100:
            break
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                tags = extract_tags_from_content(f.read())
                for tag in tags:
                    counts[tag] = counts.get(tag, 0) + 1
            count += 1
        except OSError as e:
            logger.debug("Could not read '%s': %s", archivo, e)
            continue

    top_tags = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
    return ", ".join(f"#{t}" for t, _ in top_tags)


def _collect_agent_context(vault_path: Path) -> list[str]:
    """Collect information about the .agents folder structure."""
    agent_path = vault_path / ".agents"
    if not agent_path.exists() or not agent_path.is_dir():
        return [
            "⚠️ .agents folder not found",
            "  -> Suggestion: read the setup documentation to configure "
            "vault skills and rules.",
        ]

    info = ["✅ .agents folder found."]
    for item in sorted(agent_path.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            subitems = [s.name for s in item.iterdir() if not s.name.startswith(".")]
            desc = f"  - 📂 {item.name}/"
            if subitems:
                names = ", ".join(subitems[:5])
                suffix = "..." if len(subitems) > 5 else ""
                desc += f" ({names}{suffix})"
            info.append(desc)
        else:
            info.append(f"  - 📄 {item.name}")

    return info


def read_vault_context() -> Result[str]:
    """
    Read general vault structure and key statistics.

    Returns:
        Result with formatted context report string.
    """
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("Vault path is not configured.")

        config = get_vault_config(vault_path)

        structure = _collect_folder_structure(vault_path)
        templates_folder, templates = _collect_templates(vault_path, config)
        tags_str = _collect_common_tags(vault_path)
        agent_info = _collect_agent_context(vault_path)

        # Build report
        report = "# Vault Context\n\n"

        report += "## 📂 Main Structure\n"
        report += "\n".join(structure) + "\n\n"

        if templates_folder:
            report += f"## 📝 Available Templates (in {templates_folder})\n"
            if templates:
                report += ", ".join(templates) + "\n\n"
            else:
                report += f"No templates found in {templates_folder}.\n\n"
        else:
            report += "## 📝 Templates\n"
            report += "No templates folder detected.\n\n"

        report += "## 🏷️ Common Tags (Sample)\n"
        if tags_str:
            report += tags_str + "\n\n"
        else:
            report += "No common tags detected.\n\n"

        report += "## 🤖 Agent Context (.agents)\n"
        report += "\n".join(agent_info) + "\n"

        return Result.ok(report)

    except OSError as e:
        return Result.fail(f"Error reading vault context: {e}")


def build_vault_health_report() -> Result[str]:
    """Build a health report for the active vault and MCP profile."""
    try:
        vault_path = get_vault_path()
        checks: list[tuple[str, bool, str]] = []

        if not vault_path:
            return Result.fail("Vault path is not configured.")

        checks.append(("vault_path_configured", True, str(vault_path)))
        checks.append(("vault_path_exists", vault_path.exists(), str(vault_path)))
        checks.append(("vault_path_is_directory", vault_path.is_dir(), str(vault_path)))
        if not vault_path.exists() or not vault_path.is_dir():
            return Result.ok(_render_health_report(checks))

        config = get_vault_config(vault_path)
        checks.append(
            ("vault_config_present", config is not None, ".agents/vault.yaml")
        )

        if config:
            templates_ok = bool(
                config.templates_folder
                and (vault_path / config.templates_folder).is_dir()
            )
            checks.append(
                (
                    "templates_folder_available",
                    templates_ok,
                    config.templates_folder or "not configured",
                )
            )
            checks.append(
                (
                    "profile_configured",
                    bool(config.profile.name),
                    config.profile.name or "not configured",
                )
            )
            checks.extend(
                _check_declared_files(vault_path, "standard", config.profile.standards)
            )
            checks.extend(
                _check_declared_files(
                    vault_path, "local_doc", config.profile.local_docs
                )
            )
            checks.extend(
                _check_declared_integrations(vault_path, config.profile.integrations)
            )
        else:
            checks.append(("templates_folder_available", False, "vault config missing"))
            checks.append(("profile_configured", False, "vault config missing"))

        skills_dir = vault_path / ".agents" / "skills"
        valid_skills = 0
        invalid_skills = 0
        if skills_dir.is_dir():
            for result in get_cached_skills(str(vault_path)).values():
                if result.success and result.data:
                    valid_skills += 1
                else:
                    invalid_skills += 1

        checks.append(
            ("skills_directory_present", skills_dir.is_dir(), str(skills_dir))
        )
        checks.append(("valid_skills_found", valid_skills > 0, str(valid_skills)))
        checks.append(
            ("invalid_skills_found", invalid_skills == 0, str(invalid_skills))
        )

        return Result.ok(_render_health_report(checks))

    except OSError as e:
        return Result.fail(f"Error building vault health report: {e}")


def diagnose_vault_setup_report() -> Result[str]:
    """Build a concise setup diagnosis with recommendations."""
    health = build_vault_health_report()
    if not health.success:
        return health

    report = health.data or ""
    recommendations: list[str] = []
    for line in report.splitlines():
        if line.startswith("- ❌"):
            if "vault_config_present" in line:
                recommendations.append(
                    "Create `.agents/vault.yaml` to enable profile config."
                )
            elif "templates_folder_available" in line:
                recommendations.append(
                    "Configure a valid `templates_folder` in `.agents/vault.yaml`."
                )
            elif "profile_configured" in line:
                recommendations.append(
                    "Set `profile.name` if this vault has custom behavior."
                )
            elif "skills_directory_present" in line:
                recommendations.append(
                    "Create `.agents/skills` if you want skill resources."
                )
            elif "valid_skills_found" in line:
                recommendations.append(
                    "Add at least one valid `.agents/skills/<name>/SKILL.md`."
                )
            elif "invalid_skills_found" in line:
                recommendations.append(
                    "Run `skills.sync(update=False)` to inspect invalid skills."
                )
            elif "standard:" in line:
                recommendations.append(
                    "Fix declared profile standard paths or remove stale entries."
                )
            elif "local_doc:" in line:
                recommendations.append(
                    "Fix declared local doc paths or remove stale entries."
                )

    output = "# Vault Setup Diagnosis\n\n"
    output += report
    output += "\n\n## Recommendations\n"
    if recommendations:
        output += "\n".join(f"- {item}" for item in dict.fromkeys(recommendations))
    else:
        output += "- No setup issues detected."
    return Result.ok(output)


def route_task_request(request: str) -> Result[str]:
    """Suggest the best MCP prompt, skill, and tool route for a task."""
    try:
        vault_path = get_vault_path()
        if not vault_path:
            return Result.fail("Vault path is not configured.")

        config = get_vault_config(vault_path)
        prompt_sets = set(config.profile.prompt_sets) if config else set()
        tool_sets = enabled_tool_sets()
        standards = set(config.profile.standards) if config else set()
        integrations = set(config.profile.integrations) if config else set()
        skills = {
            name
            for name, result in get_cached_skills(str(vault_path)).items()
            if result.success and result.data
        }

        route = _infer_route(
            request=request,
            skills=skills,
            standards=standards,
            prompt_sets=prompt_sets,
            tool_sets=tool_sets,
            integrations=integrations,
        )

        output = "# Task Route\n\n"
        output += f"Request: {request}\n\n"
        output += f"- Recommended prompt: `{route['prompt']}`\n"
        output += f"- Recommended skill: `{route['skill']}`\n"
        output += f"- Primary tools/resources: {', '.join(route['tools'])}\n"
        output += "\n## Steps\n"
        output += "\n".join(
            f"{index}. {step}" for index, step in enumerate(route["steps"], 1)
        )
        output += "\n\n## Notes\n"
        output += route["notes"]
        return Result.ok(output)

    except OSError as e:
        return Result.fail(f"Error routing task: {e}")


def _check_declared_files(
    vault_path: Path,
    prefix: str,
    entries: dict[str, str],
) -> list[tuple[str, bool, str]]:
    checks = []
    for name, relative in sorted(entries.items()):
        path = vault_path / relative
        checks.append((f"{prefix}:{name}", path.is_file(), relative))
    return checks


def _check_declared_integrations(
    vault_path: Path,
    integrations: dict[str, dict[str, object]],
) -> list[tuple[str, bool, str]]:
    checks = []
    for name, config in sorted(integrations.items()):
        project_path = str(config.get("project_path") or "")
        if not project_path:
            checks.append((f"integration:{name}:path", False, "project_path missing"))
            continue
        path = Path(project_path)
        if not path.is_absolute():
            path = vault_path / path
        checks.append((f"integration:{name}:path", path.exists(), str(path)))
        api_url = str(config.get("api_url") or "")
        if api_url:
            checks.append((f"integration:{name}:api_url", True, api_url))
    return checks


class TaskRoute(TypedDict):
    prompt: str
    skill: str
    tools: list[str]
    steps: list[str]
    notes: str


def _infer_route(
    request: str,
    skills: set[str],
    standards: set[str],
    prompt_sets: set[str],
    tool_sets: set[str],
    integrations: set[str],
) -> TaskRoute:
    text = request.casefold()

    is_search_request = _has_any(
        text,
        ["busca", "buscar", "encuentra", "recuerdo", "semánt", "semantic", "pregunta"],
    )
    is_media_update_request = _has_any(
        text,
        [
            "actualiza",
            "actualizar",
            "importa",
            "importar",
            "sincroniza",
            "rellena",
            "completa",
        ],
    )

    if is_search_request and not is_media_update_request:
        tools = ["obsidian://capabilities"]
        notes = (
            "Use text search and note reading unless an external RAG pack is enabled."
        )
        if "obsidianrag" in integrations or "obsidianrag" in tool_sets:
            tools.extend(["rag_health", "ask_vault", "ObsidianRAG"])
            notes = (
                "Use ObsidianRAG for natural-language vault QA. Run `rag.health` first; "
                "if the backend is offline, read `obsidian://integrations/obsidianrag/setup`."
            )
        return _route(
            "explore_vault_context",
            "explorador" if "explorador" in skills else "none",
            tools,
            [
                "Check capabilities and active RAG integration.",
                "Use ObsidianRAG for semantic search when available.",
                "Read candidate notes before answering.",
            ],
            notes,
        )

    if _has_any(text, ["película", "pelicula", "serie", "libro", "kindle", "media"]):
        if "kindle" in text:
            return _route(
                "import_kindle_highlights",
                "procesador" if "procesador" in skills else "none",
                [
                    "obsidian://standards/media",
                    "00_Sistema/Scripts/media_library_maintenance.py",
                ],
                [
                    "Read the media standard.",
                    "Run the Kindle import dry-run.",
                    "Apply only if the dry-run is clean.",
                    "Report unmatched books.",
                ],
                "Uses the Secundo Selebro media workflow when the media standard is declared.",
            )
        return _route(
            "update_media_item",
            "procesador" if "procesador" in skills else "none",
            ["obsidian://standards/media", "web lookup", "Cinemeta enrichment"],
            [
                "Search the vault for an existing media note.",
                "Resolve IMDb ID or book references before enrichment.",
                "Update YAML and summaries without overwriting human notes.",
            ],
            "Best for canonical Media library updates.",
        )

    if _has_any(text, ["moc", "mapa de contenido", "índice", "indice"]):
        return _route(
            "create_moc",
            "explorador" if "explorador" in skills else "none",
            ["obsidian://skills/explorador", "get_local_graph"],
            [
                "Read the explorer skill.",
                "Find relevant notes and graph context.",
                "Create or update the MOC with grouped links.",
            ],
            "Use only when the user wants durable organization, not a one-off search.",
        )

    if _has_any(text, ["diagrama", "mermaid", "arquitectura"]):
        prompt = (
            "create_mermaid_diagram"
            if "mermaid" in prompt_sets
            else "assistant_overview"
        )
        return _route(
            prompt,
            "diagrama-arquitectura" if "diagrama-arquitectura" in skills else "none",
            ["obsidian://skills/diagrama-arquitectura"],
            [
                "Read diagram conventions if the skill exists.",
                "Generate Obsidian-safe Mermaid.",
                "Avoid syntax known to break Obsidian rendering.",
            ],
            "The public Mermaid pack is optional and enabled per vault profile.",
        )

    if _has_any(
        text, ["audita", "limpia", "organiza", "duplicad", "frontmatter", "tags"]
    ):
        return _route(
            "audit_vault",
            "organizador" if "organizador" in skills else "none",
            ["obsidian://skills/organizador", "health_check"],
            [
                "Run health check first.",
                "Inspect tags, frontmatter, duplicates, and orphan notes.",
                "Propose changes before mutating the vault.",
            ],
            "Maintenance tasks should be explicit and reversible.",
        )

    return _route(
        "assistant_overview",
        "none",
        ["obsidian://capabilities", "read_vault_context"],
        [
            "Read capabilities.",
            "Read vault context.",
            "Choose a specific skill or prompt only if the request clearly matches.",
        ],
        "Default route for ambiguous tasks.",
    )


def _route(
    prompt: str,
    skill: str,
    tools: list[str],
    steps: list[str],
    notes: str,
) -> TaskRoute:
    return {
        "prompt": prompt,
        "skill": skill,
        "tools": tools,
        "steps": steps,
        "notes": notes,
    }


def _has_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _render_health_report(checks: list[tuple[str, bool, str]]) -> str:
    ok_count = sum(1 for _, ok, _ in checks if ok)
    output = "# Vault Health Check\n\n"
    output += f"Passed: {ok_count}/{len(checks)}\n\n"
    for name, ok, detail in checks:
        marker = "✅" if ok else "❌"
        output += f"- {marker} `{name}`: {detail}\n"
    return output.rstrip()
