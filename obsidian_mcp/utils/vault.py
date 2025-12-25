"""
Utilidades para trabajar con el vault de Obsidian
Funciones compartidas para manejo de archivos y metadata
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..config import get_vault_path


def get_vault_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas básicas del vault

    Returns:
        Diccionario con estadísticas del vault
    """
    vault_path = get_vault_path()
    if not vault_path:
        return {
            "error": "La ruta del vault no está configurada",
            "vault_name": "N/A",
            "vault_path": "N/A",
            "total_files": 0,
            "markdown_files": 0,
            "folders": 0,
            "last_scan": datetime.now().isoformat(),
        }

    markdown_files = list(vault_path.glob("**/*.md"))
    total_files = list(vault_path.glob("**/*.*"))

    return {
        "vault_name": vault_path.name,
        "vault_path": str(vault_path),
        "total_files": len(total_files),
        "markdown_files": len(markdown_files),
        "folders": len([p for p in vault_path.rglob("*") if p.is_dir()]),
        "last_scan": datetime.now().isoformat(),
    }


def find_note_by_name(name: str) -> Path | None:
    """
    Busca una nota por nombre en todo el vault

    Args:
        name: Nombre de la nota (con o sin extensión .md)

    Returns:
        Path de la nota si se encuentra, None en caso contrario
    """
    vault_path = get_vault_path()
    if not vault_path:
        return None

    # Si incluye ruta, buscar directamente
    if "/" in name:
        note_path = vault_path / name
        return note_path if note_path.exists() else None

    # Buscar en todo el vault
    for file_path in vault_path.rglob("*.md"):
        if file_path.name == name or file_path.stem == name:
            return file_path

    return None


def get_note_metadata(note_path: Path) -> Dict[str, Any]:
    """
    Obtiene metadata de una nota

    Args:
        note_path: Path de la nota

    Returns:
        Diccionario con metadata de la nota
    """
    vault_path = get_vault_path()
    if not vault_path:
        stats = note_path.stat()
        return {
            "name": note_path.name,
            "stem": note_path.stem,
            "relative_path": str(
                note_path
            ),  # Usar ruta absoluta si vault_path no está disponible
            "size_kb": stats.st_size / 1024,
            "modified": datetime.fromtimestamp(stats.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "created": datetime.fromtimestamp(stats.st_ctime).strftime(
                "%Y-%m-%d %H:%M"
            ),
        }

    stats = note_path.stat()

    return {
        "name": note_path.name,
        "stem": note_path.stem,
        "relative_path": str(note_path.relative_to(vault_path)),
        "size_kb": stats.st_size / 1024,
        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "created": datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M"),
    }


def extract_tags_from_content(content: str) -> List[str]:
    """
    Extrae etiquetas del contenido de una nota

    Args:
        content: Contenido de la nota

    Returns:
        Lista de etiquetas encontradas
    """
    # Buscar etiquetas en formato #tag (incluyendo guiones)
    # Regex mejorado: captura palabras con guiones pero no hashtags de headings
    tags = re.findall(r"(?<!\w)#([\w-]+)", content)
    return list(set(tags))  # Eliminar duplicados


def extract_internal_links(content: str) -> List[str]:
    """
    Extrae enlaces internos del contenido de una nota

    Args:
        content: Contenido de la nota

    Returns:
        Lista de enlaces internos encontrados
    """
    # Buscar enlaces en formato [[link]]
    links = re.findall(r"\[\[([^\]]+)\]\]", content)
    return list(set(links))  # Eliminar duplicados


def format_file_size(size_bytes: int) -> str:
    """
    Formatea el tamaño de archivo en una unidad legible

    Args:
        size_bytes: Tamaño en bytes

    Returns:
        Tamaño formateado (ej: "1.2KB", "3.4MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza un nombre de archivo para que sea válido en el sistema

    Args:
        filename: Nombre de archivo original

    Returns:
        Nombre de archivo sanitizado
    """
    # Reemplazar caracteres problemáticos
    sanitized = filename.replace("/", "-").replace("\\", "-")
    sanitized = re.sub(r'[<>:"|?*]', "-", sanitized)

    # Asegurar extensión .md
    if not sanitized.endswith(".md"):
        sanitized += ".md"

    return sanitized
