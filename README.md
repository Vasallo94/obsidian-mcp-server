# 🧠 Obsidian MCP Server

A Model Context Protocol (MCP) server for interacting with your Obsidian vault from Claude Desktop or your IDE. Navigate, search, create, and analyze your Obsidian notes using natural language commands.

## ✨ Features

### 📚 Navigation & Search
- **List notes**: Explore all notes organized by folders
- **Read notes**: Get complete content of any note
- **Text search**: Find specific content across your entire vault
- **Date search**: Locate notes by modification date range

### ✍️ Creation & Editing
- **Create notes**: New notes with metadata and tags
- **Add content**: Modify existing notes

### 📊 Analysis
- **Vault statistics**: Complete analysis of your knowledge
- **Metrics**: Words, characters, tags, internal links
- **Temporal activity**: Track your productivity

## 🚀 Installation

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (dependency manager)
- An Obsidian vault

### Installation Steps

1. **Clone the repository**:
   ```bash
   git clone <your-repository>
   cd obsidian-mcp-server
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure your vault**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set your vault path:
   ```
   OBSIDIAN_VAULT_PATH="/path/to/your/obsidian/vault"
   ```

4. **Run the server**:
   ```bash
   uv run python obsidian_mcp_server.py
   ```

5. **Run tests** (optional):
   ```bash
   uv run pytest
   ```

### Quick Setup Script

For automated setup, use the included setup script:

```bash
./setup.sh
```

This script will:
- ✅ Check if UV is installed
- 📦 Install all dependencies
- 🔧 Create `.env` file from template
- 🧪 Run verification tests
- 📋 Provide next steps

## 🔧 Configuration

### Environment Variables

The `.env` file must contain:

```bash
# Full path to your Obsidian vault
OBSIDIAN_VAULT_PATH="/Users/username/Documents/MyVault"
```

### Claude Desktop Configuration

To use this server with Claude Desktop, add the following configuration to your Claude config file:

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
        "/Users/username/path/to/obsidian-mcp-server",
        "obsidian_mcp_server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/username/path/to/obsidian-mcp-server"
      }
    }
  }
}
```
(Similar process for other MCP-compatible IDEs like VSCode, Cursor, etc.)

## 🛠️ Available Tools

### 📖 Navigation
- `listar_notas(carpeta?, incluir_subcarpetas?)`: List vault notes
- `leer_nota(nombre_archivo)`: Read note content
- `buscar_en_notas(texto, carpeta?, solo_titulos?)`: Search text in notes
- `buscar_notas_por_fecha(fecha_desde, fecha_hasta?)`: Search by date

### ✏️ Creation
- `crear_nota(titulo, contenido, carpeta?, etiquetas?)`: Create new note
- `agregar_a_nota(nombre_archivo, contenido, al_final?)`: Add content to existing note

### 📈 Analysis
- `estadisticas_vault()`: Complete vault statistics

## 💡 Usage Examples

Once connected to Claude Desktop, you can use commands like:

- *"Show me all my notes about artificial intelligence"*
- *"Create a note called 'Project Ideas' in the Work folder"*
- *"What are my vault statistics?"*
- *"Find notes modified in the last 7 days"*
- *"Read my note about meditation"*

## 🧪 Testing

Run the test suite to verify everything works correctly:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test class
uv run pytest tests/test_basic.py::TestConfiguration
```

The test suite includes:
- ✅ Module imports and dependencies
- ✅ Environment configuration
- ✅ MCP server initialization
- ✅ Vault content validation
- ✅ Tool registration verification
- ✅ Project structure checks

## 🗂️ Project Structure

```
obsidian-mcp-server/
├── obsidian_mcp_server.py    # Main server
├── pyproject.toml           # Project configuration
├── pytest.ini              # Test configuration
├── setup.sh                # Automated setup script
├── .env                     # Environment variables (not in git)
├── .env.example            # Configuration template
├── .gitignore              # Git ignore rules
├── README.md               # This documentation
├── LICENSE                 # MIT License
├── uv.lock                 # Dependency lock file
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py
    └── test_basic.py
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License. See `LICENSE` for details.

## 🔗 Useful Links

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Obsidian](https://obsidian.md/)

## ⚠️ Notes

- Make sure the Obsidian vault path is correct
- The server requires read/write permissions in the vault directory
- Changes are immediately reflected in Obsidian
