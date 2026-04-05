# tests/test_middleware.py
from unittest.mock import patch

import pytest

from obsidian_mcp.middleware import (
    invalidate_rules_cache,
    load_vault_rules,
    load_vault_rules_prose,
)

SAMPLE_RULES_FILE = """\
---
name: reglas-globales-agentes
validations:
  - id: no_emoji_headings
    applies_to: [create, append, edit]
    scope: headings
    pattern: "[\\U0001F300-\\U0001FFFF]"
    warning: "Emojis en cabeceras"
  - id: required_frontmatter
    applies_to: [create]
    scope: frontmatter
    required_fields: [type, status, tags]
    warning: "Frontmatter incompleto: faltan {missing_fields}"
---

# Reglas Globales para Agentes

Cero emojis en cabeceras. Frontmatter obligatorio.
"""


@pytest.fixture
def rules_file(tmp_path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    rules_path = agents_dir / "REGLAS_GLOBALES.md"
    rules_path.write_text(SAMPLE_RULES_FILE, encoding="utf-8")
    return tmp_path


class TestLoadVaultRules:
    def test_loads_validations_from_frontmatter(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            rules = load_vault_rules()
        assert len(rules) == 2
        assert rules[0]["id"] == "no_emoji_headings"
        assert rules[1]["id"] == "required_frontmatter"

    def test_caches_on_second_call(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            rules1 = load_vault_rules()
            rules2 = load_vault_rules()
        assert rules1 is rules2

    def test_returns_empty_list_when_no_file(self, tmp_path):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=tmp_path):
            rules = load_vault_rules()
        assert rules == []

    def test_returns_empty_list_on_malformed_yaml(self, tmp_path):
        invalidate_rules_cache()
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()
        (agents_dir / "REGLAS_GLOBALES.md").write_text(
            "---\n: bad: yaml: [\n---\n", encoding="utf-8"
        )
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=tmp_path):
            rules = load_vault_rules()
        assert rules == []

    def test_returns_empty_when_no_validations_key(self, tmp_path):
        invalidate_rules_cache()
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()
        (agents_dir / "REGLAS_GLOBALES.md").write_text(
            "---\nname: test\n---\nContent\n", encoding="utf-8"
        )
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=tmp_path):
            rules = load_vault_rules()
        assert rules == []


class TestLoadVaultRulesProse:
    def test_loads_prose_without_frontmatter(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            prose = load_vault_rules_prose()
        assert "# Reglas Globales para Agentes" in prose
        assert "validations:" not in prose

    def test_returns_empty_string_when_no_file(self, tmp_path):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=tmp_path):
            prose = load_vault_rules_prose()
        assert prose == ""


class TestInvalidateCache:
    def test_invalidation_forces_reload(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            rules1 = load_vault_rules()
            invalidate_rules_cache()
            rules2 = load_vault_rules()
        assert rules1 is not rules2
        assert rules1 == rules2
