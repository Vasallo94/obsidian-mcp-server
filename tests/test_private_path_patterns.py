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


def test_double_star_does_not_skip_names_with_newlines():
    """Revisión de seguridad: '.' sin DOTALL dejaba pasar nombres con '\\n'."""
    assert _match("Diario/a\nb.md", "Diario/**")
    assert _match("x/Privado/a\nb.md", "**/Privado/*")


def test_double_star_keeps_character_classes():
    """Revisión de seguridad: '[...]' debe seguir siendo una clase, como en fnmatch."""
    assert _match("x/privado/n.md", "**/[Pp]rivado/*")
    assert _match("x/Privado/n.md", "**/[Pp]rivado/*")


def test_middle_double_star_matches_zero_or_more_folders():
    assert _match("a/b", "a/**/b")
    assert _match("a/x/y/b", "a/**/b")
    assert not _match("a/x/c", "a/**/b")


def test_double_star_uses_fnmatch_case_rules():
    """Misma regla de mayúsculas que el resto de patrones (fnmatch/normcase)."""
    import fnmatch

    assert _match("x/PRIVADO/n.md", "**/Privado/*") is fnmatch.fnmatch(
        "PRIVADO/n.md", "Privado/*"
    )


@pytest.mark.parametrize("path", ["a/b/c", "a/x/b/c", "a/b/y/c", "a/x/b/y/c"])
def test_every_middle_double_star_matches_zero_or_more_folders(path):
    """Revisión de seguridad: todos los '/**/' se expanden, no solo el primero."""
    assert _match(path, "a/**/b/**/c")


def test_leading_and_middle_double_star_together():
    assert _match("b/c", "**/b/**/c")
    assert _match("x/b/y/c", "**/b/**/c")


@pytest.mark.parametrize(
    "path,pattern",
    [
        ("Privado/x.md", "Privado/**/"),
        ("Privado/sub/x.md", "Privado/**/"),
        ("cualquier/cosa.md", "**/"),
        ("a/Privado/x.md", "**/Privado/"),
        ("a/secrets.md", "/**/secrets.md"),
        ("a/x", "./**/x"),
        ("a/Privado/x.md", " **/Privado/*"),
    ],
)
def test_pattern_spelling_variants_still_protect(path, pattern):
    """Auditoría #132: '/' final, '/' o './' iniciales y espacios no deben abrir huecos."""
    assert _match(path, pattern)


@pytest.mark.parametrize(
    "path", ["prod.env", "config/production.env", "x/local.env.bak"]
)
def test_packaged_patterns_keep_protecting_named_env_files(path):
    """Auditoría #132: cobertura conservadora de ficheros .env con prefijo."""

    assert _matching_forbidden_pattern(
        Path(path), load_forbidden_patterns(force_reload=True)
    )


@pytest.mark.parametrize("pattern", ["Privado//", "Privado///", "Privado//**"])
def test_repeated_trailing_slashes_still_protect(pattern):
    """Revisión de seguridad: barras repetidas no deben abrir un hueco."""
    assert _match("Privado/x.md", pattern)
    assert _match("Privado/sub/x.md", pattern)


def test_spaces_that_belong_to_the_name_are_kept():
    """Revisión de seguridad: el patrón original también cuenta (deniega si casa cualquiera)."""
    assert _match(" Privado /x.md", " Privado /*")
    assert _match("Privado/x.md", " Privado/*")


def test_empty_pattern_after_normalisation_matches_nothing():
    for pattern in ("   ", "/", "./"):
        assert not _match("nota.md", pattern)
