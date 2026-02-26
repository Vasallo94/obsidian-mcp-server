# Obsidian MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
<br>
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-5c3cfa?style=flat)](https://modelcontextprotocol.io/)
[![Obsidian Integration](https://img.shields.io/badge/Obsidian-Vault-483699?style=flat&logo=obsidian&logoColor=white)](https://obsidian.md/)
[![Claude Desktop](https://img.shields.io/badge/Claude-Desktop-D97757?style=flat&logo=anthropic&logoColor=white)](https://claude.ai/)
[![Custom Skills](https://img.shields.io/badge/AI-Skills-10A37F?style=flat)](https://github.com/Vasallo94/obsidian-mcp-server/blob/main/docs/agent-folder-setup.md)

An advanced **MCP (Model Context Protocol)** server that turns your Obsidian vault into a dynamic brain for your AI (Claude Desktop, Cursor, Claude Code, Cline, etc.). Much more than a file reader: it is an ecosystem of tools for knowledge management, workflow automation, and semantic analysis.

---

## Features

### Tool Ecosystem (30+)

The server exposes a wide variety of tools categorized by function:

- **Navigation**: Intelligent listing, recursive reading, and advanced searching.
- **Creation and Editing**: Automatic template usage, location suggestions, and non-destructive editing preserving metadata (frontmatter/YAML).
- **Analysis and Quality**: Vault statistics, tag synchronization with the official registry, and integrity checks.
- **Graphs and Connections**: Backlink analysis, orphan note detection, and local graph visualization.
- **Skills (Agents)**: Dynamic loading of AI personalities/roles from your vault (`{vault}/.agent/skills/`).
- **Semantic Search (RAG)**: Meaning-based searches, suggestions for non-obvious connections, and vector indexing.
- **YouTube**: Extraction of transcripts to feed your knowledge base.

### Built-in Intelligence

- **Vault-Agnostic Architecture**: Independent of your folder structure; it uses intelligent auto-detection to find templates and resources.
- **Security**: Strict protection of sensitive folders via `.forbidden_paths` and vault privacy configurations.
- **Customizable Skills**: Define specific AI roles directly within your vault (`.agent/skills/`) for specialized tasks.

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
   # For semantic search capabilities (RAG):
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
4. [Agent Setup](docs/agent-folder-setup.md): How to organize your vault (`.agent/`) with skills and contextual rules.
5. [Semantic Search (RAG)](docs/semantic-search.md): Deep dive into vector indexing and RAG mechanics.
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
