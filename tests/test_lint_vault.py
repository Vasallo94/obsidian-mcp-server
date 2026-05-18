"""Tests for lint_vault and the auto_fix engine (Issue #9)."""

import pytest

from obsidian_mcp.config import reset_settings
from obsidian_mcp.middleware import (
    apply_autofix,
    invalidate_rules_cache,
    is_rule_autofixable,
)
from obsidian_mcp.tools.analysis_logic import lint_vault

RULES_FILE = """\
---
name: reglas-test
validations:
  - id: no_emoji_headings
    applies_to: [create, append, edit]
    scope: headings
    pattern: "[\\U0001F300-\\U0001FFFF]"
    warning: "Emojis en cabeceras"
  - id: required_frontmatter
    applies_to: [create]
    scope: frontmatter
    required_fields: [type, status]
    warning: "Frontmatter incompleto: faltan {missing_fields}"
---

# Reglas
"""


@pytest.fixture
def vault_with_rules(tmp_path, monkeypatch):
    v = tmp_path / "vault"
    v.mkdir()
    (v / ".agents").mkdir()
    (v / ".agents" / "REGLAS_GLOBALES.md").write_text(RULES_FILE, encoding="utf-8")

    # Clean note
    (v / "clean.md").write_text(
        "---\ntype: nota\nstatus: captura\n---\n\n## Clean Heading\nbody\n",
        encoding="utf-8",
    )
    # Emoji in heading
    (v / "emoji.md").write_text(
        "---\ntype: nota\nstatus: captura\n---\n\n## \U0001f680 Rocket Heading\nbody\n",
        encoding="utf-8",
    )
    # Missing frontmatter fields
    (v / "no_fm.md").write_text(
        "---\ntitle: x\n---\n\n## OK Heading\nbody\n", encoding="utf-8"
    )

    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
    reset_settings()
    invalidate_rules_cache()
    return v


class TestApplyAutofix:
    def test_strips_emoji_from_heading(self):
        rule = {
            "id": "no_emoji_headings",
            "scope": "headings",
            "pattern": "[\U0001f300-\U0001ffff]",
            "warning": "x",
        }
        content = "## \U0001f680 Title\nbody\n## clean\n"
        new, count = apply_autofix(rule, content)
        assert count == 1
        assert "\U0001f680" not in new
        assert "## Title" in new
        assert "## clean" in new  # untouched

    def test_does_not_touch_body_for_heading_rule(self):
        rule = {
            "id": "no_emoji_headings",
            "scope": "headings",
            "pattern": "[\U0001f300-\U0001ffff]",
            "warning": "x",
        }
        content = "## clean\nbody with \U0001f680 emoji\n"
        new, count = apply_autofix(rule, content)
        assert count == 0
        assert "\U0001f680" in new

    def test_body_scope_strips_anywhere(self):
        rule = {
            "id": "no_tags_inline",
            "scope": "body",
            "pattern": "#tag\\w+",
            "warning": "x",
        }
        content = "hello #tag1 world #tag2\n"
        new, count = apply_autofix(rule, content)
        assert count == 2
        assert "#tag" not in new

    def test_not_autofixable_for_frontmatter_rule(self):
        rule = {
            "id": "required_frontmatter",
            "scope": "frontmatter",
            "required_fields": ["type"],
            "warning": "x",
        }
        assert not is_rule_autofixable(rule)
        new, count = apply_autofix(rule, "## x\n")
        assert count == 0
        assert new == "## x\n"


class TestLintVault:
    def test_reports_violations_grouped_by_file(self, vault_with_rules):
        result = lint_vault()
        assert result.success
        text = result.data
        assert "emoji.md" in text
        assert "no_fm.md" in text
        assert "clean.md" not in text  # no violations
        assert "no_emoji_headings" in text
        assert "required_frontmatter" in text

    def test_clean_vault_returns_zero(self, tmp_path, monkeypatch):
        v = tmp_path / "vault"
        v.mkdir()
        (v / ".agents").mkdir()
        (v / ".agents" / "REGLAS_GLOBALES.md").write_text(RULES_FILE, encoding="utf-8")
        (v / "fine.md").write_text(
            "---\ntype: nota\nstatus: captura\n---\n\n## fine\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(v))
        reset_settings()
        invalidate_rules_cache()
        result = lint_vault()
        assert result.success
        assert "0 violaciones" in result.data

    def test_auto_fix_writes_changes(self, vault_with_rules):
        original = (vault_with_rules / "emoji.md").read_text(encoding="utf-8")
        assert "\U0001f680" in original

        result = lint_vault(auto_fix=True)
        assert result.success
        assert "Auto-fix aplicado" in result.data

        new_content = (vault_with_rules / "emoji.md").read_text(encoding="utf-8")
        assert "\U0001f680" not in new_content

    def test_auto_fix_does_not_alter_frontmatter_rule_target(self, vault_with_rules):
        """no_fm.md is missing frontmatter fields -- not autofixable, must stay as-is."""
        original = (vault_with_rules / "no_fm.md").read_text(encoding="utf-8")
        lint_vault(auto_fix=True)
        # Heading rule didn't apply (already clean), frontmatter rule not autofixed
        new = (vault_with_rules / "no_fm.md").read_text(encoding="utf-8")
        assert new == original

    def test_dry_run_does_not_write(self, vault_with_rules):
        original = (vault_with_rules / "emoji.md").read_text(encoding="utf-8")
        result = lint_vault(auto_fix=False)
        assert result.success
        assert "Auto-fix" not in result.data  # not reported in dry run
        new = (vault_with_rules / "emoji.md").read_text(encoding="utf-8")
        assert new == original

    def test_folder_scopes_scan(self, vault_with_rules):
        sub = vault_with_rules / "sub"
        sub.mkdir()
        (sub / "ok.md").write_text(
            "---\ntype: nota\nstatus: captura\n---\n\n## clean\n",
            encoding="utf-8",
        )
        result = lint_vault(folder="sub")
        assert result.success
        assert "0 violaciones" in result.data
        # Whole-vault scan still sees the emoji.md
        all_result = lint_vault()
        assert "emoji.md" in all_result.data

    def test_rule_id_filter(self, vault_with_rules):
        result = lint_vault(rule_ids=["no_emoji_headings"])
        assert result.success
        text = result.data
        assert "no_emoji_headings" in text
        assert "required_frontmatter" not in text

    def test_unknown_rule_id_errors(self, vault_with_rules):
        result = lint_vault(rule_ids=["totally_made_up"])
        assert not result.success
        assert "REGLAS_GLOBALES" in (result.error or "")

    def test_negative_limit_rejected(self, vault_with_rules):
        result = lint_vault(limit=-1)
        assert not result.success
