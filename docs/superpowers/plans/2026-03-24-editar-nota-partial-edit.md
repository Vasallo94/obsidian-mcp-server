# editar_nota Partial Edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign `editar_nota` to accept a list of old/new text operations instead of requiring full file content, with atomic batch semantics.

**Architecture:** The tool signature changes from `(nombre_archivo, contenido)` to `(nombre_archivo, operaciones)` where operaciones is a list of `{old, new}` dicts. A two-phase approach (validate all, then apply all) guarantees atomicity. The existing `_update_frontmatter_date` logic is extracted into a reusable helper.

**Tech Stack:** Python 3.13, Pydantic v2, FastMCP, pytest

**Spec:** `docs/superpowers/specs/2026-03-24-editar-nota-partial-edit-design.md`

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `obsidian_mcp/models/tool_inputs.py` | Modify | Add `EditOperation`, rewrite `EditarNotaInput` |
| `obsidian_mcp/tools/creation_logic.py` | Modify | Rewrite `edit_note()` with validate+apply logic |
| `obsidian_mcp/tools/creation.py` | Modify | Update `editar_nota` signature & docstring |
| `obsidian_mcp/tools/agents_generator.py` | Modify | Update Golden Rule text (2 places) |
| `tests/test_edit_note.py` | Create | All tests for the new edit_note |
| `docs/tool-reference.md` | Modify | Update editar_nota reference |
| `docs/examples/REGLAS_GLOBALES-example.md` | Modify | Update Golden Rule example |
| `docs/examples/SKILL-writer-example.md` | Modify | Update editing rules |

---

### Task 1: Add Pydantic models

**Files:**
- Modify: `obsidian_mcp/models/tool_inputs.py:52-58`

- [ ] **Step 1: Replace `EditarNotaInput` and add `EditOperation`**

In `obsidian_mcp/models/tool_inputs.py`, replace the current `EditarNotaInput` (lines 52-58) with:

```python
class EditOperation(BaseModel):
    old: str = Field(
        description="Texto exacto a buscar en la nota (debe ser unico). Vacio = reemplazo total."
    )
    new: str = Field(
        description="Texto de reemplazo."
    )


class EditarNotaInput(BaseModel):
    nombre_archivo: str = Field(
        description="Nombre o ruta de la nota a editar (ej: 'Mi Nota.md')."
    )
    operaciones: list[EditOperation] = Field(
        min_length=1,
        description="Lista de operaciones old->new a aplicar (minimo 1)."
    )
```

- [ ] **Step 2: Verify import works**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -c "from obsidian_mcp.models.tool_inputs import EditOperation, EditarNotaInput; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add obsidian_mcp/models/tool_inputs.py
git commit -m "feat(models): add EditOperation model for partial edits"
```

---

### Task 2: Write failing tests for edit_note core logic

**Files:**
- Create: `tests/test_edit_note.py`

- [ ] **Step 1: Write test file with all test cases**

Create `tests/test_edit_note.py`:

```python
"""Tests for the redesigned edit_note with old/new partial edit operations."""

import pytest

from obsidian_mcp.tools.creation_logic import edit_note


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    return vault


@pytest.fixture
def sample_note(temp_vault):
    """Create a sample note for editing tests."""
    note = temp_vault / "test_note.md"
    note.write_text(
        "---\ntitle: Test\ncreated: 2026-01-01\n---\n\n# Test Note\n\n"
        "First paragraph.\n\nSecond paragraph.\n\nThird paragraph.\n",
        encoding="utf-8",
    )
    return note


def _patch_vault(monkeypatch, vault_path):
    """Helper to monkeypatch vault path and find_note_by_name."""
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.get_vault_path",
        lambda: vault_path,
    )
    monkeypatch.setattr(
        "obsidian_mcp.tools.creation_logic.find_note_by_name",
        lambda name: vault_path / name if (vault_path / name).exists() else None,
    )


# === Happy Path ===


class TestEditNoteHappyPath:
    """Tests for successful edit operations."""

    def test_single_replace(self, temp_vault, sample_note, monkeypatch):
        """Single old->new replacement."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [{"old": "First paragraph.", "new": "Updated paragraph."}])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "Updated paragraph." in content
        assert "First paragraph." not in content
        assert "Second paragraph." in content  # untouched

    def test_multiple_operations(self, temp_vault, sample_note, monkeypatch):
        """Multiple operations applied atomically."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "Replaced first."},
            {"old": "Third paragraph.", "new": "Replaced third."},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "Replaced first." in content
        assert "Replaced third." in content
        assert "Second paragraph." in content  # untouched

    def test_insert_after_anchor(self, temp_vault, sample_note, monkeypatch):
        """Insert text after an anchor by including anchor in new."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "First paragraph.\n\nInserted paragraph."},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "First paragraph.\n\nInserted paragraph." in content

    def test_delete_fragment(self, temp_vault, sample_note, monkeypatch):
        """Delete a fragment by setting new to empty string."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "Second paragraph.\n\n", "new": ""},
        ])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "Second paragraph." not in content

    def test_full_replace(self, temp_vault, sample_note, monkeypatch):
        """Full replace mode with old=''."""
        _patch_vault(monkeypatch, temp_vault)
        new_content = "---\ntitle: Replaced\n---\n\n# New Title\n\nNew body.\n"
        result = edit_note("test_note.md", [{"old": "", "new": new_content}])
        assert result.success
        content = sample_note.read_text(encoding="utf-8")
        assert "New body." in content
        assert "First paragraph." not in content

    def test_noop_old_equals_new(self, temp_vault, sample_note, monkeypatch):
        """old == new is accepted silently as a no-op."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "First paragraph."},
        ])
        assert result.success
        # Content unchanged except possibly updated date
        content = sample_note.read_text(encoding="utf-8")
        assert "First paragraph." in content

    def test_updated_field_set(self, temp_vault, sample_note, monkeypatch):
        """The 'updated' frontmatter field should be set after editing."""
        _patch_vault(monkeypatch, temp_vault)
        edit_note("test_note.md", [{"old": "First paragraph.", "new": "Changed."}])
        content = sample_note.read_text(encoding="utf-8")
        assert "updated:" in content

    def test_success_message_format(self, temp_vault, sample_note, monkeypatch):
        """Success message includes operation count."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "A."},
            {"old": "Third paragraph.", "new": "B."},
        ])
        assert result.success
        assert "2 operaciones" in result.data

    def test_full_replace_message(self, temp_vault, sample_note, monkeypatch):
        """Full replace success message says 'reemplazo total'."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("test_note.md", [{"old": "", "new": "---\ntitle: X\n---\n\nBody\n"}])
        assert result.success
        assert "reemplazo total" in result.data


# === Atomic Failure ===


class TestEditNoteAtomicFailure:
    """Tests for atomic failure behavior -- note must remain unchanged."""

    def test_old_not_found(self, temp_vault, sample_note, monkeypatch):
        """Fail if old text is not found in the note."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [{"old": "nonexistent text", "new": "x"}])
        assert not result.success
        assert "No se encontro" in result.error
        assert sample_note.read_text(encoding="utf-8") == original  # unchanged

    def test_old_appears_multiple_times(self, temp_vault, monkeypatch):
        """Fail if old text appears more than once (ambiguity)."""
        note = temp_vault / "dup.md"
        note.write_text("hello world\nhello world\n", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        original = note.read_text(encoding="utf-8")
        result = edit_note("dup.md", [{"old": "hello world", "new": "hi"}])
        assert not result.success
        assert "aparece" in result.error
        assert "2 veces" in result.error
        assert note.read_text(encoding="utf-8") == original

    def test_overlapping_operations(self, temp_vault, sample_note, monkeypatch):
        """Fail if two operations affect overlapping text."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "First paragraph.\n\nSecond", "new": "A"},
            {"old": "Second paragraph.", "new": "B"},
        ])
        assert not result.success
        assert "mismo fragmento" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_full_replace_with_other_ops(self, temp_vault, sample_note, monkeypatch):
        """Fail if full-replace (old='') is combined with other operations."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "", "new": "full content"},
            {"old": "First paragraph.", "new": "x"},
        ])
        assert not result.success
        assert "unica operacion" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_old_empty_new_empty(self, temp_vault, sample_note, monkeypatch):
        """Fail if old='' and new='' (would erase file)."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [{"old": "", "new": ""}])
        assert not result.success
        assert "eliminar_nota" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_empty_operations_list(self, temp_vault, sample_note, monkeypatch):
        """Fail if operations list is empty."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [])
        assert not result.success
        assert "al menos una" in result.error
        assert sample_note.read_text(encoding="utf-8") == original

    def test_note_not_found(self, temp_vault, monkeypatch):
        """Fail if note does not exist."""
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("nonexistent.md", [{"old": "x", "new": "y"}])
        assert not result.success

    def test_batch_fails_atomically(self, temp_vault, sample_note, monkeypatch):
        """If one op in a batch fails, no ops are applied."""
        _patch_vault(monkeypatch, temp_vault)
        original = sample_note.read_text(encoding="utf-8")
        result = edit_note("test_note.md", [
            {"old": "First paragraph.", "new": "Changed."},  # would succeed
            {"old": "nonexistent text", "new": "x"},  # fails
        ])
        assert not result.success
        assert sample_note.read_text(encoding="utf-8") == original  # nothing changed

    def test_max_operations_exceeded(self, temp_vault, sample_note, monkeypatch):
        """Fail if more than 50 operations are submitted."""
        _patch_vault(monkeypatch, temp_vault)
        ops = [{"old": "First paragraph.", "new": f"v{i}"} for i in range(51)]
        result = edit_note("test_note.md", ops)
        assert not result.success
        assert "50" in result.error


# === Edge Cases ===


class TestEditNoteEdgeCases:
    """Tests for edge cases."""

    def test_empty_note_partial_fails(self, temp_vault, monkeypatch):
        """Partial edit on empty note fails (old not found)."""
        note = temp_vault / "empty.md"
        note.write_text("", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("empty.md", [{"old": "something", "new": "x"}])
        assert not result.success

    def test_empty_note_full_replace_works(self, temp_vault, monkeypatch):
        """Full replace on empty note works."""
        note = temp_vault / "empty.md"
        note.write_text("", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("empty.md", [{"old": "", "new": "---\ntitle: New\n---\n\nContent\n"}])
        assert result.success
        assert "Content" in note.read_text(encoding="utf-8")

    def test_old_with_trailing_whitespace(self, temp_vault, monkeypatch):
        """old with trailing whitespace must match exactly."""
        note = temp_vault / "ws.md"
        note.write_text("hello world  \ngoodbye\n", encoding="utf-8")
        _patch_vault(monkeypatch, temp_vault)
        # Exact match including trailing spaces
        result = edit_note("ws.md", [{"old": "hello world  ", "new": "hello world"}])
        assert result.success

    def test_edit_frontmatter_field(self, temp_vault, monkeypatch):
        """Edit a field inside the YAML frontmatter."""
        note = temp_vault / "fm_edit.md"
        note.write_text(
            "---\ntitle: Old Title\ncreated: 2026-01-01\ntags:\n  - draft\n---\n\nBody\n",
            encoding="utf-8",
        )
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("fm_edit.md", [
            {"old": "title: Old Title", "new": "title: New Title"},
        ])
        assert result.success
        content = note.read_text(encoding="utf-8")
        assert "title: New Title" in content
        assert "tags:" in content  # other fields untouched

    def test_user_sets_updated_field(self, temp_vault, monkeypatch):
        """If user operation sets 'updated', system does not override it."""
        note = temp_vault / "fm.md"
        note.write_text(
            "---\ntitle: Test\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nBody\n",
            encoding="utf-8",
        )
        _patch_vault(monkeypatch, temp_vault)
        result = edit_note("fm.md", [
            {"old": "updated: 2026-01-01", "new": "updated: 2099-12-31"},
        ])
        assert result.success
        content = note.read_text(encoding="utf-8")
        assert "updated: 2099-12-31" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -m pytest tests/test_edit_note.py -v --tb=short 2>&1 | head -60`
Expected: All tests FAIL (edit_note has wrong signature)

- [ ] **Step 3: Commit**

```bash
git add tests/test_edit_note.py
git commit -m "test(edit_note): add tests for old/new partial edit redesign"
```

---

### Task 3: Implement edit_note core logic

**Files:**
- Modify: `obsidian_mcp/tools/creation_logic.py:285-337`

- [ ] **Step 1: Add `_update_frontmatter_date` helper**

Add this helper function right before `edit_note` (around line 280):

```python
def _update_frontmatter_date(
    content: str, user_set_updated: bool = False
) -> str:
    """Update the 'updated' field in frontmatter to today's date.

    Args:
        content: The full note content.
        user_set_updated: If True, skip auto-update (user set it explicitly).

    Returns:
        Content with updated date in frontmatter.
    """
    if user_set_updated:
        return content

    if not content.startswith("---"):
        return content

    ahora = datetime.now().strftime("%Y-%m-%d")

    if re.search(r"^updated:", content, re.MULTILINE):
        return re.sub(
            r'^(updated:\s*["\']?)[^"\'\n]+(["\']?)$',
            rf"\g<1>{ahora}\g<2>",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    if re.search(r"^created:", content, re.MULTILINE):
        return re.sub(
            r"^(created:\s*.+)$",
            rf"\1\nupdated: {ahora}",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    return content.replace("\n---\n", f"\nupdated: {ahora}\n---\n", 1)
```

- [ ] **Step 2: Rewrite the `edit_note` function**

Replace the current `edit_note` function (lines 285-337 of `creation_logic.py`) with:

```python
def edit_note(
    nombre_archivo: str, operaciones: list[dict[str, str]]
) -> Result[str]:
    """Edit an existing note by applying a list of old->new operations.

    All operations are validated before any writes (atomic).

    Args:
        nombre_archivo: Name or path of the note to edit.
        operaciones: List of {"old": "...", "new": "..."} dicts.

    Returns:
        Result with success message or error.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return Result.fail("La ruta del vault no esta configurada.")

    nota_path = find_note_by_name(nombre_archivo)
    if not nota_path:
        return Result.fail(f"No se encontro la nota '{nombre_archivo}'")

    is_allowed, error = check_path_access(nota_path, vault_path, "editar")
    if not is_allowed:
        return Result.fail(error)

    if not operaciones:
        return Result.fail("Debe incluir al menos una operacion.")

    if len(operaciones) > 50:
        return Result.fail(
            "Maximo 50 operaciones por llamada."
        )

    with open(nota_path, "r", encoding="utf-8") as f:
        contenido_actual = f.read()

    ruta_relativa = nota_path.relative_to(vault_path)

    # --- Full-replace mode ---
    if any(op["old"] == "" for op in operaciones):
        if len(operaciones) != 1:
            return Result.fail(
                "El reemplazo total (old vacio) debe ser la unica operacion en la lista."
            )
        op = operaciones[0]
        if op["new"] == "":
            return Result.fail(
                "No se puede vaciar la nota completa. Usa eliminar_nota para borrar."
            )
        contenido_final = _process_date_placeholders(op["new"])
        # In full-replace, user provides everything -- only auto-update if
        # the new content has frontmatter but no "updated:" field yet.
        has_updated = bool(re.search(r"^updated:", op["new"], re.MULTILINE))
        contenido_final = _update_frontmatter_date(contenido_final, user_set_updated=has_updated)
        with open(nota_path, "w", encoding="utf-8") as f:
            f.write(contenido_final)
        return Result.ok(f"Nota editada: {ruta_relativa} (reemplazo total)")

    # --- Partial edit mode: validate all operations ---
    matches: list[tuple[int, int, str]] = []  # (start, end, new_text)

    for i, op in enumerate(operaciones):
        old_text = op["old"]
        new_text = op["new"]

        count = contenido_actual.count(old_text)
        if count == 0:
            preview = old_text[:80] + ("..." if len(old_text) > 80 else "")
            return Result.fail(
                f"No se encontro el texto: '{preview}' en la nota {ruta_relativa}"
            )
        if count > 1:
            preview = old_text[:80] + ("..." if len(old_text) > 80 else "")
            return Result.fail(
                f"El texto '{preview}' aparece {count} veces en la nota. "
                "Incluye mas contexto para que sea unico."
            )

        start = contenido_actual.index(old_text)
        end = start + len(old_text)
        matches.append((start, end, new_text))

    # Check for overlaps
    for i, (start_a, end_a, _) in enumerate(matches):
        for j, (start_b, end_b, _) in enumerate(matches):
            if i >= j:
                continue
            if start_a < end_b and start_b < end_a:
                return Result.fail(
                    f"Las operaciones {i + 1} y {j + 1} afectan el mismo fragmento de texto."
                )

    # Check if user explicitly modifies the "updated" field
    user_set_updated = any("updated:" in op["new"] for op in operaciones)

    # Apply in reverse order so offsets remain valid
    matches.sort(key=lambda m: m[0], reverse=True)
    resultado = contenido_actual
    for start, end, new_text in matches:
        resultado = resultado[:start] + new_text + resultado[end:]

    resultado = _process_date_placeholders(resultado)
    resultado = _update_frontmatter_date(resultado, user_set_updated=user_set_updated)

    with open(nota_path, "w", encoding="utf-8") as f:
        f.write(resultado)

    n = len(operaciones)
    return Result.ok(f"Nota editada: {ruta_relativa} ({n} operaciones aplicadas)")
```

- [ ] **Step 3: Run tests**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -m pytest tests/test_edit_note.py -v --tb=short`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add obsidian_mcp/tools/creation_logic.py
git commit -m "feat(edit_note): implement old/new partial edit with atomic batch"
```

---

### Task 4: Update MCP tool registration

**Files:**
- Modify: `obsidian_mcp/tools/creation.py:162-187`

- [ ] **Step 1: Test FastMCP support for nested Pydantic models**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -c "
from fastmcp import FastMCP
from pydantic import BaseModel, Field

class EditOp(BaseModel):
    old: str = Field(description='old text')
    new: str = Field(description='new text')

mcp = FastMCP('test')

@mcp.tool()
def test_tool(name: str, ops: list[EditOp]) -> str:
    return 'ok'

import json
tools = list(mcp._tool_manager._tools.values()) if hasattr(mcp, '_tool_manager') else []
if tools:
    print(json.dumps(tools[0].parameters, indent=2))
else:
    print('NO_TOOL_MANAGER - try alternative')
"`

This determines whether we use `list[EditOperation]` directly or fall back to JSON string.

- [ ] **Step 2: Update `editar_nota` in creation.py**

Replace the `editar_nota` function (lines 162-187) with the version that matches FastMCP's capability.

**If `list[EditOperation]` works:**

```python
    @mcp.tool()
    def editar_nota(nombre_archivo: str, operaciones: list[dict]) -> str:
        """
        Edita una nota existente aplicando una lista de operaciones old->new.

        Cada operacion busca un texto exacto (old) y lo reemplaza por otro (new).
        Todas las operaciones se validan antes de aplicar ninguna (atomico).

        Modos de uso:
        - Reemplazar fragmento: {"old": "texto viejo", "new": "texto nuevo"}
        - Insertar despues de ancla: {"old": "ancla", "new": "ancla\\n\\nnuevo texto"}
        - Eliminar fragmento: {"old": "texto a borrar", "new": ""}
        - Reemplazo total: [{"old": "", "new": "contenido completo"}] (solo 1 operacion)

        Reglas:
        - old debe coincidir EXACTAMENTE con el texto de la nota (incluyendo saltos de linea)
        - old debe ser UNICO en la nota. Si aparece mas de una vez, incluye mas contexto.
        - ANTES de editar, lee la nota con leer_nota para conocer el contenido exacto.

        Args:
            nombre_archivo: Nombre o ruta de la nota (ej: "Mi Nota.md")
            operaciones: Lista de {"old": "...", "new": "..."} a aplicar

        Returns:
            Mensaje de confirmacion con el numero de operaciones aplicadas, o error.
        """
        try:
            return edit_note(nombre_archivo, operaciones).to_display(
                success_prefix="✅"
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            return f"❌ Error al editar nota: {e}"
```

**If `list[EditOperation]` does NOT work (fallback to JSON string):**

Use `operaciones: str` parameter with `description="JSON array de operaciones..."` and parse inside the function with `json.loads()` + Pydantic validation.

- [ ] **Step 3: Run full test suite**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -m pytest tests/test_edit_note.py tests/test_quick_capture.py -v --tb=short -k "not encoding"`
Expected: All edit_note tests PASS

- [ ] **Step 4: Commit**

```bash
git add obsidian_mcp/tools/creation.py
git commit -m "feat(tools): update editar_nota registration with old/new signature"
```

---

### Task 5: Update agents_generator Golden Rule

**Files:**
- Modify: `obsidian_mcp/tools/agents_generator.py:45-49` and `obsidian_mcp/tools/agents_generator.py:363-370`

- [ ] **Step 1: Update the skill template Golden Rule (line 45-49)**

Replace lines 45-49:

```python
    ## REGLA DE ORO DE EDICION
    Cuando uses `editar_nota`, envia operaciones old->new:
    - Lee la nota primero con `leer_nota`.
    - old debe ser texto EXACTO de la nota (incluyendo saltos de linea).
    - old debe ser UNICO. Si aparece mas de una vez, incluye mas contexto.
    - Para reemplazo total: [{{"old": "", "new": "contenido completo"}}]
```

- [ ] **Step 2: Update the sync check Golden Rule (lines 363-370)**

Replace the `golden_rule` string:

```python
                golden_rule = dedent("""

                    ## REGLA DE ORO DE EDICION
                    Cuando uses `editar_nota`, envia operaciones old->new:
                    - Lee la nota primero con `leer_nota`.
                    - old debe ser texto EXACTO de la nota.
                    - old debe ser UNICO. Si aparece mas de una vez, incluye mas contexto.
                """).strip()
```

- [ ] **Step 3: Commit**

```bash
git add obsidian_mcp/tools/agents_generator.py
git commit -m "docs(agents): update Golden Rule for old/new edit pattern"
```

---

### Task 6: Update documentation

**Files:**
- Modify: `docs/tool-reference.md:18`
- Modify: `docs/examples/REGLAS_GLOBALES-example.md:24-28`
- Modify: `docs/examples/SKILL-writer-example.md:37-41`

- [ ] **Step 1: Update tool-reference.md**

Replace line 18:

```markdown
- **`editar_nota(nombre_archivo, operaciones)`**: Edits a note by applying a list of `old->new` text operations. Atomic: all operations succeed or none are applied. Supports partial edits, insertions, deletions, and full replace.
```

- [ ] **Step 2: Update REGLAS_GLOBALES-example.md (lines 24-28)**

Replace the Golden Rule section:

```markdown
### 2. Golden Rule of Editing
When using `editar_nota()`:
1. **FIRST** read the note with `leer_nota()`
2. Send `operaciones` as a list of `{"old": "exact text", "new": "replacement"}`
3. `old` must be **UNIQUE** in the note — include more context if ambiguous
4. For full replace: `[{"old": "", "new": "complete content"}]`
```

- [ ] **Step 3: Update SKILL-writer-example.md (lines 37-41)**

Replace the Important Rules section:

```markdown
## Important Rules
When using `editar_nota`, send `operaciones` as `{"old": "...", "new": "..."}`:
1. `old` must be **EXACT** text from the note (read it first with `leer_nota`)
2. `old` must be **UNIQUE** — include surrounding context if needed
3. For full rewrite: `[{"old": "", "new": "complete file with YAML"}]`
```

- [ ] **Step 4: Commit**

```bash
git add docs/tool-reference.md docs/examples/REGLAS_GLOBALES-example.md docs/examples/SKILL-writer-example.md
git commit -m "docs: update editar_nota references for old/new pattern"
```

---

### Task 7: Integration test and final verification

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -m pytest tests/ -v --tb=short -k "not test_agents and not encoding"`
Expected: All tests PASS (including new edit_note tests)

- [ ] **Step 2: Verify MCP server starts and tool schema is correct**

Run: `cd C:/Users/ldaevf1/Programs/obsidian-mcp-server && uv run python -c "
from obsidian_mcp.server import create_server
mcp = create_server()
print('Server created OK')
"`
Expected: Server creates without errors

- [ ] **Step 3: Push all commits**

```bash
git push
```
