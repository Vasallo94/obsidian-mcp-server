# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Pipeline de MCPB con binario local para generar bundles instalables por plataforma sin depender del Python del usuario.
- **AFP #51 — Reposición y borrado de grupos en canvas**: Nuevas tools `canvas.move_card(node_id, x, y)` (reposiciona cualquier nodo) y `canvas.remove_group(group_id, remove_contents=False)` (borra un grupo y, opcionalmente, las tarjetas que contiene). Antes había que editar el `.canvas` a mano.
- **AFP #52 — Registro de reglas del vault**: Nueva tool `rules.add(rule_text)` (pack `agents_admin`) para que el agente registre una regla en `.agents/REGLAS_GLOBALES.md` a petición del usuario, con confirmación interactiva (`elicit`) y sin acceso directo al fichero.
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
- Pulido el README para la beta pública con instalación Git/uvx visible, ejemplo de Codex, grafo del vault y clientes actuales.
- Añadidas plantillas de issues para bugs, ayuda de instalación y feedback de beta.
- Añadidos documentos públicos de contribución, seguridad y checklist de release.
- Añadida guía estándar de instalación para Claude Code, Codex, Hermes, Claude Desktop y MCPB.
- Regla añadida en `AGENTS.md` exigiendo actualizar el `CHANGELOG.md` antes de cada commit.
- Nueva guía: `docs/agent-folder-setup.md`.
- Roadmap de mejoras futuras: `docs/FUTURE.md`.
- Actualizados `README.md`, `configuration.md`, `tool-reference.md` y `architecture.md` con los nuevos patrones.
- Añadidos ejemplos de `SKILL.md` y `REGLAS_GLOBALES.md` en `docs/examples/`.
