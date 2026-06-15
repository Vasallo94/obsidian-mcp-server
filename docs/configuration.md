# Configuration

This page covers environment variables, vault profile configuration, tool sets,
and integration settings.

For client-specific snippets, see [Installation](installation.md).

## Environment Variables (.env)

Local development can use a `.env` file at the root of this repository.
Installed MCP clients usually set the same values in their MCP configuration.

| Variable | Required | Description |
| :--- | :---: | :--- |
| `OBSIDIAN_VAULT_PATH` | Yes | **Absolute** path to the root folder of your Obsidian vault. |
| `OBSIDIAN_MCP_TOOL_SETS` | No | Comma-separated optional tool sets, for example `notes_write,vault_analysis`. |
| `OBSIDIAN_MCP_PROFILE_NAME` | No | Optional active profile name exposed to prompts/resources. |
| `OBSIDIAN_SEARCH_TIMEOUT_SECONDS` | No | Search timeout override. |
| `OBSIDIAN_MAX_SEARCH_RESULTS` | No | Maximum default search result count. |
| `OBSIDIAN_CACHE_TTL_SECONDS` | No | Cache TTL for vault-derived context. |
| `LOG_LEVEL` | No | Log detail level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Defaults to `INFO`. |

Example `.env`:
```ini
OBSIDIAN_VAULT_PATH="/absolute/path/to/your/vault"
OBSIDIAN_MCP_TOOL_SETS="notes_write,vault_analysis"
LOG_LEVEL="DEBUG"
```

## Security and Exclusions

By design, the server ignores system and hidden folders to prevent information
leaks or corruption of Obsidian metadata:

- `.obsidian`
- `.git`
- `.trash`
- Other automatically configured directories.

To protect additional folders, use `.forbidden_paths` or
`private_paths` in `.agents/vault.yaml`.

## Vault-agnostic behavior

The server does not impose a folder structure. It auto-detects templates and
reads optional configuration from the vault.

### 1. Auto-detection
The server automatically tries to find key folders:
- **Templates**: It searches for any folder containing "template" or "plantilla" in its name (e.g., `ZZ_Templates`, `Templates`, `06_Templates`).

### Optional vault configuration

Create `.agents/vault.yaml` at the root of your vault when you want explicit
tool sets, profile resources, or integration settings:

```yaml
# .agents/vault.yaml
version: "1.0"

# Optional: Specify the templates folder if auto-detection fails
templates_folder: "MySpecialTemplatesFolder"

# Optional: Additional paths to protect from agent access
private_paths:
  - "**/Private/*"
  - "**/secrets.md"

profile:
  name: "my_profile"
  prompt_sets:
    - "mermaid"
  tool_sets:
    - "notes_write"
    - "vault_analysis"
  standards:
    writing: "Standards/Writing.md"
  local_docs:
    index: "README.md"
  integrations:
    obsidianrag:
      project_path: "/path/to/ObsidianRAG"
      api_url: "http://127.0.0.1:8000"
      env:
        OBSIDIANRAG_LLM_MODEL: "gemma3"
```

For the full `.agents/` contract, see [Agent folder setup](agent-folder-setup.md).

> [!WARNING]
> Never point `OBSIDIAN_VAULT_PATH` to a folder that contains sensitive private information outside of Obsidian, as the agent could read it if it has read permissions.

## MCP client integration

Client-specific setup lives in [Installation](installation.md). This page is
kept focused on environment variables, vault configuration, tool sets, and
profile behavior.

## Tool Sets and Client Roots

The MCP server exposes the `core` tool set by default. Extra capabilities are
explicit opt-ins:

- `notes_write`: note creation and mutation.
- `vault_analysis`: stats, tags, links, backlinks, and graph helpers.
- `agents_admin`: skill creation and validation.
- `youtube`: transcript import.
- `obsidianrag`: semantic search through the external ObsidianRAG backend.
- `canvas` and `kanvas`: visual canvas and workflow helpers.
- `legacy_semantic`: deprecated in-process semantic search. Prefer
  `obsidianrag`; this pack is kept only for backward compatibility.

Use `client.roots()` to inspect roots advertised by clients that support
the MCP `roots/list` capability. This is useful during setup because an agent
can confirm which workspaces or vault folders the client has made visible.

## ObsidianRAG Guided Setup

This project does not embed a second advanced RAG implementation by default.
When semantic search is needed, enable the `obsidianrag` tool set and declare
the local ObsidianRAG integration in `.agents/vault.yaml`.

The older `legacy_semantic` tool set is deprecated because it embeds ChromaDB
and LangChain retrievers directly in the MCP server. It now keeps only the
minimal Ollama embedding path; new deployments should use ObsidianRAG instead.

The server then exposes:

- `rag.setup_status()`: detects the configured project, backend, `uv`, Ollama
  CLI/API, and ObsidianRAG API health.
- `obsidian://integrations/obsidianrag/setup`: a setup playbook with exact
  commands, safe shell quoting, and optional environment variables.
- `rag.health()` and `rag.rebuild_index()` for readiness and first indexing.

Agents must ask for consent before installing dependencies, pulling models,
starting local services, or rebuilding a large index.

## Skills and global rules

The MCP server can read skills and global rules directly from your vault. These
files are not part of this repository.

### Expected structure

```text
your-vault/
├── .agents/
│   ├── REGLAS_GLOBALES.md      # General instructions for the assistant
│   └── skills/
│       ├── writer/
│       │   └── SKILL.md        # Definition of the "writer" skill
│       ├── researcher/
│       │   └── SKILL.md
│       └── reviewer/
│           └── SKILL.md
```

### SKILL.md Format

Each skill is defined with a `SKILL.md` file containing YAML frontmatter and
instructions:

```markdown
---
name: Technical Writer
description: Specialist in clear and concise documentation
tools:
  - notes.read
  - notes.search
  - notes.patch
---

# Instructions

You are a technical writer specializing in...

## Style
- Use active voice
- Avoid unnecessary jargon
...
```

### Frontmatter Fields

| Field | Required | Description |
| :--- | :---: | :--- |
| `name` | Yes | Readable name of the skill |
| `description` | Yes | Brief description of the role |
| `tools` | No | List of MCP tools this skill can use |

### REGLAS_GLOBALES.md

This file contains instructions that apply to all interactions with the
assistant, regardless of the active skill. For example:

```markdown
# Vault Global Rules

- Always reply in English
- Prefer existing tags before creating new ones
- Do not modify notes in 00_System without confirmation
```
