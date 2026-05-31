#!/usr/bin/env python3
"""
Vault Analytics Script
Analyzes the Obsidian vault to extract creation statistics.
"""

import logging
import os
from collections import Counter
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_file_birth_time(filepath: Path) -> datetime:
    """Get the birth (creation) time of a file on macOS."""
    stat = filepath.stat()
    # On macOS, st_birthtime gives the creation time
    return datetime.fromtimestamp(stat.st_birthtime)


def analyze_vault(vault_path: str):
    """Analyze the vault and return statistics."""
    vault = Path(vault_path)

    notes = list(vault.rglob("*.md"))

    # Filter out system files
    excluded = [".obsidian", ".git", "ZZ_Plantillas", ".trash"]
    notes = [n for n in notes if not any(ex in str(n) for ex in excluded)]

    if not notes:
        print("No notes found!")
        return

    # Get creation times
    note_times = []
    for note in notes:
        try:
            birth = get_file_birth_time(note)
            note_times.append((note, birth))
        except OSError as e:
            logger.debug("Skipping '%s', can't read birth time: %s", note, e)
            continue

    # Sort by creation time
    note_times.sort(key=lambda x: x[1])

    # Stats
    oldest = note_times[0]
    newest = note_times[-1]

    # Count by year-month
    by_month: Counter[str] = Counter()
    by_year: Counter[int] = Counter()
    for _note, birth in note_times:
        by_month[birth.strftime("%Y-%m")] += 1
        by_year[birth.year] += 1

    # Output
    print("=" * 60)
    print("📊 VAULT ANALYTICS")
    print("=" * 60)
    print(f"\n📁 Total notes: {len(note_times)}")
    print("\n🏛️ OLDEST NOTE:")
    print(f"   {oldest[0].name}")
    print(f"   Created: {oldest[1].strftime('%Y-%m-%d %H:%M')}")
    print(f"   Path: {oldest[0].relative_to(vault)}")

    print("\n🆕 NEWEST NOTE:")
    print(f"   {newest[0].name}")
    print(f"   Created: {newest[1].strftime('%Y-%m-%d %H:%M')}")

    print("\n📅 NOTES BY YEAR:")
    for year in sorted(by_year.keys()):
        chart_bar = "█" * (by_year[year] // 10) + "▌" * ((by_year[year] % 10) // 5)
        print(f"   {year}: {chart_bar} ({by_year[year]})")

    print("\n📆 NOTES BY MONTH (top 10):")
    for month, count in by_month.most_common(10):
        chart_bar = "█" * (count // 5)
        print(f"   {month}: {chart_bar} ({count})")

    # Time span
    span = newest[1] - oldest[1]
    print(
        f"\n⏱️ TIME SPAN: {span.days} days "
        f"({span.days // 365} years, {(span.days % 365) // 30} months)"
    )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys

    vault_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            "/Users/enriquebook/Personal/Obsidian/Secundo Selebro",
        )
    )
    analyze_vault(vault_path)
