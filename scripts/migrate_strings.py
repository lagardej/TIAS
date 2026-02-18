"""
migrate_strings.py - Merge reactions.csv + openers.csv into strings.csv

Adds a 'type' column: 'reaction' or 'opener'
Column order: type, text, category/mood, mode, trigger/note

Usage:
    python scripts/migrate_strings.py           # dry run
    python scripts/migrate_strings.py --write   # write strings.csv
    python scripts/migrate_strings.py --clean   # write + delete old files
"""

import csv
import sys
from pathlib import Path

ACTORS_DIR = Path(__file__).parent.parent / "resources" / "actors"


def read_csv(filepath: Path) -> list[dict]:
    with open(filepath, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def migrate_actor(actor_dir: Path, write: bool, clean: bool) -> bool:
    reactions_file = actor_dir / "reactions.csv"
    openers_file   = actor_dir / "openers.csv"
    strings_file   = actor_dir / "strings.csv"

    if strings_file.exists():
        print(f"  [{actor_dir.name}] already has strings.csv — skipping")
        return False

    if not reactions_file.exists() and not openers_file.exists():
        print(f"  [{actor_dir.name}] no CSV source files — skipping")
        return False

    rows = []

    if reactions_file.exists():
        for r in read_csv(reactions_file):
            rows.append({
                'type':     'reaction',
                'text':     r.get('text', ''),
                'category': r.get('category', ''),
                'mode':     r.get('mode', ''),
                'trigger':  r.get('trigger', ''),
                'note':     '',
            })

    if openers_file.exists():
        for r in read_csv(openers_file):
            rows.append({
                'type':     'opener',
                'text':     r.get('text', ''),
                'category': r.get('mood', ''),
                'mode':     '',
                'trigger':  '',
                'note':     r.get('note', ''),
            })

    if write or clean:
        with open(strings_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['type', 'text', 'category', 'mode', 'trigger', 'note'])
            writer.writeheader()
            writer.writerows(rows)
        print(f"  [{actor_dir.name}] wrote strings.csv ({len(rows)} rows)")
        if clean:
            for fp in [reactions_file, openers_file]:
                if fp.exists():
                    fp.unlink()
                    print(f"  [{actor_dir.name}] deleted {fp.name}")
    else:
        print(f"  [{actor_dir.name}] DRY RUN — would write strings.csv ({len(rows)} rows)")

    return True


def main():
    write = '--write' in sys.argv or '--clean' in sys.argv
    clean = '--clean' in sys.argv

    mode = 'CLEAN (write + delete)' if clean else ('WRITE' if write else 'DRY RUN')
    print(f"migrate_strings.py — mode: {mode}")
    print()

    migrated = 0
    for actor_dir in sorted(ACTORS_DIR.iterdir()):
        if not actor_dir.is_dir() or actor_dir.name.startswith('_'):
            continue
        if migrate_actor(actor_dir, write, clean):
            migrated += 1

    print()
    print("Template:")
    migrate_actor(ACTORS_DIR / '_template', write, clean)

    print()
    print(f"Done. {migrated} actors processed.")
    if not write:
        print("Run with --write to apply, --clean to apply and delete old files.")


if __name__ == '__main__':
    main()
