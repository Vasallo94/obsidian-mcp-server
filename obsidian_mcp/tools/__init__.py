"""
Herramientas MCP para el servidor de Obsidian
"""

from .analysis import register_analysis_tools
from .creation import register_creation_tools
from .navigation import register_navigation_tools

__all__ = [
    "register_analysis_tools",
    "register_creation_tools",
    "register_navigation_tools",
]
