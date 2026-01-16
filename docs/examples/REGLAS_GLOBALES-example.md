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
When using `editar_nota()`:
1. **FIRST** read the note with `leer_nota()`
2. `nuevo_contenido` must be the **COMPLETE FILE**
3. **REPLACE** existing YAML block, don't duplicate
4. **NEVER** accidentally delete existing content

### 3. Access Restrictions
- Don't access files in `.forbidden_paths`
- Respect privacy of notes tagged `#private`

---

## Protocol Before Creating Notes

### Step 1: Verify Vault Context
```python
# ALWAYS run first:
leer_contexto_vault()
```

### Step 2: Verify Correct Location
- Use `sugerir_ubicacion()` to confirm destination
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
