# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Implementado sistema de seguridad con `.forbidden_paths` para restringir acceso a carpetas sensibles.
- Añadida función `check_path_access` en `security.py` integrada en herramientas de navegación y creación.
- Soporte para placeholders de fecha dinámicos `{{date:FORMAT}}` y `{{fecha:FORMAT}}` en `crear_nota`.
- Nueva herramienta `refrescar_cache_skills()` para invalidar el caché de skills.

### Changed
- Actualizada lógica de `crear_nota` para procesar correctamente metadatos de fecha en YAML frontmatter.
- Mejorada la validación de rutas en herramientas de sistema de archivos.

### Fixed
- Corregido error en la actualización del campo `updated` al editar notas.

### Docs
- Clarificada ubicación de skills: están en el vault del usuario (`{vault}/.agent/skills/`), no en el repositorio.
- Actualizada documentación en README, architecture.md, tool-reference.md y configuration.md.
- Añadida sección completa sobre estructura de skills y REGLAS_GLOBALES.md en configuration.md.
- Completada arquitectura del sistema en `.github/copilot-instructions.md`.
- Expandida skill `mcp-developer` con patrones de código y guía de desarrollo.
