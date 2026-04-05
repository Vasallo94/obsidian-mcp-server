# tests/test_middleware.py
from unittest.mock import patch

import pytest

from obsidian_mcp.middleware import (
    enrich_response,
    invalidate_rules_cache,
    load_vault_rules,
    load_vault_rules_prose,
    run_validations,
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


EMOJI_RULE = {
    "id": "no_emoji_headings",
    "applies_to": ["create", "append", "edit"],
    "scope": "headings",
    "pattern": "[\U0001f300-\U0001ffff]",
    "warning": "Emojis en cabeceras",
}

EMOJI_TITLE_RULE = {
    "id": "no_emoji_title",
    "applies_to": ["create"],
    "scope": "title",
    "pattern": "[\U0001f300-\U0001ffff]",
    "warning": "Emojis en el titulo",
}

REQUIRED_FM_RULE = {
    "id": "required_frontmatter",
    "applies_to": ["create"],
    "scope": "frontmatter",
    "required_fields": ["type", "status", "tags"],
    "warning": "Frontmatter incompleto: faltan {missing_fields}",
}

VALID_STATUS_RULE = {
    "id": "valid_status",
    "applies_to": ["create", "edit"],
    "scope": "frontmatter",
    "field": "status",
    "allowed_values": ["captura", "en_proceso", "completo", "archivo"],
    "warning": "Valor de 'status' invalido: '{value}'",
}

ALL_RULES = [EMOJI_RULE, EMOJI_TITLE_RULE, REQUIRED_FM_RULE, VALID_STATUS_RULE]


class TestRunValidations:
    def test_no_warnings_on_clean_content(self):
        warnings = run_validations(
            ALL_RULES,
            mode="create",
            title="Mi nota",
            content="## Seccion\n\nTexto normal",
            frontmatter={"type": "apunte", "status": "captura", "tags": ["test"]},
        )
        assert not warnings

    def test_detects_emoji_in_heading(self):
        warnings = run_validations(
            [EMOJI_RULE],
            mode="create",
            content="## \U0001f680 Titulo con emoji\n\nTexto",
        )
        assert len(warnings) == 1
        assert "Emojis en cabeceras" in warnings[0]

    def test_ignores_emoji_in_body_for_headings_scope(self):
        warnings = run_validations(
            [EMOJI_RULE],
            mode="create",
            content="## Titulo limpio\n\nTexto con \U0001f680 emoji",
        )
        assert not warnings

    def test_detects_emoji_in_title(self):
        warnings = run_validations(
            [EMOJI_TITLE_RULE],
            mode="create",
            title="\U0001f4dd Mi nota",
            content="",
        )
        assert len(warnings) == 1
        assert "Emojis en el titulo" in warnings[0]

    def test_detects_missing_frontmatter_fields(self):
        warnings = run_validations(
            [REQUIRED_FM_RULE],
            mode="create",
            frontmatter={"type": "apunte"},
        )
        assert len(warnings) == 1
        assert "status" in warnings[0]
        assert "tags" in warnings[0]

    def test_detects_invalid_status(self):
        warnings = run_validations(
            [VALID_STATUS_RULE],
            mode="create",
            frontmatter={"status": "borrador"},
        )
        assert len(warnings) == 1
        assert "borrador" in warnings[0]

    def test_skips_rules_for_wrong_mode(self):
        warnings = run_validations(
            [REQUIRED_FM_RULE],  # applies_to: [create]
            mode="edit",
            frontmatter={},
        )
        assert not warnings

    def test_skips_allowed_values_when_field_missing(self):
        warnings = run_validations(
            [VALID_STATUS_RULE],
            mode="create",
            frontmatter={},
        )
        assert not warnings


class TestEnrichResponse:
    def test_passthrough_for_unknown_tool(self):
        result = enrich_response(
            tool_name="leer_nota",
            result="nota leida",
        )
        assert result == "nota leida"

    def test_adds_warnings_on_violation(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            result = enrich_response(
                tool_name="crear_nota",
                result="Nota creada: test.md",
                title="\U0001f680 Mi nota",
                content="## \U0001f680 Cabecera\n\nTexto",
                frontmatter={"type": "apunte", "status": "captura", "tags": ["test"]},
            )
        assert "[WARNINGS:" in result
        assert "Emojis en cabeceras" in result

    def test_injects_prose_for_creation_tools(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            result = enrich_response(
                tool_name="crear_nota",
                result="Nota creada: test.md",
                title="Mi nota",
                content="## Limpio\n\nTexto",
                frontmatter={"type": "apunte", "status": "captura", "tags": ["test"]},
            )
        assert "[REGLAS ACTIVAS DEL VAULT]" in result
        assert "Reglas Globales para Agentes" in result

    def test_no_prose_injection_for_edit_tool(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            result = enrich_response(
                tool_name="editar_nota",
                result="Nota editada",
                content="## Limpio\n\nTexto",
            )
        assert "[REGLAS ACTIVAS DEL VAULT]" not in result

    def test_no_prose_injection_for_captura_rapida(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            result = enrich_response(
                tool_name="captura_rapida",
                result="Captura guardada",
                title="Idea rapida",
                frontmatter={"type": "inbox", "status": "captura", "tags": []},
            )
        assert "[REGLAS ACTIVAS DEL VAULT]" not in result

    def test_clean_result_when_no_violations_still_gets_prose(self, rules_file):
        invalidate_rules_cache()
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=rules_file):
            result = enrich_response(
                tool_name="agregar_a_nota",
                result="Contenido agregado",
                content="Texto normal sin problemas",
            )
        assert "[WARNINGS:" not in result
        assert "[REGLAS ACTIVAS DEL VAULT]" in result
