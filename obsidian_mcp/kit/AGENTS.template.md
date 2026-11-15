---
title: AGENTS
description: Instrucciones operativas para agentes que trabajan sobre este vault
type: sistema
status: en_proceso
tags:
- obsidian
- agentes
---

# Instrucciones para agentes en el vault

<!-- Completar: qué es este vault y para qué se usa, en una o dos frases. -->

## Fuentes de verdad

Este archivo es un resumen. Si algo no coincide, mandan estos ficheros:

| Qué | Dónde |
|---|---|
| Taxonomía (roles de carpeta, vocabulario de `type`, plantilla y carpeta por tipo) | `.agents/vault.yaml` |
| Reglas obligatorias de escritura (validadas por el MCP) | `.agents/REGLAS_GLOBALES.md` |
| Plantillas | la carpeta `templates_folder` de `.agents/vault.yaml` |

## Cómo acceder

Usa el MCP `obsidian`, no lecturas sueltas del sistema de ficheros, para crear o editar notas: valida frontmatter, respeta las rutas privadas y escribe de forma atómica.

1. `vault.context` al empezar: estructura, plantillas y convenciones.
2. `notes.search` para buscar antes de crear (evita duplicados).
3. `notes.suggest_location` y la tabla de abajo para decidir carpeta.
4. `notes.create(note_type=...)` para crear: aplica la plantilla y la carpeta del tipo. `notes.patch` para cambios puntuales; `notes.read` siempre antes de editar.
5. `notes.validate` o `vault.lint` para comprobar.

## Plantillas por tipo

`taxonomy.templates` en `.agents/vault.yaml` dice qué plantilla y qué carpeta usa cada `type`. `templates.list` muestra el mapa. Si el tipo se archiva por tema o proyecto, pasa también `folder` con la subcarpeta; sin ella la llamada falla y lista las opciones.

Para añadir un tipo: crea la plantilla (con `{{title}}` y `{{date}}`, nunca fechas fijas), añádelo a `taxonomy.types` y a `taxonomy.templates`.

## Dónde va cada cosa

<!-- Completar con las carpetas reales del vault (roles de taxonomy.roles). -->

| Contenido | Carpeta | `type` |
|---|---|---|
| Captura sin procesar | | `inbox`, `recurso` |
| Conocimiento por tema | | `apunte`, `resumen`, `concepto`, `guía` |
| Procedimientos operativos | | `runbook` |
| Documentación de proyectos | | `proyecto`, `doc-proyecto`, `adr` |

## Frontmatter mínimo

```yaml
title: Título de la nota
description: Una frase que diga de qué va
type: runbook          # uno de los de .agents/vault.yaml
status: captura        # captura → en_proceso → completo → archivo
tags: [tema]           # solo temática, minúsculas y con acentos
created: 'AAAA-MM-DD'
updated: 'AAAA-MM-DD'
```

- Fechas reales, nunca copiadas de una plantilla.
- Archivar es `status: archivo`; no se mueve la nota a otra carpeta.
- `agente_creador` lo rellena el MCP con el nombre del cliente; pásalo solo para firmar con un rol o una skill.

## Privacidad

- Las rutas de `private_paths` en `.agents/vault.yaml` no se leen ni se resumen fuera de una petición expresa.
- Nunca escribas contraseñas, tokens ni claves en notas.
- No hagas commit ni push del vault sin que lo pida su dueño.
