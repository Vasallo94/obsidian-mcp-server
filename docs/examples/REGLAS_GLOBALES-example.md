---
name: reglas-globales-agentes
description: >
  Mandatory protocol that ALL agents must follow before creating
  or editing notes in the vault.
---

# Global Rules for Agents

> [!CAUTION]
> **REQUIRED**: Every agent must follow this protocol before creating or editing notes.

---

## Critical Rules

### 1. No Emojis
- **FORBIDDEN** in note titles
- **FORBIDDEN** in headers (`# H1`, `## H2`)
- **FORBIDDEN** in folder names
- *Exception*: Only allowed in content if semantically necessary

### 2. Golden Rule of Editing
When using `notes.patch()`:
1. **FIRST** read the note with `notes.read()`
2. Send `operations` as a list of `{"old": "exact text", "new": "replacement"}`
3. `old` must be **UNIQUE** in the note — include more context if ambiguous
4. For full-note replacement, prefer `notes.replace()` when the client supports confirmation

### 3. Access Restrictions
- Don't access files in `.forbidden_paths`
- Respect privacy of notes tagged `#private`

---

## Protocol Before Creating Notes

### Step 1: Verify Vault Context
```python
# ALWAYS run first:
vault.context()
```

### Step 2: Verify Correct Location
- Use `notes.suggest_location()` to confirm destination
- Ask user for confirmation before creating

### Step 3: Use Real Frontmatter
- **NEVER** invent frontmatter values
- **NEVER** leave placeholders (`{{date}}`)
- **ALWAYS** use real values for `type`, `tags`, `created`

---

## Standard Locations

| Content Type | Location |
|--------------|----------|
| Daily notes  | `01_Daily/` |
| Learning     | `02_Learning/` |
| Projects     | `03_Projects/` |
| Resources    | `04_Resources/` |
