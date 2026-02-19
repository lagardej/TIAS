"""
Terra Invicta Advisory System - Core Utilities

Shared utilities for environment loading, logging, and path management.
"""

import logging
import sys
from pathlib import Path


def setup_logging(verbosity: int):
    """Configure logging based on verbosity level"""
    levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }
    level = levels.get(verbosity, logging.DEBUG)

    project_root = get_project_root()
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "terractl.log"

    import sys
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a', encoding='utf-8'),
            logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False))
        ]
    )


def load_env():
    """Load .env file"""
    project_root = get_project_root()
    env_path = project_root / ".env"
    env = {}

    if not env_path.exists():
        logging.error(".env not found. Run: tias install")
        sys.exit(1)

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()

    return env


def get_project_root() -> Path:
    """Get project root directory (one level up from src/)"""
    # From src/core/core.py -> src/core/ -> src/ -> project_root/
    return Path(__file__).parent.parent.parent
