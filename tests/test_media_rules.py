"""Media notes must follow the media schema, not the generic vault one.

Regression for the 05_Media incident: agents created film notes mixing both
schemas (``tipo`` + ``type``/``status``/``title``/``created``), without the
standard metadata, with ``estado: completo`` and duplicated/uppercase tags.
Rules live in REGLAS_GLOBALES.md; the server adds ``paths``/``exclude_paths``,
``forbidden_fields``, ``unique``, per-value ``pattern`` and ``block``.
"""

import asyncio
import json
import unicodedata

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import (
    invalidate_rules_cache,
    load_vault_rules,
    run_validations,
)
from obsidian_mcp.server import create_server
from obsidian_mcp.tools.agents_logic import validate_note_logic
from obsidian_mcp.tools.analysis_logic import lint_vault
from obsidian_mcp.utils import invalidate_note_cache
from obsidian_mcp.vault_config import invalidate_vault_config_cache

RULES = """\
---
validations:
  - id: required_frontmatter
    applies_to: [create]
    scope: frontmatter
    exclude_paths: ["05_Media/*"]
    required_fields: [type, status, tags]
    warning: "Frontmatter incompleto: faltan {missing_fields}"

  - id: media_esquema_mezclado
    applies_to: [create, edit]
    block: true
    scope: frontmatter
    paths: ["05_Media/Películas/*", "05_Media/Series/*", "05_Media/Libros/*"]
    forbidden_fields: [type, status, title, created, updated]
    warning: "Ficha de media con campos del esquema genérico: {present_fields}"

  - id: media_pelicula_campos
    applies_to: [create]
    block: true
    scope: frontmatter
    paths: ["05_Media/Películas/*"]
    required_fields: [tipo, estado, titulo, imdb_id, year, director, generos,
      reparto, pais, runtime, poster, imdb_rating, fecha_creacion,
      fecha_actualizacion, tags]
    warning: "Película incompleta: faltan {missing_fields}"

  - id: media_estado
    applies_to: [create, edit]
    block: true
    scope: frontmatter
    paths: ["05_Media/Películas/*", "05_Media/Series/*", "05_Media/Libros/*"]
    field: estado
    allowed_values: [pendiente, en_progreso, completado, abandonado, sin_clasificar]
    warning: "estado inválido: '{value}'"

  - id: media_tags_unicas
    applies_to: [create, edit]
    block: true
    scope: frontmatter
    paths: ["05_Media/*"]
    field: tags
    unique: true
    warning: "Tags duplicadas: {value}"

  - id: media_tags_minusculas
    applies_to: [create, edit]
    block: true
    scope: frontmatter
    paths: ["05_Media/*"]
    field: tags
    pattern: "[A-ZÁÉÍÓÚÑÜ]"
    warning: "Tags con mayúsculas: {value}"
---

# Reglas
"""

TEMPLATE = """\
---
tipo: pelicula
estado: pendiente
titulo: "{{title}}"
imdb_id:
fecha_creacion: "{{date}}"
fecha_actualizacion: "{{date}}"
tags:
- media
- media/peliculas
year:
director:
generos:
reparto:
pais:
runtime:
poster:
imdb_rating:
---

# {{title}}

## Notas Personales
-
"""

FULL_METADATA = """\
---
imdb_id: tt0000001
year: 2025
director: [Harry Lighton]
generos: [Drama]
reparto: [Alexander Skarsgård]
pais: Reino Unido
runtime: 106 min
poster: https://example.com/p.jpg
imdb_rating: 7.1
---
"""


@pytest.fixture
def vault(isolated_vault, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "notes_write")
    reset_settings()
    agents = isolated_vault / ".agents"
    agents.mkdir()
    (agents / "REGLAS_GLOBALES.md").write_text(RULES, encoding="utf-8")
    (agents / "vault.yaml").write_text(
        'templates_folder: "ZZ_Plantillas"\n', encoding="utf-8"
    )
    (isolated_vault / "ZZ_Plantillas").mkdir()
    (isolated_vault / "ZZ_Plantillas" / "Media - Película.md").write_text(
        TEMPLATE, encoding="utf-8"
    )
    invalidate_rules_cache()
    invalidate_vault_config_cache()
    invalidate_note_cache()
    yield isolated_vault
    invalidate_rules_cache()
    invalidate_vault_config_cache()
    invalidate_note_cache()


def _create(**kwargs):
    tool = asyncio.run(create_server().get_tool("notes.create"))
    return tool.fn(**kwargs)


def test_incomplete_film_is_blocked_and_not_written(vault):
    """Pillion case: film note without the standard fields."""
    result = _create(
        title="Pillion",
        content="---\ntags: [media]\n---\n\nMe gustó.",
        folder="05_Media/Películas",
    )

    assert "Nota NO creada" in result
    assert "Película incompleta" in result
    assert "imdb_id" in result and "director" in result
    assert not (vault / "05_Media" / "Películas" / "Pillion.md").exists()
    assert not (vault / "05_Media").exists()


def test_mixed_schema_film_is_blocked(vault):
    content = (
        "---\ntipo: pelicula\nestado: completo\ntype: recurso\nstatus: completo\n"
        "tags: [media, media, DBDSM]\n---\n\nbody"
    )
    result = _create(
        title="Raw",
        content=content,
        folder="05_Media/Películas",
        template="Media - Película",
    )

    assert "Nota NO creada" in result
    assert "esquema genérico: type, status" in result
    assert "estado inválido: 'completo'" in result
    assert "Tags duplicadas: media" in result
    assert "Tags con mayúsculas: DBDSM" in result
    assert not (vault / "05_Media" / "Películas" / "Raw.md").exists()


def test_complete_film_from_template_is_created_with_media_schema_only(vault):
    result = _create(
        title="Pillion",
        content=FULL_METADATA + "\nMe gustó.",
        folder="05_Media/Películas",
        template="Media - Película",
    )

    assert result.startswith("OK"), result
    assert "WARNINGS" not in result
    written = (vault / "05_Media" / "Películas" / "Pillion.md").read_text(
        encoding="utf-8"
    )
    assert "tipo: pelicula" in written
    assert "titulo: Pillion" in written
    # No generic fields injected by the server next to titulo/fecha_creacion.
    for generic in ("\ntitle:", "\ncreated:", "\ntype:", "\nstatus:"):
        assert generic not in written


def test_generic_rules_still_apply_outside_media(vault):
    warnings = run_validations(
        _rules(),
        "create",
        frontmatter={"tags": ["x"]},
        path="02_Conocimiento/Nota.md",
    )
    assert warnings == ["Frontmatter incompleto: faltan type, status"]

    media = run_validations(
        _rules(),
        "create",
        frontmatter={"tags": ["media"]},
        path="05_Media/Media Index.md",
    )
    assert media == []


def test_path_rules_match_decomposed_unicode_paths(vault):
    nfd = unicodedata.normalize("NFD", "05_Media/Películas/X.md")
    warnings = run_validations(
        _rules(), "edit", frontmatter={"type": "recurso"}, path=nfd
    )
    assert any("esquema genérico" in w for w in warnings)


def test_validate_note_uses_note_path(vault):
    content = "---\ntipo: pelicula\nestado: completo\ntags: [media]\n---\n\nx"
    scoped = json.loads(
        validate_note_logic(
            content=content, note_path="05_Media/Películas/X.md"
        ).unwrap()
    )
    assert scoped["valid"] is False
    assert "estado inválido: 'completo'" in scoped["violations"]

    unscoped = json.loads(validate_note_logic(content=content).unwrap())
    assert "estado inválido: 'completo'" not in unscoped["violations"]


def test_edit_warns_on_mixed_schema(vault):
    note_dir = vault / "05_Media" / "Películas"
    note_dir.mkdir(parents=True)
    (note_dir / "Planet Terror.md").write_text(
        "---\ntipo: pelicula\nestado: pendiente\ntags: [media]\n---\n\nx",
        encoding="utf-8",
    )
    tool = asyncio.run(create_server().get_tool("notes.update_frontmatter"))

    result = tool.fn("Planet Terror", '{"type": "recurso", "estado": "completo"}')

    assert "esquema genérico: type" in result
    assert "estado inválido: 'completo'" in result


def test_lint_vault_flags_media_notes(vault):
    note_dir = vault / "05_Media" / "Películas"
    note_dir.mkdir(parents=True)
    (note_dir / "Raw.md").write_text(
        "---\ntipo: pelicula\nestado: completado\ntitle: Raw\n"
        "tags: [media, media]\n---\n\nx",
        encoding="utf-8",
    )

    report = lint_vault(folder="05_Media").unwrap()

    assert "media_esquema_mezclado" in report
    assert "media_tags_unicas" in report


def _rules():
    return load_vault_rules(force_reload=True)
