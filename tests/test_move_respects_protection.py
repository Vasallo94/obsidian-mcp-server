"""notes.move / notes.rename no pueden sacar ni meter notas en rutas protegidas."""

from pathlib import Path

import pytest

from obsidian_mcp.tools import navigation_logic
from obsidian_mcp.utils import security
from obsidian_mcp.vault_config import invalidate_vault_config_cache


@pytest.fixture
def vault(tmp_path: Path, monkeypatch) -> Path:
    v = tmp_path / "vault"
    for d in ("Privado", "Publico", ".git"):
        (v / d).mkdir(parents=True)
    (v / "Privado" / "x.md").write_text("secreto", encoding="utf-8")
    (v / "Publico" / "nota.md").write_text("hola", encoding="utf-8")
    (v / ".git" / "config.md").write_text("git", encoding="utf-8")
    monkeypatch.setattr(security, "get_vault_path", lambda: v)
    monkeypatch.setattr(navigation_logic, "get_vault_path", lambda: v)
    invalidate_vault_config_cache()
    security.load_forbidden_patterns(force_reload=True, vault_path=v)
    return v


@pytest.mark.parametrize("origen", ["Privado/x.md", "privado/x.md", "PRIVADO/X.md"])
def test_cannot_move_out_of_private_folder(vault, origen):
    result = navigation_logic.move_note(origen, "Publico/fuera.md")

    assert not result.success
    assert (vault / "Privado" / "x.md").exists()
    assert not (vault / "Publico" / "fuera.md").exists()


def test_cannot_move_into_private_folder(vault):
    result = navigation_logic.move_note("Publico/nota.md", "Privado/nota.md")

    assert not result.success
    assert (vault / "Publico" / "nota.md").exists()


def test_cannot_move_forbidden_paths(vault):
    """.forbidden_paths (p. ej. .git/*) también cuenta, no solo private_paths."""
    result = navigation_logic.move_note(".git/config.md", "Publico/config.md")

    assert not result.success
    assert (vault / ".git" / "config.md").exists()


def test_normal_move_still_works(vault):
    result = navigation_logic.move_note("Publico/nota.md", "Publico/renombrada.md")

    assert result.success, result.error
    assert (vault / "Publico" / "renombrada.md").exists()
