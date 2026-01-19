---
description: Debug and fix failing tests
---

# Debug Tests Workflow

Use this workflow when tests are failing and you need to debug.

## Steps

1. **Run failing test with verbose output**:
```bash
uv run pytest tests/test_file.py::test_name -vvs
```

2. **Get full traceback**:
```bash
uv run pytest tests/test_file.py::test_name --tb=long
```

3. **If needed, add breakpoint in test or code**:
   - Add `breakpoint()` where you want to pause
   - Run with: `uv run pytest tests/test_file.py::test_name -s`
   - Use `n` to step, `c` to continue, `p variable` to print

4. **Run only previously failed tests**:
```bash
uv run pytest tests/ --lf -v
```

5. **After fixing, run full suite**:
```bash
uv run pytest tests/ -v
```
