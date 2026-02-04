"""
Herramientas para interactuar con YouTube (obtención de transcripciones).
"""

from typing import Optional

from fastmcp import FastMCP


def register_youtube_tools(mcp: FastMCP) -> None:
    """
    Registra las herramientas de YouTube en el servidor MCP.
    """

    @mcp.tool()
    def get_youtube_transcript(url: str, language: Optional[str] = None) -> str:
        """
        Obtiene la transcripción de un video de YouTube.

        Args:
            url: URL del video de YouTube o ID del video.
            language: Código del idioma opcional (ej: 'es', 'en').
                      Si se omite, busca subtítulos manuales en el idioma original,
                      o falla al autogenerado del video.

        Returns:
            El texto completo de la transcripción o un mensaje de error.
        """
        from .youtube_logic import get_transcript_text

        return get_transcript_text(url, language).to_display()
