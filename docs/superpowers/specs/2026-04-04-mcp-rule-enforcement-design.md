# Diseño: Enforcement de reglas del vault en el MCP server

**Fecha:** 2026-04-04
**Estado:** Propuesta
**Problema:** Los agentes de IA no leen ni respetan las reglas del vault antes de escribir notas, a pesar de que las reglas existen en `.agents/REGLAS_GLOBALES.md` y las tool descriptions las referencian.

---

## Contexto

### Situacion actual

- Las reglas del vault viven en `.agents/REGLAS_GLOBALES.md` como prosa con un frontmatter YAML.
- Las tool descriptions de `crear_nota`, `editar_nota`, etc. incluyen advertencias que dicen "DEBES haber leido las reglas globales", pero no hay enforcement.
- Las skills en `.agents/skills/` repiten la "Regla de oro de edicion" y el callout de REGLAS_GLOBALES en cada archivo (10 veces).
- El resultado es que los agentes ignoran las reglas sistematicamente.

### Principios de diseno

1. **Enforcement server-side**: las reglas se validan dentro del MCP server, no en el cliente. Cualquier agente (Claude Code, Hermes, Gemini CLI, LangChain, etc.) recibe los mismos warnings.
2. **Vault-configurable**: las reglas son datos editables en el vault, no codigo Python hardcodeado. Anadir o modificar una regla no requiere tocar el MCP.
3. **Agnostico al vault**: el MCP no sabe nada de las convenciones especificas de un vault concreto. Lee las reglas del vault en el que esta montado y las ejecuta genericamente.
4. **Soft warning**: las operaciones nunca se bloquean. El MCP escribe la nota y devuelve los warnings al agente para que corrija.
5. **Contexto minimo**: no contaminar el context window del agente con inyecciones innecesarias. Solo inyectar donde aporta valor.

---

## Arquitectura

### Tres capas

```
VAULT (.agents/REGLAS_GLOBALES.md)
  - Define QUE se valida (bloque `validations:` en frontmatter)
  - Define QUE se inyecta (prosa del cuerpo del archivo)
  - Editable sin tocar codigo

MCP SERVER (obsidian_mcp/middleware.py - nuevo)
  - Cadena de interceptores inspirada en LangChain tool_interceptors
  - Patron "onion": cada interceptor envuelve al siguiente
  - Cache en memoria del proceso para no releer el vault en cada llamada

TOOLS (creation.py, context.py, etc.)
  - Cada tool se ejecuta a traves de la cadena de interceptores
  - No contiene logica de validacion — esta delegada al middleware
```

### Flujo de una operacion de creacion

```
1. Agente llama a crear_nota(titulo, contenido, ...)
2. La cadena de interceptores se activa:
   a. rules_validator: carga validations del vault (cache), ejecuta checks mecanicos
   b. rules_injector: carga prosa de reglas (cache), la prepara para inyectar
3. Se ejecuta la funcion real de crear_nota — la nota se escribe
4. El response se enriquece:
   - Si hay warnings: se anade bloque [WARNINGS] con violaciones especificas
   - Si aplica inyeccion: se anade bloque [REGLAS ACTIVAS] con la prosa
5. El agente recibe el response completo y puede corregir
```

---

## Formato de reglas en REGLAS_GLOBALES.md

Se anade un bloque `validations` al frontmatter existente. La prosa no cambia.

```yaml
---
name: reglas-globales-agentes
description: >
  Protocolo obligatorio que TODOS los agentes deben seguir antes de crear
  o editar notas en el vault.
updated: 2026-04-04

validations:
  - id: no_emoji_headings
    applies_to: [create, append, edit]
    scope: headings
    pattern: "[\U0001F300-\U0001FFFF\u2600-\u27BF\u2700-\u27BF]"
    warning: "Emojis en cabeceras"

  - id: no_emoji_title
    applies_to: [create]
    scope: title
    pattern: "[\U0001F300-\U0001FFFF\u2600-\u27BF]"
    warning: "Emojis en el titulo de la nota"

  - id: required_frontmatter
    applies_to: [create]
    scope: frontmatter
    required_fields: [type, status, tags]
    warning: "Frontmatter incompleto: faltan {missing_fields}"

  - id: valid_status
    applies_to: [create, edit]
    scope: frontmatter
    field: status
    allowed_values: [captura, en_proceso, completo, archivo]
    warning: "Valor de 'status' invalido: '{value}'"

  - id: valid_type
    applies_to: [create]
    scope: frontmatter
    field: type
    allowed_values: [diario, semanario, apunte, resumen, creacion, proyecto, doc-proyecto, recurso, evento, indice, prompt, factura, inbox]
    warning: "Valor de 'type' invalido: '{value}'"
---

# Reglas Globales para Agentes
(... prosa existente sin cambios ...)
```

### Tipos de validacion soportados

| Tipo | Campos YAML | Que valida |
|------|-------------|------------|
| Regex en scope | `scope` + `pattern` | Ejecuta regex contra lineas del scope (headings, title, body) |
| Campos requeridos | `scope: frontmatter` + `required_fields` | Comprueba que los campos existen |
| Valores permitidos | `scope: frontmatter` + `field` + `allowed_values` | Comprueba valor contra lista |

### Campo `applies_to`

Define en que tipo de operacion se ejecuta la validacion:

| Valor | Tools afectados |
|-------|-----------------|
| `create` | `crear_nota`, `captura_rapida` |
| `append` | `agregar_a_nota`, `agregar_en_seccion` |
| `edit` | `editar_nota` |

### Campo `scope`

Define sobre que parte del contenido se ejecuta la validacion:

| Valor | Que se inspecciona |
|-------|-------------------|
| `headings` | Lineas que empiezan con `#` |
| `title` | El parametro `titulo` de `crear_nota` |
| `body` | Todo el contenido |
| `frontmatter` | Los metadatos (campos del frontmatter) |

---

## Clasificacion de tools

### Creacion de contenido — validacion mecanica + inyeccion de prosa

- `crear_nota`
- `agregar_a_nota`
- `agregar_en_seccion`

Estas tools reciben el response enriquecido con warnings (si hay violaciones) y con la prosa de las reglas activas.

### Modificacion de contenido — solo validacion mecanica

- `editar_nota`

Ejecuta validaciones mecanicas sobre el nuevo contenido pero no inyecta prosa (el agente ya la recibio en la creacion o puede pedirla explicitamente).

### Captura rapida — validacion minima, sin inyeccion

- `captura_rapida`

Por diseno es sin friccion. Recibe mode `create` en el middleware (por lo que ejecuta las validaciones marcadas como `applies_to: [create]`), pero NO se incluye en `CONTENT_CREATION_TOOLS`, por lo que no recibe inyeccion de prosa. La captura rapida genera su propio frontmatter, asi que las validaciones de `scope: frontmatter` aplican normalmente.

### Herramientas estructurales — validadores ligeros opcionales

- `actualizar_frontmatter`: puede ejecutar `valid_status` y `valid_type` si el vault los define
- `gestionar_etiquetas`: podria cruzar contra tags canonicas (extension futura)
- `mover_nota`, `buscar_y_reemplazar_global`, `eliminar_nota`: sin validacion

### Lectura y analisis — nada

Todas las tools de lectura, busqueda, analisis y grafo no pasan por la cadena.

---

## Implementacion del middleware

### Nuevo modulo: `obsidian_mcp/middleware.py`

```python
from functools import partial
from typing import Callable

# Cache en memoria del proceso
_rules_cache: dict | None = None
_rules_prose_cache: str | None = None

CONTENT_CREATION_TOOLS = {"crear_nota", "agregar_a_nota", "agregar_en_seccion"}
CONTENT_EDIT_TOOLS = {"editar_nota"}
LIGHT_VALIDATION_TOOLS = {"captura_rapida", "actualizar_frontmatter"}

# Mapeo de tool name -> modo para applies_to
TOOL_MODE_MAP = {
    "crear_nota": "create",
    "captura_rapida": "create",
    "agregar_a_nota": "append",
    "agregar_en_seccion": "append",
    "editar_nota": "edit",
    "actualizar_frontmatter": "edit",
}


def load_vault_rules(force_reload: bool = False) -> list[dict]:
    """Carga las validations del frontmatter de REGLAS_GLOBALES.md.
    Cachea en memoria hasta force_reload."""
    global _rules_cache
    if _rules_cache is not None and not force_reload:
        return _rules_cache
    # Lee .agents/REGLAS_GLOBALES.md, parsea frontmatter, extrae 'validations'
    ...
    return _rules_cache


def load_vault_rules_prose(force_reload: bool = False) -> str:
    """Carga el cuerpo en prosa de REGLAS_GLOBALES.md (sin frontmatter)."""
    global _rules_prose_cache
    if _rules_prose_cache is not None and not force_reload:
        return _rules_prose_cache
    ...
    return _rules_prose_cache


def invalidate_rules_cache() -> None:
    """Invalida la cache. Llamar cuando se detecte cambio en REGLAS_GLOBALES."""
    global _rules_cache, _rules_prose_cache
    _rules_cache = None
    _rules_prose_cache = None


def run_validations(
    rules: list[dict],
    mode: str,
    title: str = "",
    content: str = "",
    frontmatter: dict | None = None,
) -> list[str]:
    """Ejecuta las validaciones aplicables y devuelve lista de warnings."""
    warnings = []
    for rule in rules:
        if mode not in rule.get("applies_to", []):
            continue
        warning = _check_rule(rule, title, content, frontmatter or {})
        if warning:
            warnings.append(warning)
    return warnings


def _check_rule(rule: dict, title: str, content: str, fm: dict) -> str | None:
    """Ejecuta una regla individual. Devuelve warning string o None."""
    scope = rule.get("scope", "")

    if scope in ("headings", "title", "body") and "pattern" in rule:
        return _check_pattern(rule, title, content)

    if scope == "frontmatter":
        if "required_fields" in rule:
            return _check_required_fields(rule, fm)
        if "field" in rule and "allowed_values" in rule:
            return _check_allowed_values(rule, fm)

    return None


def _check_pattern(rule: dict, title: str, content: str) -> str | None:
    """Valida regex contra el scope indicado."""
    import re
    pattern = re.compile(rule["pattern"])
    scope = rule["scope"]

    if scope == "title":
        if pattern.search(title):
            return rule["warning"]
    elif scope == "headings":
        for line in content.splitlines():
            if line.startswith("#") and pattern.search(line):
                return rule["warning"]
    elif scope == "body":
        if pattern.search(content):
            return rule["warning"]
    return None


def _check_required_fields(rule: dict, fm: dict) -> str | None:
    """Comprueba que los campos requeridos estan presentes."""
    missing = [f for f in rule["required_fields"] if f not in fm or not fm[f]]
    if missing:
        return rule["warning"].format(missing_fields=", ".join(missing))
    return None


def _check_allowed_values(rule: dict, fm: dict) -> str | None:
    """Comprueba que el valor de un campo esta en la lista permitida."""
    field = rule["field"]
    value = fm.get(field, "")
    if value and value not in rule["allowed_values"]:
        return rule["warning"].format(value=value)
    return None


def enrich_response(
    tool_name: str,
    result: str,
    title: str = "",
    content: str = "",
    frontmatter: dict | None = None,
) -> str:
    """Punto de entrada principal. Ejecuta validaciones e inyeccion."""
    mode = TOOL_MODE_MAP.get(tool_name)
    if not mode:
        return result  # tool sin validacion

    rules = load_vault_rules()
    warnings = run_validations(rules, mode, title, content, frontmatter)

    parts = [result]

    if warnings:
        parts.append("---")
        parts.append("[WARNINGS: {} violacion(es) detectada(s)]".format(len(warnings)))
        for w in warnings:
            parts.append("- " + w)

    if tool_name in CONTENT_CREATION_TOOLS:
        prose = load_vault_rules_prose()
        if prose:
            parts.append("---")
            parts.append("[REGLAS ACTIVAS DEL VAULT]")
            parts.append(prose)

    return "\n".join(parts)
```

### Integracion en tools

En `creation.py`, cada tool llama a `enrich_response` antes de devolver:

```python
from ..middleware import enrich_response

@mcp.tool()
def crear_nota(titulo, contenido, *, carpeta="", etiquetas="", ...):
    """..."""
    try:
        result = create_note(titulo, contenido, carpeta, etiquetas, ...).to_display(...)
        return enrich_response(
            tool_name="crear_nota",
            result=result,
            title=titulo,
            content=contenido,
            frontmatter=_extract_frontmatter(contenido),
        )
    except Exception as e:
        return f"Error al crear nota: {e}"
```

El patron se repite para `editar_nota`, `agregar_a_nota`, `agregar_en_seccion`, `captura_rapida` y `actualizar_frontmatter`.

---

## Invalidacion de cache

La cache se invalida en dos situaciones:

1. **Al iniciar el servidor**: la primera llamada a `load_vault_rules()` carga desde disco.
2. **Cuando se edita REGLAS_GLOBALES.md**: si `editar_nota` detecta que el archivo editado es `.agents/REGLAS_GLOBALES.md`, llama a `invalidate_rules_cache()`.

No se usa file watcher por simplicidad. La cache se recarga en la siguiente operacion.

---

## Efecto secundario: limpieza de skills

Una vez que el MCP enforce las reglas, las skills pueden eliminar:

1. **La "Regla de oro de edicion"** repetida en los 10 archivos SKILL.md
2. **El callout `> [!CAUTION] Lee las REGLAS_GLOBALES`** — el MCP ya las inyecta

Las skills quedan enfocadas en workflows especificos del vault, no en repetir reglas genericas.

---

## Defensa en profundidad (extension futura)

Si un agente consume el MCP a traves de LangChain, puede anadir `tool_interceptors` en el cliente para enforcement adicional (e.g., `human_in_the_loop` antes de `eliminar_nota`). Esto es un bonus, no un requisito — el enforcement del server es suficiente.

---

## Resumen de archivos a crear/modificar

| Archivo | Accion |
|---------|--------|
| `obsidian_mcp/middleware.py` | CREAR - logica de validacion e inyeccion |
| `obsidian_mcp/tools/creation.py` | MODIFICAR - integrar `enrich_response` en 6 tools |
| `.agents/REGLAS_GLOBALES.md` (vault) | MODIFICAR - anadir bloque `validations:` al frontmatter |
| `.agents/skills/*/SKILL.md` (vault, 10 archivos) | MODIFICAR - eliminar duplicacion de reglas |
| `tests/test_middleware.py` | CREAR - tests unitarios del middleware |

---

## Riesgos y mitigaciones

| Riesgo | Mitigacion |
|--------|-----------|
| La inyeccion de prosa engorda el response | Solo se inyecta en tools de creacion (3 tools), no en edicion ni estructurales |
| La cache queda stale si se edita REGLAS_GLOBALES fuera del MCP | Aceptable — solo pasa si se edita manualmente el archivo. El reinicio del server la limpia |
| Reglas YAML mal formadas rompen la validacion | `load_vault_rules` captura errores de parsing y devuelve lista vacia con log de warning |
| El frontmatter no se puede parsear del contenido de `crear_nota` | Se anade helper `_extract_frontmatter` que parsea el YAML del inicio del contenido |
