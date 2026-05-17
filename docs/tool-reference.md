# Tool Reference

This guide lists the public MCP tools exposed by Obsidian MCP Server. Tool
names and argument names are intentionally English, even when a vault profile
contains local Spanish documentation.

## Core Tools

Always enabled.

- `health_check()`: Validate the active vault and profile configuration.
- `diagnose_vault_setup()`: Return actionable setup recommendations.
- `list_client_roots()`: Inspect MCP client roots advertised through `roots/list`.
- `route_task(request)`: Recommend prompts, skills, resources, and tools for a task.
- `read_vault_context()`: Summarize folders, templates, common tags, and `.agents`.
- `list_notes(folder, include_subfolders, limit, offset, pattern)`: List
  Markdown notes with pagination. Default `limit=500`; pass `limit=0` for
  no limit. Use `pattern` (glob like `"2026-*.md"`) to narrow further.
  Responses include a `Truncated:` footer with the next `offset` when more
  results exist.
- `read_note(note_path)`: Read one note, with path checks and output limits.
- `search_notes(query, folder, titles_only)`: Search titles or Markdown content.
- `search_notes_by_date(date_from, date_to)`: Find recently modified notes.
- `read_notes(paths)`: Batch-read notes with a response-size guard. `paths` is
  a list of vault-relative paths (one Pydantic argument, not `query=`).
- `get_note_info(paths)`: Return metadata without full note content.
- `list_templates()`: List available vault templates.
- `get_frontmatter(note_path)`: Read YAML frontmatter.
- `list_skills()`: List valid vault skills from `.agents/skills`.
- `read_skill(name)`: Read a declared vault skill.
- `get_global_rules()`: Read vault-level global agent rules.
- `validate_note(content, title, mode)`: Lint a note against vault rules WITHOUT
  writing it. Returns JSON `{valid, mode, violations[]}`. Call before
  `create_note` / `patch_note` to skip a write round-trip. `mode` is
  `create` (default), `edit`, or `append`.

## Optional Tool Sets

Optional tools are enabled from `.agents/vault.yaml` with
`profile.tool_sets`, or from `OBSIDIAN_MCP_TOOL_SETS`.

### `notes_write`

- `suggest_note_location(title, content, tags)`: Suggest a vault folder.
- `create_note(title, content, folder, tags, template, created_by)`: Create a note.
  `tags` is a comma-separated string (e.g. `"astro, equipo"`); it is normalized
  to a YAML list in the saved frontmatter. If `content` already starts with a
  `---...---` frontmatter block, embedded fields (`type`, `status`, custom keys)
  are preserved; conflicts with explicit parameters resolve in favour of the
  embedded frontmatter.
- `append_to_note(note_path, content, at_end)`: Append or prepend content.
- `patch_note(note_path, operations)`: Apply atomic exact-match edits with
  operations shaped as `{"old": "...", "new": "..."}`. Compatibility aliases
  `oldText`/`newText` and `old_text`/`new_text` are accepted, but clients
  should prefer `old`/`new`.
- `replace_note(note_path, content)`: Replace a full note.
- `update_frontmatter(note_path, updates)`: Update YAML frontmatter.
- `update_note_tags(note_path, tags)`: Update tag metadata.
- `move_note(source, destination, create_folders, update_links)`: Move or
  rename a note. When `update_links=True`, every vault wikilink targeting
  the old stem is rewritten to the new stem (aliases/sections preserved).
  When `False`, the response still reports how many references became
  stale so you can re-run with `update_links=True`.
- `rename_note(source, new_name, update_links=True)`: Rename a note in
  place and update all wikilinks referencing it. Pass `new_name` as the
  stem (without `.md`), or as a path to also move folders.
- `delete_note(note_path, confirm)`: Delete a note after explicit confirmation.
- `preview_replace_in_notes(...)`: Preview global replacements.
- `apply_replace_in_notes(...)`: Apply global replacements.

### `vault_analysis`

- `get_vault_stats()`: Count notes, tags, links, and vault size.
- `get_canonical_tags()`: Read the canonical tag registry.
- `analyze_tags()`: Compare used tags against canonical tags.
- `sync_tag_registry(update)`: Update tag registry statistics.
- `list_tags()`: List tags currently used in the vault.
- `analyze_links()`: Inspect internal link health.
- `summarize_recent_activity(days)`: Summarize recent vault changes.
- `get_backlinks(note_path)`: Find backlinks for a note.
- `get_notes_by_tag(tag)`: Find notes with a tag.
- `get_local_graph(note_path, depth)`: Explore local graph connections.
- `find_orphan_notes()`: Find notes without incoming or outgoing links.
- `find_broken_wikilinks(limit=100)`: List every `[[target]]` in the vault
  whose target note doesn't exist. Returns source file + line + fuzzy
  match suggestions per broken reference (Issue #6). Pair with `rename_note`
  or `apply_replace_in_notes` to fix them in bulk.

### `obsidianrag`

This pack delegates advanced semantic search to the external ObsidianRAG
project instead of embedding a second RAG stack inside this MCP server.

- `rag_setup_status()`: Diagnose the local ObsidianRAG setup.
- `rag_health()`: Check whether the ObsidianRAG HTTP API is reachable.
- `ask_vault(question, session_id)`: Ask a semantic question through ObsidianRAG.
- `rebuild_rag_index()`: Trigger ObsidianRAG index rebuild.

### Other Packs

- `agents_admin`: `refresh_skills_cache`, `create_skill`, `suggest_vault_skills`,
  `sync_skills`.
- `youtube`: `get_youtube_transcript`.
- `legacy_semantic`: deprecated in-process semantic tools, disabled by default.
  Prefer `obsidianrag` for all new semantic-search deployments.
- `canvas`: Obsidian Canvas read/write tools.
- `kanvas`: workflow/task-board tools.
- `secundo_selebro`: personal profile tools such as `quick_capture`.

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

- **Verb-first** for generic note operations: `create_note`, `read_note`,
  `patch_note`, `move_note`, `delete_note`, `analyze_links`, `find_orphan_notes`.
- **Namespace-prefixed** for domain-specific tool families: `canvas_*` (Obsidian
  Canvas), `kanvas_*` (workflow boards), `rag_*` / `ask_vault` (semantic search).

Renaming public tools is a breaking change for MCP clients, so the mix is
intentional. When in doubt, search this reference first; the function-name
prefix matches the tool name verbatim.
