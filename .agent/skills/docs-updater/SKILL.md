---
name: Documentation Updater
description: >
  Skill para mantener la documentación sincronizada con el código.
  Incluye patrones de documentación, ubicaciones estándar, y checklists.
tools:
  - read
  - edit
  - grep_search
---

# Documentation Updater Skill

## Cuándo usar esta skill

- Cuando añadas nuevas herramientas (tools) al MCP.
- Cuando modifiques parámetros o comportamiento de herramientas.
- Cuando añadas nuevas features al proyecto.
- Cuando actualices la arquitectura.

## Estructura de Documentación

```
docs/
├── architecture.md       # Visión general arquitectónica
├── configuration.md      # Variables de entorno y configuración
├── tool-reference.md     # Referencia de todas las herramientas MCP
├── semantic-search.md    # Guía de búsqueda semántica
├── agent-folder-setup.md # Configuración de carpeta .agent
├── FUTURE.md            # Ideas para desarrollo futuro
└── examples/            # Ejemplos de configuración
```

## Documentos a Actualizar por Tipo de Cambio

### Nueva herramienta MCP

1. **`docs/tool-reference.md`** - Añadir entrada con:
   - Nombre de la herramienta
   - Descripción
   - Parámetros (nombre, tipo, requerido, descripción)
   - Ejemplo de uso
   - Valor de retorno

2. **`CHANGELOG.md`** - Añadir en `[Unreleased] > Added`

### Cambio en configuración

1. **`docs/configuration.md`** - Actualizar tabla de variables
2. **`README.md`** - Si afecta quickstart

### Cambio arquitectónico

1. **`docs/architecture.md`** - Actualizar diagramas y descripciones
2. **`CHANGELOG.md`** - Documentar en Changed

## Formato para Tool Reference

```markdown
### nombre_herramienta

**Descripción**: Qué hace la herramienta.

**Parámetros**:

| Nombre | Tipo | Requerido | Descripción |
|--------|------|-----------|-------------|
| param1 | str | Sí | Descripción del parámetro |
| param2 | bool | No | Descripción (default: False) |

**Retorna**: Descripción del valor de retorno.

**Ejemplo**:
```python
result = nombre_herramienta(param1="valor")
```
```

## Checklist de Documentación

Al añadir nueva feature:

- [ ] Docstring en el código fuente
- [ ] Entrada en `tool-reference.md` (si es tool)
- [ ] Entrada en `CHANGELOG.md`
- [ ] Actualizar `README.md` si afecta uso básico
- [ ] Actualizar `configuration.md` si añade variables

## Mantener README.md

El README debe incluir:

1. **Descripción breve** del proyecto
2. **Instalación rápida**
3. **Configuración básica**
4. **Ejemplo de uso**
5. **Links a documentación detallada**

> No incluir detalles exhaustivos en README. Referir a docs/.

## Convenciones de Estilo

- **Títulos**: Sentence case (`Nueva feature` no `Nueva Feature`)
- **Código**: Usar bloques de código con lenguaje
- **Tablas**: Para parámetros y configuración
- **Ejemplos**: Siempre incluir ejemplos funcionales

## Ejemplo de Actualización Completa

Si añades una nueva herramienta `buscar_imagenes`:

### 1. CHANGELOG.md
```markdown
### Added
- Nueva herramienta `buscar_imagenes` para buscar por descripciones.
```

### 2. tool-reference.md
```markdown
### buscar_imagenes

**Descripción**: Busca imágenes por sus descripciones/captions.

**Parámetros**:
| Nombre | Tipo | Requerido | Descripción |
|--------|------|-----------|-------------|
| query | str | Sí | Texto a buscar en descripciones |

**Retorna**: Lista de imágenes con sus rutas y captions.
```

### 3. Verificar coherencia
- ¿Los parámetros documentados coinciden con el código?
- ¿Los ejemplos funcionan?
- ¿El CHANGELOG refleja el cambio correctamente?
