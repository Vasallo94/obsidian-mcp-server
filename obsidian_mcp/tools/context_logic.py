"""
Core business logic for context tools.

This module contains the implementation of context gathering operations,
separated from the MCP tool registration.
"""

from typing import Dict

from ..config import get_vault_path
from ..result import Result
from ..utils import extract_tags_from_content, get_logger
from ..vault_config import get_vault_config

logger = get_logger(__name__)


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

        # Check vault configuration (optional)
        config = get_vault_config(vault_path)

        # 1. Estructura de carpetas (primer nivel y algunos segundos niveles clave)
        estructura = []
        excluidos = {
            ".git",
            ".obsidian",
            ".trash",
            ".gemini",
            ".space",
            ".makemd",
            ".obsidianrag",
            ".agent",
        }

        # Buscar carpetas principales
        for item in sorted(vault_path.iterdir()):
            if (
                item.is_dir()
                and item.name not in excluidos
                and not item.name.startswith(".")
            ):
                subcarpetas = []
                try:
                    for sub in sorted(item.iterdir()):
                        if sub.is_dir() and not sub.name.startswith("."):
                            subcarpetas.append(sub.name)
                except PermissionError:
                    pass

                desc = f"📂 {item.name}"
                if subcarpetas:
                    if len(subcarpetas) > 5:
                        desc += f" (incluye: {', '.join(subcarpetas[:5])}, ...)"
                    else:
                        desc += f" (incluye: {', '.join(subcarpetas)})"
                estructura.append(desc)

        # 2. Plantillas disponibles
        plantillas = []
        templates_folder = None
        if config and config.templates_folder:
            templates_folder = config.templates_folder
        else:
            # Auto-detect: look for folders with "plantilla" or "template" in name
            for item in vault_path.iterdir():
                if item.is_dir() and any(
                    t in item.name.lower()
                    for t in ["plantilla", "template", "templates"]
                ):
                    templates_folder = item.name
                    break

        if templates_folder:
            plantillas_path = vault_path / templates_folder
            if plantillas_path.exists():
                for item in sorted(plantillas_path.glob("*.md")):
                    plantillas.append(item.stem)

        # 3. Etiquetas más comunes (muestreo)
        conteo_etiquetas: Dict[str, int] = {}
        limit_files = 100
        count = 0
        for archivo in vault_path.rglob("*.md"):
            if count >= limit_files:
                break
            try:
                with open(archivo, "r", encoding="utf-8") as f:
                    tags = extract_tags_from_content(f.read())
                    for tag in tags:
                        conteo_etiquetas[tag] = conteo_etiquetas.get(tag, 0) + 1
                count += 1
            except OSError as e:
                logger.debug("No se pudo leer '%s': %s", archivo, e)
                continue

        top_tags = sorted(conteo_etiquetas.items(), key=lambda x: x[1], reverse=True)[
            :20
        ]
        tags_str = ", ".join([f"#{t}" for t, _ in top_tags])

        # 4. Contexto del Agente (.agent)
        agent_info = []
        agent_path = vault_path / ".agent"
        if agent_path.exists() and agent_path.is_dir():
            agent_info.append("✅ Carpeta .agent encontrada.")
            # Listar estructura básica de .agent
            for item in sorted(agent_path.iterdir()):
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    subitems = [
                        s.name for s in item.iterdir() if not s.name.startswith(".")
                    ]
                    desc = f"  - 📂 {item.name}/"
                    if subitems:
                        desc += (
                            f" ({', '.join(subitems[:5])}"
                            f"{'...' if len(subitems) > 5 else ''})"
                        )
                    agent_info.append(desc)
                else:
                    agent_info.append(f"  - 📄 {item.name}")
        else:
            agent_info.append("⚠️ No se encontró la carpeta .agent")
            agent_info.append(
                "  -> SUGESTIÓN: Lee la documentación para configurar "
                "tus Agentes y Reglas."
            )

        # Construir reporte
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

        reporte += "## 🤖 Contexto del Agente (.agent)\n"
        reporte += "\n".join(agent_info) + "\n"

        return Result.ok(reporte)

    except OSError as e:
        return Result.fail(f"Error al leer contexto: {e}")
