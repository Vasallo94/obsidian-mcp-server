"""
Utilidades para trabajar con el vault de Obsidian.

Funciones compartidas para manejo de archivos, metadata y caché.
"""

import re
from datetime import datetime
from pathlib import Path
from time import time
from typing import Any, Dict, List, Optional, Tuple

import aiofiles

from ..config import get_vault_path, get_vault_settings

# --- Note Cache ---
# Simple time-based cache for find_note_by_name
_note_cache: Dict[str, Tuple[float, Optional[Path]]] = {}


def _get_cache_ttl() -> int:
    """Get cache TTL from settings."""
    try:
        return get_vault_settings().cache_ttl_seconds
    except Exception:
        return 300  # Default 5 minutes


def invalidate_note_cache(name: Optional[str] = None) -> None:
    """
    Invalidate the note cache.

    Args:
        name: Optional specific note name to invalidate. If None, clears all.
    """
    global _note_cache
    if name is None:
        _note_cache.clear()
    else:
        cache_key = name.lower().replace(".md", "")
        _note_cache.pop(cache_key, None)


def get_vault_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas básicas del vault.

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


def find_note_by_name(name: str, use_cache: bool = True) -> Optional[Path]:
    """
    Busca una nota por nombre en todo el vault (insensible a mayúsculas).

    Args:
        name: Nombre de la nota (con o sin extensión .md)
        use_cache: Si usar resultados cacheados (default: True)

    Returns:
        Path de la nota si se encuentra, None en caso contrario
    """
    cache_key = name.lower().replace(".md", "")
    cache_ttl = _get_cache_ttl()

    # Check cache
    if use_cache and cache_key in _note_cache:
        cached_time, cached_path = _note_cache[cache_key]
        if time() - cached_time < cache_ttl:
            # Verify file still exists
            if cached_path is None or cached_path.exists():
                return cached_path

    # Perform actual lookup
    result = _find_note_by_name_impl(name)

    # Cache result
    _note_cache[cache_key] = (time(), result)

    return result


def _find_note_by_name_impl(name: str) -> Optional[Path]:
    """Internal implementation of note lookup."""
    vault_path = get_vault_path()
    if not vault_path:
        return None

    # Si incluye ruta, buscar directamente
    if "/" in name:
        note_path = vault_path / name
        return note_path if note_path.exists() else None

    # Buscar en todo el vault (insensible a mayúsculas)
    name_lower = name.lower().replace(".md", "")
    for file_path in vault_path.rglob("*.md"):
        if file_path.stem.lower() == name_lower:
            return file_path

    return None


def get_note_metadata(note_path: Path) -> Dict[str, Any]:
    """
    Obtiene metadata de una nota.

    Args:
        note_path: Path de la nota

    Returns:
        Diccionario con metadata de la nota
    """
    vault_path = get_vault_path()
    stats = note_path.stat()

    if not vault_path:
        return {
            "name": note_path.name,
            "stem": note_path.stem,
            "relative_path": str(note_path),
            "size_kb": stats.st_size / 1024,
            "modified": datetime.fromtimestamp(stats.st_mtime).strftime(
                "%Y-%m-%d %H:%M"
            ),
            "created": datetime.fromtimestamp(stats.st_ctime).strftime(
                "%Y-%m-%d %H:%M"
            ),
        }

    return {
        "name": note_path.name,
        "stem": note_path.stem,
        "relative_path": str(note_path.relative_to(vault_path)),
        "size_kb": stats.st_size / 1024,
        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "created": datetime.fromtimestamp(stats.st_ctime).strftime("%Y-%m-%d %H:%M"),
    }


# --- Async File Operations ---


async def read_note_async(note_path: Path) -> str:
    """
    Read note content asynchronously.

    Args:
        note_path: Path to the note file

    Returns:
        Content of the note as string
    """
    async with aiofiles.open(note_path, "r", encoding="utf-8") as f:
        return await f.read()


async def write_note_async(note_path: Path, content: str) -> None:
    """
    Write note content asynchronously.

    Args:
        note_path: Path to the note file
        content: Content to write
    """
    async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
        await f.write(content)


# --- Tag and Link Extraction ---


def extract_tags_from_content(content: str) -> List[str]:
    """
    Extrae etiquetas tanto del frontmatter YAML como del cuerpo de la nota.

    Args:
        content: Contenido de la nota

    Returns:
        Lista de etiquetas únicas encontradas
    """
    tags = set()

    # 1. Extraer del YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            # Buscar línea de tags: tags: [a, b] o tags: a, b
            tags_match = re.search(r"^tags:\s*(.*)$", frontmatter, re.MULTILINE)
            if tags_match:
                tags_raw = tags_match.group(1).strip()
                # Caso [tag1, tag2]
                if tags_raw.startswith("[") and tags_raw.endswith("]"):
                    tags_list = tags_raw[1:-1].split(",")
                    for t in tags_list:
                        tags.add(t.strip().lstrip("#"))
                # Caso lista YAML o string simple
                else:
                    # Intentar buscar formato de lista - tag
                    fm_list = re.findall(r"^\s*-\s*([\w-]+)", frontmatter, re.MULTILINE)
                    if fm_list:
                        for t in fm_list:
                            tags.add(t.strip())
                    else:
                        # Caso simple separado por comas
                        for t in tags_raw.split(","):
                            cleaned = t.strip().lstrip("#")
                            if cleaned:
                                tags.add(cleaned)

    # 2. Extraer del cuerpo (formato #tag)
    # Regex mejorado: captura palabras con guiones pero no hashtags de headings
    body_tags = re.findall(r"(?<!\w)#([\w-]+)", content)
    for t in body_tags:
        tags.add(t)

    return sorted(list(tags))


def extract_internal_links(content: str) -> List[str]:
    """
    Extrae enlaces internos del contenido de una nota.

    Args:
        content: Contenido de la nota

    Returns:
        Lista de enlaces internos encontrados
    """
    # Buscar enlaces en formato [[link]]
    links = re.findall(r"\[\[([^\]]+)\]\]", content)
    return list(set(links))  # Eliminar duplicados


# --- Utility Functions ---


def format_file_size(size_bytes: int) -> str:
    """
    Formatea el tamaño de archivo en una unidad legible.

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
    Sanitiza un nombre de archivo para que sea válido en el sistema.

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
