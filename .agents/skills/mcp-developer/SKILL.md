---
name: MCP Developer
description: >
  Skill para desarrollar, mantener y extender el servidor MCP de Obsidian.
  Incluye patrones de código, arquitectura, testing y gestión de paquetes.
tools:
  - read
  - edit
  - run_command
  - grep_search
---

# MCP Server Developer

## Cuándo usar esta skill

- Cuando añadas nuevas herramientas (tools) o recursos al servidor MCP.
- Cuando resuelvas bugs o mejores el rendimiento del servidor.
- Cuando necesites ejecutar tests o linters en este proyecto.
- Cuando modifiques la configuración o el sistema de logging.

## Arquitectura del Proyecto

```
obsidian-mcp-server/
├── obsidian_mcp/
│   ├── server.py          # Punto de entrada - crea FastMCP y registra módulos
│   ├── config.py          # Pydantic Settings (OBSIDIAN_VAULT_PATH, LOG_LEVEL)
│   ├── tools/             # Herramientas MCP (funciones invocables)
│   │   ├── navigation.py  # Leer, listar, buscar notas
│   │   ├── creation.py    # Crear, editar, eliminar notas
│   │   ├── analysis.py    # Estadísticas, gestión de tags
│   │   ├── graph.py       # Backlinks, notas huérfanas
│   │   ├── agents.py      # Cargador de skills (del vault del usuario)
│   │   ├── semantic.py    # Integración RAG/búsqueda vectorial
│   │   ├── context.py     # Contexto y estructura del vault
│   │   └── youtube.py     # Extracción de transcripciones
│   ├── semantic/          # Módulo RAG opcional (ChromaDB)
│   │   ├── indexer.py     # Generación de embeddings
│   │   ├── retriever.py   # Búsqueda por similitud
│   │   └── service.py     # API de alto nivel RAG
│   ├── resources/         # Recursos MCP (endpoints de solo lectura)
│   ├── prompts/           # Prompts MCP (system prompts para IA)
│   └── utils/             # Utilidades compartidas
│       ├── logging.py     # Logging centralizado (a stderr)
│       ├── security.py    # Validación de rutas
│       └── vault.py       # Operaciones de archivos del vault
├── tests/                 # Suite de tests pytest
└── docs/                  # Documentación
```

## Reglas Core (Estrictas)

### Package Management
- **SIEMPRE** usa `uv`. **NUNCA** uses pip.
- Instalar: `uv add package`
- Ejecutar: `uv run tool`
- Dev dependencies: `uv add --dev package`

### Type Hints
- Requeridos al 100% en todo el código.
- Verificar con: `uv run pyright`

### Async
- Usa `anyio` para tests asíncronos, no `asyncio` directo.

## Patrón para Crear una Nueva Tool

> **IMPORTANTE**: Separa siempre la lógica del registro MCP.
> Esto permite testear las funciones independientemente y reduce la complejidad.

### Estructura de archivos

Para cada módulo de tools, mantén **dos archivos**:

```
obsidian_mcp/tools/
├── navigation.py        # Solo registro MCP (wrappers delgados)
├── navigation_logic.py  # Lógica de negocio (funciones puras)
├── analysis.py
├── analysis_logic.py
└── ...
```

### 1. Archivo de lógica (`*_logic.py`)

Contiene la implementación real, testeable independientemente:

```python
"""
Core business logic for XXX tools.

This module contains the actual implementation, separated from MCP
registration to improve testability and maintain single responsibility.
"""

from pathlib import Path

from ..config import get_vault_path
from ..utils import get_logger

logger = get_logger(__name__)


def do_something(param: str) -> str:
    """
    Descripción de lo que hace la función.

    Args:
        param: Descripción del parámetro.

    Returns:
        Resultado formateado como string.
    """
    vault_path = get_vault_path()
    if not vault_path:
        return "Error: La ruta del vault no está configurada."

    # ... implementación
    logger.info(f"Ejecutando do_something con {param}")

    return "Resultado exitoso"
```

### 2. Archivo de registro (`*.py`)

Contiene **solo wrappers delgados** que delegan a la lógica:

```python
"""
MCP tool registration for XXX functionality.
"""

from fastmcp import FastMCP

from .xxx_logic import do_something


def register_xxx_tools(mcp: FastMCP) -> None:
    """Registra las herramientas de XXX."""

    @mcp.tool()
    def mi_herramienta(param: str) -> str:
        """
        Descripción de lo que hace la herramienta.

        Args:
            param: Descripción del parámetro.

        Returns:
            Descripción del resultado.
        """
        return do_something(param)
```

### Beneficios de esta separación

| Aspecto | Sin separación | Con separación |
|---------|---------------|----------------|
| Testabilidad | Requiere MCP mock | Import directo |
| Complejidad | Alta (C901 > 10) | Baja (~1-2) |
| Reutilización | Imposible | Fácil |
| Mantenibilidad | Difícil | Simple |

### Pasos para añadir una tool:

1. **Crear la lógica** en `*_logic.py` (funciones puras, testeables)
2. **Crear el wrapper** en `*.py` con el decorator `@mcp.tool()`
3. **Registrar** en `server.py` si es un nuevo módulo
4. **Añadir tests** en `tests/` (importando desde `*_logic.py`)
5. **Documentar** en `docs/tool-reference.md`

## Módulos Centralizados

### Constantes (`constants.py`)

Todas las constantes numéricas deben estar centralizadas:

```python
from obsidian_mcp.constants import (
    SemanticDefaults,   # CHUNK_SIZE, VECTOR_K, DEFAULT_THRESHOLD...
    SearchLimits,       # MAX_SEARCH_RESULTS, MAX_DISPLAY_FILES...
    FolderSuggestion,   # SIMILAR_NOTES_LIMIT, HIGH_CONFIDENCE_THRESHOLD...
)
```

**NO hagas esto** (magic numbers dispersos):
```python
# ❌ MAL
if len(results) > 100:
    results = results[:100]
```

**Haz esto**:
```python
# ✅ BIEN
from ..constants import SearchLimits

if len(results) > SearchLimits.MAX_SEARCH_RESULTS:
    results = results[:SearchLimits.MAX_SEARCH_RESULTS]
```

### Mensajes (`messages.py`)

Mensajes de error y éxito estandarizados:

```python
from obsidian_mcp.messages import ErrorMessages, SuccessMessages

# Uso
return ErrorMessages.VAULT_NOT_CONFIGURED
return SuccessMessages.format_note_created(path)
```

### Configuración de exclusiones (`vault_config.py`)

Carpetas y patrones excluidos:

```python
from obsidian_mcp.vault_config import (
    DEFAULT_EXCLUDED_FOLDERS,  # [".git", ".obsidian", ...]
    DEFAULT_EXCLUDED_PATTERNS, # ["*.tmp", "*.bak", ...]
)
```

## Comandos de Desarrollo

```bash
# Formatear código
uv run ruff format .

# Verificar linting
uv run ruff check .

# Corregir linting automáticamente
uv run ruff check . --fix

# Verificar tipos
uv run pyright

# Ejecutar tests
uv run pytest tests/

# Ejecutar servidor en modo desarrollo
uv run mcp dev obsidian_mcp/server.py
```

## Estilo de Código

- **Formatter**: `uv run ruff format .`
- **Linter**: `uv run ruff check . --fix`
- **Line length**: 88 caracteres máximo
- **Docstrings**: Obligatorios en APIs públicas
- **Naming**: snake_case para funciones/variables, PascalCase para clases

## Sistema de Skills (en el Vault del Usuario)

Las skills NO están en este repositorio. Se cargan desde el vault del usuario:

- **Ubicación**: `{vault}/.agents/skills/{nombre_skill}/SKILL.md`
- **Formato**: Frontmatter YAML + cuerpo Markdown
- **Reglas globales**: `{vault}/.agents/REGLAS_GLOBALES.md`

## Logging

- Los logs van a `stderr` (stdout está reservado para el protocolo MCP)
- Usar: `from ..utils import get_logger; logger = get_logger(__name__)`
- Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Configurar con variable de entorno `LOG_LEVEL`

## Configuración (config.py)

Variables de entorno soportadas:

| Variable | Requerido | Descripción |
|----------|-----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Sí | Ruta absoluta al vault |
| `LOG_LEVEL` | No | Nivel de logging (default: INFO) |
| `OBSIDIAN_TEMPLATES_FOLDER` | No | Carpeta de plantillas |
| `OBSIDIAN_SYSTEM_FOLDER` | No | Carpeta del sistema |

## Anti-patrones (Qué NO hacer)

### ❌ Lógica dentro del decorator

```python
# MAL - No testeable, alta complejidad
@mcp.tool()
def mi_herramienta() -> str:
    # 100 líneas de código aquí
    ...
```

### ❌ Magic numbers dispersos

```python
# MAL - ¿Qué significa 100? ¿Por qué 0.7?
if len(results) > 100:
    ...
if similarity < 0.7:
    ...
```

### ❌ Strings de error duplicados

```python
# MAL - Mismo mensaje en 5 archivos distintos
return "❌ Error: La ruta del vault no está configurada."
```

### ❌ Funciones de registro demasiado largas

```python
# MAL - Complejidad ciclomática > 10
def register_xxx_tools(mcp):  # 500+ líneas
    @mcp.tool()
    def tool1(): ...  # 80 líneas
    @mcp.tool()
    def tool2(): ...  # 100 líneas
    # ... más funciones anidadas
```

### Verificar complejidad

```bash
# Muestra funciones con complejidad > 10
uv run ruff check . --select=C901
```

## Commits

- Usar conventional commits: `type(scope): description`
- NO incluir `Co-Authored-By`
- Para bugs reportados: `git commit --trailer "Reported-by:<name>"`
- Para issues de GitHub: `git commit --trailer "Github-Issue:#<number>"`
