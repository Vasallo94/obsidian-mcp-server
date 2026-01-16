# ⚙️ Guía de Configuración

Para que el servidor MCP funcione correctamente, es necesario configurar el entorno y conocer la estructura de carpetas especiales que el servidor espera encontrar en tu vault.

## Variables de Entorno (.env)

El archivo `.env` en la raíz del proyecto es fundamental:

| Variable | Requerido | Descripción |
| :--- | :---: | :--- |
| `OBSIDIAN_VAULT_PATH` | Sí | Ruta **absoluta** a la carpeta raíz de tu vault de Obsidian. |
| `LOG_LEVEL` | No | Nivel de detalle de los logs (`INFO`, `DEBUG`, `ERROR`). Por defecto `INFO`. |

Ejemplo de `.env`:
```ini
OBSIDIAN_VAULT_PATH="/Users/enrique/Documentos/MiCerebroDigital"
LOG_LEVEL="DEBUG"
```


## Seguridad y Exclusiones

Por diseño, el servidor ignora carpetas de sistema y ocultas para evitar fugas de información o corrupción de metadatos de Obsidian:
- `.obsidian`
- `.git`
- `.trash`
- Otros directorios configurados en `context.py`.

> [!WARNING]
> Nunca apuntes `OBSIDIAN_VAULT_PATH` a una carpeta que contenga información privada sensible fuera de Obsidian, ya que el agente podría leerla si tiene permisos de lectura.

## 🔌 Integración con Clientes MCP

El servidor puede configurarse para múltiples clientes MCP. A continuación se muestran las configuraciones para los más comunes.

### Claude Code (CLI)

```bash
# Añadir a nivel de usuario (disponible en todos los proyectos)
claude mcp add-json --scope user obsidian '{
  "command": "uv",
  "args": ["run", "--directory", "/ruta/a/obsidian-mcp-server", "obsidian-mcp-server"],
  "env": {
    "OBSIDIAN_VAULT_PATH": "/ruta/a/tu/vault"
  }
}'
```

### Claude Desktop

Archivo: `%APPDATA%\Claude\claude_desktop_config.json` (Windows) o `~/.config/claude/claude_desktop_config.json` (Linux/Mac)

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "--directory", "/ruta/a/obsidian-mcp-server", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/ruta/a/tu/vault"
      }
    }
  }
}
```

### VSCode (Extensión Claude / GitHub Copilot)

Archivo: `~/.vscode/mcp.json`

```json
{
  "servers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "--directory", "/ruta/a/obsidian-mcp-server", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/ruta/a/tu/vault"
      }
    }
  }
}
```

### Gemini CLI

Archivo: `~/.gemini/settings.json`

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "--directory", "/ruta/a/obsidian-mcp-server", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/ruta/a/tu/vault"
      }
    }
  }
}
```

### Nota para Windows

En Windows, si usas `npx` o scripts que requieren shell, usa el prefijo `cmd /c`:

```json
{
  "command": "cmd",
  "args": ["/c", "uv", "run", "--directory", "C:/ruta/al/servidor", "obsidian-mcp-server"]
}
```

## 🤖 Skills y Reglas Globales (en tu Vault)

El servidor MCP puede leer **skills** (personalidades/roles de IA) y **reglas globales** directamente desde tu vault de Obsidian. Estos archivos **no están en el repositorio del MCP**, sino en tu vault personal.

### Estructura esperada en tu Vault

```
Tu_Vault/
├── .agent/
│   ├── REGLAS_GLOBALES.md      # Instrucciones generales para el asistente
│   └── skills/
│       ├── escritor/
│       │   └── SKILL.md        # Definición de la skill "escritor"
│       ├── investigador/
│       │   └── SKILL.md
│       └── revisor/
│           └── SKILL.md
```

### Formato de SKILL.md

Cada skill se define con un archivo `SKILL.md` que contiene frontmatter YAML y el prompt:

```markdown
---
name: Escritor Técnico
description: Especialista en documentación clara y concisa
tools:
  - crear_nota
  - editar_nota
  - buscar_en_notas
---

# Instrucciones

Eres un escritor técnico especializado en...

## Estilo
- Usa voz activa
- Evita jerga innecesaria
...
```

### Campos del frontmatter

| Campo | Requerido | Descripción |
| :--- | :---: | :--- |
| `name` | Sí | Nombre legible de la skill |
| `description` | Sí | Descripción breve del rol |
| `tools` | No | Lista de herramientas MCP que esta skill puede usar |

### REGLAS_GLOBALES.md

Este archivo contiene instrucciones que aplican a **todas** las interacciones con el asistente, independientemente de la skill activa. Por ejemplo:

```markdown
# Reglas Globales del Vault

- Siempre usa español
- Prefiere etiquetas existentes antes de crear nuevas
- No modifiques notas en 00_Sistema sin confirmación
```

> **Nota**: El servidor también busca en `.github/copilot-instructions.md` como ubicación legacy.
