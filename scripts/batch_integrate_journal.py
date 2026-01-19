from pathlib import Path

VAULT_PATH = "/Users/enriquebook/Personal/Obsidian/Secundo Selebro"
JOURNAL_FOLDER = "01_Diario"

FOOTER = """
---
[[01_Diario/01_Diario|📅 Diario]] | [[00_Sistema/00_Home|⬅️ Volver al Home]]
"""

THEMATIC_LINKS = {
    "#terapia": "[[Psicología MOC]]",
    "#ansiedad": "[[Psicología MOC]]",
    "#poesía": "[[Poesía MOC]]",
    "#filosofía": "[[Filosofía MOC]]",
    "#ciencia": "[[Ciencia MOC]]",
}


def process_journal():
    path = Path(VAULT_PATH) / JOURNAL_FOLDER
    count = 0
    for file in path.glob("*.md"):
        if file.name == "01_Diario.md":
            continue

        with open(file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if already has a footer (approximate check)
        if "Volver al Home" in content:
            continue

        new_footer = FOOTER

        # Add thematic links based on tags
        for tag, link in THEMATIC_LINKS.items():
            if tag in content:
                if link not in content:
                    new_footer += f"\n- {link}"

        with open(file, "a", encoding="utf-8") as f:
            f.write(new_footer)
            count += 1

    print(f"✅ Procesadas {count} notas del diario.")


if __name__ == "__main__":
    process_journal()
