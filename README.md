# 🧠 Obsidian MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Un servidor avanzado de **MCP** que conecta tu inteligencia artificial (Claude, IDEs) directamente con tu "Vault" en Obsidian. No es solo un lector de archivos; es un **agente activo** capaz de entender la estructura, seguir tus reglas de etiquetado y adoptar personalidades especializadas (Guardián, Investigador, etc.).

---

## ✨ Características Principales

### 🔍 Navegación y Contexto
- **Mapa del Vault**: Herramientas como `leer_contexto_vault` le dan a la IA una visión general de tu estructura de carpetas (excluyendo archivos de sistema).
- **Búsqueda Semántica**: Encuentra información relevante sin necesidad de recordar nombres exactos de archivos.

### 🤖 Sistema de Agentes Integrado
El servidor lee tu carpeta `.github/agents` y permite a la IA adoptar roles específicos:
- **🛡️ Guardián del Conocimiento**: Mantiene el orden y la estructura. Tiene permisos especiales (`mover_nota`) para reorganizar tu vault.
- **🔬 Investigador**: Crea notas profundas y estructuradas sobre nuevos temas.
- **🕸️ Tejedor de Conexiones**: Encuentra relaciones ocultas entre tus notas.

### ✍️ Creación Inteligente
- **Plantillas**: Utiliza tus archivos de `ZZ_Plantillas` automáticamente, reemplazando variables como `{{title}}` y `{{date}}`.
- **Smart Tagging**: Antes de crear una tag, el servidor consulta las existentes (`obtener_lista_etiquetas`) para evitar duplicados y sinónimos.

### 🔒 Seguridad y Privacidad
- **Protección de Datos**: Bloqueo estricto de lectura/escritura en carpetas sensibles (ej: `04_Recursos/Privado`).
- **Validación de Rutas**: Previene accesos fuera del directorio del vault.

---

## 🚀 Requisitos e Instalación

### Prerrequisitos
- Python 3.11 superior
- `uv` (recomendado para gestión de dependencias)

### Instalación

1.  **Clonar** el repositorio:
    ```bash
    git clone https://github.com/usuario/obsidian-mcp-server.git
    cd obsidian-mcp-server
    ```

2.  **Instalar dependencias**:
    ```bash
    make install
    ```

3.  **Configuración**:
    Crea un archivo `.env` basado en el ejemplo:
    ```bash
    cp .env.example .env
    ```
    Edita `.env` y define la ruta absoluta a tu vault:
    ```ini
    OBSIDIAN_VAULT_PATH="/Users/tu_usuario/Desktop/Obsidian/TuVault"
    ```

---

## 💻 Uso

### Modo Desarrollo
Para probar el servidor localmente con el inspector de MCP:

```bash
make dev
```

### Integración con Claude Desktop

Agrega la configuración a tu archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "/ruta/a/tu/python/o/uv",
      "args": [
        "run",
        "--package",
        "obsidian-mcp-server",
        "obsidian-mcp-server"
      ],
      "env": {
        "OBSIDIAN_VAULT_PATH": "/Users/tu_usuario/Desktop/Obsidian/TuVault"
      }
    }
  }
}
```

---

## 🛠️ Estructura del Proyecto

El código está organizado siguiendo estándares profesionales de ingeniería de software en Python:

```text
obsidian-mcp-server/
├── obsidian_mcp/           # Código fuente del paquete
│   ├── tools/              # Módulos de herramientas MCP
│   │   ├── agents.py       # Lógica de agentes (.github/agents)
│   │   ├── context.py      # Análisis de estructura del vault
│   │   ├── navigation.py   # Operaciones de archivo (mover, leer)
│   │   └── ...
│   └── server.py           # Configuración del servidor FastMCP
├── tests/                  # Suite de pruebas automatizadas (pytest)
├── scripts/                # Scripts de mantenimiento y verificación
├── docs/                   # Documentación adicional
├── pyproject.toml          # Configuración unificada (ruff, pytest, deps)
└── Makefile                # Automatización de tareas de desarrollo
```

---

## 🧪 Pruebas y Calidad

El proyecto cuenta con un sistema robusto de CI/CD local:

| Comando | Acción |
| :--- | :--- |
| `make test` | Ejecuta todos los tests unitarios y de integración |
| `make lint` | Verifica el estilo de código (Ruff) y tipos estáticos (Mypy) |
| `make format` | Corrige automáticamente problemas de formato |
| `make verify` | Ejecuta scripts de verificación en vivo contra el vault |

---

## 🤝 Contribución

1.  Haz un fork del proyecto.
2.  Crea una rama para tu feature (`git checkout -b feature/nueva-magia`).
3.  Asegúrate de que `make lint` y `make test` pasen correctamente.
4.  Envía un Pull Request.

---

## 📄 Licencia

Este proyecto está bajo la licencia MIT.
