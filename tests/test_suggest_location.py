"""suggest_folder_location: palabras clave enteras, no subcadenas."""

import pytest

from obsidian_mcp.tools.creation_logic import suggest_folder_location


@pytest.mark.parametrize(
    ("title", "content", "folder"),
    [
        ("Configurar SSH en el NAS", "", "Sistemas"),
        ("Redes del homelab", "", "Sistemas"),
        ("Agentes LLM", "", "IA"),
        ("Script de backup", "en bash", "Programación"),
        ("Poemas de otoño", "", "Poemas"),
    ],
)
def test_keywords_pick_their_folder(isolated_vault, title, content, folder):
    assert f"/{folder}`" in suggest_folder_location(title, content)


def test_recipe_is_not_filed_by_substrings(isolated_vault):
    (isolated_vault / "00_Bandeja").mkdir()
    result = suggest_folder_location(
        "Receta de paella",
        "Berenjenas, media cebolla y pimiento rojo para una persona. Remover.",
    )

    assert result == "📂 Sugerencia: `00_Bandeja` (Categoría general)"
