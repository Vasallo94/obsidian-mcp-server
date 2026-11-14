"""notes.create(note_type=...) elige plantilla y carpeta desde taxonomy.templates."""

import asyncio

import pytest
import yaml

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import invalidate_rules_cache
from obsidian_mcp.server import create_server
from obsidian_mcp.utils import invalidate_note_cache

VAULT_YAML = """\
templates_folder: Plantillas
taxonomy:
  types: [runbook, apunte, inbox]
  templates:
    runbook: {template: Runbook.md, folder: Sistemas}
    apunte: {template: Apunte.md, folder: Conocimiento, choose_subfolder: true}
"""


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    for d in (
        "Plantillas",
        "Sistemas",
        "Conocimiento/IA",
        "Conocimiento/Física",
        ".agents",
    ):
        (v / d).mkdir(parents=True)
    (v / ".agents" / "vault.yaml").write_text(VAULT_YAML, encoding="utf-8")
    (v / "Plantillas" / "Runbook.md").write_text(
        "---\ntitle: '{{title}}'\ntype: runbook\nstatus: en_proceso\n---\n\n## Contexto\n",
        encoding="utf-8",
    )
    (v / "Plantillas" / "Apunte.md").write_text(
        "---\ntitle: '{{title}}'\ntype: apunte\nstatus: en_proceso\n---\n\n## Idea principal\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "notes_write,vault_analysis")
    reset_settings()
    invalidate_rules_cache()
    invalidate_note_cache()
    return v


def _tool(name):
    return asyncio.run(create_server().get_tool(name)).fn


def _fm(path):
    return yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])


def test_note_type_picks_template_and_folder(vault):
    result = _tool("notes.create")("Backup del NAS", "", note_type="runbook")

    note = vault / "Sistemas" / "Backup del NAS.md"
    assert note.exists(), result
    assert _fm(note)["type"] == "runbook"
    assert "## Contexto" in note.read_text(encoding="utf-8")


def test_choose_subfolder_requires_folder_and_lists_options(vault):
    result = _tool("notes.create")("Redes neuronales", "", note_type="apunte")

    assert "IA" in result and "Física" in result
    assert not list(vault.rglob("Redes neuronales.md"))


def test_choose_subfolder_with_folder_creates_note(vault):
    _tool("notes.create")(
        "Redes neuronales", "", folder="Conocimiento/IA", note_type="apunte"
    )

    note = vault / "Conocimiento" / "IA" / "Redes neuronales.md"
    assert _fm(note)["type"] == "apunte"
    assert "## Idea principal" in note.read_text(encoding="utf-8")


def test_unknown_note_type_is_rejected(vault):
    result = _tool("notes.create")("X", "", folder="Sistemas", note_type="inventado")

    assert "inventado" in result and "runbook" in result
    assert not (vault / "Sistemas" / "X.md").exists()


def test_valid_type_without_template_sets_type(vault):
    _tool("notes.create")("Idea", "hola", folder="Sistemas", note_type="inbox")

    assert _fm(vault / "Sistemas" / "Idea.md")["type"] == "inbox"


def test_templates_list_shows_mapping(vault):
    result = _tool("templates.list")()

    assert "runbook" in result and "Runbook.md" in result and "Sistemas" in result


def _rewrite_yaml(vault, text):
    (vault / ".agents" / "vault.yaml").write_text(text, encoding="utf-8")
    invalidate_rules_cache()  # also drops the vault.yaml cache


def test_subfolder_listing_hides_private_folders(vault):
    """Auditoría #131 (1): no se listan carpetas privadas."""
    (vault / "Conocimiento" / "SecretoSalud").mkdir()
    (vault / "Conocimiento" / "Privado").mkdir()
    _rewrite_yaml(
        vault, VAULT_YAML + 'private_paths: ["Conocimiento/Secreto*", "**/Privado/*"]\n'
    )

    result = _tool("notes.create")("X", "", note_type="apunte")

    assert "IA" in result
    assert "Secreto" not in result and "Privado" not in result


def test_bad_templates_entry_does_not_disable_private_paths(vault):
    """Auditoría #131 (2): una entrada mala no tumba vault.yaml (ni private_paths)."""
    from obsidian_mcp.vault_config import get_vault_config

    _rewrite_yaml(
        vault,
        "templates_folder: Plantillas\nprivate_paths: ['Diario/**']\n"
        "taxonomy:\n  types: [runbook, apunte]\n  templates:\n"
        "    runbook: Runbook.md\n    apunte: 3\n",
    )

    config = get_vault_config(vault)
    assert config is not None
    assert config.private_paths == ["Diario/**"]
    assert config.taxonomy.templates["runbook"].template == "Runbook.md"
    assert "apunte" not in config.taxonomy.templates


def test_choose_subfolder_rejects_folder_outside_base(vault):
    """Auditoría #131 (3): con choose_subfolder la carpeta va dentro de la base."""
    create = _tool("notes.create")
    for folder in ("Sistemas", "Conocimiento"):
        result = create("X", "", folder=folder, note_type="apunte")
        assert "Conocimiento" in result
        assert not (vault / folder / "X.md").exists()


def test_note_type_overrides_template_type(vault):
    """Auditoría #131 (4): note_type gana al type de la plantilla."""
    _tool("notes.create")(
        "Mixta", "", folder="Conocimiento/IA", template="Runbook.md", note_type="apunte"
    )

    assert _fm(vault / "Conocimiento" / "IA" / "Mixta.md")["type"] == "apunte"


def test_type_names_are_unicode_normalised(vault):
    """Auditoría #131 (6): 'física' en NFD en vault.yaml casa con NFC del caller."""
    import unicodedata

    nfd = unicodedata.normalize("NFD", "física")
    _rewrite_yaml(vault, f"templates_folder: Plantillas\ntaxonomy:\n  types: [{nfd}]\n")

    _tool("notes.create")("N", "x", folder="Sistemas", note_type="física")

    assert (vault / "Sistemas" / "N.md").exists()


def test_type_only_in_templates_is_rejected(vault):
    """Auditoría #131 (8): el vocabulario válido es taxonomy.types."""
    _rewrite_yaml(
        vault,
        VAULT_YAML + "    solo_plantilla: {template: Runbook.md, folder: Sistemas}\n",
    )

    result = _tool("notes.create")("X", "", note_type="solo_plantilla")

    assert not (vault / "Sistemas" / "X.md").exists()
    assert "solo_plantilla" in result


def test_missing_template_creates_no_folder(vault):
    """Auditoría #131 (5): si la plantilla falla no quedan carpetas vacías."""
    _rewrite_yaml(
        vault,
        "templates_folder: Plantillas\ntaxonomy:\n  types: [x]\n"
        "  templates:\n    x: {template: NoExiste.md, folder: Nueva/Carpeta}\n",
    )

    _tool("notes.create")("X", "", note_type="x")

    assert not (vault / "Nueva").exists()


def test_nfd_note_type_is_written_in_nfc(vault):
    """Auditoría #131 r2 (1): el type escrito queda en NFC aunque el caller mande NFD."""
    import unicodedata

    _rewrite_yaml(vault, "templates_folder: Plantillas\ntaxonomy:\n  types: [física]\n")

    _tool("notes.create")(
        "N", "x", folder="Sistemas", note_type=unicodedata.normalize("NFD", "física")
    )

    assert _fm(vault / "Sistemas" / "N.md")["type"] == unicodedata.normalize(
        "NFC", "física"
    )


def test_choose_subfolder_rejects_dotdot(vault):
    """Auditoría #131 r2 (3): 'Base/../Otra' no pasa por subcarpeta."""
    _tool("notes.create")(
        "X", "", folder="Conocimiento/../Sistemas", note_type="apunte"
    )

    assert not (vault / "Sistemas" / "X.md").exists()


def test_subfolder_listing_checks_the_folder_itself(vault):
    """Auditoría #131 r2 (4): un patrón que casa con la carpeta, no con su contenido."""
    (vault / "Conocimiento" / "SecretoSalud").mkdir()
    _rewrite_yaml(vault, VAULT_YAML + 'private_paths: ["*/SecretoSalud"]\n')

    result = _tool("notes.create")("X", "", note_type="apunte")

    assert "IA" in result and "SecretoSalud" not in result


def test_subfolder_listing_skips_symlinks(vault):
    """Auditoría #131 r2 (4): los enlaces simbólicos no se ofrecen."""
    (vault / "Conocimiento" / "Atajo").symlink_to(
        vault / "Sistemas", target_is_directory=True
    )

    result = _tool("notes.create")("X", "", note_type="apunte")

    assert "IA" in result and "Atajo" not in result


def test_empty_types_key_keeps_config(vault):
    """Auditoría #131 r2 (9): 'types:' vacío no tumba vault.yaml."""
    from obsidian_mcp.vault_config import get_vault_config

    _rewrite_yaml(
        vault,
        "templates_folder: Plantillas\nprivate_paths: ['X/*']\ntaxonomy:\n  types:\n",
    )

    config = get_vault_config(vault)
    assert config is not None and config.private_paths == ["X/*"]


def _body(path):
    return path.read_text(encoding="utf-8").split("---", 2)[2]


def test_plain_content_goes_after_title_before_skeleton(vault):
    (vault / "Plantillas" / "Runbook.md").write_text(
        "---\ntype: runbook\n---\n# {{title}}\n\n## Contexto\n\n## Incidentes\n",
        encoding="utf-8",
    )
    _tool("notes.create")("Backup", "Resumen rápido.", note_type="runbook")

    body = _body(vault / "Sistemas" / "Backup.md")
    assert (
        body.index("# Backup")
        < body.index("Resumen rápido.")
        < body.index("## Contexto")
    )
    assert "## Incidentes" in body


def test_content_section_fills_matching_template_section(vault):
    (vault / "Plantillas" / "Runbook.md").write_text(
        "---\ntype: runbook\n---\n# {{title}}\n\n## Contexto\n\nGuía.\n\n"
        "## Incidentes\n\n[[Home|Volver]]\n",
        encoding="utf-8",
    )
    _tool("notes.create")(
        "Backup", "## Contexto\n\nNAS en casa.\n", note_type="runbook"
    )

    body = _body(vault / "Sistemas" / "Backup.md")
    assert body.count("## Contexto") == 1 and "Guía." not in body
    assert (
        body.index("# Backup")
        < body.index("NAS en casa.")
        < body.index("## Incidentes")
    )
    assert "[[Home|Volver]]" in body


def test_content_with_only_h1_keeps_skeleton(vault):
    _tool("notes.create")("Backup", "# Mi título\n\nResumen.", note_type="runbook")

    body = _body(vault / "Sistemas" / "Backup.md")
    assert body.count("\n# ") + body.startswith("# ") == 1
    assert (
        body.index("# Mi título") < body.index("Resumen.") < body.index("## Contexto")
    )


def test_template_intro_without_title_is_kept(vault):
    (vault / "Plantillas" / "Runbook.md").write_text(
        "---\ntype: runbook\n---\n> la cita\n\n## Contexto\n", encoding="utf-8"
    )
    _tool("notes.create")("Cita", "## Contexto\n\nDicho en 1900", note_type="runbook")

    body = _body(vault / "Sistemas" / "Cita.md")
    assert body.index("> la cita") < body.index("Dicho en 1900")


def test_new_sections_go_above_template_sections(vault):
    _tool("notes.create")("Backup", "## Pasos\n\n1. uno", note_type="runbook")

    body = _body(vault / "Sistemas" / "Backup.md")
    assert body.index("## Pasos") < body.index("## Contexto")


def test_content_indentation_is_kept(vault):
    _tool("notes.create")("Backup", "    sudo reboot\n    uptime", note_type="runbook")

    assert "    sudo reboot\n    uptime" in _body(vault / "Sistemas" / "Backup.md")


def test_longer_fence_hides_inner_heading(vault):
    content = "````md\n```\n## Contexto\n```\n````\ntexto"
    _tool("notes.create")("Backup", content, note_type="runbook")

    body = _body(vault / "Sistemas" / "Backup.md")
    assert body.count("## Contexto") == 2  # the template's and the one in code


def test_skeleton_without_h1_gets_plain_content_first(vault):
    _tool("notes.create")("Backup", "Resumen.", note_type="runbook")

    body = _body(vault / "Sistemas" / "Backup.md")
    assert body.index("Resumen.") < body.index("## Contexto")


def test_code_block_hash_is_not_a_heading(vault):
    _tool("notes.create")(
        "Backup", "```bash\n# comentario\nls\n```", note_type="runbook"
    )

    body = _body(vault / "Sistemas" / "Backup.md")
    assert "## Contexto" in body


CONCEPTO = "---\ntype: runbook\n---\n# {{title}}\n\n## Definición\n\n## Ejemplo\n\n## Relacionado\n"


def _concepto(vault, content):
    (vault / "Plantillas" / "Runbook.md").write_text(CONCEPTO, encoding="utf-8")
    _tool("notes.create")("C", content, note_type="runbook")
    return _body(vault / "Sistemas" / "C.md")


def test_subsections_stay_with_their_parent(vault):
    body = _concepto(vault, "## Definición\nd\n### Detalle\nx\n## Ejemplo\ne")
    assert (
        body.index("## Definición")
        < body.index("### Detalle")
        < body.index("## Ejemplo")
    )
    assert body.count("## Ejemplo") == 1


def test_template_subsections_go_with_replaced_section(vault):
    (vault / "Plantillas" / "Runbook.md").write_text(
        "---\ntype: runbook\n---\n# T\n\n## A\nguía\n### A1\nguía A1\n## B\n",
        encoding="utf-8",
    )
    _tool("notes.create")("C", "## A\nmío", note_type="runbook")
    body = _body(vault / "Sistemas" / "C.md")
    assert "guía" not in body and "## B" in body


def test_h1_after_text_is_not_the_title(vault):
    body = _concepto(vault, "Pensamiento\n# Idea grande\ndetalle")
    assert body.index("# C") < body.index("Pensamiento") < body.index("# Idea grande")


def test_duplicate_content_sections_keep_order(vault):
    body = _concepto(vault, "## Definición\nprimera\n## Definición\nsegunda")
    assert body.index("primera") < body.index("segunda") < body.index("## Ejemplo")


def test_comment_or_open_fence_is_appended_not_merged(vault):
    body = _concepto(vault, "<!--\n## Ejemplo\nborrador\n-->\nok")
    assert body.index("## Relacionado") < body.index("<!--")


def test_code_span_is_not_a_fence(vault):
    body = _concepto(vault, "## Definición\n```npm i```\n## Ejemplo\ne")
    assert body.count("## Ejemplo") == 1


def test_closing_hashes_match_template_heading(vault):
    body = _concepto(vault, "## Definición ##\nd")
    assert body.count("Definición") == 1


def test_new_section_follows_preceding_matched_section(vault):
    body = _concepto(vault, "## Definición\nd\n## Nueva\nn\n## Relacionado\nr")
    assert (
        body.index("## Definición")
        < body.index("## Nueva")
        < body.index("## Ejemplo")
        < body.index("## Relacionado")
    )


def test_details_block_is_appended_not_merged(vault):
    body = _concepto(vault, "<details>\n\n## Ejemplo\ne\n\n</details>")
    assert body.index("## Relacionado") < body.index("<details>")


def test_heading_colon_and_bold_still_match(vault):
    body = _concepto(vault, "## Definición:\nd\n## **Ejemplo**\ne")
    assert body.count("Definición") == 1 and body.count("Ejemplo") == 1


def test_long_space_run_in_heading_is_fast():
    import time

    from obsidian_mcp.tools.creation_logic import _split_markdown

    start = time.monotonic()
    _split_markdown("# a" + " " * 50000 + "b")
    assert time.monotonic() - start < 1
