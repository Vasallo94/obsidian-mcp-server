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

## Estructuras Especiales del Vault

El servidor interactúa con ciertas carpetas y archivos específicos para ofrecer funcionalidades avanzadas:

### 1. Plantillas (`ZZ_Plantillas/`)
El servidor busca automáticamente plantillas en esta carpeta cuando se usa la herramienta `crear_nota`.
- **Variables soportadas**: `{{title}}` (se reemplaza por el título de la nota) y `{{date}}` (fecha actual).
- **Tip**: Mantén tus plantillas en formato `.md`.

### 2. Agentes (`.github/agents/`)
Aquí es donde reside la "personalidad" de tu IA.
- El servidor lista cualquier archivo que termine en `.agent.md` o `.md` dentro de esta carpeta.
- Estos archivos contienen los system prompts que el agente debe seguir para tareas específicas (ej: Investigador, Guardián).

### 3. Registro de Tags (`Registro de Tags del Vault.md`)
Utilizado por las herramientas de análisis para validar el uso de etiquetas.
- El servidor intenta leer las etiquetas "oficiales" de este archivo para compararlas con las usadas en tus notas.

### 4. Instrucciones Globales (`.github/copilot-instructions.md`)
Contiene las reglas de oro que el agente siempre debe recordar al interactuar con tu vault.

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
