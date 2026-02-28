---
description: Run full quality check (format, lint, types, tests)
---

# Full Quality Check Workflow

Run this workflow before pushing any changes to ensure code quality.

// turbo-all

## Steps

1. Format code with Ruff:
```bash
uv run ruff format .
```

2. Run linting and auto-fix:
```bash
uv run ruff check . --fix
```

3. Verify type annotations:
```bash
uv run pyright
```

4. Run all tests:
```bash
uv run pytest tests/ -v
```

5. If all steps pass, the code is ready for commit.
