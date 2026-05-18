# Agent Quickstart

A short orientation for AI agents using the Obsidian MCP server. Read this once at the start of a session and you'll skip a lot of trial-and-error.

## First two calls

1. `read_vault_context()` — folder layout, templates, common tags, active profile.
2. `get_global_rules()` — vault-wide author rules (frontmatter required fields, heading conventions, etc.). The server enforces these on every write and surfaces violations in the response; reading them upfront tells you what to comply with.

After those two calls you have enough context to write correctly. Everything below is a "when you need it" reference.

## Decision table — pick the right tool

| You need to… | Use |
|---|---|
| List notes in the vault | `list_notes(folder=, limit=500, offset=0, pattern=)` — paginates by default |
| Read one note | `read_note(note_path)` |
| Read several notes | `read_notes(paths=[...])` — note: `paths`, not `query=` |
| Search by text | `search_notes(query=, titles_only=False)` |
| Search by date | `search_notes_by_date(date_from, date_to)` |
| Create a note | `create_note(title, content, folder, tags, ...)` — embed YAML frontmatter in `content` and it'll be merged with parameters |
| Lint a note before writing | `validate_note(content, title, mode='create')` — pre-flight, no write |
| Edit fragments of a note | `patch_note(note_path, operations=[{old, new}, ...])` — fuzzy suggestions on miss |
| Replace whole note body | `replace_note(note_path, content)` — requires client elicit() support |
| Delete a note | `delete_note(note_path)` — requires client elicit() support |
| Rename a note + update wikilinks | `rename_note(source, new_name, update_links=True)` |
| Move a note | `move_note(source, destination, update_links=True)` |
| Find broken wikilinks across the vault | `find_broken_wikilinks(limit=100)` — returns source file + line + fuzzy suggestions |
| Link/orphan analysis | `analyze_links()`, `find_orphan_notes()` |
| Bulk find/replace text | `preview_replace_in_notes(...)` then `apply_replace_in_notes(...)` |
| Lint every note against vault rules (heading emojis, missing frontmatter fields, etc.) | `lint_vault(auto_fix=False)` to scan, then `lint_vault(auto_fix=True)` to apply regex-based fixes |
| Vault stats / tag audit | `get_vault_stats()`, `analyze_tags()`, `list_tags()` |
| Routing help | `route_task(request)` — suggests prompts/skills/tools for an ambiguous task |

## Common traps

- **`read_notes` argument name** is `paths` (a list), not `query`. Pydantic will reject `query=`.
- **Tags passed as a string** like `"astro, equipo"` are normalized to a YAML list in frontmatter. This is intentional but undocumented in the field name.
- **Embedded frontmatter wins**: if your `create_note` content starts with `---...---`, fields like `type` and `status` are preserved over parameter-derived defaults (since v post-2026-05-17).
- **`delete_note` / `replace_note`** require an MCP client that supports `elicit()` for confirmation. If your host can't surface the prompt you'll get a specific Spanish error explaining what to try instead — don't fall back to `rm` or full-file `patch_note` without checking the message.
- **Vault-rule warnings** appear in the response of `create_note` / `patch_note` etc. when content violates the rules. The full rule prose is only attached when violations are present; for clean writes the server emits a compact pointer back to `get_global_rules()`.
- **`list_notes` is paginated** at 500 notes by default. Pass `limit=0` for "everything" on small vaults, or watch the `Truncated:` footer for the next `offset`.

## When in doubt

Call `route_task("I need to X")` — it returns the right combination of prompts, skills, and tool calls for vague requests.
