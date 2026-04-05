# MCP Rule Enforcement Middleware — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce vault rules from `.agents/REGLAS_GLOBALES.md` automatically on write operations, returning soft warnings to any MCP client.

**Architecture:** A `middleware.py` module loads machine-readable `validations:` from the vault's REGLAS_GLOBALES frontmatter, runs checks against content on write tools, and enriches tool responses with warnings and rule prose. Integration into existing tools via a single `enrich_response()` call at each tool's return point.

**Tech Stack:** Python 3.11+, PyYAML (already a dependency), `re` stdlib, pytest

**Spec:** `docs/superpowers/specs/2026-04-04-mcp-rule-enforcement-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `obsidian_mcp/middleware.py` | CREATE | Rule loading, caching, validation engine, response enrichment |
| `obsidian_mcp/tools/creation.py` | MODIFY | Call `enrich_response` in 6 tool functions |
| `tests/test_middleware.py` | CREATE | Unit tests for all middleware logic |

---

### Task 1: Rule loading and caching

**Files:**
- Create: `obsidian_mcp/middleware.py`
- Test: `tests/test_middleware.py`

- [ ] **Step 1: Write the failing test for rule loading**

```python
# tests/test_middleware.py
import pytest
from pathlib import Path
from unittest.mock import patch
from obsidian_mcp.middleware import load_vault_rules, load_vault_rules_prose, invalidate_rules_cache


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
        (agents_dir / "REGLAS_GLOBALES.md").write_text("---\n: bad: yaml: [\n---\n", encoding="utf-8")
        with patch("obsidian_mcp.middleware.get_vault_path", return_value=tmp_path):
            rules = load_vault_rules()
        assert rules == []

    def test_returns_empty_when_no_validations_key(self, tmp_path):
        invalidate_rules_cache()
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()
        (agents_dir / "REGLAS_GLOBALES.md").write_text("---\nname: test\n---\nContent\n", encoding="utf-8")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_middleware.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'obsidian_mcp.middleware'`

- [ ] **Step 3: Implement rule loading**

```python
# obsidian_mcp/middleware.py
"""
Middleware for vault rule enforcement.

Loads machine-readable validations from .agents/REGLAS_GLOBALES.md,
runs checks against content on write operations, and enriches tool
responses with warnings and rule prose.

This is agent-agnostic: any MCP client receives the same enforcement.
"""

import re
from typing import Any

import yaml

from .config import get_vault_path
from .utils import get_logger

logger = get_logger(__name__)

# --- Cache ---

_rules_cache: list[dict[str, Any]] | None = None
_prose_cache: str | None = None

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


def _read_rules_file() -> tuple[dict[str, Any], str]:
    """Read and parse REGLAS_GLOBALES.md, returning (frontmatter_dict, prose_body)."""
    vault_path = get_vault_path()
    if not vault_path:
        return {}, ""

    rules_path = vault_path / ".agents" / "REGLAS_GLOBALES.md"
    if not rules_path.exists():
        return {}, ""

    try:
        content = rules_path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("Could not read rules file: %s", e)
        return {}, ""

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content

    try:
        frontmatter = yaml.safe_load(match.group(1))
        if not isinstance(frontmatter, dict):
            return {}, match.group(2).strip()
        return frontmatter, match.group(2).strip()
    except yaml.YAMLError as e:
        logger.warning("Malformed YAML in REGLAS_GLOBALES.md: %s", e)
        return {}, ""


def load_vault_rules(force_reload: bool = False) -> list[dict[str, Any]]:
    """Load validations from vault rules frontmatter. Cached in memory."""
    global _rules_cache
    if _rules_cache is not None and not force_reload:
        return _rules_cache

    frontmatter, _ = _read_rules_file()
    validations = frontmatter.get("validations", [])
    _rules_cache = validations if isinstance(validations, list) else []
    return _rules_cache


def load_vault_rules_prose(force_reload: bool = False) -> str:
    """Load the prose body of REGLAS_GLOBALES.md (without frontmatter). Cached."""
    global _prose_cache
    if _prose_cache is not None and not force_reload:
        return _prose_cache

    _, prose = _read_rules_file()
    _prose_cache = prose
    return _prose_cache


def invalidate_rules_cache() -> None:
    """Invalidate both caches. Called when REGLAS_GLOBALES.md is edited."""
    global _rules_cache, _prose_cache
    _rules_cache = None
    _prose_cache = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_middleware.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
git add obsidian_mcp/middleware.py tests/test_middleware.py
git commit -m "feat: add rule loading and caching for vault middleware"
```

---

### Task 2: Validation engine

**Files:**
- Modify: `obsidian_mcp/middleware.py`
- Modify: `tests/test_middleware.py`

- [ ] **Step 1: Write failing tests for validation checks**

Append to `tests/test_middleware.py`:

```python
from obsidian_mcp.middleware import run_validations


EMOJI_RULE = {
    "id": "no_emoji_headings",
    "applies_to": ["create", "append", "edit"],
    "scope": "headings",
    "pattern": "[\U0001F300-\U0001FFFF]",
    "warning": "Emojis en cabeceras",
}

EMOJI_TITLE_RULE = {
    "id": "no_emoji_title",
    "applies_to": ["create"],
    "scope": "title",
    "pattern": "[\U0001F300-\U0001FFFF]",
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
        assert warnings == []

    def test_detects_emoji_in_heading(self):
        warnings = run_validations(
            [EMOJI_RULE],
            mode="create",
            content="## \U0001F680 Titulo con emoji\n\nTexto",
        )
        assert len(warnings) == 1
        assert "Emojis en cabeceras" in warnings[0]

    def test_ignores_emoji_in_body_for_headings_scope(self):
        warnings = run_validations(
            [EMOJI_RULE],
            mode="create",
            content="## Titulo limpio\n\nTexto con \U0001F680 emoji",
        )
        assert warnings == []

    def test_detects_emoji_in_title(self):
        warnings = run_validations(
            [EMOJI_TITLE_RULE],
            mode="create",
            title="\U0001F4DD Mi nota",
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
        assert warnings == []

    def test_skips_allowed_values_when_field_missing(self):
        warnings = run_validations(
            [VALID_STATUS_RULE],
            mode="create",
            frontmatter={},
        )
        assert warnings == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_middleware.py::TestRunValidations -v`
Expected: FAIL with `ImportError: cannot import name 'run_validations'`

- [ ] **Step 3: Implement validation engine**

Append to `obsidian_mcp/middleware.py`:

```python
# --- Validation Engine ---


def run_validations(
    rules: list[dict[str, Any]],
    mode: str,
    title: str = "",
    content: str = "",
    frontmatter: dict[str, Any] | None = None,
) -> list[str]:
    """Run applicable validations and return list of warning strings."""
    warnings = []
    for rule in rules:
        if mode not in rule.get("applies_to", []):
            continue
        warning = _check_rule(rule, title, content, frontmatter or {})
        if warning:
            warnings.append(warning)
    return warnings


def _check_rule(
    rule: dict[str, Any], title: str, content: str, fm: dict[str, Any]
) -> str | None:
    """Execute a single rule. Returns warning string or None."""
    scope = rule.get("scope", "")

    if scope in ("headings", "title", "body") and "pattern" in rule:
        return _check_pattern(rule, title, content)

    if scope == "frontmatter":
        if "required_fields" in rule:
            return _check_required_fields(rule, fm)
        if "field" in rule and "allowed_values" in rule:
            return _check_allowed_values(rule, fm)

    return None


def _check_pattern(rule: dict[str, Any], title: str, content: str) -> str | None:
    """Validate regex against the indicated scope."""
    try:
        pattern = re.compile(rule["pattern"])
    except re.error as e:
        logger.warning("Invalid regex in rule '%s': %s", rule.get("id", "?"), e)
        return None

    scope = rule["scope"]

    if scope == "title":
        if pattern.search(title):
            return rule["warning"]
    elif scope == "headings":
        for line in content.splitlines():
            if line.startswith("#") and pattern.search(line):
                return rule["warning"]
    elif scope == "body":
        if pattern.search(content):
            return rule["warning"]

    return None


def _check_required_fields(rule: dict[str, Any], fm: dict[str, Any]) -> str | None:
    """Check that required frontmatter fields are present and non-empty."""
    missing = [f for f in rule["required_fields"] if f not in fm or not fm[f]]
    if missing:
        return rule["warning"].format(missing_fields=", ".join(missing))
    return None


def _check_allowed_values(rule: dict[str, Any], fm: dict[str, Any]) -> str | None:
    """Check that a frontmatter field value is in the allowed list."""
    field = rule["field"]
    value = fm.get(field, "")
    if value and value not in rule["allowed_values"]:
        return rule["warning"].format(value=value)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_middleware.py -v`
Expected: All 16 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
git add obsidian_mcp/middleware.py tests/test_middleware.py
git commit -m "feat: add validation engine for vault rules"
```

---

### Task 3: Response enrichment

**Files:**
- Modify: `obsidian_mcp/middleware.py`
- Modify: `tests/test_middleware.py`

- [ ] **Step 1: Write failing tests for enrich_response**

Append to `tests/test_middleware.py`:

```python
from obsidian_mcp.middleware import enrich_response


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
                title="\U0001F680 Mi nota",
                content="## \U0001F680 Cabecera\n\nTexto",
                frontmatter={"type": "apunte", "status": "captura", "tags": ["test"]},
            )
        assert "[WARNINGS:" in result
        assert "Emojis en cabeceras" in result
        assert "Emojis en el titulo" in result

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_middleware.py::TestEnrichResponse -v`
Expected: FAIL with `ImportError: cannot import name 'enrich_response'`

- [ ] **Step 3: Implement enrich_response**

Append to `obsidian_mcp/middleware.py`:

```python
# --- Response Enrichment ---

CONTENT_CREATION_TOOLS = frozenset({"crear_nota", "agregar_a_nota", "agregar_en_seccion"})

TOOL_MODE_MAP: dict[str, str] = {
    "crear_nota": "create",
    "captura_rapida": "create",
    "agregar_a_nota": "append",
    "agregar_en_seccion": "append",
    "editar_nota": "edit",
    "actualizar_frontmatter": "edit",
}


def enrich_response(
    tool_name: str,
    result: str,
    title: str = "",
    content: str = "",
    frontmatter: dict[str, Any] | None = None,
) -> str:
    """Main entry point. Run validations and inject rules prose into tool response."""
    mode = TOOL_MODE_MAP.get(tool_name)
    if not mode:
        return result

    rules = load_vault_rules()
    warnings = run_validations(rules, mode, title, content, frontmatter)

    parts = [result]

    if warnings:
        parts.append("---")
        parts.append(f"[WARNINGS: {len(warnings)} violacion(es) detectada(s)]")
        for w in warnings:
            parts.append(f"- {w}")

    if tool_name in CONTENT_CREATION_TOOLS:
        prose = load_vault_rules_prose()
        if prose:
            parts.append("---")
            parts.append("[REGLAS ACTIVAS DEL VAULT]")
            parts.append(prose)

    return "\n".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_middleware.py -v`
Expected: All 22 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
git add obsidian_mcp/middleware.py tests/test_middleware.py
git commit -m "feat: add response enrichment with warnings and rule injection"
```

---

### Task 4: Integrate middleware into creation tools

**Files:**
- Modify: `obsidian_mcp/tools/creation.py:34-119` (6 tool functions)

The pattern is the same for each tool: call `enrich_response` on the successful result before returning. The frontmatter extraction uses the existing `_extract_frontmatter_from_content` from `creation_logic.py`.

- [ ] **Step 1: Add import to creation.py**

At the top of `obsidian_mcp/tools/creation.py`, after the existing imports from `creation_logic`, add:

```python
from ..middleware import enrich_response, invalidate_rules_cache
```

- [ ] **Step 2: Integrate into `crear_nota`**

In `obsidian_mcp/tools/creation.py`, replace the `crear_nota` try block:

```python
    @mcp.tool()
    def crear_nota(
        titulo: str,
        contenido: str,
        *,
        carpeta: str = "",
        etiquetas: str = "",
        plantilla: str = "",
        agente_creador: str = "",
        descripcion: str = "",
    ) -> str:
        """
        Crea una nueva nota en el vault.

        ⚠️ ADVERTENCIA CRITICA PARA AGENTES DE IA: ⚠️
        1. NO uses herramientas genericas de sistema de archivos (como write_file).
           SIEMPRE usa esta herramienta para crear notas en el vault.
        2. ANTES de ejecutar esta accion, DEBES haber leido las reglas globales
           con `leer_contexto_vault` y `obtener_reglas_globales`.
        3. Verifica si existe una SKILL aplicable (ej: investigador, escritor)
           y sigue sus instrucciones especificas.

        Args:
            titulo: Titulo de la nota.
            contenido: Contenido de la nota.
            carpeta: Carpeta donde crear la nota (vacio = raiz).
            etiquetas: Etiquetas separadas por comas.
            plantilla: Nombre del archivo de plantilla (ej: "Diario.md").
            agente_creador: Si se creo usando un agente especifico (ej: "escritor").
            descripcion: Descripcion breve de la nota (para placeholder
                {{description}}).
        """
        try:
            result = create_note(
                titulo,
                contenido,
                carpeta,
                etiquetas,
                plantilla,
                agente_creador,
                descripcion,
            ).to_display(success_prefix="✅")
            return enrich_response(
                tool_name="crear_nota",
                result=result,
                title=titulo,
                content=contenido,
                frontmatter=_extract_fm(contenido),
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al crear nota: {e}"
```

- [ ] **Step 3: Add `_extract_fm` helper at module level in creation.py**

Add after the imports:

```python
def _extract_fm(contenido: str) -> dict:
    """Extract frontmatter dict from content for middleware validation."""
    from .creation_logic import _extract_frontmatter_from_content
    fm, _ = _extract_frontmatter_from_content(contenido)
    return fm
```

- [ ] **Step 4: Integrate into `agregar_a_nota`**

Wrap the return in the try block:

```python
        try:
            result = append_to_note(nombre_archivo, contenido, al_final).to_display(
                success_prefix="✅"
            )
            return enrich_response(
                tool_name="agregar_a_nota",
                result=result,
                content=contenido,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al agregar contenido: {e}"
```

- [ ] **Step 5: Integrate into `agregar_en_seccion`**

Wrap the return in the try block:

```python
        try:
            result = append_to_section(
                nombre_archivo, seccion, contenido, crear_si_no_existe
            ).to_display()
            return enrich_response(
                tool_name="agregar_en_seccion",
                result=result,
                content=contenido,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al añadir a sección: {e}"
```

- [ ] **Step 6: Integrate into `editar_nota`**

For edit_note, the content is the full new content assembled from operations. We validate the result after operations are applied. Since `edit_note` receives operations (not full content), we validate the final note content after applying them. The simplest approach: just pass the operations' "new" values concatenated for heading checks:

```python
        try:
            result = edit_note(nombre_archivo, operaciones).to_display(
                success_prefix="✅"
            )
            combined_new = "\n".join(op.get("new", "") for op in operaciones)
            return enrich_response(
                tool_name="editar_nota",
                result=result,
                content=combined_new,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al editar nota: {e}"
```

- [ ] **Step 7: Integrate into `captura_rapida`**

```python
        try:
            result = quick_capture(texto, etiquetas).to_display()
            return enrich_response(
                tool_name="captura_rapida",
                result=result,
                title=texto[:80],
                content=texto,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error en captura rápida: {e}"
```

- [ ] **Step 8: Integrate into `actualizar_frontmatter`**

```python
        try:
            result = update_frontmatter_logic(
                nombre_archivo, frontmatter_updates, merge
            ).to_display(success_prefix="✅")
            import json as _json
            try:
                fm = _json.loads(frontmatter_updates)
            except (ValueError, TypeError):
                fm = {}
            return enrich_response(
                tool_name="actualizar_frontmatter",
                result=result,
                frontmatter=fm,
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al actualizar frontmatter: {e}"
```

- [ ] **Step 9: Add cache invalidation to `editar_nota`**

In the `editar_nota` function, after the result is computed but before `enrich_response`, add detection of REGLAS_GLOBALES edits:

```python
            if "REGLAS_GLOBALES" in nombre_archivo:
                invalidate_rules_cache()
```

- [ ] **Step 10: Run full test suite**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/ -v`
Expected: All tests pass (middleware + existing tests)

- [ ] **Step 11: Commit**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
git add obsidian_mcp/tools/creation.py
git commit -m "feat: integrate rule enforcement middleware into creation tools"
```

---

### Task 5: Add `validations:` block to vault's REGLAS_GLOBALES.md

**Files:**
- Modify: `.agents/REGLAS_GLOBALES.md` (in the vault, via MCP)

This task modifies the live vault, not the codebase. Use the Obsidian MCP `editar_nota` to add the `validations:` block to the frontmatter.

- [ ] **Step 1: Read current REGLAS_GLOBALES.md**

Use `leer_nota(".agents/REGLAS_GLOBALES.md")` to get exact current content.

- [ ] **Step 2: Add validations block to frontmatter**

Use `editar_nota` to replace the existing frontmatter with the version that includes `validations:`. The full validations block to add (from the spec):

```yaml
validations:
  - id: no_emoji_headings
    applies_to: [create, append, edit]
    scope: headings
    pattern: "[\U0001F300-\U0001FFFF\u2600-\u27BF\u2700-\u27BF]"
    warning: "Emojis en cabeceras"
  - id: no_emoji_title
    applies_to: [create]
    scope: title
    pattern: "[\U0001F300-\U0001FFFF\u2600-\u27BF]"
    warning: "Emojis en el titulo de la nota"
  - id: required_frontmatter
    applies_to: [create]
    scope: frontmatter
    required_fields: [type, status, tags]
    warning: "Frontmatter incompleto: faltan {missing_fields}"
  - id: valid_status
    applies_to: [create, edit]
    scope: frontmatter
    field: status
    allowed_values: [captura, en_proceso, completo, archivo]
    warning: "Valor de 'status' invalido: '{value}'"
  - id: valid_type
    applies_to: [create]
    scope: frontmatter
    field: type
    allowed_values: [diario, semanario, apunte, resumen, creacion, proyecto, doc-proyecto, recurso, evento, indice, prompt, factura, inbox]
    warning: "Valor de 'type' invalido: '{value}'"
```

- [ ] **Step 3: Verify by calling `obtener_reglas_globales`**

Confirm the validations block appears in the output and the prose content is intact.

---

### Task 6: Manual smoke test

**Files:** None (verification only)

- [ ] **Step 1: Restart MCP server**

```bash
# Kill any running instance and restart
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
# Restart will depend on how the server is launched (e.g., via Claude Code MCP config)
```

- [ ] **Step 2: Test crear_nota with emoji violation**

Call `crear_nota` with an emoji in the title or heading. Verify the response contains `[WARNINGS:]` with the specific violation AND `[REGLAS ACTIVAS DEL VAULT]` with the prose.

- [ ] **Step 3: Test crear_nota with clean content**

Call `crear_nota` with valid content. Verify NO warnings appear but `[REGLAS ACTIVAS DEL VAULT]` is still injected.

- [ ] **Step 4: Test editar_nota**

Call `editar_nota` with an emoji in a heading replacement. Verify warnings appear but NO prose injection.

- [ ] **Step 5: Test captura_rapida**

Call `captura_rapida`. Verify NO prose injection.

- [ ] **Step 6: Commit verification notes if needed**

```bash
cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server
git add -A
git commit -m "docs: add implementation plan for rule enforcement middleware"
```

---

### Task 7: Clean up duplicated rules from skills

**Files:**
- Modify (vault): `.agents/skills/*/SKILL.md` (10 files)

Now that the MCP enforces rules automatically, remove the duplicated boilerplate from each skill file.

- [ ] **Step 1: Remove "Regla de oro de edicion" block from all skills**

In each of the 10 SKILL.md files, remove the repeated block that looks like:

```markdown
## REGLA DE ORO DE EDICION
Cuando uses `editar_nota`, el `nuevo_contenido`
debe ser el **ARCHIVO COMPLETO**.
- **NUNCA** dupliques el bloque YAML.
- **REEMPLAZA** la metadata anterior.
```

Or the variant:

```markdown
## Regla de oro de edicion

Cuando uses `editar_nota()`:
1. Lee PRIMERO la nota con `leer_nota()`
2. El contenido nuevo debe ser el ARCHIVO COMPLETO
3. REEMPLAZA el bloque YAML existente, no lo dupliques
4. NUNCA elimines contenido existente accidentalmente
```

Skills affected: `escritor`, `documentador`, `organizador`, `procesador`, `explorador`, `registrador`, `revision`, `diario-reflexivo`, `kanban-manager`, `prompt-engineer`.

Use `editar_nota` via the MCP for each file. Read each first with `leer_nota` to get the exact text to remove.

- [ ] **Step 2: Verify skills still contain their workflow-specific content**

After removal, confirm each skill file still has its `## Cuando usar esta skill` section and unique workflows intact. The CAUTION callout (`> [!CAUTION] Antes de crear o editar notas, lee las REGLAS_GLOBALES`) can optionally stay as a lightweight pointer — it does no harm and costs very few tokens.

- [ ] **Step 3: Verify the MCP server still loads skills correctly**

Run: `cd /Users/enriquebook/Personal/Developer/obsidian-mcp-server && uv run pytest tests/test_agents.py -v`
Expected: All skill loading tests pass
