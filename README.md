# 🧠 Obsidian MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Un servidor avanzado de **MCP** (Model Context Protocol) que convierte tu vault de Obsidian en un cerebro dinámico para tu IA (Claude Desktop, Claude Code, Cursor, etc.). Mucho más que un lector de archivos: es un ecosistema de herramientas para la gestión del conocimiento, automatización y análisis semántico.

---

## ✨ Características Principales

### 🛠️ Ecosistema de Herramientas (30+)
El servidor expone una amplia variedad de herramientas categorizadas por su función:
- **📂 Navegación**: Listado inteligente, lectura recursiva y búsqueda avanzada.
- **✍️ Creación y Edición**: Uso automático de plantillas, sugerencia de ubicación y edición con preservación de metadatos.
- **📊 Análisis y Calidad**: Estadísticas del vault, sincronización de etiquetas con el registro oficial y comprobación de integridad.
- **🕸️ Grafos y Conexiones**: Análisis de backlinks, detección de notas huérfanas y visualización de grafos locales.
- **🤖 Skills (Agentes)**: Carga dinámica de personalidades/roles desde tu vault (`{vault}/.agent/skills/`).
- **🔍 Búsqueda Semántica (RAG)**: Búsquedas por significado, sugerencia de conexiones no obvias e indexación vectorial.
- **📺 YouTube**: Extracción de transcripciones para alimentar tu base de conocimientos.

### 🤖 Inteligencia Integrada
- **Plantillas Dinámicas**: Reemplazo automático de variables en archivos de plantillas.
- **Smart Tagging**: Consulta el historial de etiquetas para mantener la coherencia semántica.
- **Seguridad**: Protección estricta de carpetas sensibles y validación de rutas.
- **Skills Personalizables**: Define roles de IA en tu vault para tareas específicas.

---

## 🚀 Instalación Rápida

### Prerrequisitos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recomendado)

### Pasos
1. **Clonar**:
   ```bash
   git clone https://github.com/Vasallo94/obsidian-mcp-server.git
   cd obsidian-mcp-server
   ```
2. **Instalar**:
   ```bash
   make install
   # Para búsqueda semántica:
   pip install "obsidian-mcp-server[rag]"
   ```
3. **Configurar**:
   ```bash
   cp .env.example .env
   # Edita .env con la ruta absoluta a tu vault
   ```

---

## 💻 Uso

### Integración con Claude Desktop
Añade esto a tu `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "obsidian": {
      "command": "uv",
      "args": ["run", "obsidian-mcp-server"],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/Ruta/A/Tu/Vault"
      }
    }
  }
}
```

---

## 📚 Documentación Técnica

Para profundizar en el funcionamiento del servidor, consulta nuestras guías detalladas en la carpeta `docs/`:

1.  [🏛️ Arquitectura](docs/architecture.md): Estructura modular y flujo de datos.
2.  [🔧 Referencia de Herramientas](docs/tool-reference.md): Listado completo y parámetros de cada herramienta.
3.  [⚙️ Configuración](docs/configuration.md): Guía sobre variables de entorno y carpetas especiales.
4.  [🧠 Búsqueda Semántica (RAG)](docs/semantic-search.md): Cómo funciona la indexación vectorial y el modo RAG.

---

## 🛠️ Desarrollo y Calidad

| Comando | Descripción |
| :--- | :--- |
| `make test` | Ejecuta la suite de pruebas (pytest) |
| `make lint` | Verificación estática (Ruff + Mypy) |
| `make format` | Formateo automático de código |
| `make dev` | Ejecuta el inspector de MCP para pruebas en vivo |

---

## 📄 Licencia
Este proyecto está bajo la licencia MIT.
