"""
Core business logic for context tools.

This module contains the implementation of context gathering operations,
separated from the MCP tool registration.
"""

from pathlib import Path
from typing import Dict, Optional

from ..config import get_vault_path
from ..result import Result
from ..utils import extract_tags_from_content, get_logger
from ..vault_config import VaultConfig, get_vault_config

logger = get_logger(__name__)


def _collect_folder_structure(vault_path: Path) -> list[str]:
    """Collect top-level folder structure with immediate subfolders."""
    excluidos = {
        ".git",
        ".obsidian",
        ".trash",
        ".gemini",
        ".space",
        ".makemd",
        ".obsidianrag",
        ".agents",
    }
    estructura = []

    for item in sorted(vault_path.iterdir()):
        if not item.is_dir() or item.name in excluidos or item.name.startswith("."):
            continue

        subcarpetas = []
        try:
            for sub in sorted(item.iterdir()):
                if sub.is_dir() and not sub.name.startswith("."):
                    subcarpetas.append(sub.name)
        except PermissionError:
            pass

        desc = f"📂 {item.name}"
        if subcarpetas:
            nombres = ", ".join(subcarpetas[:5])
            if len(subcarpetas) > 5:
                desc += f" (incluye: {nombres}, ...)"
            else:
                desc += f" (incluye: {nombres})"
        estructura.append(desc)

    return estructura


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

    plantillas: list[str] = []
    if templates_folder:
        plantillas_path = vault_path / templates_folder
        if plantillas_path.exists():
            plantillas = [item.stem for item in sorted(plantillas_path.glob("*.md"))]

    return templates_folder, plantillas


def _collect_common_tags(vault_path: Path) -> str:
    """Sample up to 100 notes and return top 20 tags as a formatted string."""
    conteo: Dict[str, int] = {}
    count = 0

    for archivo in vault_path.rglob("*.md"):
        if count >= 100:
            break
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                tags = extract_tags_from_content(f.read())
                for tag in tags:
                    conteo[tag] = conteo.get(tag, 0) + 1
            count += 1
        except OSError as e:
            logger.debug("No se pudo leer '%s': %s", archivo, e)
            continue

    top_tags = sorted(conteo.items(), key=lambda x: x[1], reverse=True)[:20]
    return ", ".join(f"#{t}" for t, _ in top_tags)


def _collect_agent_context(vault_path: Path) -> list[str]:
    """Collect information about the .agents folder structure."""
    agent_path = vault_path / ".agents"
    if not agent_path.exists() or not agent_path.is_dir():
        return [
            "⚠️ No se encontró la carpeta .agents",
            "  -> SUGESTIÓN: Lee la documentación para configurar "
            "tus Agentes y Reglas.",
        ]

    info = ["✅ Carpeta .agents encontrada."]
    for item in sorted(agent_path.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            subitems = [s.name for s in item.iterdir() if not s.name.startswith(".")]
            desc = f"  - 📂 {item.name}/"
            if subitems:
                nombres = ", ".join(subitems[:5])
                suffix = "..." if len(subitems) > 5 else ""
                desc += f" ({nombres}{suffix})"
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
            return Result.fail("La ruta del vault no está configurada.")

        config = get_vault_config(vault_path)

        estructura = _collect_folder_structure(vault_path)
        templates_folder, plantillas = _collect_templates(vault_path, config)
        tags_str = _collect_common_tags(vault_path)
        agent_info = _collect_agent_context(vault_path)

        # Build report
        reporte = "# Contexto del Vault\n\n"

        reporte += "## 📂 Estructura Principal\n"
        reporte += "\n".join(estructura) + "\n\n"

        if templates_folder:
            reporte += f"## 📝 Plantillas Disponibles (en {templates_folder})\n"
            if plantillas:
                reporte += ", ".join(plantillas) + "\n\n"
            else:
                reporte += f"No se encontraron plantillas en {templates_folder}.\n\n"
        else:
            reporte += "## 📝 Plantillas\n"
            reporte += "No se detectó carpeta de plantillas.\n\n"

        reporte += "## 🏷️ Etiquetas Comunes (Muestreo)\n"
        if tags_str:
            reporte += tags_str + "\n\n"
        else:
            reporte += "No se detectaron etiquetas comunes.\n\n"

        reporte += "## 🤖 Contexto del Agente (.agents)\n"
        reporte += "\n".join(agent_info) + "\n"

        return Result.ok(reporte)

    except OSError as e:
        return Result.fail(f"Error al leer contexto: {e}")
