# Tool Reference

This guide lists the public MCP tools exposed by Obsidian MCP Server. Tool
names and argument names are intentionally English, even when a vault profile
contains local Spanish documentation.

## Core Tools

Always enabled.

- `vault.health()`: Validate the active vault and profile configuration.
- `vault.diagnose()`: Return actionable setup recommendations.
- `client.roots()`: Inspect MCP client roots advertised through `roots/list`.
- `route.task(request)`: Recommend prompts, skills, resources, and tools for a task.
- `vault.context()`: Summarize folders, templates, common tags, and `.agents`.
- `notes.list(folder, include_subfolders, limit, offset, pattern)`: List
  Markdown notes with pagination. Default `limit=500`; pass `limit=0` for
  no limit. Use `pattern` (glob like `"2026-*.md"`) to narrow further.
  Responses include a `Truncated:` footer with the next `offset` when more
  results exist.
- `notes.read(note_path)`: Read one note, with path checks and output limits.
- `notes.search(query, folder, titles_only)`: Search titles or Markdown content.
- `notes.search_by_date(date_from, date_to)`: Find recently modified notes.
- `notes.read_many(paths)`: Batch-read notes with a response-size guard. `paths` is
  a list of vault-relative paths (one Pydantic argument, not `query=`).
- `notes.info(paths)`: Return metadata without full note content.
- `templates.list()`: List available vault templates.
- `notes.get_frontmatter(note_path)`: Read YAML frontmatter.
- `skills.list()`: List valid vault skills from `.agents/skills`.
- `skills.read(name)`: Read a declared vault skill.
- `rules.get()`: Read vault-level global agent rules.
- `notes.validate(content, title, mode)`: Lint a note against vault rules WITHOUT
  writing it. Returns JSON `{valid, mode, violations[]}`. Call before
  `notes.create` / `notes.patch` to skip a write round-trip. `mode` is
  `create` (default), `edit`, or `append`.

## Optional Tool Sets

Optional tools are enabled from `.agents/vault.yaml` with
`profile.tool_sets`, or from `OBSIDIAN_MCP_TOOL_SETS`.

### `notes_write`

- `notes.suggest_location(title, content, tags)`: Suggest a vault folder.
- `notes.create(title, content, folder, tags, template, created_by)`: Create a note.
  `tags` is a comma-separated string (e.g. `"astro, equipo"`); it is normalized
  to a YAML list in the saved frontmatter. If `content` already starts with a
  `---...---` frontmatter block, embedded fields (`type`, `status`, custom keys)
  are preserved; conflicts with explicit parameters resolve in favour of the
  embedded frontmatter.
- `notes.append(note_path, content, at_end)`: Append or prepend content.
- `notes.patch(note_path, operations)`: Apply atomic exact-match edits with
  operations shaped as `{"old": "...", "new": "..."}`. Compatibility aliases
  `oldText`/`newText` and `old_text`/`new_text` are accepted, but clients
  should prefer `old`/`new`.
- `notes.replace(note_path, content)`: Replace a full note.
- `notes.update_frontmatter(note_path, updates)`: Update YAML frontmatter.
- `notes.update_tags(note_path, tags)`: Update tag metadata.
- `notes.move(source, destination, create_folders, update_links)`: Move or
  rename a note. When `update_links=True`, every vault wikilink targeting
  the old stem is rewritten to the new stem (aliases/sections preserved).
  When `False`, the response still reports how many references became
  stale so you can re-run with `update_links=True`.
- `notes.rename(source, new_name, update_links=True)`: Rename a note in
  place and update all wikilinks referencing it. Pass `new_name` as the
  stem (without `.md`), or as a path to also move folders.
- `notes.delete(note_path, confirm)`: Delete a note after explicit confirmation.
- `notes.preview_replace(...)`: Preview global replacements.
- `notes.apply_replace(...)`: Apply global replacements.

### `vault_analysis`

- `vault.stats()`: Count notes, tags, links, and vault size.
- `tags.canonical()`: Read the canonical tag registry.
- `tags.analyze()`: Compare used tags against canonical tags.
- `tags.sync_registry(update)`: Update tag registry statistics.
- `tags.list()`: List tags currently used in the vault.
- `links.analyze()`: Inspect internal link health.
- `activity.recent(days)`: Summarize recent vault changes.
- `links.backlinks(note_path)`: Find backlinks for a note.
- `tags.notes_with(tag)`: Find notes with a tag.
- `links.local_graph(note_path, depth)`: Explore local graph connections.
- `links.find_orphans()`: Find notes without incoming or outgoing links.
- `vault.lint(folder, rule_ids, auto_fix, limit)`: Run vault rules across
  every note in one sweep (Issue #9). With `auto_fix=True` the
  regex-based heading/body rules are rewritten in place; frontmatter
  rules remain report-only because they need semantic input.
- `links.find_broken(limit=100)`: List every `[[target]]` in the vault
  whose target note doesn't exist. Returns source file + line + fuzzy
  match suggestions per broken reference (Issue #6). Pair with `notes.rename`
  or `notes.apply_replace` to fix them in bulk.

### `obsidianrag`

This pack delegates advanced semantic search to the external ObsidianRAG
project instead of embedding a second RAG stack inside this MCP server.

- `rag.setup_status()`: Diagnose the local ObsidianRAG setup.
- `rag.health()`: Check whether the ObsidianRAG HTTP API is reachable.
- `rag.ask(question, session_id)`: Ask a semantic question through ObsidianRAG.
- `rag.rebuild_index()`: Trigger ObsidianRAG index rebuild.

### Other Packs

- `agents_admin`: `skills.refresh_cache`, `skills.create`, `skills.suggest`,
  `skills.sync`, `rules.add`. `rules.add(rule_text)` registers a new global
  rule in `.agents/REGLAS_GLOBALES.md` after interactive confirmation, so the
  agent never edits that file directly.
- `youtube`: `youtube.transcript`.
- `legacy_semantic`: deprecated in-process semantic tools, disabled by default:
  `semantic.index`, `semantic.search`, and `semantic.suggest_connections`.
  Prefer `obsidianrag` for all new semantic-search deployments.
- `canvas`: Obsidian Canvas read/write tools — `canvas.read` (surfaces the
  standard color legend and any board "Legend"/"Leyenda" card), `canvas.list`,
  `canvas.add_card`, `canvas.add_group`, `canvas.add_edge`, `canvas.update_card`,
  `canvas.move_card` (reposition a node by x/y), `canvas.remove_card`,
  `canvas.remove_group(group_id, remove_contents=False)`, and `canvas.remove_edge`.
  Card text is validated against the vault rules (e.g. no emojis in headings),
  just like `notes.*`. Standard colors: `"0"`=default, `"1"`=red, `"2"`=orange,
  `"3"`=yellow, `"4"`=green, `"5"`=cyan, `"6"`=purple.
- `kanvas`: workflow/task-board tools — `kanvas.init`, `kanvas.status`,
  `kanvas.task`, `kanvas.ready`, `kanvas.blocked`, `kanvas.start`,
  `kanvas.finish`, `kanvas.pause`, `kanvas.approve`, `kanvas.complete`,
  `kanvas.edit_task`, `kanvas.add_dependency`, `kanvas.propose_task`, and
  `kanvas.propose_group`.
- Profile-specific packs such as `secundo_selebro`: local tools enabled only by
  a matching vault profile, for example `inbox.capture` and `random.concept`.

## Resources

- `obsidian://docs/agent-quickstart`: AI-agent orientation (start here on
  every new session). Two-call boot sequence, decision table mapping
  intent -> tool, and common pitfalls.
- `obsidian://capabilities`: Active prompts, tool sets, resources, and integrations.
- `obsidian://profile`: Safe active profile summary.
- `obsidian://skills/list`: Valid and invalid vault skills.
- `obsidian://skills/catalog`: Skills with use-case hints.
- `obsidian://skills/{name}`: A specific skill file.
- `obsidian://standards/{name}`: A declared profile standard.
- `obsidian://local_docs/{name}`: A declared local document.
- `obsidian://integrations/obsidianrag/setup`: Guided ObsidianRAG setup playbook.
- `obsidian://integrations/obsidianrag/config`: Safe ObsidianRAG integration config.

## Naming Conventions

Tool names follow two patterns by intent:

- **Verb-first** for generic note operations: `notes.create`, `notes.read`,
  `notes.patch`, `notes.move`, `notes.delete`, `links.analyze`, `links.find_orphans`.
- **Namespace-prefixed** for domain-specific tool families: `canvas.*`
  (Obsidian Canvas), `kanvas.*` (workflow boards), and `rag.*`
  (semantic search).

Renaming public tools is a breaking change for MCP clients, so the mix is
intentional. When in doubt, search this reference first; the function-name
prefix matches the tool name verbatim.
