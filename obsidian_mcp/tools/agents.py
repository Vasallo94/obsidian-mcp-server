"""
Herramientas para la integración de Agentes (Guardian, Investigador, etc.)

Estas herramientas permiten al cliente MCP leer las definiciones y prompts
de los agentes almacenados en la carpeta .github del vault.
"""

from fastmcp import FastMCP

from ..config import get_vault_path


def register_agent_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas y recursos de gestión de agentes.
    """

    @mcp.resource("agents://list")
    def resource_listar_agentes() -> str:
        """Recurso que devuelve la lista de agentes disponibles."""
        return listar_agentes_logic()

    @mcp.tool()
    def listar_agentes() -> str:
        """Lista los agentes disponibles en el vault."""
        return listar_agentes_logic()

    def listar_agentes_logic() -> str:
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            agents_path = vault_path / ".github" / "agents"
            if not agents_path.exists():
                return "ℹ️ No se encontró la carpeta .github/agents."

            agentes = []
            for item in sorted(agents_path.glob("*.agent.md")):
                nombre = item.name.replace(".agent.md", "")
                agentes.append(nombre)

            if not agentes:
                return "ℹ️ No se encontraron archivos .agent.md."

            return "🤖 **Agentes Disponibles:**\n" + "\n".join(
                [f"- {a}" for a in agentes]
            )
        except Exception as e:
            return f"❌ Error: {e}"

    @mcp.tool()
    def obtener_instrucciones_agente(nombre: str) -> str:
        """Obtiene el prompt de un agente específico."""
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            agents_path = vault_path / ".github" / "agents"
            target_file = agents_path / f"{nombre}.agent.md"

            if not target_file.exists():
                # Fallback para nombres sin extensión o .md simple
                if nombre.endswith(".agent.md"):
                    target_file = agents_path / nombre
                else:
                    target_file = agents_path / f"{nombre}.md"

            if not target_file.exists():
                return f"❌ No se encontró el agente '{nombre}'."

            with open(target_file, "r", encoding="utf-8") as f:
                contenido = f.read()

            return f"📄 **Instrucciones para Agente: {nombre}**\n\n{contenido}"

        except Exception as e:
            return f"❌ Error: {e}"

    @mcp.tool()
    def obtener_reglas_globales() -> str:
        """Obtiene las reglas globales (copilot-instructions.md)."""
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            rules_path = vault_path / ".github" / "copilot-instructions.md"

            if not rules_path.exists():
                return "ℹ️ No se encontró .github/copilot-instructions.md."

            with open(rules_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            return f"📜 **Reglas Globales**\n\n{contenido}"

        except Exception as e:
            return f"❌ Error: {e}"
