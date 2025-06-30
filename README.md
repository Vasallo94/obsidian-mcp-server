# 🧠 Obsidian MCP Server

Un servidor Model Context Protocol (MCP) para interactuar con tu vault de Obsidian desde Claude. Te permite navegar, buscar, crear y analizar tus notas de Obsidian mediante comandos naturales.

## ✨ Características

### 📚 Navegación y Búsqueda
- **Lista notas**: Explora todas las notas organizadas por carpetas
- **Lee notas**: Obtén el contenido completo de cualquier nota
- **Búsqueda de texto**: Encuentra contenido específico en todo el vault
- **Búsqueda por fecha**: Localiza notas por rango de fechas de modificación

### ✍️ Creación y Edición
- **Crear notas**: Nuevas notas con metadatos y etiquetas
- **Agregar contenido**: Modifica notas existentes

### 📊 Análisis
- **Estadísticas del vault**: Análisis completo de tu conocimiento
- **Métricas**: Palabras, caracteres, etiquetas, enlaces internos
- **Actividad temporal**: Seguimiento de tu productividad

## 🚀 Instalación

### Prerrequisitos
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (gestor de dependencias)
- Un vault de Obsidian

### Pasos de instalación

1. **Clona el repositorio**:
   ```bash
   git clone <tu-repositorio>
   cd obsidian-mcp-server
   ```

2. **Instala las dependencias**:
   ```bash
   uv sync
   ```

3. **Configura tu vault**:
   ```bash
   cp .env.example .env
   ```
   
   Edita `.env` y configura la ruta a tu vault:
   ```
   OBSIDIAN_VAULT_PATH="/ruta/a/tu/vault/de/obsidian"
   ```

4. **Ejecuta el servidor**:
   ```bash
   uv run python obsidian_mcp_server.py
   ```

5. **Ejecuta los tests** (opcional):
   ```bash
   uv run pytest
   ```

## 🔧 Configuración

### Variables de entorno

El archivo `.env` debe contener:

```bash
# Ruta completa al vault de Obsidian
OBSIDIAN_VAULT_PATH="/Users/usuario/Documents/MiVault"
```

### Configuración de Claude Desktop

Para usar este servidor con Claude Desktop, agrega la siguiente configuración a tu archivo de configuración de Claude:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "obsidian-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/usuario/ruta/al/obsidian-mcp-server",
        "obsidian_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/usuario/ruta/al/obsidian-mcp-server"
      }
    }
  }
}
```
(Proceso parecido para IDEs que acepten MCP como VSCode, Cursor, etc.)

## 🛠️ Herramientas disponibles

### 📖 Navegación
- `listar_notas(carpeta?, incluir_subcarpetas?)`: Lista notas del vault
- `leer_nota(nombre_archivo)`: Lee el contenido de una nota
- `buscar_en_notas(texto, carpeta?, solo_titulos?)`: Busca texto en las notas
- `buscar_notas_por_fecha(fecha_desde, fecha_hasta?)`: Busca por fecha

### ✏️ Creación
- `crear_nota(titulo, contenido, carpeta?, etiquetas?)`: Crea una nueva nota
- `agregar_a_nota(nombre_archivo, contenido, al_final?)`: Agrega contenido

### 📈 Análisis
- `estadisticas_vault()`: Estadísticas completas del vault

## 💡 Ejemplos de uso

Una vez conectado a Claude, puedes usar comandos como:

- *"Muéstrame todas mis notas sobre inteligencia artificial"*
- *"Crea una nota llamada 'Ideas para el proyecto' en la carpeta Trabajo"*
- *"¿Cuáles son las estadísticas de mi vault?"*
- *"Busca notas modificadas en los últimos 7 días"*
- *"Lee mi nota sobre meditación"*

## 🗂️ Estructura del proyecto

```
obsidian-mcp-server/
├── obsidian_mcp_server.py    # Servidor principal
├── pyproject.toml           # Configuración del proyecto
├── .env                     # Variables de entorno (no incluir en git)
├── .env.example            # Plantilla de configuración
├── .gitignore              # Archivos a ignorar en git
├── README.md               # Esta documentación
└── uv.lock                 # Lock file de dependencias
```

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🔗 Enlaces útiles

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Obsidian](https://obsidian.md/)

## ⚠️ Notas

- Asegúrate de que la ruta al vault de Obsidian sea correcta
- El servidor requiere permisos de lectura/escritura en el directorio del vault
- Las modificaciones se reflejan inmediatamente en Obsidian
