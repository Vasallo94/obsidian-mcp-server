---
description: Quick commit and push changes to remote
---

# Quick Push Workflow

Use this workflow to quickly commit and push changes after verification passes.

## Steps

1. Check current status:
```bash
git status
```

2. Stage all changes:
```bash
git add .
```

3. Commit with appropriate message (use conventional commits):
```bash
git commit -m "type(scope): description"
```

Replace `type` with: feat, fix, docs, style, refactor, test, chore
Replace `scope` with the affected module (optional)

4. Push to remote:
```bash
git push origin main
```
