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

Cada módulo de tools sigue este patrón:

```python
"""
Descripción del módulo de herramientas.
"""

from fastmcp import FastMCP

from ..config import get_vault_path
from ..utils import get_logger

logger = get_logger(__name__)


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
        vault_path = get_vault_path()
        if not vault_path:
            return "❌ Error: La ruta del vault no está configurada."

        # ... implementación
        logger.info(f"Ejecutando mi_herramienta con {param}")

        return "✅ Resultado exitoso"
```

### Pasos para añadir una tool:

1. **Crear la función** en el archivo de tools correspondiente (`obsidian_mcp/tools/`)
2. **Registrar** en `server.py` si es un nuevo módulo
3. **Añadir tests** en `tests/`
4. **Documentar** en `docs/tool-reference.md`

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

- **Ubicación**: `{vault}/.agent/skills/{nombre_skill}/SKILL.md`
- **Formato**: Frontmatter YAML + cuerpo Markdown
- **Reglas globales**: `{vault}/.agent/REGLAS_GLOBALES.md`

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

## Commits

- Usar conventional commits: `type(scope): description`
- NO incluir `Co-Authored-By`
- Para bugs reportados: `git commit --trailer "Reported-by:<name>"`
- Para issues de GitHub: `git commit --trailer "Github-Issue:#<number>"`
