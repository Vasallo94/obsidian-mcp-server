# Troubleshooting

## MCP connection fails on reconnect / timeout at startup

**Symptoms**: Claude Code (or Claude Desktop) shows a connection error when starting or reconnecting the MCP server. The `/mcp` reconnect button fails.

**Cause**: When dependencies are not yet installed or the `.venv` is stale (e.g., after cloning on a new machine, after updating `uv.lock`, or after a `uv` cache clean), `uv run` needs to resolve and install packages before the server can start. This download/install phase can exceed the client's connection timeout, causing the MCP handshake to fail.

**Quick fix**:

```bash
cd /path/to/obsidian-mcp-server
uv sync
```

Then reconnect the MCP from Claude Code (`/mcp` > reconnect).

**Permanent fix**: Use the wrapper script `scripts/start-mcp.sh` instead of calling `uv run` directly. This script runs `uv sync --quiet` before launching the server, ensuring dependencies are always ready.

Update your `.mcp.json` (or `claude_desktop_config.json`) to use:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "bash",
      "args": [
        "C:/Users/ldaevf1/Programs/obsidian-mcp-server/scripts/start-mcp.sh"
      ],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/Absolute/Path/To/Your/Vault"
      }
    }
  }
}
```

## FastMCP version check hangs in corporate networks

**Symptoms**: The server takes several seconds to start, or hangs briefly at startup.

**Cause**: FastMCP 3.x calls `check_for_newer_version()` at startup, which makes an HTTP request to PyPI. In corporate networks with proxy restrictions, this request may hang until its 2-second timeout.

**Fix**: Set the environment variable to disable the version check:

```json
"env": {
  "OBSIDIAN_VAULT_PATH": "...",
  "FASTMCP_CHECK_FOR_UPDATES": "off"
}
```
