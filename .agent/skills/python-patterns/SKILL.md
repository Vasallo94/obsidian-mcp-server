---
name: Python Patterns
description: >
  Buenas prácticas y patrones de desarrollo Python para el proyecto MCP.
  Incluye estándares de código, patrones arquitectónicos, y convenciones.
tools:
  - read
  - edit
  - grep_search
---

# Python Patterns Skill

## Cuándo usar esta skill

- Al escribir nuevo código Python.
- Al revisar código existente.
- Cuando necesites decidir patrones de diseño.
- Al estructurar módulos y clases.

## Patrones Core del Proyecto

### 1. Estructura de Módulos

```python
"""
Descripción breve del módulo.

Descripción más detallada si es necesario.
"""

# 1. Imports de stdlib primero
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List

# 2. Imports de terceros
from fastmcp import FastMCP
from pydantic import BaseModel

# 3. Imports locales (relativos)
from ..config import get_vault_path
from ..utils import get_logger

# 4. Logger al inicio
logger = get_logger(__name__)


# 5. Funciones helper (privadas) primero
def _helper_function(data: str) -> str:
    """Helper interno del módulo."""
    return data.strip()


# 6. Funciones/clases públicas después
def public_function(param: str) -> str:
    """
    Función pública del módulo.
    
    Args:
        param: Descripción del parámetro.
        
    Returns:
        Descripción del retorno.
    """
    return _helper_function(param)
```

### 2. Type Hints (Obligatorio)

```python
# ✅ CORRECTO: Todo tipado
def process_note(
    path: Path,
    options: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str]:
    ...

# ❌ INCORRECTO: Sin tipos
def process_note(path, options=None):
    ...
```

**Tipos comunes en el proyecto**:

```python
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Any, Literal

# Para retornos con error
def operation() -> Tuple[bool, str]:
    """Retorna (success, message)."""
    if error:
        return False, "Error message"
    return True, "Success"

# Para configuración opcional
TransportType = Literal["stdio", "http", "sse"]
```

### 3. Patrón de Resultado (Success/Error)

```python
# Patrón estándar del proyecto para operaciones
def operation(param: str) -> str:
    """
    Realiza operación.
    
    Returns:
        Mensaje con emoji indicando resultado.
    """
    try:
        # Validación temprana
        if not param:
            return "❌ Error: Parámetro requerido"
        
        vault_path = get_vault_path()
        if not vault_path:
            return "❌ Error: La ruta del vault no está configurada."
        
        # Lógica principal
        result = do_something(param)
        
        # Éxito
        return f"✅ Operación completada: {result}"
        
    except SpecificError as e:
        return f"❌ Error específico: {e}"
    except Exception as e:
        return f"❌ Error inesperado: {e}"
```

### 4. Patrón de Validación (Tuple)

```python
def validate_something(value: str) -> Tuple[bool, str]:
    """
    Valida un valor.
    
    Returns:
        Tupla (es_valido, mensaje_error).
    """
    if not value:
        return False, "El valor es requerido"
    if len(value) < 3:
        return False, "El valor debe tener al menos 3 caracteres"
    return True, ""


# Uso
is_valid, error = validate_something(input_value)
if not is_valid:
    return f"❌ {error}"
```

### 5. Configuración con Pydantic

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MySettings(BaseSettings):
    """Configuración con validación automática."""
    
    model_config = SettingsConfigDict(
        env_prefix="MY_APP_",
        env_file=".env",
        extra="ignore",
    )
    
    required_field: str = Field(
        description="Campo requerido"
    )
    
    optional_field: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Campo opcional con límites"
    )
    
    @field_validator("required_field", mode="before")
    @classmethod
    def validate_field(cls, v: str) -> str:
        """Validación personalizada."""
        if not v:
            raise ValueError("Campo no puede estar vacío")
        return v.strip()
```

### 6. Singleton Pattern (Settings)

```python
_settings: Optional[MySettings] = None


def get_settings() -> MySettings:
    """Get or create singleton."""
    global _settings
    if _settings is None:
        _settings = MySettings()
    return _settings


def reset_settings() -> None:
    """Reset singleton (for testing)."""
    global _settings
    _settings = None
```

## Convenciones de Nombres

| Tipo | Convención | Ejemplo |
|------|------------|---------|
| Funciones | snake_case | `buscar_notas()` |
| Variables | snake_case | `vault_path` |
| Constantes | UPPER_SNAKE | `MAX_RESULTS` |
| Clases | PascalCase | `VaultSettings` |
| Módulos | snake_case | `navigation.py` |
| Privados | _prefijo | `_helper()` |

## Docstrings (Google Style)

```python
def function_name(param1: str, param2: int = 10) -> Dict[str, Any]:
    """
    Descripción breve en una línea.
    
    Descripción más detallada si es necesario. Puede
    ocupar múltiples líneas.
    
    Args:
        param1: Descripción del primer parámetro.
        param2: Descripción del segundo parámetro.
            Continuación indentada si es largo.
    
    Returns:
        Descripción del valor de retorno.
        
    Raises:
        ValueError: Si param1 está vacío.
        
    Example:
        >>> result = function_name("test")
        >>> print(result)
    """
```

## Error Handling

```python
# Específico antes de genérico
try:
    result = risky_operation()
except FileNotFoundError:
    logger.warning(f"Archivo no encontrado: {path}")
    return "❌ Archivo no existe"
except PermissionError:
    logger.error(f"Sin permisos: {path}")
    return "⛔ Acceso denegado"
except Exception as e:
    logger.exception(f"Error inesperado: {e}")
    return f"❌ Error: {e}"
```

## Logging

```python
from ..utils import get_logger

logger = get_logger(__name__)

# Niveles apropiados
logger.debug("Detalles de debugging")      # Solo en dev
logger.info("Operación completada")         # Flujo normal
logger.warning("Situación anómala")         # Problema no fatal
logger.error("Error en operación")          # Error que afecta función
logger.exception("Con traceback completo")  # En bloques except
```

## Anti-Patterns a Evitar

```python
# ❌ Imports dentro de funciones (excepto lazy imports justificados)
def my_function():
    import os  # Moverlo arriba
    ...

# ❌ Mutable default arguments
def bad(items: List = []):  # ¡Peligro!
    items.append(1)

# ✅ Correcto
def good(items: Optional[List] = None):
    if items is None:
        items = []

# ❌ Bare except
try:
    ...
except:  # Captura TODO incluido KeyboardInterrupt
    pass

# ✅ Correcto
try:
    ...
except Exception as e:
    logger.error(f"Error: {e}")

# ❌ String concatenation en loops
result = ""
for item in items:
    result += str(item)  # Ineficiente

# ✅ Correcto
result = "".join(str(item) for item in items)
```

## Checklist de Revisión

Al revisar código nuevo, verificar:

- [ ] Type hints en todas las funciones públicas
- [ ] Docstrings en funciones públicas
- [ ] Manejo de errores apropiado
- [ ] Logging en puntos críticos
- [ ] Sin argumentos mutables por defecto
- [ ] Imports organizados (stdlib → third-party → local)
- [ ] Nombres descriptivos y en español/inglés consistente
- [ ] Validación temprana de inputs
