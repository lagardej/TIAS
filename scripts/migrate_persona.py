"""
migrate_persona.py - Merge background.txt + personality.txt + stage.txt into persona.md

Usage:
    python scripts/migrate_persona.py           # dry run (preview only)
    python scripts/migrate_persona.py --write   # actually write files
    python scripts/migrate_persona.py --clean   # write + delete old files

Old files are NOT deleted unless --clean is passed.
"""

import sys
from pathlib import Path

ACTORS_DIR = Path(__file__).parent.parent / "resources" / "actors"

SECTION_MAP = [
    ("background.txt",  "Background"),
    ("personality.txt", "Personality"),
    ("stage.txt",       "Stage"),
]


def migrate_actor(actor_dir: Path, write: bool, clean: bool) -> bool:
    """Migrate one actor directory. Returns True if migration was needed."""
    persona_file = actor_dir / "persona.md"

    # Skip if already migrated
    if persona_file.exists():
        print(f"  [{actor_dir.name}] already has persona.md — skipping")
        return False

    # Skip if no source files exist
    sources = [(actor_dir / fn, section) for fn, section in SECTION_MAP]
    existing = [(fp, s) for fp, s in sources if fp.exists()]
    if not existing:
        print(f"  [{actor_dir.name}] no source files found — skipping")
        return False

    # Build persona.md content
    actor_name = actor_dir.name.upper()
    lines = [f"# {actor_name} - Persona", ""]

    for filepath, section_name in sources:
        lines.append(f"## {section_name}")
        lines.append("")
        if filepath.exists():
            content = filepath.read_text(encoding='utf-8').strip()
            # Strip old file-level header comments like "# WALE - Personality"
            content_lines = content.split('\n')
            filtered = []
            skip_next_blank = False
            for line in content_lines:
                if (line.startswith('#') and
                        any(kw in line.upper() for kw in
                            ['BACKGROUND', 'PERSONALITY', 'STAGE DIRECTION', 'PERSONA']) and
                        ' - ' in line):
                    skip_next_blank = True
                    continue
                if skip_next_blank and not line.strip():
                    skip_next_blank = False
                    continue
                skip_next_blank = False
                filtered.append(line)
            content = '\n'.join(filtered).strip()
            lines.append(content)
        else:
            lines.append("# TODO")
        lines.append("")
        lines.append("")

    persona_content = '\n'.join(lines).rstrip() + '\n'

    if write or clean:
        persona_file.write_text(persona_content, encoding='utf-8')
        print(f"  [{actor_dir.name}] wrote persona.md")
        if clean:
            for filepath, _ in existing:
                filepath.unlink()
                print(f"  [{actor_dir.name}] deleted {filepath.name}")
    else:
        print(f"  [{actor_dir.name}] DRY RUN — would write persona.md ({len(persona_content)} chars)")
        if clean:
            for filepath, _ in existing:
                print(f"  [{actor_dir.name}] DRY RUN — would delete {filepath.name}")

    return True


def main():
    write = '--write' in sys.argv or '--clean' in sys.argv
    clean = '--clean' in sys.argv

    mode = 'CLEAN (write + delete)' if clean else ('WRITE' if write else 'DRY RUN')
    print(f"migrate_persona.py — mode: {mode}")
    print(f"Scanning: {ACTORS_DIR}")
    print()

    migrated = 0
    for actor_dir in sorted(ACTORS_DIR.iterdir()):
        if not actor_dir.is_dir() or actor_dir.name.startswith('_'):
            continue
        if migrate_actor(actor_dir, write, clean):
            migrated += 1

    # Also handle _template
    template_dir = ACTORS_DIR / '_template'
    if template_dir.exists():
        print()
        print("Template:")
        migrate_actor(template_dir, write, clean)

    print()
    print(f"Done. {migrated} actors processed.")
    if not write:
        print("Run with --write to apply, --clean to apply and delete old files.")


if __name__ == '__main__':
    main()
