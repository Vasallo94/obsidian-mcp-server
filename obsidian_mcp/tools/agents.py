"""
Herramientas para la integración de Agentes (Guardian, Investigador, etc.)

Estas herramientas permiten al cliente MCP leer las definiciones y prompts
de los agentes almacenados en la carpeta .github del vault.
"""

from fastmcp import FastMCP

from ..config import get_vault_path


def register_agent_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de gestión de agentes en el servidor MCP.
    """

    @mcp.tool()
    def listar_agentes() -> str:
        """
        Lista los agentes disponibles en el vault (carpeta .github/agents).

        Returns:
            Lista de nombres de agentes disponibles.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            agents_path = vault_path / ".github" / "agents"
            if not agents_path.exists():
                return "ℹ️ No se encontró la carpeta .github/agents en el vault."

            agentes = []
            for item in sorted(agents_path.glob("*.agent.md")):
                # Extraer nombre limpio (sin .agent.md)
                nombre = item.name.replace(".agent.md", "")
                agentes.append(nombre)

            if not agentes:
                return (
                    "ℹ️ No se encontraron archivos .agent.md en la carpeta de agentes."
                )

            return "🤖 **Agentes Disponibles:**\n" + "\n".join(
                [f"- {a}" for a in agentes]
            )

        except Exception as e:
            return f"❌ Error al listar agentes: {e}"

    @mcp.tool()
    def obtener_instrucciones_agente(nombre: str) -> str:
        """
        Obtiene el prompt/instrucciones completas de un agente específico.

        Args:
            nombre: Nombre del agente (ej: "investigador" o "guadian_del_conocimiento").
                   No es necesario poner la extensión .agent.md

        Returns:
            Contenido completo de la definición del agente.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            agents_path = vault_path / ".github" / "agents"

            # Intentar encontrar el archivo con o sin extensión
            target_file = agents_path / f"{nombre}.agent.md"
            if not target_file.exists():
                # Intentar sin el .agent si el usuario ya lo puso, o simplemente .md
                if nombre.endswith(".agent.md"):
                    target_file = agents_path / nombre
                else:
                    target_file = agents_path / f"{nombre}.md"

            if not target_file.exists():
                return (
                    f"❌ No se encontró el agente '{nombre}'. "
                    "Usa listar_agentes() para ver los disponibles."
                )

            with open(target_file, "r", encoding="utf-8") as f:
                contenido = f.read()

            return f"📄 **Instrucciones para Agente: {nombre}**\n\n{contenido}"

        except Exception as e:
            return f"❌ Error al obtener instrucciones del agente: {e}"

    @mcp.tool()
    def obtener_reglas_globales() -> str:
        """
        Obtiene las reglas globales del vault (copilot-instructions.md).
        Estas reglas aplican a todos los agentes.

        Returns:
            Contenido de las instrucciones globales.
        """
        try:
            vault_path = get_vault_path()
            if not vault_path:
                return "❌ Error: La ruta del vault no está configurada."

            rules_path = vault_path / ".github" / "copilot-instructions.md"

            if not rules_path.exists():
                return (
                    "ℹ️ No se encontró el archivo de reglas globales "
                    "(.github/copilot-instructions.md)."
                )

            with open(rules_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            return f"📜 **Reglas Globales (Copilot Instructions)**\n\n{contenido}"

        except Exception as e:
            return f"❌ Error al obtener reglas globales: {e}"
