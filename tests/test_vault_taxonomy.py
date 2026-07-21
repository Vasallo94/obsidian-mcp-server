"""Taxonomy resolvers: role lookup and tag-registry fallback."""

from pathlib import Path

from obsidian_mcp.vault_config import (
    invalidate_vault_config_cache,
    resolve_local_doc,
    resolve_role,
)


def _make_vault(tmp_path: Path, yaml_body: str) -> Path:
    (tmp_path / ".agents").mkdir()
    (tmp_path / ".agents" / "vault.yaml").write_text(yaml_body, encoding="utf-8")
    invalidate_vault_config_cache()
    return tmp_path


def test_resolve_role_returns_existing_folder(tmp_path):
    (tmp_path / "02_Conocimiento").mkdir()
    vault = _make_vault(
        tmp_path, "taxonomy:\n  roles:\n    knowledge: 02_Conocimiento\n"
    )
    assert resolve_role(vault, "knowledge") == vault / "02_Conocimiento"


def test_resolve_role_missing_folder_is_none(tmp_path):
    vault = _make_vault(
        tmp_path, "taxonomy:\n  roles:\n    knowledge: 02_Conocimiento\n"
    )
    assert resolve_role(vault, "knowledge") is None  # declared but absent
    assert resolve_role(vault, "inbox") is None  # not declared


def test_resolve_local_doc_prefers_config(tmp_path):
    doc = tmp_path / "02_Conocimiento" / "Obsidian" / "Registro de Tags del Vault.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("- `ia`\n", encoding="utf-8")
    vault = _make_vault(
        tmp_path,
        "profile:\n  local_docs:\n    tag_registry: "
        '"02_Conocimiento/Obsidian/Registro de Tags del Vault.md"\n',
    )
    assert (
        resolve_local_doc(vault, "tag_registry", "Registro de Tags del Vault.md") == doc
    )


def test_resolve_local_doc_falls_back_to_name_search(tmp_path):
    # No config entry: a folder rename must not make the registry unreadable.
    doc = tmp_path / "somewhere" / "Registro de Tags del Vault.md"
    doc.parent.mkdir(parents=True)
    doc.write_text("- `ia`\n", encoding="utf-8")
    vault = _make_vault(tmp_path, "version: '1.0'\n")
    assert (
        resolve_local_doc(vault, "tag_registry", "Registro de Tags del Vault.md") == doc
    )


def test_resolve_local_doc_absent_everywhere_is_none(tmp_path):
    vault = _make_vault(tmp_path, "version: '1.0'\n")
    assert (
        resolve_local_doc(vault, "tag_registry", "Registro de Tags del Vault.md")
        is None
    )
