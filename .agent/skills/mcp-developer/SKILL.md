---
name: mcp-developer
description: >
  Usa esta skill para desarrollar, mantener y extender el servidor MCP de Obsidian
  (obsidian-mcp-server). Incluye reglas de código, testing y gestión de paquetes.
tools: ['read', 'edit', 'run_command', 'grep_search']
---

# MCP Server Developer

## Cuándo usar esta skill
- Cuando añadas nuevas herramientas o recursos al servidor MCP.
- Cuando resuelvas bugs o mejores el rendimiento del servidor.
- Cuando necesites ejecutar tests o linters en este proyecto.

## Cómo usar esta skill

### 1. Reglas Core (Strict)
- **Package Management**: SIEMPRE usa `uv`. NUNCA uses pip.
  - Instalar: `uv add package`
  - Ejecutar: `uv run tool`
- **Type Hints**: Requeridos al 100%. Usa `uv run pyright` para verificar.
- **Async**: Usa `anyio` para tests asíncronos, no `asyncio` directo si es posible.

### 2. Estilo de Código
- **Formatter**: `uv run ruff format .`
- **Linter**: `uv run ruff check . --fix`
- **Docstrings**: Obligatorios en APIs públicas.

### 3. Workflow de Desarrollo
1.  **Crear Tool**: Define la función en `obsidian_mcp/tools/`.
2.  **Registrar**: Añádela en `server.py` o módulo correspondiente.
3.  **Testear**:
    ```bash
    uv run pytest tests/
    ```

### 4. Estructura
- `obsidian_mcp/tools/`: Lógica de las herramientas.
- `obsidian_mcp/server.py`: Punto de entrada del servidor FastMCP.
- `tests/`: Tests con pytest.

### 5. Configuración
Usa `obsidian_mcp/config.py` para manejar variables de entorno y rutas del vault.
