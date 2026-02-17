"""
Preset command - Combine actor contexts and game state into final LLM context
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from src.core.core import get_project_root
from src.core.date_utils import parse_flexible_date
from src.preset.launch_windows import calculate_launch_windows
from src.perf.performance import timed_command


# Context file ordering: system first, then actors alphabetically, codex last
_CONTEXT_ORDER_FIRST = ['context_system.txt']
_CONTEXT_ORDER_LAST  = ['context_codex.txt']


def load_context_files(generated_dir: Path) -> list[tuple[str, str]]:
    """Load staged context files in canonical order.

    Returns list of (filename, content) in order:
      context_system.txt, context_<actors alphabetically>, context_codex.txt

    Warns if no context files found (stage hasn't been run).
    """
    if not generated_dir.exists():
        logging.warning("generated/ directory missing - run: tias stage --date DATE")
        return []

    all_files = sorted(generated_dir.glob('context_*.txt'))
    if not all_files:
        logging.warning("No context_*.txt files found - run: tias stage --date DATE")
        return []

    first = [f for f in all_files if f.name in _CONTEXT_ORDER_FIRST]
    last  = [f for f in all_files if f.name in _CONTEXT_ORDER_LAST]
    mid   = [f for f in all_files if f.name not in _CONTEXT_ORDER_FIRST
                                   and f.name not in _CONTEXT_ORDER_LAST]

    ordered = first + mid + last
    result = []
    for path in ordered:
        content = path.read_text(encoding='utf-8').strip()
        if content:
            result.append((path.name, content))
            logging.info(f"  loaded {path.name} ({len(content)} chars)")

    return result


@timed_command
def cmd_preset(args):
    """Combine actor contexts and game state into final LLM context"""
    project_root = get_project_root()

    game_date, iso_date = parse_flexible_date(args.date)

    templates_db   = project_root / "build" / "game_templates.db"
    savegame_db    = project_root / "build" / f"savegame_{iso_date}.db"
    templates_file = project_root / "build" / "templates" / "TISpaceBodyTemplate.json"
    generated_dir  = project_root / "generated"
    output_file    = generated_dir / "mistral_context.txt"
    generated_dir.mkdir(exist_ok=True)

    if not templates_db.exists():
        logging.error("Templates DB missing. Run: tias load")
        return 1

    if not savegame_db.exists():
        logging.error(f"Savegame DB missing. Run: tias stage --date {args.date}")
        return 1

    logging.info("Loading staged actor contexts...")
    context_files = load_context_files(generated_dir)

    logging.info("Calculating launch windows...")
    launch_windows = calculate_launch_windows(game_date, templates_file)

    logging.info("Assembling final context...")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# TERRA INVICTA - LLM CONTEXT\n")
        f.write(f"# Game Date: {game_date.strftime('%Y-%m-%d')}\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")

        # Actor contexts from stage
        if context_files:
            for filename, content in context_files:
                f.write(content)
                f.write("\n\n")
        else:
            logging.warning("No actor contexts available - context will be sparse")

        # Game state: hab sites
        conn = sqlite3.connect(templates_db)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT h.body, h.displayName,
                   p.water_mean, p.metals_mean
            FROM hab_sites h
            JOIN mining_profiles p ON h.miningProfile = p.dataName
            WHERE h.body IN ('Luna', 'Mars')
            ORDER BY h.body, h.displayName
        ''')
        rows = cursor.fetchall()
        conn.close()

        if rows:
            f.write("# GAME STATE\n\n")
            f.write("## Key Hab Sites\n")
            current_body = None
            for body, name, wm, mm in rows:
                if body != current_body:
                    f.write(f"\n### {body}\n")
                    current_body = body
                f.write(f"{name}: W={wm:.0f} M={mm:.0f}\n")
            f.write("\n")

        # Game state: launch windows
        if launch_windows:
            f.write("## Launch Windows\n")
            for target, data in launch_windows.items():
                f.write(f"{target}: Next window {data['next_window']} ")
                f.write(f"({data['days_away']} days, ~{data['days_away'] // 30} months)")
                if 'current_penalty' in data:
                    f.write(f", Current penalty: {data['current_penalty']}%")
                f.write("\n")

    size = output_file.stat().st_size / 1024
    logging.info("=" * 60)
    logging.info(f"[OK] Preset complete: {output_file.name} ({size:.1f}KB, {len(context_files)} context files)")
    print(f"\n[OK] Preset complete: {output_file.name} ({size:.1f}KB, {len(context_files)} actor contexts)")
    if not context_files:
        print("     WARNING: No actor contexts - run: tias stage --date DATE")
