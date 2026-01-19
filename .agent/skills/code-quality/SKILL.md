---
name: Code Quality
description: >
  Skill para mantener la calidad del código: linting, formatting,
  type checking. Garantiza que el código cumple con los estándares del proyecto.
tools:
  - run_command
  - read
  - edit
---

# Code Quality Skill

## Cuándo usar esta skill

- Antes de hacer commit de cualquier cambio.
- Cuando corrijas errores de linting o tipos.
- Cuando formatees código nuevo.
- Cuando necesites verificar la calidad general del código.

## Herramientas de Calidad

Este proyecto usa:

| Herramienta | Propósito |
|-------------|-----------|
| **Ruff** | Linting + Formatting |
| **Pyright** | Type checking |

## Flujo de Verificación Completo

### Paso 1: Formatear código

```bash
uv run ruff format .
```

Aplica formato automático a todo el código.

### Paso 2: Verificar y corregir linting

```bash
# Solo verificar
uv run ruff check .

# Corregir automáticamente lo posible
uv run ruff check . --fix
```

### Paso 3: Verificar tipos

```bash
uv run pyright
```

## Errores Comunes y Soluciones

### E501: Line too long

**Problema**: Línea excede 88 caracteres.

**Soluciones**:
```python
# Antes
mensaje = "Este es un mensaje muy largo que excede el límite de caracteres permitidos por el linter"

# Después - usando paréntesis
mensaje = (
    "Este es un mensaje muy largo que excede "
    "el límite de caracteres permitidos por el linter"
)

# Después - para docstrings, usar noqa
"""Línea muy larga que es difícil de partir.  # noqa: E501"""
```

### Missing type hints

**Problema**: Función sin anotaciones de tipo.

**Solución**:
```python
# Antes
def process(data):
    return data.upper()

# Después
def process(data: str) -> str:
    return data.upper()
```

### Import ordering

**Problema**: Imports desordenados.

**Solución**: Ruff format los ordena automáticamente. Orden correcto:
1. Standard library
2. Third-party
3. Local imports

```python
import os
from pathlib import Path

from fastmcp import FastMCP
import anyio

from ..config import get_vault_path
from ..utils import get_logger
```

## Configuración Actual

Ver `pyproject.toml` para configuración:

```toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "standard"
```

## Comando Todo-en-Uno

Script para verificar todo antes de commit:

```bash
# Formatear + Lint + Tipos
uv run ruff format . && uv run ruff check . --fix && uv run pyright
```

## Ignorar Reglas (Casos Excepcionales)

Si necesitas ignorar una regla específica:

```python
# Ignorar línea específica
long_string = "..."  # noqa: E501

# Ignorar bloque
# ruff: noqa: E501
def function_with_long_lines():
    ...
```

> ⚠️ **Usar con moderación**. Preferir corregir el código.

## Checklist de Calidad

Antes de considerar el código listo:

- [ ] `uv run ruff format .` - Sin cambios pendientes
- [ ] `uv run ruff check .` - Sin errores
- [ ] `uv run pyright` - Sin errores de tipos
- [ ] Docstrings en funciones públicas
- [ ] Nombres descriptivos (snake_case)
