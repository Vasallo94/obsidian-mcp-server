# 🧠 Obsidian MCP Server

A modular Model Context Protocol (MCP) server for interacting with your Obsidian vault from Claude Desktop or your IDE. Navigate, search, create, and analyze your Obsidian notes using natural language commands.

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
- Python 3.11+
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
   # Using the new modular entry point (recommended)
   uv run obsidian-mcp-server
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
      "command": [
        "uv",
        "run",
        "--directory",
        "/Users/username/path/to/obsidian-mcp-server",
        "obsidian-mcp-server"
      ]
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

### ✏️ Creation & Editing
- `crear_nota(titulo, contenido, carpeta?, etiquetas?)`: Create new note
- `agregar_a_nota(nombre_archivo, contenido, al_final?)`: Add content to existing note

### 🤖 Prompt Engineering (NEW!)
- `guardar_prompt_refinado(titulo, prompt_original, prompt_refinado, contexto, tags?, carpeta?)`: Save refined prompts for reuse
- `actualizar_prompt_biblioteca(nombre_prompt, nuevas_notas?, calificacion?, casos_uso_adicionales?, variaciones?)`: Update existing prompts
- `listar_biblioteca_prompts()`: List all saved prompts in your library

### 📈 Analysis
- `estadisticas_vault()`: Complete vault statistics

## 💡 Usage Examples

Once connected to Claude Desktop, you can use commands like:

### Basic Operations
- *"Show me all my notes about artificial intelligence"*
- *"Create a note called 'Project Ideas' in the Work folder"*
- *"What are my vault statistics?"*
- *"Find notes modified in the last 7 days"*
- *"Read my note about meditation"*

### NEW! Prompt Engineering Features
- *"Save this refined prompt to my vault"* - After Claude creates a great prompt
- *"Show me all my saved prompts"* - List your prompt library
- *"Update my 'Creative Writing' prompt with new usage notes"* - Improve existing prompts

### Smart Prompt Management Workflow
1. **Work with Claude** on refining a prompt until it works perfectly
2. **Say**: *"Save this refined prompt as 'Data Analysis Helper' with context about when to use it"*
3. **Claude uses** `guardar_prompt_refinado()` to save it to your Obsidian vault
4. **Later**, access your prompt library anytime for reuse and iteration

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

The test suite uses `anyio` for asynchronous tests and includes:
- ✅ Module imports and dependencies
- ✅ Environment configuration
- ✅ MCP server initialization
- ✅ Vault content validation
- ✅ Tool registration verification
- ✅ Project structure checks

## 🗂️ Project Structure

### Modular Architecture

```
obsidian-mcp-server/
├── obsidian_mcp/                 # 📦 Main package (modular structure)
│   ├── __init__.py              # Package exports
│   ├── config.py                # ⚙️ Configuration and environment
│   ├── server.py                # 🚀 Main MCP server
│   ├── tools/                   # 🛠️ MCP tools organized by category
│   │   ├── __init__.py
│   │   ├── navigation.py        # 📚 Navigation (list, read, search)
│   │   ├── creation.py          # ✍️ Note creation and editing
│   │   └── analysis.py          # 📊 Analysis and statistics
│   ├── resources/               # 📋 MCP resources
│   │   ├── __init__.py
│   │   └── vault_info.py        # ℹ️ Vault information
│   ├── prompts/                 # 💭 Specialized prompts
│   │   ├── __init__.py
│   │   └── assistant.py         # 🤖 Assistant prompts
│   └── utils/                   # 🔧 Shared utilities
│       ├── __init__.py
│       ├── vault.py             # 📂 Vault utilities
│       └── logging.py           # 📝 Logging configuration
├── main.py                      # 🎯 Main entry point
├── diagnose.py                  # 🔍 Diagnostic script
├── pyproject.toml              # Project configuration
├── pytest.ini                 # Test configuration
├── setup.sh                   # Automated setup script
├── .env                        # Environment variables (not in git)
├── .env.example               # Configuration template
├── .gitignore                 # Git ignore rules
├── README.md                  # This documentation
├── LICENSE                    # MIT License
├── uv.lock                    # Dependency lock file
└── tests/                     # Test suite
    ├── __init__.py
    ├── conftest.py
    └── test_basic.py
```

### Benefits of Modular Architecture

- **Separation of concerns**: Each module has a specific responsibility
- **Maintainability**: Organized code that's easy to locate and modify
- **Scalability**: Easy to add new tools and extend functionality
- **Testing**: Isolated tests for better coverage and reliability
- **Reusability**: Components can be imported and used independently

### Usage Examples

```bash
# Run the server
uv run main.py

# Import modular components
python -c "from obsidian_mcp import create_server; print('✅ Modular import works')"

# Run diagnostics
uv run diagnose.py
```

## 🚀 Future Features & Roadmap

Here are some exciting features planned for future releases:

### 🤖 AI-Powered Intelligence
- **Smart Connection Suggestions**: AI-powered analysis to suggest meaningful links between related notes based on content similarity and semantic relationships
- **Semantic Search**: Search by meaning and context, not just exact word matches - find conceptually related content even when different terminology is used
- **Question Answering**: Ask specific questions about your vault content and get intelligent answers based on your knowledge base

### 📝 Prompt Engineering Toolkit
- **Refined Prompt Library**: Automatically save and organize successful prompts from AI conversations for reuse and refinement
- **Prompt Templates**: Create template prompts for common tasks and scenarios
- **Conversation Context Preservation**: Save important AI conversation contexts as structured notes

### 🔍 Advanced Analysis
- **Knowledge Graph Visualization**: Understand connections and patterns in your knowledge base
- **Content Gap Detection**: Identify areas where your knowledge could be expanded
- **Learning Path Suggestions**: AI-recommended reading and study paths based on your current knowledge

### 🔗 Enhanced Connectivity
- **Auto-linking Intelligence**: Suggest and create links between conceptually related notes
- **Broken Link Management**: Detect and help fix broken internal links
- **Cross-Reference Analysis**: Deep analysis of how concepts relate across your vault

### 📊 Smart Organization
- **Auto-tagging**: Intelligent tag suggestions based on content analysis
- **Dynamic Organization**: AI-suggested folder structures and note categorization
- **Duplicate Content Detection**: Find and manage similar or duplicate content

These features will make your Obsidian vault not just a storage system, but an intelligent knowledge companion that grows and learns with you.

*Want to contribute to any of these features? Check out our contributing guidelines below!*

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
