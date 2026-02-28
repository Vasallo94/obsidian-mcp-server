# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nueva arquitectura **Vault-Agnostic**: el servidor es ahora genérico e independiente de la estructura de carpetas.
- Lógica de **auto-detección inteligente** de carpetas de plantillas y recursos.
- Configuración opcional mediante `.agents/vault.yaml` para personalización avanzada de rutas y privacidad.
- Soporte para **procesamiento de fechas** dinámico (`{{date}}`, `{{fecha}}`) en `crear_nota`.
- Seguridad mejorada con **listas blancas y negras** configurables mediante `private_paths`.
- Herramienta `leer_contexto_vault` mejorada con resumen de estructura y etiquetas.
- **Indexación Semántica de Imágenes**: El sistema ahora extrae descripciones de imágenes (`![[img|desc]]` o `![desc](img)`) y las inyecta como contexto semántico, haciendo buscable el contenido visual.

### Fixed
- **Import circular** en `security.py` que impedía el arranque del servidor MCP. El import de `vault_config` se movió a nivel de función para romper el ciclo de dependencias.

### Changed
- Refactorizado `vault_config.py` para un enfoque minimalista y no prescriptivo.
- Herramientas de navegación, creación y seguridad migradas para usar la nueva arquitectura dinámica.
- Prompt del asistente actualizado para priorizar el chequeo de `skills` disponibles.

### Docs
- Nueva guía: `docs/agent-folder-setup.md`.
- Roadmap de mejoras futuras: `docs/FUTURE.md`.
- Actualizados `README.md`, `configuration.md`, `tool-reference.md` y `architecture.md` con los nuevos patrones.
- Añadidos ejemplos de `SKILL.md` y `REGLAS_GLOBALES.md` en `docs/examples/`.
