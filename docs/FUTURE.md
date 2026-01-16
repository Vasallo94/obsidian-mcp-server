# Future Improvements

Ideas for future development of obsidian-mcp-server.

---

## Migration Tool

**Status**: Deferred

**Description**: Tool that automatically generates `.agent/vault.yaml` from an existing vault structure.

**Implementation ideas**:
- Scan root folders and detect naming patterns
- Identify templates folder (look for `.md` files with Mustache/placeholder syntax)
- Detect tag registry files
- Present detected structure to user for confirmation
- Generate complete `vault.yaml`

**Tool signature**:
```python
@mcp.tool()
def generar_vault_config(confirmar: bool = False) -> str:
    """
    Escanea el vault y genera .agent/vault.yaml.
    
    Args:
        confirmar: Si True, crea el archivo. Si False, solo muestra preview.
    """
```

---

## Multi-Vault Support

Support connecting to multiple vaults simultaneously.

---

## Vault Templates Repository

Pre-made vault configurations for common use cases:
- Personal Knowledge Management
- Academic Research
- Software Documentation
- Creative Writing
