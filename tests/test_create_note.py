"""Tests for create_note logic, focused on frontmatter merging.

Issue #2: when the `content` arg already includes a YAML frontmatter block,
fields like `type`/`status` from the embedded frontmatter must survive.
"""

import re

import pytest
import yaml

from obsidian_mcp.tools.creation_logic import create_note


@pytest.fixture
def temp_vault(tmp_path, monkeypatch):
    """Create a temp vault and patch the vault path."""
    vault = tmp_path / "vault"
    vault.mkdir()
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.get_vault_path",
        lambda: vault,
    )
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.get_vault_config",
        lambda *_args, **_kwargs: None,
    )
    return vault


def _read_frontmatter(note_path):
    """Pull YAML frontmatter dict out of a written note."""
    raw = note_path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
    assert match, f"No frontmatter in {note_path}: {raw[:200]}"
    return yaml.safe_load(match.group(1))


class TestCreateNoteFrontmatterMerge:
    """Issue #2: embedded frontmatter must not be stripped by tool-generated one."""

    def test_embedded_type_and_status_are_preserved(self, temp_vault):
        embedded = (
            "---\n"
            "title: X\n"
            "type: recurso\n"
            "status: completo\n"
            "tags: [astro, equipo]\n"
            "---\n\n"
            "# X\n\nbody\n"
        )
        result = create_note(
            titulo="X",
            contenido=embedded,
            carpeta="notes",
            etiquetas="",
        )
        assert result.success

        fm = _read_frontmatter(temp_vault / "notes" / "X.md")
        assert fm["type"] == "recurso"
        assert fm["status"] == "completo"
        assert fm["title"] == "X"

    def test_embedded_custom_fields_survive(self, temp_vault):
        embedded = (
            "---\n"
            "title: Y\n"
            "type: nota\n"
            "status: captura\n"
            "related: ['[[Otra nota]]']\n"
            "rating: 5\n"
            "---\n\nbody\n"
        )
        result = create_note(
            titulo="Y",
            contenido=embedded,
            carpeta="notes",
            etiquetas="",
        )
        assert result.success

        fm = _read_frontmatter(temp_vault / "notes" / "Y.md")
        assert fm["related"] == ["[[Otra nota]]"]
        assert fm["rating"] == 5

    def test_parameter_tags_merge_with_embedded_tags(self, temp_vault):
        embedded = (
            "---\ntitle: Z\ntype: nota\nstatus: captura\ntags: [astro]\n---\n\nbody\n"
        )
        result = create_note(
            titulo="Z",
            contenido=embedded,
            carpeta="notes",
            etiquetas="equipo, fotografia",
        )
        assert result.success

        fm = _read_frontmatter(temp_vault / "notes" / "Z.md")
        assert set(fm["tags"]) == {"astro", "equipo", "fotografia"}

    def test_embedded_title_wins_over_parameter_title(self, temp_vault):
        """When both are present, embedded title is the source of truth.

        The filename still comes from the `titulo` parameter (the
        sanitization happens in the call), but the frontmatter title
        should reflect the author's embedded value.
        """
        embedded = (
            "---\ntitle: Titulo Embebido\ntype: nota\nstatus: captura\n---\n\nbody\n"
        )
        result = create_note(
            titulo="ParamTitle",
            contenido=embedded,
            carpeta="notes",
            etiquetas="",
        )
        assert result.success

        fm = _read_frontmatter(temp_vault / "notes" / "ParamTitle.md")
        assert fm["title"] == "Titulo Embebido"

    def test_embedded_created_date_is_preserved(self, temp_vault):
        embedded = (
            "---\n"
            "title: Histo\n"
            "type: nota\n"
            "status: captura\n"
            "created: '2020-01-15'\n"
            "---\n\nbody\n"
        )
        result = create_note(
            titulo="Histo",
            contenido=embedded,
            carpeta="notes",
            etiquetas="",
        )
        assert result.success

        fm = _read_frontmatter(temp_vault / "notes" / "Histo.md")
        assert str(fm["created"]) == "2020-01-15"

    def test_no_embedded_frontmatter_falls_back_to_params(self, temp_vault):
        """When content has no frontmatter, build one from parameters."""
        result = create_note(
            titulo="Plain",
            contenido="body without frontmatter\n",
            carpeta="notes",
            etiquetas="one, two",
        )
        assert result.success

        fm = _read_frontmatter(temp_vault / "notes" / "Plain.md")
        assert fm["title"] == "Plain"
        assert set(fm["tags"]) == {"one", "two"}
        assert "created" in fm
