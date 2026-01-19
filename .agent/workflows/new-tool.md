---
description: Add a new MCP tool to the server
---

# New Tool Workflow

Follow this workflow when adding a new tool to the MCP server.

## Steps

1. **Decide location**: Choose the appropriate module in `obsidian_mcp/tools/`:
   - `navigation.py` - Reading, listing, searching notes
   - `creation.py` - Creating, editing, deleting notes
   - `analysis.py` - Statistics, tag management
   - `graph.py` - Backlinks, orphan notes
   - `semantic.py` - Vector/RAG functionality
   - `context.py` - Vault structure and context
   - Or create a new module if it's a new category

2. **Implement the tool** following this pattern:
```python
@mcp.tool()
def tool_name(param: str, optional_param: bool = False) -> str:
    """
    Brief description of what the tool does.

    Args:
        param: Description of the parameter.
        optional_param: Description (default: False).

    Returns:
        Description of the return value.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return "❌ Error: La ruta del vault no está configurada."

    # Implementation here
    logger.info(f"Executing tool_name with {param}")

    return "✅ Result message"
```

3. **Register the tool** (only if new module):
   - Add import to `server.py`
   - Add registration call in `create_server()`

4. **Add tests** in `tests/test_*.py`:
```python
def test_tool_name() -> None:
    """Test tool_name functionality."""
    result = tool_name("input")
    assert "expected" in result
```

5. **Update documentation**:
   - Add entry to `docs/tool-reference.md`
   - Add to `CHANGELOG.md` under `[Unreleased] > Added`

6. **Run verification**:
```bash
uv run ruff format . && uv run ruff check . --fix && uv run pyright && uv run pytest tests/ -v
```
