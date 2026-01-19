---
name: Git Workflow
description: >
  Skill para manejar el flujo de trabajo de Git: changelog, commits,
  push, y releases. Automatiza el proceso de versionado y publicación.
tools:
  - run_command
  - read
  - edit
---

# Git Workflow Skill

## Cuándo usar esta skill

- Cuando necesites actualizar el CHANGELOG.md con nuevos cambios.
- Cuando vayas a hacer commit de cambios al repositorio.
- Cuando necesites hacer push de cambios al remoto.
- Cuando prepares una nueva release.

## Convenciones de Commits

Este proyecto usa **Conventional Commits**:

```
type(scope): description
```

### Tipos válidos:
| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bugs |
| `docs` | Cambios en documentación |
| `style` | Formato (sin cambio de código) |
| `refactor` | Refactorización |
| `test` | Añadir/modificar tests |
| `chore` | Mantenimiento |

### Ejemplos:
```bash
feat(semantic): add image caption indexing
fix(navigation): resolve path validation error
docs: update tool reference with new parameters
```

## Flujo de Trabajo Completo

### 1. Verificar estado actual

```bash
# Ver estado de archivos
git status

# Ver historial reciente
git log --oneline -10
```

### 2. Actualizar CHANGELOG.md

**Formato requerido** (Keep a Changelog):

```markdown
## [Unreleased]

### Added
- Nueva feature X que hace Y.

### Changed
- Modificación en Z.

### Fixed
- Corrección del bug en W.
```

**Secciones válidas**: Added, Changed, Deprecated, Removed, Fixed, Security

### 3. Realizar commit

```bash
# Añadir todos los cambios
git add .

# Commit con mensaje convencional
git commit -m "type(scope): descripción"
```

**Trailers especiales**:
- Para bugs reportados: `git commit --trailer "Reported-by:<name>"`
- Para issues: `git commit --trailer "Github-Issue:#<number>"`

> ⚠️ **NUNCA** incluir `Co-Authored-By` en los commits.

### 4. Push al remoto

```bash
git push origin main
```

## Proceso de Release

Para crear una nueva versión:

### 1. Mover cambios de Unreleased a una versión

```markdown
## [1.2.0] - 2026-01-20

### Added
- (mover items de Unreleased)
```

### 2. Actualizar versión en pyproject.toml

```toml
[project]
version = "1.2.0"
```

### 3. Commit de release

```bash
git add .
git commit -m "chore(release): bump to v1.2.0"
git tag v1.2.0
git push origin main --tags
```

## Checklist Pre-Push

Antes de hacer push, verifica:

- [ ] Tests pasan: `uv run pytest tests/`
- [ ] Linting limpio: `uv run ruff check .`
- [ ] Tipos correctos: `uv run pyright`
- [ ] CHANGELOG actualizado
- [ ] Commit message sigue convención

## Comandos Rápidos

```bash
# Quick commit de docs
git add . && git commit -m "docs: update documentation"

# Quick commit de fix
git add . && git commit -m "fix(module): brief description"

# Ver cambios desde última release
git log --oneline $(git describe --tags --abbrev=0)..HEAD
```
