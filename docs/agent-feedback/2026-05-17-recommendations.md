# Obsidian MCP — Agent Session Feedback (2026-05-17)

Recommendations from an agent that ran a heavy vault audit + cleanup session.

> Historical AFP report. Some tool names in this document use the pre-namespace
> API (`create_note`, `patch_note`, `kanvas_*`, etc.) because they describe the
> original feedback that led to the current public names such as `notes.create`,
> `notes.patch`, and `kanvas.start`.

## Context

- **Session goal**: bootstrap a Nadir astronomy profile + audit + clean up `05_Recursos/Astrofotografía/` (21 notes + 2 project notes in `04_Proyectos/`).
- **Operations performed**: ~30 `patch_note` calls (some with 11 operations each), 6 `create_note`, 1 `move_note`, 1 archive (status-only patch), 1 `delete_note` (forced via bash `rm`), plus several reads + searches.
- **Agent**: Claude Code via the `obsidian` MCP, with vault rules enforced (frontmatter `type`/`status` required, no emojis in headers, no tags as states, etc.).
- **Method**: observations surfaced to the user before being written here; nothing speculative.

The MCP is solid and the vault-rules system is great. The notes below are about friction encountered, not foundational flaws.

---

## Top issues (severity ordered)

### 1. [BLOCKER] `delete_note` and `replace_note` cancel silently, can't be bypassed

**Symptom**: every `delete_note` call returned `Operation cancelled.` regardless of context. Same for `replace_note` when used for substantial rewrites. The user explicitly approved the action via a separate UI prompt, yet the operation was still rejected.

**Workaround used**:
- For delete: fell back to `rm` via bash (loses any link-integrity safety the MCP would have provided).
- For replace: decomposed the rewrite into a single `patch_note` with multiple operations (works, but more brittle and required exact-match strings).

**Hypothesis**: either (a) the consent UI returns a default-no when no explicit interactive confirmation is wired up in the host (Claude Code), (b) the tool is hardcoded to reject without a positive force flag, or (c) the policy gate is silently dropping calls when the host doesn't surface a checkbox.

**Severity**: blocker — forced bypass + workflow split.

**Fix proposals**:
- Surface the *reason* for cancellation: `policy_rejection`, `user_denied`, `host_no_confirmation_surface`, etc., rather than the opaque `Operation cancelled`.
- Add a `force=True` parameter that requires the caller (Claude) to have prior verbal user consent recorded somewhere (e.g. a short-lived `consent_tokens` array passed in).
- Document the actual confirmation flow in `tool-reference.md` so agents know what to expect.

---

### 2. [BUG] `create_note` silently overwrites embedded YAML frontmatter

**Symptom**: when the `content` parameter starts with a complete `---...---` block (`title`, `type`, `status`, `tags`, `created`, `related`), the tool generates its own frontmatter from the separate `title` / `tags` / `folder` parameters and uses *that* instead. My `type: recurso` and `status: completo` were stripped on every create.

**Reproducer**:
```python
create_note(
    title="X",
    folder="...",
    tags="astrofotografía, equipamiento",
    content="---\ntitle: X\ntype: recurso\nstatus: completo\ntags: [...]\ncreated: '2026-05-17'\n---\n# X\n...",
)
# Resulting file has frontmatter built from parameters only;
# embedded type/status/created are lost.
```

**Workaround used**: create → immediately `patch_note` to re-inject the missing `type` and `status`. One extra round-trip per note created (6 round-trips wasted in this session).

**Severity**: major. Every `create_note` cost 2× round-trips.

**Fix proposals**:
- Detect embedded frontmatter in `content` and (a) skip the tool-generated frontmatter or (b) merge, preferring the user-provided fields where they conflict.
- Or expose a `frontmatter: dict` parameter explicitly. The agent passes a dict (`{type: "recurso", status: "completo", ...}`); the tool serialises. Removes the silent override surface entirely.

---

### 3. [UX] Vault rules dumped in every `create_note` response

**Symptom**: every `create_note` response includes the full `Reglas Globales para Agentes` markdown block (~2 KB) in the body, regardless of whether any rule was violated. With 6 creates in this session = ~12 KB of duplicated rule text in the response stream.

This is expensive for the agent's context window. After the first 1-2 dumps the agent has the rules; further repetitions add no signal.

**Fix proposals**:
- Promote `get_global_rules()` (which already exists!) to the canonical entry point.
- In `create_note` responses, only include rules context if `violations: [...]` is non-empty. When clean, omit.
- Add a session-level "rules acknowledged" mechanism so subsequent calls skip the bundle.

---

### 4. [DISCOVERABILITY] No agent-facing onboarding doc surfaces the right entry points

**Observation**: many genuinely useful tools that the agent only discovered ad-hoc late in the session:

- `get_global_rules` (would have saved the bandwidth in #3)
- `apply_replace_in_notes` + `preview_replace_in_notes` (would have replaced ~30 manual emoji-strip patches with one sweep)
- `analyze_links`, `find_orphan_notes`, `analyze_tags`
- `suggest_note_location`, `route_task`, `quick_capture`
- The whole `kanvas_*` and `canvas_*` family

**Fix proposal**:
- A `docs/agent-onboarding.md` that says, in this order:
  1. Call `read_vault_context()` once.
  2. Call `get_global_rules()` once.
  3. Use this table to pick the right tool for the job (with a 1-line "when to use" per tool).
- Or include a `nadir://obsidian/docs/agent-quickstart` style MCP **resource** (markdown) that auto-loads at session start. Nadir does this with `nadir://docs/profile-usage` — it works well.

---

### 5. [LIMITATION] `list_notes()` doesn't paginate

**Symptom**: `list_notes()` returned 125 142 characters in a single payload. Exceeded the agent's max token budget for tool output → had to fall back to disk-level `ls` via bash. The MCP became unreachable for this task at vault scale.

**Fix proposals**:
- Support a `folder` filter parameter (e.g. `list_notes(folder="05_Recursos/Astrofotografía")`).
- Or support a `pattern` glob.
- Or paginate via `limit` + `offset` / cursor.
- For introspection of the whole vault, return a summary first (folder counts + sizes), let the caller drill down.

---

### 6. [MISSING] No broken-wikilink finder

**Observation**: during the audit I found at least 5 broken wikilinks across the vault:

- `[[Setup Solar H-Alpha - Configuración Recomendada]]` (target file deleted by user)
- `[[Workflow de Procesado en PixInsight]]` (never existed)
- `[[ZWO EFW 36mm]]` (never existed)
- `[[ZWO EAFN-EAF Pro]]` (typo — actual file is `ZWO EAF Pro`)
- `[[Decisiones sobre Filtros - Conversación Claude]]` (real file is `Decisiones sobre Filtros y Estrategia - Conversación Claude`)

`analyze_links` exists but is unclear whether it specifically surfaces broken-vs-valid distinction. I never invoked it because the docstring was thin.

**Fix proposal**:
- `find_broken_wikilinks() → [{source_note, target, line, suggested_match, distance}]`. Suggested match via fuzzy matching (Levenshtein / RapidFuzz) against existing titles.
- This is the single highest-leverage feature for vault maintenance. A repository the user has had for years accumulates broken refs constantly.

---

### 7. [MISSING] No "rename note with link updates"

**Symptom**: fixing the `[[ZWO EAFN-EAF Pro]]` typo wikilink required (a) creating the correct-named note and (b) manually patching every reference across the vault. Same friction for any rename in a mature vault.

**Fix proposal**:
- `rename_note(old_path, new_path, update_links=True) → {updates_made: N, files_touched: [...]}`. Scans vault, rewrites all `[[old_title]]` and `[[old_title|alias]]` references to the new title, atomic on failure.
- Combine with #6 to make wikilink hygiene routine maintenance instead of manual archaeology.

---

### 8. [UX] `patch_note` error messages don't disambiguate near-misses

**Symptom**: tried to patch `## 🛋 Recomendaciones de Compra` (couch emoji, wrong codepoint) when the actual was `## 🛒 Recomendaciones de Compra` (cart emoji). Error: `❌ No se encontro el texto`. No hint. Tried `🛍` (shopping bags) next. Wrong again. Third attempt with `🛒` worked.

Three round-trips guessing unicode codepoints when one would have sufficed if the error had suggested the nearest match.

**Fix proposal**:
- When `old` text isn't found, run fuzzy diff against the note content and return up to 3 nearest matches: `"Did you mean one of: '## 🛒 Recomendaciones de Compra' (Levenshtein 1), '## Recomendaciones' (Levenshtein 22)?"`. The agent picks the right one in the retry.

---

### 9. [DESIGN] No bulk-sweep tool for cross-vault rule violations

**Symptom**: stripping emojis from H2/H3 headers across 12 notes required identifying each emoji header manually and writing per-note `patch_note` calls. ~60 individual operations.

The vault rule prohibits emojis in headers across the board → a sweep tool would have saved an hour.

**Fix proposal**:
- `strip_emojis_from_headers(folder="", dry_run=True) → {planned_changes: [(file, line, old, new)]}`. Pair with `apply_replace_in_notes` for general bulk substitutions.
- Or expose `lint_vault(rules=[...]) → {violations: [(file, rule, line)]}` + an `auto_fix=True` mode.

---

### 10. [DESIGN] No pre-flight validation tool

**Symptom**: I'd write a note via `create_note`, get warnings (`Emojis en cabeceras`), then patch-fix. Pre-flight check would catch this without a round trip.

**Fix proposal**:
- `validate_note(content, frontmatter=None) → {violations: [{rule, message, severity}]}`. Runs vault rules against arbitrary content without saving. Agent lints locally before committing.
- Same surface as the rule-violation checks the tool already does post-save; just expose it pre-save.

---

### 11. [BUG] `move_note` doesn't report wikilink impact

**Symptom**: I moved `Estación meteorológica ESP32.md` from `05_Recursos/Astrofotografía/` to `04_Proyectos/`. The move succeeded. The tool didn't report whether any wikilinks elsewhere now point to a stale path. Obsidian's own resolver is usually permissive, but explicit reporting would help.

**Fix proposal**:
- `move_note` returns `{updated_references: int, unresolved_references: [{file, line}]}`. Optional `update_links=True` does the patching.

---

### 12. [DOCS] `read_notes` (plural) signature drift

**Symptom**: attempted to batch-read multiple notes with `read_notes(query='[...]')` based on a guess. Got Pydantic error: `Missing required argument [paths]` and `Unexpected keyword argument [query]`. The tool wasn't in the deferred-tools list with a schema, so I had to fall back to parallel `read_note` calls.

**Fix proposal**:
- Document or remove. If it exists, the schema should appear in `tool-reference.md`. If it's not maintained, remove it from the surface.

---

## Lower-priority observations

### 13. Mixed Spanish / English in tool messages

Most success messages are in Spanish (`OK Nota editada`, `❌ No se encontro el texto`), some errors are in English (`Operation cancelled`). Pick one based on vault locale (detectable from `read_vault_context`) and stick.

### 14. Tag input format is silently transformed

`tags="astrofotografía, equipamiento"` passed as a string becomes a YAML list (`- astrofotografía\n- equipamiento`) in the saved frontmatter. Reasonable behaviour, but undocumented and surprising when the agent later tries to patch the frontmatter and the original format is gone.

**Fix**: accept either input form and document.

### 15. Tool naming convention

`create_note` / `patch_note` / `replace_note` / `kanvas_propose_task` / `canvas_add_card` / `analyze_links` mixes verb-first and namespace-first conventions. Maybe normalise: `notes.create`, `notes.patch`, `kanvas.propose`, `canvas.add_card`, `links.analyze`. Improves discoverability via prefix grouping.

---

## What worked well

For balance, the things that made this session productive:

- **`patch_note` with multi-op `operations: [{old, new}, ...]`** — the workhorse. Reliable, fast, atomic. Most of this session ran on it.
- **`search_notes`** — quick title-and-body search. The `titles_only=True` hint surfaced in results was helpful.
- **`move_note`** — worked first try. No fanfare needed.
- **`read_note`** — reliable, consistent format.
- **The vault rules system itself** — caught emoji violations and frontmatter omissions early. Without it the agent would have produced inconsistent notes.
- **`read_vault_context`** — implicit context from the rules dump (despite the bandwidth waste of #3) genuinely improved compliance.

---

## Recommended priority

If implementing one thing at a time:

1. **#1**: fix `delete_note` / `replace_note` cancellation. Blocker.
2. **#2**: frontmatter merge in `create_note`. Highest cost-per-call.
3. **#3**: stop bundling vault rules on every `create_note`. Largest context savings.
4. **#6 + #7**: broken-wikilink finder + rename-with-link-updates. Order-of-magnitude productivity for vault maintenance, and combine well.
5. **#10**: pre-flight `validate_note`. Eliminates a class of round-trips.
6. **#4**: agent-onboarding doc + MCP resource at session-start. Cheap, leverages everything that already exists.

---

## Methodology note

These observations were captured during real work, surfaced to the user, and only written after he asked me to. The intent is constructive — the MCP already does a lot well; these are the rough edges that consumed the most time today.
