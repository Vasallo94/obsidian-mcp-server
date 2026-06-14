# Installation

Obsidian MCP Server runs as a local stdio MCP server. The only required
configuration is `OBSIDIAN_VAULT_PATH`, an absolute path to the Obsidian vault.

## Recommended command

After the package is published, use:

```bash
uvx obsidian-mcp-server
```

Before the package is published to PyPI, use the Git source:

```bash
uvx --from git+https://github.com/Vasallo94/obsidian-mcp-server.git obsidian-mcp-server
```

For local development:

```bash
uv run --directory /path/to/obsidian-mcp-server obsidian-mcp-server
```

## Claude Code

```bash
claude mcp add-json --scope user obsidian '{
  "type": "stdio",
  "command": "uvx",
  "args": ["obsidian-mcp-server"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
  }
}'
```

For a Git install before PyPI publication:

```bash
claude mcp add-json --scope user obsidian '{
  "type": "stdio",
  "command": "uvx",
  "args": ["--from", "git+https://github.com/Vasallo94/obsidian-mcp-server.git", "obsidian-mcp-server"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
  }
}'
```

## Codex

Add this to `~/.codex/config.toml`:

```toml
[mcp_servers.obsidian]
command = "uvx"
args = ["obsidian-mcp-server"]
startup_timeout_sec = 30
tool_timeout_sec = 120

[mcp_servers.obsidian.env]
OBSIDIAN_VAULT_PATH = "/absolute/path/to/your/vault"
```

For a Git install before PyPI publication:

```toml
[mcp_servers.obsidian]
command = "uvx"
args = [
  "--from",
  "git+https://github.com/Vasallo94/obsidian-mcp-server.git",
  "obsidian-mcp-server",
]
startup_timeout_sec = 30
tool_timeout_sec = 120

[mcp_servers.obsidian.env]
OBSIDIAN_VAULT_PATH = "/absolute/path/to/your/vault"
```

## Hermes

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  obsidian:
    command: "uvx"
    args: ["obsidian-mcp-server"]
    env:
      OBSIDIAN_VAULT_PATH: "/absolute/path/to/your/vault"
```

For a Git install before PyPI publication:

```yaml
mcp_servers:
  obsidian:
    command: "uvx"
    args:
      - "--from"
      - "git+https://github.com/Vasallo94/obsidian-mcp-server.git"
      - "obsidian-mcp-server"
    env:
      OBSIDIAN_VAULT_PATH: "/absolute/path/to/your/vault"
```

## Claude Desktop

Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": ["obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
      }
    }
  }
}
```

For a Git install before PyPI publication:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Vasallo94/obsidian-mcp-server.git",
        "obsidian-mcp-server"
      ],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/absolute/path/to/your/vault"
      }
    }
  }
}
```

## Optional tool sets

Core read tools are enabled by default. Enable write/analysis integrations with
`OBSIDIAN_MCP_TOOL_SETS`:

```json
{
  "OBSIDIAN_MCP_TOOL_SETS": "notes_write,vault_analysis"
}
```

Common tool sets: `notes_write`, `vault_analysis`, `agents_admin`, `youtube`,
`obsidianrag`, `canvas`, `kanvas`, and `legacy_semantic`.

## MCPB

MCPB bundles are intended for one-click local installation in apps that support
the `.mcpb` format. MCPB bundles are release artifacts, so use the published
bundle for your operating system when one is available.

Until a release artifact is published for your operating system, use the
Git-source install path for pre-release testing:

```bash
uvx --from git+https://github.com/Vasallo94/obsidian-mcp-server.git obsidian-mcp-server
```

Source bundle build tooling belongs to the release pipeline and is not a manual
installation step here yet.
