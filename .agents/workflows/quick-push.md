---
description: Commit and push an explicitly approved change after verification
---

# Approved Commit and Push

Read `AGENTS.md` first. This workflow is available only when the user explicitly requests the relevant operation; loading it does not authorize a commit or push. A commit request alone does not authorize publication.

1. Inspect `git status`, the current branch, the unstaged diff, and the staged diff. Preserve unrelated work and do not switch branches automatically.
2. Run relevant checks from `AGENTS.md`; report pre-existing failures. Update `CHANGELOG.md` for the authorized commit. Do not bypass hooks without explicit approval.
3. Stage only explicit task-owned paths with `git add -- <approved-paths>`. Never use `git add .` as the default. If unrelated changes are already staged or share the same files, stop and agree on isolation rather than including or resetting them.
4. Inspect `git diff --cached` and create one logical Conventional Commit only if committing is authorized.
5. Confirm that push is explicitly authorized for the intended remote and branch. Inspect its configured upstream and ahead commits; do not publish unrelated earlier commits without approval. Push only the approved branch, never `main`, all branches, or all tags by assumption.
6. Report the commit and push outcome separately. Tags and releases require their own explicit authorization.

Angle-bracket arguments above are placeholders to replace with reviewed paths; they are not literal shell commands.
