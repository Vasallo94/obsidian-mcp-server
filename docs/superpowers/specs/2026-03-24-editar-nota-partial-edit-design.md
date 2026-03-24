# Design: editar_nota Partial Edit (old/new pattern)

**Date:** 2026-03-24
**Status:** Approved

## Problem

The current `editar_nota` tool requires the AI agent to send the **complete file content** on every edit. This is:

- **Token-expensive**: Large notes waste input/output tokens on unchanged content.
- **Error-prone**: Agents can accidentally lose content, duplicate YAML frontmatter, or corrupt formatting.
- **Slow**: Round-trip cost grows linearly with note size.

Other editing tools in the codebase (`agregar_a_nota`, `agregar_en_seccion`) only cover append/prepend and section insertion. There is no way to do a surgical in-place edit of a specific fragment.

## Solution

Redesign `editar_nota` to accept a list of `old -> new` text replacement operations, following the same pattern used by Claude Code's `Edit` tool, Cursor, and Copilot. This pattern is already familiar to LLMs.

## API

### Signature

```python
editar_nota(
    nombre_archivo: str,
    operaciones: list[EditOperation],   # [{"old": "...", "new": "..."}, ...]
)
```

The function signature uses `list[EditOperation]` (not `list[dict]`) so that FastMCP
generates a proper JSON Schema with the `old` and `new` keys visible to the LLM.
If FastMCP does not serialize nested Pydantic models correctly, fall back to
`operaciones: str` (JSON string) and parse manually, similar to `actualizar_frontmatter`.

### Pydantic Models

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

**Note on Pydantic models:** The input models in `tool_inputs.py` serve as schema
documentation and validation reference. The actual MCP tool registration in `creation.py`
uses plain function parameters. During implementation, test whether FastMCP supports
`list[EditOperation]` as a parameter type. If not, accept `str` (JSON) and validate
with the Pydantic model manually inside the function.

### Usage Modes

| Mode | old | new | Example |
|---|---|---|---|
| Replace fragment | exact text | replacement | `{"old": "typo", "new": "fixed"}` |
| Insert after anchor | anchor text | anchor + inserted text | `{"old": "anchor", "new": "anchor\n\nnew paragraph"}` |
| Delete fragment | text to remove | `""` | `{"old": "delete me", "new": ""}` |
| Full replace | `""` | complete content | `[{"old": "", "new": "full file..."}]` |

### Constraints

- `old` must match **exactly** (including whitespace and newlines).
- `old` must be **unique** in the note. If it appears more than once, the agent must include more surrounding context to disambiguate.
- Full-replace mode (`old=""`) is only allowed when the list contains exactly one operation.
- `old=""` + `new=""` is rejected: use `eliminar_nota` to delete a note entirely.
- `old == new` is accepted silently as a no-op.
- `operaciones` must contain at least one operation (enforced via `min_length=1`).
- Maximum 50 operations per call to prevent pathological overlap-checking costs.

## Execution Flow

```
1. Read current note content
2. VALIDATION PHASE (no writes):
   a. For each operation:
      - If old="" -> full-replace mode (must be the only operation)
      - Find old in current content
      - If not found -> ATOMIC FAIL, nothing is applied
      - If old appears more than once -> ATOMIC FAIL (ambiguity)
      - Record match position (start, end)
   b. Check that no operations overlap
      Overlap = ranges [start_a, end_a) and [start_b, end_b) have non-empty
      intersection (start_a < end_b AND start_b < end_a).
      Adjacent ranges sharing an endpoint are allowed.
3. APPLICATION PHASE (only if all validated):
   - Apply operations in reverse position order (bottom-to-top)
     so that earlier offsets are not displaced
   - Process date placeholders
   - Update "updated" field in frontmatter AFTER all operations are applied.
     If a user operation explicitly sets the "updated" field, the system
     does NOT override it (user intent takes precedence).
4. Write result to file
```

### Error Messages (actionable)

| Condition | Message |
|---|---|
| `old` not found | `"No se encontro el texto: '<first 80 chars>...' en la nota X.md"` |
| `old` appears N times | `"El texto '<first 80 chars>...' aparece N veces en la nota. Incluye mas contexto para que sea unico."` |
| Operations overlap | `"Las operaciones 1 y 3 afectan el mismo fragmento de texto."` |
| Full-replace + other ops | `"El reemplazo total (old vacio) debe ser la unica operacion en la lista."` |
| Empty list | `"Debe incluir al menos una operacion."` |
| old="" + new="" | `"No se puede vaciar la nota completa. Usa eliminar_nota para borrar."` |

## Docstring (agent-facing)

```python
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
```

## Impact on Existing Tools

### Changed

- `editar_nota` — new signature `(nombre_archivo, operaciones)` replaces `(nombre_archivo, contenido)`. Breaking change.
- `EditarNotaInput` in `models/tool_inputs.py` — new model with `EditOperation`.
- `edit_note()` in `tools/creation_logic.py` — new validation + application logic.
- `tools/agents_generator.py` — "Golden Rule" updated. New text:
  ```
  Cuando uses `editar_nota`, envia operaciones old->new:
  - Lee la nota primero con `leer_nota`.
  - old debe ser texto EXACTO de la nota (incluyendo saltos de linea).
  - old debe ser UNICO. Si aparece mas de una vez, incluye mas contexto.
  - Para reemplazo total: [{"old": "", "new": "contenido completo"}]
  ```
- `docs/tool-reference.md`, `docs/examples/REGLAS_GLOBALES-example.md`, `docs/examples/SKILL-writer-example.md` — updated references.

### Unchanged

- `agregar_a_nota` — still useful for quick append/prepend without reading the note first.
- `agregar_en_seccion` — still useful for inserting under a heading without knowing exact content.
- `buscar_y_reemplazar_global` — operates on the whole vault, different use case.
- `actualizar_frontmatter` — operates only on metadata, more convenient than manual patching.

## Test Plan

### Happy Path

- Single search/replace operation
- Multiple operations in batch (all applied)
- Insertion via anchor (old="anchor", new="anchor\nnew content")
- Fragment deletion (new="")
- Full-replace with `[{"old": "", "new": "..."}]`
- `updated` field in frontmatter is set after editing

### Atomic Failure

- `old` not found -> all fail, note unchanged
- `old` appears more than once -> all fail with "include more context" message
- Two operations that overlap -> all fail
- Full-replace (old="") with additional operations in list -> fail
- Empty operaciones list -> fail
- old="" + new="" -> fail with "use eliminar_nota"
- Note not found / forbidden path -> existing errors

### Edge Cases

- old == new (no-op, accepted silently)
- old with trailing whitespace/newlines
- Empty note (0 bytes): partial replace fails (old not found), full-replace works
- Operation where old includes part of YAML frontmatter
- `updated` field set by user operation: system does not override it

### Success Message Format

```
"Nota editada: Mi Nota.md (3 operaciones aplicadas)"
```

For full-replace mode:
```
"Nota editada: Mi Nota.md (reemplazo total)"
```
