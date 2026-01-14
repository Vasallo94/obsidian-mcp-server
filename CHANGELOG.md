# Changelog

Todos los cambios notables de este proyecto se documentan aquí.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Implementado sistema de seguridad con `.forbidden_paths` para restringir acceso a carpetas sensibles.
- Añadida función `check_path_access` en `security.py` integrada en herramientas de navegación y creación.
- Soporte para placeholders de fecha dinámicos `{{date:FORMAT}}` y `{{fecha:FORMAT}}` en `crear_nota`.

### Changed
- Actualizada lógica de `crear_nota` para procesar correctamente metadatos de fecha en YAML frontmatter.
- Mejorada la validación de rutas en herramientas de sistema de archivos.

### Fixed
- Corregido error en la actualización del campo `updated` al editar notas.
