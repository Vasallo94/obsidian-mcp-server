---
name: Test Runner
description: >
  Skill para ejecutar y gestionar tests. Incluye patrones de testing,
  fixtures comunes, y estrategias de debugging de tests fallidos.
tools:
  - run_command
  - read
  - edit
---

# Test Runner Skill

## Cuándo usar esta skill

- Cuando ejecutes tests del proyecto.
- Cuando añadas nuevos tests.
- Cuando debuggees tests que fallan.
- Cuando necesites verificar cobertura.

## Comandos de Ejecución

### Ejecutar todos los tests

```bash
uv run pytest tests/
```

### Ejecutar test específico

```bash
# Por archivo
uv run pytest tests/test_basic.py

# Por función
uv run pytest tests/test_basic.py::test_function_name

# Por clase
uv run pytest tests/test_basic.py::TestClassName
```

### Opciones útiles

```bash
# Verbose - más detalle
uv run pytest tests/ -v

# Stop en primer fallo
uv run pytest tests/ -x

# Solo tests que fallaron antes
uv run pytest tests/ --lf

# Mostrar prints
uv run pytest tests/ -s

# Combinado: verbose, stop, prints
uv run pytest tests/ -vxs
```

## Estructura de Tests

Los tests están en `tests/`:

```
tests/
├── conftest.py           # Fixtures compartidas
├── test_basic.py         # Tests de herramientas básicas
├── test_security.py      # Tests de seguridad/paths
├── test_agents.py        # Tests de carga de skills
├── test_connection_logic.py  # Tests de conexiones semánticas
└── test_image_indexing.py    # Tests de indexación de imágenes
```

## Patrón para Nuevos Tests

```python
"""
Tests para {módulo}.
"""

import pytest
import anyio  # Para tests async

from obsidian_mcp.module import function_to_test


class TestFunctionName:
    """Tests para function_to_test."""

    def test_caso_normal(self) -> None:
        """Verifica comportamiento normal."""
        result = function_to_test("input")
        assert result == "expected"

    def test_caso_error(self) -> None:
        """Verifica manejo de errores."""
        with pytest.raises(ValueError):
            function_to_test(None)

    @pytest.mark.asyncio
    async def test_async_function(self) -> None:
        """Verifica función asíncrona."""
        result = await async_function()
        assert result is not None
```

## Fixtures Comunes

En `conftest.py`:

```python
import pytest
from pathlib import Path


@pytest.fixture
def test_vault(tmp_path: Path) -> Path:
    """Crea un vault temporal para tests."""
    vault = tmp_path / "test_vault"
    vault.mkdir()
    # Crear estructura básica
    (vault / "note1.md").write_text("# Test Note")
    return vault


@pytest.fixture
def sample_note(test_vault: Path) -> Path:
    """Crea una nota de ejemplo."""
    note = test_vault / "sample.md"
    note.write_text("---\ntags: [test]\n---\n# Sample")
    return note
```

## Debugging Tests Fallidos

### 1. Ver output detallado

```bash
uv run pytest tests/test_failing.py -vvs
```

### 2. Usar breakpoint

```python
def test_something():
    result = function()
    breakpoint()  # Pausa aquí
    assert result == expected
```

Luego ejecutar:
```bash
uv run pytest tests/test_file.py -s
```

### 3. Ver traceback completo

```bash
uv run pytest tests/ --tb=long
```

## Marcadores Útiles

```python
# Saltar test
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    ...

# Saltar condicionalmente
@pytest.mark.skipif(condition, reason="...")
def test_conditional():
    ...

# Esperar fallo
@pytest.mark.xfail(reason="Known bug")
def test_known_issue():
    ...
```

## Variables de Entorno para Tests

Algunos tests necesitan configuración:

```bash
# Ejecutar con vault de prueba
OBSIDIAN_VAULT_PATH=/tmp/test_vault uv run pytest tests/
```

## Checklist Pre-Push

Antes de hacer push, ejecutar suite completa:

```bash
# Todos los tests deben pasar
uv run pytest tests/ -v

# Verificar que no hay warnings críticos
uv run pytest tests/ -W error
```

## Reports

Para generar reporte HTML (si pytest-html está instalado):

```bash
uv run pytest tests/ --html=report.html
```
