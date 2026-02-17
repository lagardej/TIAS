"""
Parse command - Parse savegame to SQLite database
"""

import gzip
import json
import logging
import sqlite3
from pathlib import Path

from src.core.core import load_env, get_project_root
from src.core.date_utils import parse_flexible_date
from src.perf.performance import timed_command


def find_savegame(saves_dir: Path, game_date) -> Path:
    """Find savegame file matching date.

    Savegame filenames use the game's format: *_2027-8-1.gz (no zero-padding)
    """
    game_format = f"{game_date.year}-{game_date.month}-{game_date.day}"
    pattern = f"*_{game_format}.gz"

    if isinstance(saves_dir, str):
        saves_dir = Path(saves_dir)

    matches = list(saves_dir.glob(pattern))

    if not matches:
        logging.error(f"Searched in: {saves_dir}")
        logging.error(f"Pattern: {pattern}")
        logging.error(f"Available files: {[f.name for f in saves_dir.glob('*.gz')]}")
        raise FileNotFoundError(f"No savegame found matching {pattern}")
    if len(matches) > 1:
        logging.warning(f"Multiple matches: {[m.name for m in matches]}")

    return matches[0]


def parse_savegame(saves_dir: Path, game_date, db_path: Path) -> int:
    """Parse savegame .gz into SQLite DB. Returns number of gamestate keys.

    Extracted as a standalone function so stage can call it internally
    without going through argparse.
    """
    savegame_path = find_savegame(saves_dir, game_date)
    logging.info(f"Parsing {savegame_path.name}...")

    with gzip.open(savegame_path, 'rt', encoding='utf-8-sig') as f:
        data = json.load(f)

    logging.info(f"Loaded {len(json.dumps(data)) / 1024 / 1024:.1f}MB JSON")

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE campaign (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE gamestates (key TEXT PRIMARY KEY, data TEXT)''')

    gamestates = data.get('gamestates', {})
    for key, value in gamestates.items():
        cursor.execute('INSERT INTO gamestates VALUES (?, ?)', (key, json.dumps(value)))

    conn.commit()
    conn.close()

    return len(gamestates)


@timed_command
def cmd_parse(args):
    """Parse savegame to database"""
    env = load_env()

    project_root = get_project_root()
    saves_dir = Path(env['GAME_SAVES_DIR'])
    game_date, iso_date = parse_flexible_date(args.date)
    db_path = project_root / "build" / f"savegame_{iso_date}.db"

    n_keys = parse_savegame(saves_dir, game_date, db_path)

    db_size = db_path.stat().st_size / 1024 / 1024
    logging.info("=" * 60)
    logging.info(f"[OK] Parse complete: {db_path.name} ({db_size:.1f}MB, {n_keys} keys)")
    print(f"\n[OK] Parse complete: {db_path.name} ({db_size:.1f}MB, {n_keys} keys)")
