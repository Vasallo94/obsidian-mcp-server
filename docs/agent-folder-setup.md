# Agent Folder Setup

The `.agents/` folder lives inside your Obsidian vault. It is optional, but it
is the recommended way to make the MCP server behave like your vault rather than
a generic file browser.

```text
your-vault/
├── .agents/
│   ├── vault.yaml
│   ├── REGLAS_GLOBALES.md
│   └── skills/
│       └── writer/
│           └── SKILL.md
└── ... your notes
```

## What each file does

| Path | Purpose | Exposed through |
|---|---|---|
| `.agents/vault.yaml` | Optional profile, tool sets, standards, integrations, private paths | `vault.health`, `vault.diagnose`, `obsidian://profile`, `obsidian://capabilities` |
| `.agents/REGLAS_GLOBALES.md` | Global instructions and validation rules for agents | `rules.get()` |
| `.agents/skills/<name>/SKILL.md` | Reusable agent roles or workflows | `skills.list()`, `skills.read(name)`, `obsidian://skills/{name}` |

## Minimal vault.yaml

Most vaults do not need a config file. Create one only when you want explicit
tool sets, profile resources, or privacy rules.

```yaml
version: "1.0"

templates_folder: "Templates"

private_paths:
  - "**/Private/**"
  - "**/secrets.md"

profile:
  name: "my_vault"
  tool_sets:
    - "notes_write"
    - "vault_analysis"
  prompt_sets:
    - "mermaid"
  standards:
    writing: "Standards/Writing.md"
  local_docs:
    index: "README.md"
```

If omitted, the server:

- enables only the safe `core` tools;
- auto-detects template folders containing `template` or `plantilla`;
- uses `.forbidden_paths` plus built-in hidden/system exclusions;
- still exposes `vault.context()`, `rules.get()`, and `skills.*` when those
  files exist.

## Enabling tool sets

Tool sets can be enabled from the client environment:

```bash
OBSIDIAN_MCP_TOOL_SETS="notes_write,vault_analysis"
```

Or from the vault profile:

```yaml
profile:
  tool_sets:
    - "notes_write"
    - "vault_analysis"
    - "obsidianrag"
```

Use the smallest set that fits your workflow. Write tools are intentionally
opt-in.

## Global rules

`REGLAS_GLOBALES.md` is read with `rules.get()`. Agents should call it near the
start of a session, usually after `vault.context()`.

Example:

```markdown
---
name: global-agent-rules
description: Mandatory protocol for agents working in this vault.
---

# Global Rules

## Editing

- Read a note with `notes.read()` before editing it.
- Use `notes.patch()` for exact-match edits.
- Use `notes.validate()` before creating or replacing a large note.

## Privacy

- Do not access notes tagged `#private`.
- Ask before enabling write-heavy workflows.
```

## Skills

Each skill is a folder with a `SKILL.md` file:

```text
.agents/
└── skills/
    └── writer/
        └── SKILL.md
```

Example:

```markdown
---
name: writer
description: Draft and edit notes while preserving the user's voice.
tools:
  - notes.read
  - notes.search
  - notes.patch
---

# Writer

Read the target note before editing. Preserve the author's tone. When changing
text, prefer `notes.patch()` with exact `old` and `new` fragments.
```

The server validates skills and reports invalid files through:

- `skills.list()`;
- `skills.read(name)`;
- `obsidian://skills/list`;
- `obsidian://skills/catalog`.

## Standards and local docs

Profile standards and local docs expose vault-owned documentation as MCP
resources.

```yaml
profile:
  standards:
    media: "Standards/Media.md"
    writing: "Standards/Writing.md"
  local_docs:
    workflows: "Docs/Workflows.md"
```

Agents can read them through:

- `obsidian://standards/media`;
- `obsidian://standards/writing`;
- `obsidian://local_docs/workflows`.

## ObsidianRAG integration

Use the external ObsidianRAG service for semantic search:

```yaml
profile:
  tool_sets:
    - "obsidianrag"
  integrations:
    obsidianrag:
      project_path: "/path/to/ObsidianRAG"
      api_url: "http://127.0.0.1:8000"
      env:
        OBSIDIANRAG_LLM_MODEL: "gemma3"
        OBSIDIANRAG_OLLAMA_EMBEDDING_MODEL: "embeddinggemma"
```

Agents should read `obsidian://integrations/obsidianrag/setup` or call
`rag.setup_status()` before starting services, installing dependencies, pulling
models, or rebuilding an index.
