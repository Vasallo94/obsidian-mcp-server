# Configuration Guide

For the MCP server to function correctly, you need to configure the environment and understand the structure of the special folders the server expects to find in your vault.

## Environment Variables (.env)

The `.env` file at the root of the project is essential:

| Variable | Required | Description |
| :--- | :---: | :--- |
| `OBSIDIAN_VAULT_PATH` | Yes | **Absolute** path to the root folder of your Obsidian vault. |
| `OBSIDIAN_MCP_TOOL_SETS` | No | Comma-separated optional tool sets, for example `notes_write,vault_analysis`. |
| `LOG_LEVEL` | No | Log detail level (`INFO`, `DEBUG`, `ERROR`). Defaults to `INFO`. |

Example `.env`:
```ini
OBSIDIAN_VAULT_PATH="/Users/enrique/Documents/MyDigitalBrain"
OBSIDIAN_MCP_TOOL_SETS="notes_write,vault_analysis"
LOG_LEVEL="DEBUG"
```

## Security and Exclusions

By design, the server ignores system and hidden folders to prevent information leaks or corruption of Obsidian metadata:
- `.obsidian`
- `.git`
- `.trash`
- Other automatically configured directories.

To protect additional folders, use the `.forbidden_paths` file at the root of the server or the `private_paths` configuration in `vault.yaml`.

## Vault-Agnostic Architecture

The server is designed to be **vault-independent**. It does not impose any mandatory folder structure and uses an intelligent auto-detection logic.

### 1. Auto-detection
The server automatically tries to find key folders:
- **Templates**: It searches for any folder containing "template" or "plantilla" in its name (e.g., `ZZ_Templates`, `Templates`, `06_Templates`).

### 2. Optional Configuration (`vault.yaml`)
If you have a non-standard structure or want more granular control, you can create a `.agents/vault.yaml` file at the root of your vault:

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

For a detailed guide on how to configure the `.agents/` folder, refer to the [Agent Folder Setup Guide](agent-folder-setup.md).

> [!WARNING]
> Never point `OBSIDIAN_VAULT_PATH` to a folder that contains sensitive private information outside of Obsidian, as the agent could read it if it has read permissions.

## MCP Clients Integration

The server can be configured for multiple MCP clients. Below are the configurations for the most common ones.

### Claude Code (CLI)

```bash
# Add at the user level (available in all projects)
claude mcp add-json --scope user obsidian '{
  "command": "uv",
  "args": ["run", "--directory", "/path/to/obsidian-mcp-server", "obsidian-mcp-server"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/path/to/your/vault"
  }
}'
```

### Claude Desktop

File: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/.config/claude/claude_desktop_config.json` (Linux/Mac)

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/obsidian-mcp-server", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### VSCode (Claude Extension / GitHub Copilot)

File: `~/.vscode/mcp.json`

```json
{
  "servers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/obsidian-mcp-server", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### Cursor / Cline

You can add it as a new MCP server in their settings panel by specifying:
- **Type**: `command`
- **Command**: `uv run --directory /path/to/obsidian-mcp-server obsidian-mcp-server`
- Ensure the `OBSIDIAN_VAULT_PATH` environment variable is available.

### Gemini CLI

File: `~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/obsidian-mcp-server", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/path/to/your/vault"
      }
    }
  }
}
```

### Windows Note

On Windows, if you use `npx` or scripts that require a shell, use the `cmd /c` prefix:

```json
{
  "command": "cmd",
  "args": ["/c", "uv", "run", "--directory", "C:/path/to/server", "obsidian-mcp-server"]
}
```

## Tool Sets and Client Roots

The MCP server exposes a small core by default. Extra capabilities are explicit
opt-ins:

- `notes_write`: note creation and mutation.
- `vault_analysis`: stats, tags, links, backlinks, and graph helpers.
- `agents_admin`: skill creation and validation.
- `youtube`: transcript import.
- `obsidianrag`: semantic search through the external ObsidianRAG backend.
- `canvas` and `kanvas`: visual canvas and workflow helpers.

Use `list_client_roots()` to inspect roots advertised by clients that support
the MCP `roots/list` capability. This is useful during setup because an agent
can confirm which workspaces or vault folders the client has made visible.

## ObsidianRAG Guided Setup

This project does not embed a second advanced RAG implementation. When semantic
search is needed, enable the `obsidianrag` tool set and declare the local
ObsidianRAG integration in `.agents/vault.yaml`.

The server then exposes:

- `rag_setup_status()`: detects the configured project, backend, `uv`, Ollama
  CLI/API, and ObsidianRAG API health.
- `obsidian://integrations/obsidianrag/setup`: a setup playbook with exact
  commands, safe shell quoting, and optional environment variables.
- `rag_health()` and `rebuild_rag_index()` for readiness and first indexing.

Agents must ask for consent before installing dependencies, pulling models,
starting local services, or rebuilding a large index.

## Skills and Global Rules (in your Vault)

The MCP server can read **skills** (AI personalities/roles) and **global rules** directly from your Obsidian vault. These files **are not in the MCP repository**, but in your personal vault.

### Expected Structure in your Vault

```text
Your_Vault/
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

Each skill is defined with a `SKILL.md` file containing YAML frontmatter and the prompt:

```markdown
---
name: Technical Writer
description: Specialist in clear and concise documentation
tools:
  - create_note
  - patch_note
  - search_notes
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

This file contains instructions that apply to **all** interactions with the assistant, regardless of the active skill. For example:

```markdown
# Vault Global Rules

- Always reply in English
- Prefer existing tags before creating new ones
- Do not modify notes in 00_System without confirmation
```
