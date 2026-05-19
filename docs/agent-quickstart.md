# Agent Quickstart

A short orientation for AI agents using the Obsidian MCP server. Read this once at the start of a session and you'll skip a lot of trial-and-error.

## First two calls

1. `vault.context()` — folder layout, templates, common tags, active profile.
2. `rules.get()` — vault-wide author rules (frontmatter required fields, heading conventions, etc.). The server enforces these on every write and surfaces violations in the response; reading them upfront tells you what to comply with.

After those two calls you have enough context to write correctly. Everything below is a "when you need it" reference.

## Decision table — pick the right tool

| You need to… | Use |
|---|---|
| List notes in the vault | `notes.list(folder=, limit=500, offset=0, pattern=)` — paginates by default |
| Read one note | `notes.read(note_path)` |
| Read several notes | `notes.read_many(paths=[...])` — note: `paths`, not `query=` |
| Search by text | `notes.search(query=, titles_only=False)` |
| Search by date | `notes.search_by_date(date_from, date_to)` |
| Create a note | `notes.create(title, content, folder, tags, ...)` — embed YAML frontmatter in `content` and it'll be merged with parameters |
| Lint a note before writing | `notes.validate(content, title, mode='create')` — pre-flight, no write |
| Edit fragments of a note | `notes.patch(note_path, operations=[{old, new}, ...])` — fuzzy suggestions on miss |
| Replace whole note body | `notes.replace(note_path, content)` — requires client elicit() support |
| Delete a note | `notes.delete(note_path)` — requires client elicit() support |
| Rename a note + update wikilinks | `notes.rename(source, new_name, update_links=True)` |
| Move a note | `notes.move(source, destination, update_links=True)` |
| Find broken wikilinks across the vault | `links.find_broken(limit=100)` — returns source file + line + fuzzy suggestions |
| Link/orphan analysis | `links.analyze()`, `links.find_orphans()` |
| Bulk find/replace text | `notes.preview_replace(...)` then `notes.apply_replace(...)` |
| Lint every note against vault rules (heading emojis, missing frontmatter fields, etc.) | `vault.lint(auto_fix=False)` to scan, then `vault.lint(auto_fix=True)` to apply regex-based fixes |
| Vault stats / tag audit | `vault.stats()`, `tags.analyze()`, `tags.list()` |
| Routing help | `route.task(request)` — suggests prompts/skills/tools for an ambiguous task |

## Common traps

- **`notes.read_many` argument name** is `paths` (a list), not `query`. Pydantic will reject `query=`.
- **Tags passed as a string** like `"astro, equipo"` are normalized to a YAML list in frontmatter. This is intentional but undocumented in the field name.
- **Embedded frontmatter wins**: if your `notes.create` content starts with `---...---`, fields like `type` and `status` are preserved over parameter-derived defaults (since v post-2026-05-17).
- **`notes.delete` / `notes.replace`** require an MCP client that supports `elicit()` for confirmation. If your host can't surface the prompt you'll get a specific Spanish error explaining what to try instead — don't fall back to `rm` or full-file `notes.patch` without checking the message.
- **Vault-rule warnings** appear in the response of `notes.create` / `notes.patch` etc. when content violates the rules. The full rule prose is only attached when violations are present; for clean writes the server emits a compact pointer back to `rules.get()`.
- **`notes.list` is paginated** at 500 notes by default. Pass `limit=0` for "everything" on small vaults, or watch the `Truncated:` footer for the next `offset`.

## When in doubt

Call `route.task("I need to X")` — it returns the right combination of prompts, skills, and tool calls for vague requests.
