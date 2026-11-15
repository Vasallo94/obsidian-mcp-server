"""Enlace desde el índice al crear, y deuda de la fusión de plantillas y del kit."""

import asyncio
import builtins
import time
from pathlib import Path

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import invalidate_rules_cache
from obsidian_mcp.server import create_server
from obsidian_mcp.tools import agents_logic
from obsidian_mcp.tools.creation_logic import (
    _extract_frontmatter_from_content,
    _place_content,
    _split_markdown,
    normalize_agent_name,
)
from obsidian_mcp.utils import invalidate_note_cache
from obsidian_mcp.utils.security import _matching_forbidden_pattern

MOC = """\
---
title: Sistemas MOC
type: índice
updated: '2020-01-01'
---
# Sistemas MOC

Intro.

## Runbooks

- [[Runbook A]]

## Navegación

[[Home]]
"""


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    (v / "Conocimiento" / "Sistemas" / "Sub").mkdir(parents=True)
    (v / "Conocimiento" / "Física").mkdir(parents=True)
    (v / "Conocimiento" / "Sistemas" / "00 Sistemas MOC.md").write_text(
        MOC, encoding="utf-8"
    )
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "notes_write,agents_admin")
    reset_settings()
    invalidate_rules_cache()
    invalidate_note_cache()
    return v


def _tool(name):
    return asyncio.run(create_server().get_tool(name)).fn


def _moc(vault):
    return (vault / "Conocimiento" / "Sistemas" / "00 Sistemas MOC.md").read_text(
        encoding="utf-8"
    )


# --- B: enlace desde el índice ---


def test_new_note_is_linked_above_the_first_section(vault):
    result = _tool("notes.create")(
        "Backup", "x", folder="Conocimiento/Sistemas", description="copia\nnocturna"
    )

    assert "Enlazada desde: Conocimiento/Sistemas/00 Sistemas MOC.md" in result
    moc = _moc(vault)
    assert (
        "Intro.\n\n## Por clasificar\n\n- [[Backup]]: copia nocturna\n\n## Runbooks"
        in moc
    )
    assert moc.endswith("[[Home]]\n")  # the footer stays last
    assert "updated: '2020-01-01'" not in moc


def test_second_note_goes_into_the_existing_section(vault):
    create = _tool("notes.create")
    create("Uno", "x", folder="Conocimiento/Sistemas")
    create("Dos", "x", folder="Conocimiento/Sistemas")

    assert "## Por clasificar\n\n- [[Uno]]\n- [[Dos]]\n\n## Runbooks" in _moc(vault)


def test_nearest_index_going_up_is_used(vault):
    _tool("notes.create")("Hondo", "x", folder="Conocimiento/Sistemas/Sub")

    assert "- [[Hondo]]" in _moc(vault)


def test_no_index_no_link_and_opt_out(vault):
    before = _moc(vault)
    result = _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")
    _tool("notes.create")(
        "Sin enlace", "x", folder="Conocimiento/Sistemas", link_from_index=False
    )

    assert "Enlazada" not in result
    assert _moc(vault) == before


def test_already_linked_or_index_itself_is_not_linked(vault):
    before = _moc(vault)
    _tool("notes.create")("Runbook A", "x", folder="Conocimiento/Sistemas/Sub")
    _tool("notes.create")("Red MOC", "x", folder="Conocimiento/Sistemas")

    assert _moc(vault) == before


def test_index_without_h2_gets_the_section_at_the_end(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_text("# Física\n\nTexto.", encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert index.read_text(encoding="utf-8") == (
        "# Física\n\nTexto.\n\n## Por clasificar\n\n- [[Caos]]\n"
    )


def test_heading_inside_code_is_not_a_section(vault):
    index = vault / "Conocimiento" / "Física" / "index.md"
    index.write_text("# F\n\n```\n## no\n```\n\n## Sí\n", encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert "```\n## no\n```\n\n## Por clasificar\n\n- [[Caos]]\n\n## Sí" in (
        index.read_text(encoding="utf-8")
    )


# --- Deuda de la fusión de plantillas ---

TEMPLATE = "# T\n\n## Notas\n\nguía\n\n## Fuentes\n\n- \n"


def test_section_one_level_off_fills_the_template_section():
    body = _place_content(TEMPLATE, "### Notas\n\nmío\n\n#### Detalle\n\nd\n")

    assert body == "# T\n\n## Notas\n\nmío\n\n### Detalle\n\nd\n\n## Fuentes\n\n- \n"


def test_comment_markers_inside_code_do_not_block_the_merge():
    content = "## Notas\n\n```\n%% x %%\n<!-- y -->\n```\n\nUsa `%%` así.\n"
    body = _place_content(TEMPLATE, content)

    assert body.startswith("# T\n\n## Notas\n\n```\n%% x %%")
    assert body.count("## Notas") == 1


def test_comment_markers_in_prose_still_append_unmerged():
    body = _place_content(TEMPLATE, "## Notas\n\n%% oculto %%\n")

    assert body.endswith("## Notas\n\n%% oculto %%\n")
    assert body.count("## Notas") == 2


def test_plugin_frontmatter_with_blank_line_is_still_frontmatter():
    """Kanban y Excalidraw escriben '---', línea en blanco y las claves."""
    meta, body = _extract_frontmatter_from_content(
        "---\n\nkanban-plugin: board\n\n---\n\n## Hacer\n"
    )

    assert meta == {"kanban-plugin": "board"} and body == "## Hacer\n"
    # A rule wrapping plain prose is not a mapping, so nothing is taken.
    prose = "---\n\nSolo texto.\n\n---\nResto\n"
    assert _extract_frontmatter_from_content(prose) == ({}, prose)


def test_fence_detection_is_linear():
    start = time.perf_counter()
    _split_markdown("`" * 200_000 + "a`")
    assert time.perf_counter() - start < 1


def test_backtick_fence_with_backtick_info_is_not_a_fence():
    _, _, sections, unsafe = _split_markdown("```npm i```\n\n## A\n")

    assert not unsafe and [k for k, _ in sections] == [(2, "a")]


# --- Robustez ---


@pytest.mark.parametrize("raw", ["\u200d", " \u200d\u200d ", "\u200b\u200d"])
def test_joiner_only_creator_is_dropped(raw):
    assert normalize_agent_name(raw) == ""


@pytest.mark.parametrize(
    "pattern,path",
    [
        ("Notas [2024]/*", "Notas [2024]/x.md"),
        ("Notas [2024]", "Notas [2024]/sub/x.md"),
        ("**/Notas [2024]/**", "A/Notas [2024]/x.md"),
    ],
)
def test_folders_with_brackets_are_protected(pattern, path):
    assert _matching_forbidden_pattern(Path(path), [pattern])


def test_character_classes_keep_working():
    assert _matching_forbidden_pattern(Path("Privado/x.md"), ["Priv[ao]do/*"])
    assert not _matching_forbidden_pattern(Path("Otro/x.md"), ["Priv[ao]do/*"])


def test_kit_rollback_keeps_folders_another_process_created(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    v.mkdir()
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    reset_settings()
    real_mkdir, real_open = Path.mkdir, builtins.open

    def racing_mkdir(self, *args, **kwargs):
        if self.name == "Plantillas":
            real_mkdir(self)  # someone else got there first
        return real_mkdir(self, *args, **kwargs)

    def failing_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if mode == "x" and Path(path).parent.name == "Plantillas":
            raise OSError("disco lleno")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", racing_mkdir)
    monkeypatch.setattr(agents_logic, "open", failing_open, raising=False)

    result = agents_logic.init_vault_kit(write=True)

    assert not result.success
    assert (v / "Plantillas").is_dir()  # not ours: kept
    assert not (v / ".agents").exists()  # ours: rolled back


# --- Hallazgos de la auditoría ---


def test_templates_and_hidden_folders_are_never_linked(vault):
    plantillas = vault / "Plantillas"
    plantillas.mkdir()
    moc = "---\nupdated: {{date:YYYY-MM-DD}}\n---\n# {{title}}\n"
    (plantillas / "MOC.md").write_text(moc, encoding="utf-8")
    (vault / ".agents").mkdir()
    (vault / ".agents" / "Índice.md").write_text("# x\n", encoding="utf-8")
    from obsidian_mcp.tools.creation_logic import link_from_index

    assert _tool("notes.create")("Plantilla Reunión", "x", folder="Plantillas")
    assert link_from_index(vault / ".agents" / "nota.md", vault) == ""
    assert (plantillas / "MOC.md").read_text(encoding="utf-8") == moc


def test_index_date_changes_only_in_its_frontmatter(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    body = "# F\n\nestado:: ok\nupdated:: 2024-01-01\n\n```yaml\ncreated: x\n```\n"
    index.write_text("---\ntitle: F\n---\n" + body, encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    text = index.read_text(encoding="utf-8")
    assert text.startswith("---\ntitle: F\nupdated: ")
    assert "updated:: 2024-01-01\n" in text and "```yaml\ncreated: x\n```" in text


def test_index_without_frontmatter_gets_no_date(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_text("---\n\nTexto\n\n---\nMás\n", encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert "updated" not in index.read_text(encoding="utf-8")


def test_crlf_index_keeps_its_line_endings(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_bytes(b"# F\r\n\r\n## A\r\n")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert index.read_bytes() == (
        b"# F\r\n\r\n## Por clasificar\r\n\r\n- [[Caos]]\r\n\r\n## A\r\n"
    )


@pytest.mark.parametrize("title", ["C# tips", "Nota ]x"])
def test_titles_that_cannot_be_link_targets_are_not_linked(vault, title):
    before = _moc(vault)
    _tool("notes.create")(title, "x", folder="Conocimiento/Sistemas")

    assert _moc(vault) == before


def test_folder_named_like_an_index_is_skipped(vault):
    fisica = vault / "Conocimiento" / "Física"
    (fisica / "index.md").mkdir()
    (fisica / "Índice.md").write_text("# F\n", encoding="utf-8")
    result = _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert "Enlazada desde: Conocimiento/Física/Índice.md" in result


def test_section_inside_a_comment_is_ignored(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_text("# F\n\n%%\n## Por clasificar\n%%\n\n## A\n", encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert "%%\n\n## Por clasificar\n\n- [[Caos]]\n\n## A" in (
        index.read_text(encoding="utf-8")
    )


def test_empty_index_gets_only_the_section(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_text("", encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert index.read_text(encoding="utf-8") == "## Por clasificar\n\n- [[Caos]]\n"


def test_duplicate_check_is_linear(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_text("[[" * 20_000, encoding="utf-8")
    start = time.perf_counter()
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")
    assert time.perf_counter() - start < 1


def test_escaped_backtick_keeps_markers_as_prose():
    body = _place_content(TEMPLATE, "## Notas\n\n\\`%%\\` texto\n")

    assert body.count("## Notas") == 2  # appended unmerged, as before


@pytest.mark.parametrize("raw", ["ㅤ", "⠀", "ᅟᅠ"])
def test_blank_printable_creator_is_dropped(raw):
    assert normalize_agent_name(raw) == ""


# --- Hallazgos de la reauditoría ---

TPL_MOC = "---\nupdated: {{date:YYYY-MM-DD}}\n---\n# {{title}}\n"


def _templates(vault, rel="Plantillas"):
    folder = vault / rel
    folder.mkdir(parents=True)
    (folder / "MOC.md").write_text(TPL_MOC, encoding="utf-8")
    return folder / "MOC.md"


def test_templates_folder_case_differs_from_config(vault):
    moc = _templates(vault)
    (vault / ".agents").mkdir()
    (vault / ".agents" / "vault.yaml").write_text(
        "templates_folder: plantillas\n", encoding="utf-8"
    )
    reset_settings()
    _tool("notes.create")("Nueva", "x", folder="plantillas")

    assert moc.read_text(encoding="utf-8") == TPL_MOC


def test_index_symlinked_into_templates_is_not_touched(vault):
    moc = _templates(vault)
    (vault / "Proyectos").mkdir()
    (vault / "Proyectos" / "MOC.md").symlink_to(moc)
    _tool("notes.create")("Nueva", "x", folder="Proyectos")

    assert moc.read_text(encoding="utf-8") == TPL_MOC


def test_nested_templates_folder_without_config(vault):
    moc = _templates(vault, "Sistema/Plantillas")
    _tool("notes.create")("Nueva", "x", folder="Sistema/Plantillas")

    assert moc.read_text(encoding="utf-8") == TPL_MOC


def test_inline_code_percent_does_not_hide_sections(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    index.write_text(
        "# F\n\nEscribe `%%` para comentar.\n\n## Uso de `%%x%%`\n\n## Por clasificar\n\n- [[A]]\n",
        encoding="utf-8",
    )
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    text = index.read_text(encoding="utf-8")
    assert text.count("## Por clasificar") == 1 and text.endswith(
        "- [[A]]\n- [[Caos]]\n"
    )


@pytest.mark.parametrize("raw", ["\ufe0f", "\u034f", " \u0301 "])
def test_combining_only_creator_is_dropped(raw):
    assert normalize_agent_name(raw) == ""


def test_link_from_index_outside_vault_returns_empty(tmp_path):
    from obsidian_mcp.tools.creation_logic import link_from_index

    (tmp_path / "v").mkdir()
    assert link_from_index(tmp_path / "otro" / "n.md", tmp_path / "v") == ""


# --- Deuda baja ---


def test_empty_frontmatter_before_a_rule_keeps_the_body_date(vault):
    index = vault / "Conocimiento" / "Física" / "Índice.md"
    body = "# F\n\nupdated: 2020-01-01\n\n---\n\nB\n"
    index.write_text("---\n---\n" + body, encoding="utf-8")
    _tool("notes.create")("Caos", "x", folder="Conocimiento/Física")

    assert index.read_text(encoding="utf-8").startswith("---\n---\n" + body)


def test_folder_containing_template_as_a_substring_is_linked(vault):
    folder = vault / "Conocimiento" / "Contemplates"
    folder.mkdir()
    (folder / "Índice.md").write_text("# C\n", encoding="utf-8")
    result = _tool("notes.create")("Zen", "x", folder="Conocimiento/Contemplates")

    assert "Enlazada desde" in result


@pytest.mark.parametrize("folder", [".", "../fuera"])
def test_templates_folder_not_inside_the_vault_disables_linking(vault, folder):
    (vault / ".agents").mkdir()
    (vault / ".agents" / "vault.yaml").write_text(
        f'templates_folder: "{folder}"\n', encoding="utf-8"
    )
    from obsidian_mcp.vault_config import invalidate_vault_config_cache

    invalidate_vault_config_cache()
    result = _tool("notes.create")("Backup", "x", folder="Conocimiento/Sistemas")
    invalidate_vault_config_cache()

    assert "Enlazada desde" not in result and "[[Backup]]" not in _moc(vault)


def test_templates_folder_symlinked_outside_still_allows_linking(vault, tmp_path):
    shared = tmp_path / "plantillas_compartidas"
    shared.mkdir()
    (vault / "ZZ").symlink_to(shared, target_is_directory=True)
    (vault / ".agents").mkdir()
    (vault / ".agents" / "vault.yaml").write_text(
        'templates_folder: "ZZ"\n', encoding="utf-8"
    )
    from obsidian_mcp.vault_config import invalidate_vault_config_cache

    invalidate_vault_config_cache()
    result = _tool("notes.create")("Backup", "x", folder="Conocimiento/Sistemas")
    invalidate_vault_config_cache()

    assert "Enlazada desde" in result
