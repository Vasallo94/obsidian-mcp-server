# Release Checklist

## Pre-release

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run bandit -c pyproject.toml -r obsidian_mcp/
uv run pip-audit
uv run pytest tests/
rm -rf dist build
uv build --sdist --wheel
uv run python scripts/build_mcpb.py
```

## Versioning

1. Move relevant `CHANGELOG.md` entries from `[Unreleased]` to the release
   version.
2. Update `pyproject.toml` version.
3. Ensure `packaging/mcpb/manifest.template.json` picks up the same version via
   `scripts/build_mcpb.py`.
4. Tag the release as `vX.Y.Z`.

## Publish

Publish the Python package to PyPI and attach platform-specific `.mcpb`
artifacts to the GitHub release.
