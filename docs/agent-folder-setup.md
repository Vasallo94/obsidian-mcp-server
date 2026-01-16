# Agent Folder Setup Guide

This guide explains how to configure the `.agent/` folder in your Obsidian vault for use with the MCP server.

## Directory Structure

```
your-vault/
├── .agent/
│   ├── vault.yaml        # (Optional) Minimal operational settings
│   ├── REGLAS_GLOBALES.md # Agent behavior & global rules
│   └── skills/           # Specialized agent capabilities
│       ├── escritor/
│       │   └── SKILL.md
│       └── investigador/
│           └── SKILL.md
└── ... your notes
```

## vault.yaml (Optional)

Minimal operational settings. Only required if auto-detection doesn't work.

```yaml
# .agent/vault.yaml
version: "1.0"

# Where templates are stored (auto-detected if contains "plantilla" or "template")
templates_folder: "06_Plantillas"

# Paths to protect from agent access
private_paths:
  - "**/Privado/*"
  - "**/Private/*"
  - "**/secrets.md"
```

**If omitted**, the server:
- Auto-detects templates folder
- Uses `.forbidden_paths` for security
- Works with any vault structure

## REGLAS_GLOBALES.md

Defines agent behavior. Read by `obtener_reglas_globales()`.

```markdown
---
name: reglas-globales-agentes
description: Mandatory protocol for all agents
---

# Global Rules

## Critical Rules
- No emojis in titles
- Read notes before editing
- Confirm with user before creating

## Folder Conventions
| Content Type | Location |
|--------------|----------|
| Daily notes  | 01_Diario/ |
| Learning     | 02_Aprendizaje/ |
| Projects     | 03_Proyectos/ |
```

## Skills

Each skill is a folder with `SKILL.md`. Loaded by `listar_agentes()` and `obtener_instrucciones_agente()`.

```markdown
---
name: escritor
description: Writing and editing assistance
tools: ['read', 'edit', 'search']
---

# Writer Skill

Instructions for this specialized mode...
```

## No Configuration Needed

The MCP server works without any configuration:
- Templates: auto-detected
- Security: uses `.forbidden_paths` file
- Behavior: from `REGLAS_GLOBALES.md` + skills
