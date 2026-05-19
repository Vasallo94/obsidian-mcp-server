# Obsidian MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
<br>
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-5c3cfa?style=flat)](https://modelcontextprotocol.io/)
[![Obsidian Integration](https://img.shields.io/badge/Obsidian-Vault-483699?style=flat&logo=obsidian&logoColor=white)](https://obsidian.md/)
[![Claude Desktop](https://img.shields.io/badge/Claude-Desktop-D97757?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/)
[![Custom Skills](https://img.shields.io/badge/AI-Skills-10A37F?style=flat)](https://github.com/Vasallo94/obsidian-mcp-server/blob/main/docs/agent-folder-setup.md)

An **MCP (Model Context Protocol)** server that makes an Obsidian vault useful to AI clients such as Claude Desktop, Claude Code, Cursor, and Cline. It is designed as a public, reusable core with optional tool sets and vault-specific profiles layered on top.

---

## Features

### Public Core

The core tool set is always available and stays vault-agnostic:

- Vault diagnostics, task routing, and MCP client root inspection.
- Note listing, reading, metadata inspection, and search.
- Vault context resources for profiles, skills, standards, and local docs.
- Core prompts for structured notes, template usage, and context exploration.

### Optional Tool Sets

Optional packs are enabled explicitly from `.agents/vault.yaml` or
`OBSIDIAN_MCP_TOOL_SETS`:

- **`notes_write`**: Create, patch, move, and delete notes.
- **`vault_analysis`**: Vault statistics, tags, links, backlinks, and graph tools.
- **`agents_admin`**: Skill creation, validation, and cache management.
- **`youtube`**: Transcript extraction.
- **`obsidianrag`**: Semantic search through the external ObsidianRAG service.
- **`canvas` / `kanvas`**: Canvas and workflow helpers.
- **Profile packs**: Personal workflows only when a vault profile opts in.

### Design Principles

- **Public core, personal profiles**: The repository remains reusable; local workflows live in vault configuration and resources.
- **English technical surface**: Tool names, prompt names, docs, and code identifiers are English.
- **Safe by default**: Write tools are opt-in, protected paths are blocked, and large reads are capped.
- **External RAG by integration**: Advanced semantic search delegates to ObsidianRAG instead of duplicating a RAG stack inside the MCP server.

## Quick Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recommended)

### Steps

1. **Clone**:

   ```bash
   git clone https://github.com/Vasallo94/obsidian-mcp-server.git
   cd obsidian-mcp-server
   ```

2. **Install**:

   ```bash
   make install
   # Optional legacy in-process semantic stack:
   pip install "obsidian-mcp-server[rag]"
   ```

3. **Configure**:

   ```bash
   cp .env.example .env
   # Edit .env with the absolute path to your Obsidian vault
   ```

---

## Usage

The MCP server connects to compatible clients using the `uv run obsidian-mcp-server` command. Below are setup instructions for popular AI clients.

### Claude Desktop Integration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/Absolute/Path/To/Your/Vault"
      }
    }
  }
}
```

### Optional Tool Sets

Enable optional tools from the client environment:

```json
{
  "env": {
    "OBSIDIAN_VAULT_PATH": "/Absolute/Path/To/Your/Vault",
    "OBSIDIAN_MCP_TOOL_SETS": "notes_write,vault_analysis,obsidianrag"
  }
}
```

Or declare them in your vault profile:

```yaml
profile:
  name: "my_profile"
  prompt_sets:
    - "mermaid"
  tool_sets:
    - "notes_write"
    - "vault_analysis"
  standards:
    media: "Standards/Media.md"
  local_docs:
    index: "README.md"
```

### ObsidianRAG Integration

For semantic vault search, enable the `obsidianrag` tool set and declare the
integration:

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

Then read `obsidian://integrations/obsidianrag/setup` or call
`rag.setup_status`. Agents should show setup commands before installing
dependencies, starting services, pulling models, or rebuilding the index.

### Cursor & Cline Integration

For other clients like Cursor or Cline, you can add it as a new MCP server in their settings panel by specifying:
- **Type**: `command`
- **Command**: `uv run obsidian-mcp-server`
- Ensure the `OBSIDIAN_VAULT_PATH` environment variable is available to the instance running the command.

---

## Technical Documentation

To dive deeper into how the server works and how to customize it, check our detailed guides located in the `docs/` folder:

1. [Architecture](docs/architecture.md): Modular structure and data flow of the project.
2. [Tool Reference](docs/tool-reference.md): Complete list of available MCP tools and their parameters.
3. [Server Configuration](docs/configuration.md): Guide on environment variables and technical configuration.
4. [Agent Setup](docs/agent-folder-setup.md): How to organize your vault (`.agents/`) with skills and contextual rules.
5. [Semantic Search](docs/semantic-search.md): ObsidianRAG integration and legacy RAG migration notes.
6. [Future Roadmap](docs/FUTURE.md): Planned improvements and next steps for the server.

---

## Development & Quality

| Command | Description |
| :--- | :--- |
| `make test` | Run the test suite (pytest) |
| `make lint` | Run static checks (Ruff + Mypy + Pylint) |
| `make format` | Automatically format code |
| `make dev` | Run the MCP inspector for live testing |

---

## License

This project is licensed under the MIT License.
