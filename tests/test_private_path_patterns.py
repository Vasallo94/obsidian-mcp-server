"""Patrones de private_paths: '**' anclado, Unicode normalizado y caché invalidable."""

import unicodedata
from pathlib import Path

import pytest

from obsidian_mcp.utils.security import (
    _matching_forbidden_pattern,
    load_forbidden_patterns,
)
from obsidian_mcp.vault_config import invalidate_vault_config_cache


def _match(path: str, pattern: str) -> bool:
    return bool(_matching_forbidden_pattern(Path(path), [pattern]))


@pytest.mark.parametrize(
    "path,expected",
    [
        ("Diario/hoy.md", True),
        ("Diario/2026/hoy.md", True),
        ("Otra/nota.md", False),
        ("DiarioX/a.md", False),
    ],
)
def test_trailing_double_star_is_anchored_to_its_folder(path, expected):
    """Antes 'Diario/**' casaba con cualquier ruta del vault."""
    assert _match(path, "Diario/**") is expected


@pytest.mark.parametrize(
    "path,expected",
    [
        ("Privado/x.md", True),
        ("01_Personal/Privado/x.md", True),
        ("01_Personal/Privado/sub/y.md", True),  # las subcarpetas siguen protegidas
        ("01_Personal/Publico/x.md", False),
    ],
)
def test_leading_double_star_keeps_protecting_contents(path, expected):
    assert _match(path, "**/Privado/*") is expected


def test_double_star_extension_pattern():
    assert _match("a/b/clave.secret", "**/*.secret")
    assert not _match("a/b/clave.md", "**/*.secret")


def test_unicode_forms_are_compared_normalised():
    nfd = unicodedata.normalize("NFD", "Conocimiento/Salúd/nota.md")
    nfc_pattern = unicodedata.normalize("NFC", "Conocimiento/Salúd/*")
    assert _match(nfd, nfc_pattern)


def test_pattern_cache_reloads_after_vault_config_invalidation(tmp_path):
    agents = tmp_path / ".agents"
    agents.mkdir()
    (agents / "vault.yaml").write_text("private_paths: ['A/*']\n", encoding="utf-8")
    invalidate_vault_config_cache()
    assert "A/*" in load_forbidden_patterns(vault_path=tmp_path)

    (agents / "vault.yaml").write_text("private_paths: ['B/*']\n", encoding="utf-8")
    invalidate_vault_config_cache()

    patterns = load_forbidden_patterns(vault_path=tmp_path)
    assert "B/*" in patterns and "A/*" not in patterns
