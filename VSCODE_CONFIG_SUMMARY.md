# Configuración de VS Code para Obsidian MCP Server

## Resumen de Configuración

Este documento describe la configuración de VS Code optimizada para el desarrollo del Obsidian MCP Server, siguiendo las directrices establecidas en `.github/copilot-instructions.md`.

## Archivos Configurados

### `.vscode/settings.json`
**Configuración principal del proyecto:**

- **Python Environment**: Configurado para usar `.venv` creado por `uv`
- **Package Manager**: Configurado para usar `uv` como gestor de paquetes predeterminado
- **Formateo**: `ruff` como formateador predeterminado con formato automático al guardar
- **Linting**: `ruff` habilitado con corrección automática de imports y errores
- **Type Checking**: `pyright` en modo estricto
- **Testing**: `pytest` configurado con autodescubrimiento
- **Exclusiones**: Archivos de cache y temporales excluidos de búsqueda y explorador

### `.vscode/tasks.json`
**Tareas automatizadas para desarrollo:**

- `uv: Install Dependencies` - Instalar dependencias con `uv sync --group dev`
- `ruff: Format Code` - Formatear código con `uv run ruff format .`
- `ruff: Check Code` - Verificar código con `uv run ruff check .`
- `ruff: Fix Issues` - Corregir problemas con `uv run ruff check . --fix`
- `pyright: Type Check` - Verificar tipos con `uv run pyright .`
- `pytest: Run Tests` - Ejecutar tests con `uv run pytest -v`
- `pytest: Run Tests with Coverage` - Tests con cobertura
- `MCP Server: Run Development` - Ejecutar servidor en desarrollo
- `Quality Check: All` - Tarea compuesta que ejecuta todas las verificaciones

### `.vscode/launch.json`
**Configuraciones de depuración:**

- `Python: MCP Server` - Depurar el servidor MCP principal
- `Python: Current File` - Depurar archivo actual
- `Python: Pytest Current File` - Depurar tests del archivo actual
- `Python: Pytest All Tests` - Depurar todos los tests

### `.vscode/extensions.json`
**Extensiones recomendadas para el equipo:**

- `ms-python.python` - Soporte Python principal
- `ms-python.debugpy` - Depuración Python
- `charliermarsh.ruff` - Linter y formateador Ruff
- `tamasfe.even-better-toml` - Soporte TOML para pyproject.toml
- `yzhang.markdown-all-in-one` - Edición Markdown
- Extensiones adicionales para Git, JSON, YAML

## Características Principales

### 🔧 Herramientas Integradas
- **uv**: Gestor de paquetes y entornos virtuales
- **ruff**: Linting y formateo ultrarrápido
- **pyright**: Type checking estricto
- **pytest**: Framework de testing con anyio

### 🚀 Automatización
- Formato automático al guardar
- Corrección automática de imports
- Detección automática de tests
- Tareas predefinidas para flujo de desarrollo

### 🎯 Calidad de Código
- Type hints obligatorios
- Línea máxima de 88 caracteres
- Imports organizados automáticamente
- Coverage de tests integrado

### 🤝 Colaboración
- Configuración compartida para el equipo
- Extensiones recomendadas estandarizadas
- Depuración configurada y lista para usar
- Exclusión de archivos personales (.local, temp)

## Uso Recomendado

### Comandos Rápidos (Ctrl/Cmd + Shift + P):
- `Tasks: Run Task` → Seleccionar cualquier tarea automatizada
- `Python: Select Interpreter` → Debería detectar automáticamente `.venv/bin/python`
- `Test: Discover Tests` → Autodescubrir tests de pytest

### Atajos de Teclado:
- **Ctrl/Cmd + S**: Guardado con formato automático
- **Ctrl/Cmd + Shift + P** → `ruff: Fix All Issues`: Corregir todos los problemas
- **F5**: Ejecutar configuración de depuración actual

### Flujo de Desarrollo:
1. VS Code detecta automáticamente el entorno `.venv`
2. Al guardar archivos Python, se formatea automáticamente con `ruff`
3. Los errores de tipo se muestran en tiempo real con `pyright`
4. Los tests se descubren automáticamente y se pueden ejecutar desde la UI
5. Las tareas están disponibles en el Command Palette

## Verificación de Configuración

Para verificar que todo está funcionando:

```bash
# Verificar herramientas
uv run ruff format .
uv run ruff check .
uv run pyright .
uv run pytest -v

# Debería mostrar:
# - 19 files left unchanged (ruff format)
# - All checks passed! (ruff check)
# - 0 errors, 0 warnings, 0 informations (pyright)
# - 16 passed (pytest)
```

La configuración garantiza un entorno de desarrollo consistente, moderno y eficiente para todo el equipo.
