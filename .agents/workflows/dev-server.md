---
description: Run the MCP server in development mode
---

# Dev Server Workflow

Run the MCP server in development mode for testing.

// turbo

## Steps

1. Ensure environment is set up:
```bash
cat .env
```
Should show `OBSIDIAN_VAULT_PATH=...`

2. Run the development server:
```bash
uv run mcp dev obsidian_mcp/server.py
```

3. The server will start and show available tools.

4. Use Ctrl+C to stop the server.
