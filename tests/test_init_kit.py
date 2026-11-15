"""vault.init_kit copia el kit base solo donde falta."""

import asyncio

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import invalidate_rules_cache
from obsidian_mcp.server import create_server
from obsidian_mcp.tools.agents_logic import KIT_DIR


@pytest.fixture
def vault(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    v.mkdir()
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    monkeypatch.setenv("OBSIDIAN_MCP_TOOL_SETS", "agents_admin,notes_write")
    reset_settings()
    invalidate_rules_cache()
    return v


def _tool(name):
    return asyncio.run(create_server().get_tool(name)).fn


def test_preview_writes_nothing(vault):
    result = _tool("vault.init_kit")()

    assert "Se crearían" in result and "Plantillas/Runbook.md" in result
    assert not list(vault.iterdir())


def test_confirm_creates_kit_and_rules_are_active(vault):
    _tool("vault.init_kit")(confirm=True)

    assert (vault / ".agents" / "REGLAS_GLOBALES.md").exists()
    assert (vault / "AGENTS.md").exists()
    assert len(list((vault / "Plantillas").glob("*.md"))) == len(
        list((KIT_DIR / "templates").glob("*.md"))
    )
    assert "Frontmatter incompleto" in _tool("notes.validate")("# Hola", title="Hola")


def test_existing_files_are_never_overwritten(vault):
    (vault / "AGENTS.md").write_text("mío", encoding="utf-8")
    (vault / "Templates").mkdir()
    (vault / "Templates" / "Runbook.md").write_text("mío", encoding="utf-8")

    result = _tool("vault.init_kit")(confirm=True)

    assert (vault / "AGENTS.md").read_text(encoding="utf-8") == "mío"
    assert (vault / "Templates" / "Runbook.md").read_text(encoding="utf-8") == "mío"
    assert (vault / "Templates" / "Apunte.md").exists()  # detected folder reused
    assert not (vault / "Plantillas").exists()
    assert "Ya existían" in result


def test_configured_templates_folder_is_used(vault):
    (vault / ".agents").mkdir()
    (vault / ".agents" / "vault.yaml").write_text(
        'templates_folder: "ZZ"\n', encoding="utf-8"
    )

    _tool("vault.init_kit")(confirm=True)

    assert (vault / "ZZ" / "Idea.md").exists()


def test_symlinked_folder_outside_vault_is_refused(vault, tmp_path):
    outside = tmp_path / "fuera"
    outside.mkdir()
    (vault / "Plantillas").symlink_to(outside)

    result = _tool("vault.init_kit")(confirm=True)

    assert "escapes vault" in result and "No se ha escrito nada" in result
    assert not list(outside.iterdir())
    assert not (vault / "AGENTS.md").exists()


def test_kit_templates_use_placeholders_not_fixed_dates():
    for template in (KIT_DIR / "templates").glob("*.md"):
        text = template.read_text(encoding="utf-8")
        assert "{{title}}" in text and "{{date}}" in text, template.name
        assert "2026-" not in text, template.name


def _vault_yaml(vault, text):
    (vault / ".agents").mkdir(exist_ok=True)
    (vault / ".agents" / "vault.yaml").write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "folder", ["Privado", ".obsidian", "../fuera", "/tmp/kit-fuera", "."]
)
def test_protected_or_outside_folder_writes_nothing(vault, folder):
    _vault_yaml(vault, f'templates_folder: "{folder}"\n')
    before = sorted(p.relative_to(vault) for p in vault.rglob("*"))

    result = _tool("vault.init_kit")(confirm=True)

    assert "❌" in result or "Error" in result
    assert sorted(p.relative_to(vault) for p in vault.rglob("*")) == before


def test_private_paths_are_respected(vault):
    _vault_yaml(vault, 'templates_folder: "Secreto"\nprivate_paths: ["Secreto/**"]\n')

    result = _tool("vault.init_kit")(confirm=True)

    assert not (vault / "Secreto").exists() and not (vault / "AGENTS.md").exists()
    assert "No se ha escrito nada" in result


def test_templates_folder_that_is_a_file_writes_nothing(vault):
    (vault / "Plantillas").write_text("no soy carpeta", encoding="utf-8")

    result = _tool("vault.init_kit")(confirm=True)

    assert "no es una carpeta" in result and not (vault / "AGENTS.md").exists()


def test_kit_templates_are_found_by_templates_list(vault):
    _tool("vault.init_kit")(confirm=True)

    assert "Runbook.md" in _tool("templates.list")()


def test_file_created_meanwhile_is_not_replaced(vault, monkeypatch):
    import builtins

    real_open = builtins.open

    def racing_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if mode == "x" and str(path).endswith("AGENTS.md"):
            with real_open(path, "w", encoding="utf-8") as other:  # appears in between
                other.write("mío")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", racing_open)
    _tool("vault.init_kit")(confirm=True)

    assert (vault / "AGENTS.md").read_text(encoding="utf-8") == "mío"


def test_kit_has_no_personal_leftovers():
    rules = (KIT_DIR / "REGLAS_GLOBALES.md").read_text(encoding="utf-8")
    for leftover in (
        "Briñol",
        "tálamo",
        "diagrama-arquitectura",
        "Secundo",
        "Synology",
        "05_Media",
    ):
        assert leftover not in rules


def test_write_failure_rolls_back_and_leaves_nothing(vault):
    (vault / "Plantillas").mkdir()
    (vault / "Plantillas").chmod(0o500)
    try:
        result = _tool("vault.init_kit")(confirm=True)
    finally:
        (vault / "Plantillas").chmod(0o700)

    assert "No se ha dejado nada" in result
    assert not (vault / "AGENTS.md").exists()
    assert not (vault / ".agents" / "REGLAS_GLOBALES.md").exists()


def test_dotdot_back_to_root_is_refused(vault):
    _vault_yaml(vault, 'templates_folder: "Plantillas/.."\n')

    result = _tool("vault.init_kit")(confirm=True)

    assert "raíz del vault" in result and not (vault / "Idea.md").exists()


def test_templater_scripts_folder_is_not_picked(vault):
    for name in ("Templater", "Templates", ".templates"):
        (vault / name).mkdir()

    _tool("vault.init_kit")(confirm=True)

    assert (vault / "Templates" / "Idea.md").exists()
    assert not any(list((vault / n).iterdir()) for n in ("Templater", ".templates"))


def test_no_personal_leftovers_in_any_kit_file():
    for path in KIT_DIR.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for leftover in (
            "Briñol",
            "tálamo",
            "Secundo",
            "Synology",
            "Llavero",
            "05_Media",
        ):
            assert leftover not in text, (path.name, leftover)


def test_templater_folder_alone_is_still_the_templates_folder(vault):
    (vault / "Templater").mkdir()
    (vault / "Templater" / "Diario.md").write_text("# {{title}}\n", encoding="utf-8")

    assert "Diario.md" in _tool("templates.list")()


def test_rollback_removes_folders_it_created(vault, monkeypatch):
    import builtins

    real_open = builtins.open
    calls = {"n": 0}

    def failing_open(path, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if mode == "x":
            calls["n"] += 1
            if calls["n"] == 5:
                raise OSError(28, "No space left on device")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", failing_open)
    result = _tool("vault.init_kit")(confirm=True)

    assert "No se ha dejado nada" in result
    assert not list(vault.iterdir())
