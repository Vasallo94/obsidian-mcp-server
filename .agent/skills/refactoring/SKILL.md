---
name: Refactoring
description: >
  Guía para refactorizar código Python de forma segura y efectiva.
  Incluye técnicas de refactoring, detección de code smells, y mejoras.
tools:
  - read
  - edit
  - grep_search
  - run_command
---

# Refactoring Skill

## Cuándo usar esta skill

- Cuando detectes código duplicado.
- Cuando funciones sean demasiado largas (>50 líneas).
- Cuando módulos tengan demasiadas responsabilidades.
- Cuando quieras mejorar la legibilidad o mantenibilidad.

## Regla de Oro

> **Nunca refactorizar sin tests.** Ejecuta `uv run pytest tests/` antes y
> después de cada refactoring para verificar que no rompiste nada.

## Proceso de Refactoring Seguro

### 1. Verificar estado inicial

```bash
# Tests deben pasar
uv run pytest tests/ -v

# Sin errores de linting/tipos
uv run ruff check . && uv run pyright
```

### 2. Hacer cambio pequeño

Solo UN cambio a la vez. No mezclar refactorings.

### 3. Verificar después del cambio

```bash
uv run pytest tests/ -v
uv run ruff check . && uv run pyright
```

### 4. Commit si pasa

```bash
git add . && git commit -m "refactor(module): descripción breve"
```

## Code Smells Comunes

### 1. Función Larga (>50 líneas)

**Problema**: Difícil de entender y testear.

**Solución**: Extract Method

```python
# ❌ ANTES: Función monolítica
def process_vault(path: Path) -> str:
    # 100 líneas de código...
    pass

# ✅ DESPUÉS: Funciones pequeñas
def process_vault(path: Path) -> str:
    """Procesa el vault completo."""
    notes = _find_notes(path)
    filtered = _filter_forbidden(notes)
    formatted = _format_results(filtered)
    return formatted

def _find_notes(path: Path) -> List[Path]:
    """Busca notas en el vault."""
    return list(path.rglob("*.md"))

def _filter_forbidden(notes: List[Path]) -> List[Path]:
    """Filtra notas prohibidas."""
    return [n for n in notes if not is_forbidden(n)]

def _format_results(notes: List[Path]) -> str:
    """Formatea lista de notas."""
    return "\n".join(str(n) for n in notes)
```

### 2. Código Duplicado

**Problema**: Cambios requieren editar múltiples lugares.

**Solución**: Extract Function o clase base.

```python
# ❌ ANTES: Duplicado en cada tool
def tool1():
    vault_path = get_vault_path()
    if not vault_path:
        return "❌ Error: La ruta del vault no está configurada."
    # lógica...

def tool2():
    vault_path = get_vault_path()
    if not vault_path:
        return "❌ Error: La ruta del vault no está configurada."
    # lógica...

# ✅ DESPUÉS: Helper reutilizable
def _get_vault_or_error() -> Tuple[Optional[Path], Optional[str]]:
    """Obtiene vault path o mensaje de error."""
    vault_path = get_vault_path()
    if not vault_path:
        return None, "❌ Error: La ruta del vault no está configurada."
    return vault_path, None

def tool1():
    vault_path, error = _get_vault_or_error()
    if error:
        return error
    # lógica...
```

### 3. Parámetros Excesivos (>4)

**Problema**: Difícil de usar y recordar el orden.

**Solución**: Parameter Object (dataclass/TypedDict)

```python
# ❌ ANTES: Demasiados parámetros
def create_note(
    title: str,
    content: str,
    folder: str,
    tags: str,
    template: str,
    description: str,
    author: str,
) -> str:
    ...

# ✅ DESPUÉS: Objeto de configuración
from dataclasses import dataclass

@dataclass
class NoteConfig:
    title: str
    content: str
    folder: str = ""
    tags: str = ""
    template: str = ""
    description: str = ""
    author: str = ""

def create_note(config: NoteConfig) -> str:
    ...
```

### 4. Condicionales Anidados

**Problema**: Difícil de seguir la lógica.

**Solución**: Guard Clauses (early return)

```python
# ❌ ANTES: Anidamiento profundo
def process(data):
    if data:
        if data.is_valid:
            if data.has_permissions:
                return do_work(data)
            else:
                return "Sin permisos"
        else:
            return "Datos inválidos"
    else:
        return "Sin datos"

# ✅ DESPUÉS: Guard clauses
def process(data):
    if not data:
        return "Sin datos"
    if not data.is_valid:
        return "Datos inválidos"
    if not data.has_permissions:
        return "Sin permisos"
    
    return do_work(data)
```

### 5. Magic Numbers/Strings

**Problema**: Significado no claro, difícil de cambiar.

**Solución**: Constantes nombradas

```python
# ❌ ANTES
if len(content) > 100:
    content = content[:100] + "..."

# ✅ DESPUÉS
MAX_PREVIEW_LENGTH = 100
TRUNCATION_SUFFIX = "..."

if len(content) > MAX_PREVIEW_LENGTH:
    content = content[:MAX_PREVIEW_LENGTH] + TRUNCATION_SUFFIX
```

## Técnicas de Refactoring

### Rename (Renombrar)

Cambiar nombre para mejorar claridad.

```python
# ❌ Nombre vago
def proc(d):
    ...

# ✅ Nombre descriptivo
def process_markdown_content(content: str) -> str:
    ...
```

### Extract Variable

Hacer explícito un cálculo complejo.

```python
# ❌ ANTES
if path.suffix == ".md" and not str(path).startswith(".") and path.stat().st_size > 0:
    ...

# ✅ DESPUÉS
is_markdown = path.suffix == ".md"
is_not_hidden = not str(path).startswith(".")
is_not_empty = path.stat().st_size > 0

if is_markdown and is_not_hidden and is_not_empty:
    ...
```

### Replace Temp with Query

Método en vez de variable temporal.

```python
# ❌ ANTES
base_price = quantity * item_price
discount = base_price * 0.1

# ✅ DESPUÉS
def calculate_base_price() -> float:
    return quantity * item_price

def calculate_discount() -> float:
    return calculate_base_price() * 0.1
```

### Move Method

Mover función al módulo donde pertenece.

```python
# ❌ Función de seguridad en navigation.py
# obsidian_mcp/tools/navigation.py
def is_path_safe(path: Path) -> bool:
    ...

# ✅ Mover a security.py
# obsidian_mcp/utils/security.py
def is_path_safe(path: Path) -> bool:
    ...
```

## Refactoring en Este Proyecto

### Módulos Principales y Responsabilidades

| Módulo | Responsabilidad |
|--------|-----------------|
| `config.py` | Solo configuración de entorno |
| `vault_config.py` | Config específica del vault |
| `utils/security.py` | Validación de paths |
| `utils/vault.py` | Operaciones de archivo |
| `tools/*.py` | Herramientas MCP |

### Dónde Buscar Oportunidades

```bash
# Funciones largas
uv run ruff check . --select=C901

# Complejidad ciclomática alta
uv run radon cc obsidian_mcp/ -a

# Código duplicado (si radon disponible)
uv run radon raw obsidian_mcp/
```

## Checklist de Refactoring

Antes de refactorizar:

- [ ] Tests pasan (`uv run pytest tests/`)
- [ ] Entiendo el código actual
- [ ] Tengo claro el objetivo del refactoring

Durante el refactoring:

- [ ] Un cambio pequeño a la vez
- [ ] Tests después de cada cambio
- [ ] Commits frecuentes

Después del refactoring:

- [ ] Tests pasan
- [ ] Linting/tipos limpios
- [ ] Código más legible/mantenible
- [ ] Documentación actualizada si cambió API
