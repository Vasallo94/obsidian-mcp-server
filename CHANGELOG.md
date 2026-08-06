# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **CI: matriz de sistemas y versiones**: el job de tests pasa de un único runner a una matriz de 5 entradas — Python 3.11/3.12/3.13 en Linux, más 3.11 en macOS y Windows. Windows es el que ejecuta código hasta ahora muerto: las dos ramas de plataforma del paquete son exclusivas de Windows — el fallback de SIGALRM a threading en `utils/timeout.py` y el salto del `fsync` de directorio en las escrituras atómicas de `utils/vault.py` cuando `os.name == "nt"`. macOS recorre las mismas ramas que Linux; está por el sistema de ficheros insensible a mayúsculas de APFS, un riesgo real para una herramienta cuya frontera de seguridad es la comparación de rutas.
- **CI: el interpréte declarado ahora es el que se usa**: los jobs fijaban `PYTHON_VERSION: "3.11"` e instalaban 3.11, pero `uv sync` resolvía el intérprete desde el `.python-version` del repo (3.13), así que el pipeline llevaba ejecutándose en 3.13 mientras decía 3.11. Sustituido por `UV_PYTHON`, que sí tiene precedencia sobre `.python-version`.
- **CI: umbral de cobertura de 25% a 60%**: la cobertura medida es 64.89%; el margen restante es holgura para variación entre plataformas, no una afirmación de que los módulos opcionales de `semantic/` estén cubiertos — no lo están, y no se excluyen de la medición para maquillar el número.

### Removed
- **CI: paso de preparación del vault de prueba**: copiaba `.env.example` y lo reescribía con `sed -i`, incompatible con el sed de BSD en macOS. Resulta que el paso entero sobraba: el fixture autouse `isolated_vault` de `tests/conftest.py` apunta `OBSIDIAN_VAULT_PATH` a un `tmp_path` en cada test, así que el vault que preparaba CI no se leía nunca. Comprobado: la suite pasa con la variable sin definir y también apuntando a una ruta inexistente.

### Added
- Pipeline de MCPB con binario local para generar bundles instalables por plataforma sin depender del Python del usuario.
- **AFP #51 — Reposición y borrado de grupos en canvas**: Nuevas tools `canvas.move_card(node_id, x, y)` (reposiciona cualquier nodo) y `canvas.remove_group(group_id, remove_contents=False)` (borra un grupo y, opcionalmente, las tarjetas que contiene). Antes había que editar el `.canvas` a mano.
- **AFP #52 — Registro de reglas del vault**: Nueva tool `rules.add(rule_text, confirm=True)` (pack `agents_admin`) para que el agente registre una regla en `.agents/REGLAS_GLOBALES.md` a petición del usuario, con gate de confirmación (`confirm=True`) y sin acceso directo al fichero.
- **Agent Feedback Protocol**: Añadido `afp.json` y una guía de uso out-of-band para que agentes y harnesses puedan generar drafts de fricción sin añadir tools MCP nuevas.
- **Canvas Integration (22 nuevas herramientas)**: Soporte completo para ficheros `.canvas` de Obsidian con dos capas:
  - **8 herramientas genéricas** (`canvas.read`, `canvas.list`, `canvas.add_card`, `canvas.add_group`, `canvas.add_edge`, `canvas.update_card`, `canvas.remove_card`, `canvas.remove_edge`) para CRUD sobre cualquier canvas.
  - **14 herramientas de workflow Kanvas** (`kanvas.init`, `kanvas.status`, `kanvas.task`, `kanvas.ready`, `kanvas.blocked`, `kanvas.start`, `kanvas.finish`, `kanvas.pause`, `kanvas.approve`, `kanvas.complete`, `kanvas.edit_task`, `kanvas.add_dependency`, `kanvas.propose_task`, `kanvas.propose_group`) para gestión de proyectos con estados codificados por color (gris=bloqueado, rojo=pendiente, naranja=en curso, cian=revisión, verde=hecho, morado=propuesto).
  - Dos modos de workflow: **STRICT** (solo el humano aprueba/completa) y **RELAXED** (el agente también puede).
  - Detección automática de ciclos en dependencias entre tareas.
  - Normalización automática de estados (bloqueos) al guardar.


- **Pydantic Tool Validations**: Implementación de jerarquía `BaseModel` para todas las **40 herramientas** mediante `tool_inputs.py`, logrando validación rigurosa de tipos. Las descripciones y metadatos se exponen ahora dinámicamente al `_tool_manager` de FastMCP.
- **Seguridad y Calidad en CI**: Integración completa de validadores como `pip-audit` (`make audit`) y `actionlint` en los `pre-commit hooks` y en `GitHub Actions` (pipeline `ci.yml`). El proyecto ahora exige y pasa con un **10.00/10 en Pylint**.
- Nueva arquitectura **Vault-Agnostic**: el servidor es ahora genérico e independiente de la estructura de carpetas.
- Lógica de **auto-detección inteligente** de carpetas de plantillas y recursos.
- Configuración opcional mediante `.agents/vault.yaml` para personalización avanzada de rutas y privacidad.
- Soporte para **procesamiento de fechas** dinámico (`{{date}}`, `{{fecha}}`) en `crear_nota`.
- Seguridad mejorada con **listas blancas y negras** configurables mediante `private_paths`.
- Herramienta `leer_contexto_vault` mejorada con resumen de estructura y etiquetas.
- **Indexación Semántica de Imágenes**: El sistema ahora extrae descripciones de imágenes (`![[img|desc]]` o `![desc](img)`) y las inyecta como contexto semántico, haciendo buscable el contenido visual.

### Fixed
- **Legacy-encoded note resilience**: Vault statistics, tag analysis, backlinks, local graphs, and orphan detection now skip non-UTF-8 notes instead of failing the entire scan.
- **Vault exclusion hygiene**: `.trash`, `.git`, and `.obsidian` are now part of the shared packaged boundary, diagnostics use that boundary, and unused `.mcpignore` and YouTube verification scripts were removed so the documented security model has one source of truth.
- **Lint and skill-sync partial writes**: Vault lint now skips and reports unreadable notes instead of aborting after partial fixes, and skill synchronization preserves both generated guidance blocks while reporting unreadable or unwritable skills.
- **Bulk write safety and public contracts**: Global replacements now re-read each note immediately before writing, report when the file limit truncates results, and note moves report partial success if wikilink rewriting fails. Public tool signatures now match registered schemas, and the vault bootstrap prompt no longer instructs agents to commit or push.
- **Crash-safe writes and Canvas confirmation**: Vault text and Canvas files now use same-directory atomic replacement so failed writes preserve the previous file. New files default to owner-only permissions while existing permissions are preserved. Destructive `canvas.remove_card`, `canvas.remove_group`, and `canvas.remove_edge` calls now require `confirm=True`.
- **Vault filesystem boundary**: Canvas/Kanvas, note creation, skill generation, templates, configured documents, search, analysis, graph, context, wikilink, and legacy semantic operations now canonicalize paths, reject traversal and symlink escapes, and consistently skip protected files. Vault `.forbidden_paths` entries are merged with defaults shipped inside the package.
- **Test isolation**: The default test suite now uses a generated temporary vault instead of loading or traversing the developer's configured vault.
- **ObsidianRAG resource secrets**: Integration config resources no longer expose raw environment mappings, and setup resources omit secret-like variables.
- **Dependency security**: Updated `cryptography` to 50.0.0 to resolve CVE-2026-69247.
- **`tags.analyze` / `tags.list` / `vault_stats` — tags de frontmatter corruptas**: `extract_tags_from_content` parseaba el campo `tags:` del frontmatter con un regex línea a línea; en listas YAML en bloque (`tags:\n  - "media"\n  - "media/peliculas"`), el `\s*` tras `tags:` engullía el salto de línea y capturaba literalmente el primer ítem de la lista como valor completo, produciendo una tag basura como `- "media"` y descartando el resto de ítems de la lista. Ahora el frontmatter se parsea con `yaml.safe_load` (mismo patrón que `_extract_frontmatter_from_content`), soportando lista YAML, array inline y string simple/separado por comas. La detección de tags inline `#tag` en el cuerpo ahora excluye bloques de código (fenced e inline) para no confundir referencias como `(#80)` en changelogs pegados.
- **AFP — Confirmación de escrituras destructivas inalcanzable**: `notes.replace`, `notes.apply_replace`, `notes.delete` y `rules.add` dependían de `ctx.elicit()`, que en clientes sin la capability de *elicitation* (p. ej. Claude Code) se auto-rechaza sin mostrar ningún diálogo, devolviendo "el usuario rechazó explícitamente la confirmación" y bloqueando toda sobrescritura o borrado de notas existentes. Ahora el gate es un argumento explícito `confirm=True`; la aprobación humana real es el propio prompt de permisos del host. Se eliminó la dependencia de `elicit()` y los mensajes `OPERATION_*` asociados.
- **AFP — `rag.ask` / `rag.rebuild_index` con backend caído**: los errores ahora nombran la URL del backend ObsidianRAG y explican que debe arrancarse (con puntero al recurso de setup y a `rag.health`), en vez de un genérico "query failed".
- **AFP — Contrato de `notes.create` ambiguo**: el docstring documenta ahora que `folder` es vault-relative, que las carpetas padre se crean automáticamente y que la tool nunca sobrescribe una nota existente.
- Saneada la higiene de dependencias: `pip-audit` queda limpio tras subir `cryptography`, `starlette`, `python-multipart`, `tqdm` y `pip-audit`, y el extra legacy `[rag]` deja de arrastrar PyTorch.
- MCPB ahora tiene una única fuente de verdad binaria, genera artefactos versionados por plataforma en `dist/mcpb/` y evita dejar ficheros `.spec` en la raíz del repositorio.
- Evitado que `route.task` recomiende workflows personales de media en vaults genéricos sin estándar `media` declarado.
- **`inbox.capture` — warning falso de frontmatter**: la tool pasaba `frontmatter={}` al middleware de reglas, por lo que cualquier regla `required_fields` (scope `frontmatter`, `applies_to: [create]`) disparaba un `[WARNINGS: Frontmatter incompleto: faltan type, status, tags]` falso aunque la nota creada en disco sí tenía esos campos. Ahora `inbox.capture` propaga el frontmatter real (`type`/`status`/`created`/`updated`/`tags`) vía el nuevo helper `inbox_capture_frontmatter`. El fixture de tests AFP limpia además el caché global de reglas entre tests para eliminar la dependencia de orden que enmascaraba el bug.
- **AFP #50 — Reglas del vault en canvas**: `canvas.add_card` y `canvas.update_card` ahora validan el texto de las tarjetas contra las reglas del vault (p. ej. sin emojis en cabeceras) y devuelven `[WARNINGS: ...]`, igual que las tools `notes.*`. Antes la capa de reglas solo se aplicaba a notas.
- **AFP #49 — Leyenda de colores en canvas**: `canvas.read` expone ahora el mapeo estándar de colores de Obsidian y, si existe, el contenido de la tarjeta "Legend"/"Leyenda" del board. Los docstrings de `canvas.add_card`/`canvas.update_card` documentan el significado de `"0"`-`"6"` para no elegir color a ciegas.
- **Security**: Actualizado `starlette` a `1.2.0` para resolver la vulnerabilidad `PYSEC-2026-161` detectada por `pip-audit`.
- **Semantic Hook Failures**: Ajustado `semantic_logic.py` para declarar explícitamente las capturas amplias esperadas en la capa de tool logic y refactorizados los tests de conexiones para evitar accesos protegidos y warnings de `pytest.importorskip`, permitiendo que `pre-commit` vuelva a pasar sin atajos.
- **Actionable Errors**: Las herramientas ahora devuelven mensajes semánticos al modelo LLM ante errores (Ej: `❌ No se encontró la nota 'X', usa listar_notas primero`) en lugar de levantar excepciones nativas como `FileNotFoundError` que rompían el agente.
- **QA Code Coverage**: Arreglados todos los avisos estrictos de `pylint` (reduciendo la complejidad ciclomática explícita y gestionando *lazy loading* de paquetes RAG).
- **Vulnerabilidades Corregidas**: Mitigadas 2 vulnerabilidades moderadas/altas (CVEs) encontradas en dependencias secundarias (`authlib` y `diskcache`) vía `uv sync --upgrade`.
- **Tag Extraction**: Filtro de códigos de color hexadecimales (`#fff`, etc.) en `extract_tags_from_content` para evitar falsos positivos.
- **Tag Sync**: Búsqueda flexible (regex) del encabezado de estadísticas en el Registro de Tags y fallback de creación iterativo si no existe en `tags.sync_registry`.
- **Import circular** en `security.py` que impedía el arranque del servidor MCP. El import de `vault_config` se movió a nivel de función para romper el ciclo de dependencias.

### Changed
- Preparada la metadata pública del paquete y limpiado el sdist para excluir planes internos, scripts personales y configuración de agentes local.
- Refactorizado `vault_config.py` para un enfoque minimalista y no prescriptivo.
- Herramientas de navegación, creación y seguridad migradas para usar la nueva arquitectura dinámica e inputs validados.
- Prompt del asistente actualizado para priorizar el chequeo de `skills` disponibles.

### Removed
- Eliminados planes internos de desarrollo y scripts personales/backup que contenían rutas locales antes de publicar el repositorio.

### Docs
- Reorganizada la documentación como wiki pública con `docs/index.md`, arquitectura actualizada, guía `.agents` vigente, página de semantic search con ObsidianRAG y contratos contra links rotos/nombres antiguos de tools.
- Pulido el README para la beta pública con instalación Git/uvx visible, ejemplo de Codex, grafo del vault y clientes actuales.
- Añadidas plantillas de issues para bugs, ayuda de instalación y feedback de beta.
- Añadidos documentos públicos de contribución, seguridad y checklist de release.
- Añadida guía estándar de instalación para Claude Code, Codex, Hermes, Claude Desktop y MCPB.
- Regla añadida en `AGENTS.md` exigiendo actualizar el `CHANGELOG.md` antes de cada commit.
- Nueva guía: `docs/agent-folder-setup.md`.
- Roadmap de mejoras futuras: `docs/FUTURE.md`.
- Actualizados `README.md`, `configuration.md`, `tool-reference.md` y `architecture.md` con los nuevos patrones.
- Añadidos ejemplos de `SKILL.md` y `REGLAS_GLOBALES.md` en `docs/examples/`.
