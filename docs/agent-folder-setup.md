# Agent Folder Setup Guide

This guide explains how to configure the `.agent/` folder in your Obsidian vault for use with the MCP server.

## Directory Structure

```text
your-vault/
├── .agent/
│   ├── vault.yaml        # (Optional) Minimal operational settings
│   ├── REGLAS_GLOBALES.md # Agent behavior & global rules
│   └── skills/           # Specialized agent capabilities
│       ├── writer/
│       │   └── SKILL.md
│       └── researcher/
│           └── SKILL.md
└── ... your notes
```

## vault.yaml (Optional)

Minimal operational settings. Only required if auto-detection doesn't work.

```yaml
# .agent/vault.yaml
version: "1.0"

# Where templates are stored (auto-detected if contains "template" or "plantilla")
templates_folder: "06_Templates"

# Paths to protect from agent access
private_paths:
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
name: global-agent-rules
description: Mandatory protocol for all agents
---

# Global Rules

## Critical Rules
- Read notes before editing
- Confirm with user before creating

## Folder Conventions
| Content Type | Location |
|--------------|----------|
| Daily notes  | 01_Daily/ |
| Learning     | 02_Learning/ |
| Projects     | 03_Projects/ |
```

## Skills

Each skill is a folder with `SKILL.md`. Loaded by `listar_agentes()` and `obtener_instrucciones_agente()`.

```markdown
---
name: writer
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
