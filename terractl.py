#!/usr/bin/env python3
"""
TerraCtl - Terra Invicta Advisory System Control

Unified build, parse, inject, and run pipeline.
"""

import sys
import os
import subprocess
import argparse
import logging
import json
import gzip
import csv
import hashlib
import sqlite3
import math
from pathlib import Path
from datetime import datetime, timedelta

# Python version check
if sys.version_info < (3, 11):
    print("ERROR: Python 3.11+ required")
    print(f"Current version: {sys.version}")
    print("Please upgrade Python and try again.")
    sys.exit(1)

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

import time
import functools

def timed_command(func):
    """Decorator to time command execution and log performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        command_name = func.__name__.replace('cmd_', '')
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # Log to performance log
            log_performance(command_name, elapsed, success=True)
            
            # Console output
            if elapsed > 1.0:
                logging.warning(f"Performance: {command_name} took {elapsed:.2f}s (threshold: 1.0s)")
            else:
                logging.debug(f"Performance: {command_name} completed in {elapsed:.3f}s")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            log_performance(command_name, elapsed, success=False, error=str(e))
            raise
    
    return wrapper

def log_performance(command: str, elapsed: float, success: bool = True, error: str = None):
    """Append performance metrics to performance log"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    perf_log = log_dir / "performance.log"
    
    timestamp = datetime.now().isoformat()
    status = "SUCCESS" if success else "FAILED"
    
    with open(perf_log, 'a') as f:
        if error:
            f.write(f"{timestamp},{command},{elapsed:.3f},{status},{error}\n")
        else:
            f.write(f"{timestamp},{command},{elapsed:.3f},{status}\n")

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging(verbosity: int):
    """Configure logging based on verbosity level"""
    levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }
    level = levels.get(verbosity, logging.DEBUG)
    
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "terractl.log"
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='a'),
            logging.StreamHandler()
        ]
    )

# ============================================================================
# ENVIRONMENT
# ============================================================================

def load_env():
    """Load .env file"""
    env_path = Path(__file__).parent / ".env"
    env = {}
    
    if not env_path.exists():
        logging.error(".env not found. Copy .env.dist to .env")
        sys.exit(1)
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
    
    return env

# ============================================================================
# INSTALL COMMAND
# ============================================================================

def auto_detect_path(candidates: list) -> Path:
    """Try to auto-detect path from candidates"""
    for path_str in candidates:
        path = Path(os.path.expanduser(path_str))
        if path.exists():
            return path
    return None

def prompt_path(message: str, default: str = None) -> str:
    """Prompt user for path with optional default"""
    if default:
        user_input = input(f"{message} [{default}]: ").strip()
        return user_input if user_input else default
    else:
        while True:
            user_input = input(f"{message}: ").strip()
            if user_input:
                return user_input
            print("  Path required. Please try again.")

@timed_command
def cmd_install(args):
    """Interactive setup - auto-detect paths and create .env"""
    import platform
    
    print("Terra Invicta Advisory System - Installation")
    print("="*60)
    
    is_windows = platform.system() == 'Windows'
    print(f"Detected OS: {'Windows' if is_windows else 'Linux'}")
    print()
    
    # Auto-detect game installation
    print("[1/5] Detecting game installation...")
    game_candidates = [
        "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Terra Invicta",
        "~/.steam/steam/steamapps/common/Terra Invicta",
        "~/.local/share/Steam/steamapps/common/Terra Invicta"
    ]
    game_dir = auto_detect_path(game_candidates)
    
    if game_dir:
        print(f"  Found: {game_dir}")
        confirm = input("  Use this path? [Y/n]: ").strip().lower()
        if confirm in ['n', 'no']:
            game_dir = prompt_path("  Enter game install path")
    else:
        print("  Not found in common locations")
        game_dir = prompt_path("  Enter game install path")
    
    # Auto-detect saves directory
    print("\n[2/5] Detecting saves directory...")
    saves_candidates = [
        "C:\\Users\\" + os.getenv('USERNAME', 'User') + "\\Documents\\My Games\\TerraInvicta\\Saves",
        "~/.local/share/Pavonis Interactive/Terra Invicta/Saves"
    ]
    saves_dir = auto_detect_path(saves_candidates)
    
    if saves_dir:
        print(f"  Found: {saves_dir}")
        confirm = input("  Use this path? [Y/n]: ").strip().lower()
        if confirm in ['n', 'no']:
            saves_dir = prompt_path("  Enter saves directory")
    else:
        print("  Not found in common locations")
        saves_dir = prompt_path("  Enter saves directory")
    
    # Prompt for KoboldCpp (can't auto-detect)
    print("\n[3/5] KoboldCpp configuration...")
    kobold_dir = prompt_path("  KoboldCpp directory")
    
    print("\n[4/5] Model configuration...")
    print("  Note: Configure base model only (others optional)")
    model_path_base = prompt_path("  Base model path (mistral-7b-q4.gguf)")
    
    # GPU backend
    print("\n[5/5] GPU backend selection...")
    if is_windows:
        print("  Recommended for Windows + AMD: vulkan")
        gpu_backend = prompt_path("  GPU backend", "vulkan")
    else:
        print("  Recommended for Linux + AMD: clblast (requires ROCm)")
        print("  Alternative: vulkan (works on any GPU)")
        gpu_backend = prompt_path("  GPU backend", "clblast")
    
    # Write .env file
    print("\n" + "="*60)
    print("Writing .env file...")
    
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    gitignore_file = project_root / ".gitignore"
    
    # Ensure .env is in .gitignore
    if gitignore_file.exists():
        with open(gitignore_file) as f:
            gitignore_content = f.read()
        if '.env' not in gitignore_content and '*.env' not in gitignore_content:
            print("\nWARNING: .env not found in .gitignore")
            print("Adding .env to .gitignore to prevent committing secrets...")
            with open(gitignore_file, 'a') as f:
                f.write("\n# Environment configuration (contains secrets)\n.env\n")
    else:
        print("\nWARNING: .gitignore not found")
        print("Creating .gitignore to protect .env file...")
        with open(gitignore_file, 'w') as f:
            f.write("# Environment configuration (contains secrets)\n.env\n")
    
    with open(env_file, 'w') as f:
        f.write("# Terra Invicta Advisory System - Configuration\n")
        f.write(f"# Generated by: terractl.py install\n")
        f.write(f"# Date: {datetime.now().isoformat()}\n")
        f.write("\n")
        
        f.write("# KoboldCpp\n")
        f.write("KOBOLDCPP_URL=http://localhost:5001\n")
        f.write(f"KOBOLDCPP_DIR={kobold_dir}\n")
        f.write(f"KOBOLDCPP_MODEL_BASE={model_path_base}\n")
        f.write(f"KOBOLDCPP_MODEL_MAX=# Optional: Path to mistral-7b-q6.gguf\n")
        f.write(f"KOBOLDCPP_MODEL_NUCLEAR=# Optional: Path to qwen2.5-14b-q4.gguf\n")
        f.write(f"KOBOLDCPP_MODEL_RIDICULOUS=# Optional: Path to qwen2.5-32b-q4.gguf\n")
        f.write(f"KOBOLDCPP_MODEL_LUDICROUS=# Optional: Path to qwen2.5-72b-q2.gguf\n")
        f.write("KOBOLDCPP_QUALITY=base\n")
        f.write("KOBOLDCPP_PORT=5001\n")
        f.write(f"KOBOLDCPP_GPU_BACKEND={gpu_backend}\n")
        f.write("KOBOLDCPP_GPU_LAYERS=35\n")
        f.write("KOBOLDCPP_CONTEXT_SIZE=16384\n")
        f.write("KOBOLDCPP_THREADS=8\n")
        f.write("\n")
        
        f.write("# Terra Invicta\n")
        f.write(f"GAME_INSTALL_DIR={game_dir}\n")
        f.write("GAME_VERSION=1.0.29\n")
        f.write(f"GAME_SAVES_DIR={saves_dir}\n")
        f.write("\n")
        
        f.write("# Paths\n")
        f.write("SRC_DIR=./src\n")
        f.write("BUILD_DIR=./build\n")
        f.write("GENERATED_DIR=./generated\n")
        f.write("LOGS_DIR=./logs\n")
        f.write("\n")
        
        f.write("# System\n")
        f.write("LOG_LEVEL=INFO\n")
        f.write("CURRENT_TIER=1\n")
    
    logging.info(f"Created .env file: {env_file}")
    print(f"\n[OK] Installation complete!")
    print(f"  Configuration saved to: {env_file}")
    print(f"\nNext steps:")
    print(f"  1. python terractl.py build")
    print(f"  2. python terractl.py parse --date YYYY-M-D")
    print(f"  3. python terractl.py run --date YYYY-M-D")

# ============================================================================
# CLEAN COMMAND
# ============================================================================

@timed_command
def cmd_clean(args):
    """Remove build directory"""
    import shutil
    
    project_root = Path(__file__).parent
    build_dir = project_root / "build"
    
    if not build_dir.exists():
        logging.info("Nothing to clean - build directory does not exist")
        print("Nothing to clean")
        return
    
    # Count files
    file_count = sum(1 for _ in build_dir.rglob('*') if _.is_file())
    
    # Remove entire directory
    shutil.rmtree(build_dir)
    
    logging.info("="*60)
    logging.info(f"[OK] Clean complete")
    logging.info(f"  Removed: build/ ({file_count} files)")
    print(f"\n[OK] Clean complete: build/ removed ({file_count} files)")

# ============================================================================
# BUILD COMMAND
# ============================================================================

def parse_localization_file(loc_file: Path) -> dict:
    """Parse .en localization file"""
    localizations = {}
    
    with open(loc_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            parts = key.split('.')
            
            if len(parts) < 3:
                continue
            
            field = parts[1]
            data_name = '.'.join(parts[2:])
            
            if data_name not in localizations:
                localizations[data_name] = {}
            
            localizations[data_name][field] = value
    
    return localizations

def merge_localization(data, localizations: dict):
    """Recursively merge localization"""
    if isinstance(data, dict):
        merged = {}
        for key, value in data.items():
            merged[key] = merge_localization(value, localizations)
        
        data_name = merged.get('dataName')
        if data_name and data_name in localizations:
            loc = localizations[data_name]
            if 'displayName' in loc:
                merged['displayName'] = loc['displayName']
            if 'description' in loc:
                merged['description'] = loc['description']
        
        return merged
    
    elif isinstance(data, list):
        return [merge_localization(item, localizations) for item in data]
    
    else:
        return data

def build_actors(src_dir: Path, build_dir: Path) -> dict:
    """Build actor JSON files from TOML/CSV"""
    import tomllib
    
    actors_src = src_dir / "actors"
    actors_build = build_dir / "actors"
    actors_build.mkdir(exist_ok=True)
    
    built_files = {}
    
    for actor_dir in actors_src.iterdir():
        if not actor_dir.is_dir() or actor_dir.name.startswith('_'):
            continue
        
        spec_file = actor_dir / "spec.toml"
        if not spec_file.exists():
            continue
        
        logging.info(f"Building {actor_dir.name}...")
        
        with open(spec_file, 'rb') as f:
            spec = tomllib.load(f)
        
        # Load background
        bg_file = actor_dir / "background.txt"
        if bg_file.exists():
            with open(bg_file, encoding='utf-8') as f:
                spec['background'] = f.read()
        
        # Load openers
        openers_file = actor_dir / "openers.csv"
        if openers_file.exists():
            spec['openers'] = []
            with open(openers_file, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                spec['openers'] = list(reader)
        else:
            logging.warning(f"  WARNING: No openers defined")
        
        # Load reactions
        reactions_file = actor_dir / "reactions.csv"
        if reactions_file.exists():
            spec['reactions'] = []
            with open(reactions_file, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                spec['reactions'] = list(reader)
        else:
            logging.warning(f"  WARNING: No reactions defined")
        
        # Write JSON
        output_file = actors_build / f"{actor_dir.name}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(spec, f, indent=2, ensure_ascii=False)
        
        built_files[actor_dir.name] = str(output_file)
        logging.info(f"  -> {output_file}")
    
    return built_files

def build_templates(game_dir: Path, build_dir: Path) -> dict:
    """Build templates with localization"""
    templates_src = game_dir / "TerraInvicta_Data/StreamingAssets/Templates"
    loc_dir = game_dir / "TerraInvicta_Data/StreamingAssets/Localization/en"
    templates_build = build_dir / "templates"
    templates_build.mkdir(exist_ok=True)
    
    built_files = {}
    
    for template_file in templates_src.glob("*.json"):
        template_name = template_file.stem
        logging.debug(f"  -> {template_name}")
        
        try:
            with open(template_file, encoding='utf-8') as f:
                template_data = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"  ERROR: {template_name}: {e}")
            continue
        
        # Load localization
        loc_file = loc_dir / f"{template_name}.en"
        localizations = {}
        if loc_file.exists():
            localizations = parse_localization_file(loc_file)
        
        # Merge
        merged_data = merge_localization(template_data, localizations)
        
        # Write
        output_file = templates_build / template_file.name
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, indent=2, ensure_ascii=False)
        
        built_files[template_name] = str(output_file)
    
    return built_files

def create_templates_db(build_dir: Path, templates_dir: Path):
    """Create SQLite DB from templates"""
    db_path = build_dir / "game_templates.db"
    
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tables
    cursor.execute('''CREATE TABLE space_bodies (
        dataName TEXT PRIMARY KEY,
        displayName TEXT,
        objectType TEXT,
        parent TEXT,
        mass_kg TEXT,
        radius_km REAL
    )''')
    
    cursor.execute('''CREATE TABLE hab_sites (
        dataName TEXT PRIMARY KEY,
        displayName TEXT,
        body TEXT,
        miningProfile TEXT,
        water INT,
        metals INT,
        nobles INT,
        fissiles INT
    )''')
    
    cursor.execute('''CREATE TABLE mining_profiles (
        dataName TEXT PRIMARY KEY,
        displayName TEXT,
        water_mean REAL, water_width REAL, water_min REAL,
        metals_mean REAL, metals_width REAL, metals_min REAL,
        nobles_mean REAL, nobles_width REAL, nobles_min REAL,
        fissiles_mean REAL, fissiles_width REAL, fissiles_min REAL
    )''')
    
    cursor.execute('''CREATE TABLE traits (
        dataName TEXT PRIMARY KEY,
        displayName TEXT,
        description TEXT
    )''')
    
    # Load space bodies
    bodies_file = templates_dir / "TISpaceBodyTemplate.json"
    if bodies_file.exists():
        with open(bodies_file, encoding='utf-8') as f:
            bodies = json.load(f)
        for body in bodies:
            cursor.execute('''INSERT INTO space_bodies VALUES (?, ?, ?, ?, ?, ?)''',
                (body.get('dataName'),
                 body.get('displayName', body.get('friendlyName')),
                 body.get('objectType'),
                 body.get('barycenterName'),
                 str(body.get('mass_kg')) if body.get('mass_kg') else None,
                 body.get('equatorialRadius_km')))
    
    # Load mining profiles
    profiles_file = templates_dir / "TIMiningProfileTemplate.json"
    profiles_map = {}
    if profiles_file.exists():
        with open(profiles_file, encoding='utf-8') as f:
            profiles = json.load(f)
        for profile in profiles:
            cursor.execute('''INSERT INTO mining_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (profile.get('dataName'),
                 profile.get('displayName', profile.get('friendlyName', profile.get('dataName'))),
                 profile.get('water_mean', 0), profile.get('water_width', 0), profile.get('water_min', 0),
                 profile.get('metals_mean', 0), profile.get('metals_width', 0), profile.get('metals_min', 0),
                 profile.get('nobles_mean', 0), profile.get('nobles_width', 0), profile.get('nobles_min', 0),
                 profile.get('fissiles_mean', 0), profile.get('fissiles_width', 0), profile.get('fissiles_min', 0)))
            profiles_map[profile.get('dataName')] = {
                'water': profile.get('water_mean', 0),
                'metals': profile.get('metals_mean', 0),
                'nobles': profile.get('nobles_mean', 0),
                'fissiles': profile.get('fissiles_mean', 0)
            }
    
    # Load hab sites
    sites_file = templates_dir / "TIHabSiteTemplate.json"
    if sites_file.exists():
        with open(sites_file, encoding='utf-8') as f:
            sites = json.load(f)
        for site in sites:
            profile_name = site.get('miningProfileName')
            resources = profiles_map.get(profile_name, {})
            cursor.execute('''INSERT INTO hab_sites VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (site.get('dataName'),
                 site.get('displayName', site.get('friendlyName', site.get('dataName'))),
                 site.get('parentBodyName'),
                 profile_name,
                 resources.get('water', 0),
                 resources.get('metals', 0),
                 resources.get('nobles', 0),
                 resources.get('fissiles', 0)))
    
    # Load traits
    traits_file = templates_dir / "TITraitTemplate.json"
    if traits_file.exists():
        with open(traits_file, encoding='utf-8') as f:
            traits = json.load(f)
        for trait in traits:
            cursor.execute('''INSERT INTO traits VALUES (?, ?, ?)''',
                (trait.get('dataName'),
                 trait.get('displayName', trait.get('friendlyName')),
                 trait.get('description', '')))
    
    conn.commit()
    conn.close()
    
    logging.info(f"OK Created game database: {db_path}")

@timed_command
def cmd_build(args):
    """Build game templates database"""
    env = load_env()
    
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    build_dir = project_root / "build"
    game_dir = Path(env['GAME_INSTALL_DIR'])
    
    # Ensure build directory exists
    build_dir.mkdir(exist_ok=True)
    
    logging.info("Building actors...")
    actor_files = build_actors(src_dir, build_dir)
    logging.info(f"Built {len(actor_files)} actors")
    
    logging.info("Building templates...")
    template_files = build_templates(game_dir, build_dir)
    logging.info(f"Built {len(template_files)} templates")
    
    logging.info("Creating database...")
    create_templates_db(build_dir, build_dir / "templates")
    
    logging.info("="*60)
    logging.info(f"[OK] Build complete: {len(actor_files) + len(template_files)} files")
    logging.info(f"  Actors: {len(actor_files)}")
    logging.info(f"  Templates: {len(template_files)}")
    logging.info(f"  Database: {build_dir / 'game_templates.db'}")
    print(f"\n[OK] Build complete: {len(actor_files) + len(template_files)} files")

# ============================================================================
# PARSE COMMAND
# ============================================================================

def find_savegame(saves_dir: Path, date_str: str) -> Path:
    """Find savegame matching date"""
    pattern = f"*_{date_str}.gz"
    
    # Ensure Path object
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

@timed_command
def cmd_parse(args):
    """Parse savegame to database"""
    env = load_env()
    
    project_root = Path(__file__).parent
    saves_dir = Path(env['GAME_SAVES_DIR'])
    db_path = project_root / "build" / f"savegame_{args.date.replace('-', '_')}.db"
    
    logging.info(f"Finding savegame for {args.date}...")
    savegame_path = find_savegame(saves_dir, args.date)
    logging.info(f"Loading {savegame_path.name}...")
    
    with gzip.open(savegame_path, 'rt', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    logging.info(f"Loaded {len(json.dumps(data))/1024/1024:.1f}MB JSON")
    
    # Create DB
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE campaign (key TEXT PRIMARY KEY, value TEXT)''')
    cursor.execute('''CREATE TABLE gamestates (key TEXT PRIMARY KEY, data TEXT)''')
    
    # Store all gamestates
    gamestates = data.get('gamestates', {})
    for key, value in gamestates.items():
        cursor.execute('INSERT INTO gamestates VALUES (?, ?)', (key, json.dumps(value)))
    
    conn.commit()
    conn.close()
    
    db_size = db_path.stat().st_size / 1024 / 1024
    logging.info("="*60)
    logging.info(f"[OK] Parse complete: {db_path.name}")
    logging.info(f"  Size: {db_size:.1f}MB")
    logging.info(f"  Keys: {len(gamestates)}")
    print(f"\n[OK] Parse complete: {db_path.name} ({db_size:.1f}MB, {len(gamestates)} keys)")

# ============================================================================
# LAUNCH WINDOW CALCULATIONS
# ============================================================================

def calculate_launch_windows(game_date: datetime, templates_file: Path) -> dict:
    """Calculate launch windows for major targets using known synodic periods"""
    import json
    
    if not templates_file.exists():
        logging.warning(f"Templates file not found: {templates_file}")
        return {}
    
    # Load templates
    with open(templates_file, encoding='utf-8') as f:
        templates_data = json.load(f)
    
    # Known optimal windows (from game verification)
    # Mars windows repeat every 780 days
    mars_base_window = datetime(2026, 11, 13)  # Known optimal
    mars_synodic = 780  # days
    
    # NEA windows (Near-Earth Asteroids)
    sisyphus_base_window = datetime(2027, 8, 2)
    sisyphus_synodic = 592  # days
    
    hephaistos_base_window = datetime(2027, 8, 1)
    hephaistos_synodic = 533  # days
    
    results = {}
    
    # Calculate Mars window
    days_since_base = (game_date - mars_base_window).days
    cycles_passed = days_since_base / mars_synodic
    next_cycle = math.ceil(cycles_passed)
    next_mars_window = mars_base_window + timedelta(days=next_cycle * mars_synodic)
    days_to_mars = (next_mars_window - game_date).days
    
    # Mars penalty (calibrated)
    days_from_optimal = min(days_to_mars, mars_synodic - days_to_mars)
    normalized = days_from_optimal / (mars_synodic / 2.0)
    mars_penalty = 40.0 * (normalized ** 0.5)
    
    results['Mars'] = {
        'next_window': next_mars_window.strftime('%Y-%m-%d'),
        'days_away': days_to_mars,
        'current_penalty': int(mars_penalty)
    }
    
    # Calculate Sisyphus window (NEA - no penalty yet)
    days_since_sis = (game_date - sisyphus_base_window).days
    cycles_sis = days_since_sis / sisyphus_synodic
    next_cycle_sis = math.ceil(cycles_sis)
    next_sis_window = sisyphus_base_window + timedelta(days=next_cycle_sis * sisyphus_synodic)
    days_to_sis = (next_sis_window - game_date).days
    
    results['Sisyphus'] = {
        'next_window': next_sis_window.strftime('%Y-%m-%d'),
        'days_away': days_to_sis
    }
    
    # Calculate Hephaistos window (NEA - no penalty yet)
    days_since_heph = (game_date - hephaistos_base_window).days
    cycles_heph = days_since_heph / hephaistos_synodic
    next_cycle_heph = math.ceil(cycles_heph)
    next_heph_window = hephaistos_base_window + timedelta(days=next_cycle_heph * hephaistos_synodic)
    days_to_heph = (next_heph_window - game_date).days
    
    results['Hephaistos'] = {
        'next_window': next_heph_window.strftime('%Y-%m-%d'),
        'days_away': days_to_heph
    }
    
    return results

# ============================================================================
# INJECT COMMAND
# ============================================================================

def load_actors(src_dir: Path) -> dict:
    """Load actor specs"""
    import tomllib
    
    actors = {}
    actors_dir = src_dir / "actors"
    
    for actor_dir in actors_dir.iterdir():
        if not actor_dir.is_dir() or actor_dir.name.startswith('_'):
            continue
        
        spec_file = actor_dir / "spec.toml"
        if not spec_file.exists():
            continue
        
        with open(spec_file, 'rb') as f:
            spec = tomllib.load(f)
        
        actors[spec['name']] = spec
    
    return actors

@timed_command
def cmd_inject(args):
    """Generate LLM context"""
    project_root = Path(__file__).parent
    templates_db = project_root / "build" / "game_templates.db"
    savegame_db = project_root / "build" / f"savegame_{args.date.replace('-', '_')}.db"
    templates_file = project_root / "build" / "templates" / "TISpaceBodyTemplate.json"
    output_file = project_root / "generated" / "mistral_context.txt"
    output_file.parent.mkdir(exist_ok=True)
    
    if not templates_db.exists():
        logging.error("Templates DB missing. Run: terractl.py build")
        return 1
    
    if not savegame_db.exists():
        logging.error(f"Savegame DB missing. Run: terractl.py parse --date {args.date}")
        return 1
    
    logging.info("Loading actors...")
    actors = load_actors(project_root / "src")
    
    logging.info("Calculating launch windows...")
    game_date = datetime.strptime(args.date, '%Y-%m-%d')
    launch_windows = calculate_launch_windows(game_date, templates_file)
    
    logging.info("Generating context...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# TERRA INVICTA - LLM CONTEXT\n")
        f.write(f"# Game Date: {game_date.strftime('%Y-%m-%d')}\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
        
        # Actors
        f.write("# ADVISORS\n")
        for name, spec in actors.items():
            display = spec.get('display_name', name)
            domain = spec.get('domain_primary', 'Unknown')
            f.write(f"{display} - {domain}\n")
        f.write("\n")
        
        # Hab sites
        conn = sqlite3.connect(templates_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT h.body, h.displayName, 
                   p.water_mean, p.water_width, p.water_min,
                   p.metals_mean, p.metals_width, p.metals_min
            FROM hab_sites h
            JOIN mining_profiles p ON h.miningProfile = p.dataName
            WHERE h.body IN ('Luna', 'Mars')
            ORDER BY h.body, h.displayName
        ''')
        
        f.write("# KEY HAB SITES\n")
        current_body = None
        for row in cursor.fetchall():
            body, name, wm, ww, wmin, mm, mw, mmin = row
            if body != current_body:
                f.write(f"\n## {body}\n")
                current_body = body
            f.write(f"{name}: W={wm:.0f} M={mm:.0f}\n")
        
        conn.close()
        
        # Launch windows
        if launch_windows:
            f.write("\n# LAUNCH WINDOWS\n")
            for target, data in launch_windows.items():
                f.write(f"{target}: Next window {data['next_window']} ")
                f.write(f"({data['days_away']} days, ~{data['days_away']//30} months)")
                if 'current_penalty' in data:
                    f.write(f", Current penalty: {data['current_penalty']}%")
                f.write("\n")
    
    size = output_file.stat().st_size / 1024
    logging.info("="*60)
    logging.info(f"[OK] Context generated: {output_file.name}")
    logging.info(f"  Size: {size:.1f}KB")
    logging.info(f"  Actors: {len(actors)}")
    print(f"\n[OK] Context ready: {output_file} ({size:.1f}KB)")

# ============================================================================
# VALIDATE COMMAND
# ============================================================================

@timed_command
def cmd_validate(args):
    """Validate configuration and paths"""
    print("Terra Invicta Advisory System - Configuration Validation")
    print("="*60)
    
    project_root = Path(__file__).parent
    errors = []
    warnings = []
    
    # Check .env exists
    env_file = project_root / ".env"
    if not env_file.exists():
        errors.append(".env file not found. Run: terractl.py install")
        print("\n[FAIL] .env file missing")
        print("  Run: python terractl.py install")
        return 1
    
    print("[OK] .env file found")
    
    # Load and validate .env
    try:
        env = load_env()
    except SystemExit:
        return 1
    
    # Validate game installation
    print("\nValidating game installation...")
    game_dir = Path(os.path.expanduser(env.get('GAME_INSTALL_DIR', '')))
    if not game_dir.exists():
        errors.append(f"Game directory not found: {game_dir}")
        print(f"  [FAIL] Not found: {game_dir}")
    else:
        templates_dir = game_dir / "TerraInvicta_Data/StreamingAssets/Templates"
        if not templates_dir.exists():
            errors.append(f"Templates directory not found: {templates_dir}")
            print(f"  [FAIL] Templates not found")
        else:
            print(f"  [OK] Game found: {game_dir}")
    
    # Validate saves directory
    print("\nValidating saves directory...")
    saves_dir = Path(os.path.expanduser(env.get('GAME_SAVES_DIR', '')))
    if not saves_dir.exists():
        errors.append(f"Saves directory not found: {saves_dir}")
        print(f"  [FAIL] Not found: {saves_dir}")
    else:
        savegames = list(saves_dir.glob('*.gz'))
        if not savegames:
            warnings.append(f"No savegames found in {saves_dir}")
            print(f"  [WARN] No savegames found")
        else:
            print(f"  [OK] Saves found: {len(savegames)} savegames")
    
    # Validate KoboldCpp
    print("\nValidating KoboldCpp...")
    kobold_dir = Path(os.path.expanduser(env.get('KOBOLDCPP_DIR', '')))
    if not kobold_dir.exists():
        errors.append(f"KoboldCpp directory not found: {kobold_dir}")
        print(f"  [FAIL] Not found: {kobold_dir}")
    else:
        kobold_exe = kobold_dir / "koboldcpp.exe"
        if not kobold_exe.exists():
            kobold_exe = kobold_dir / "koboldcpp"
        if not kobold_exe.exists():
            errors.append(f"KoboldCpp executable not found in {kobold_dir}")
            print(f"  [FAIL] Executable not found")
        else:
            print(f"  [OK] KoboldCpp found: {kobold_exe}")
    
    # Validate model
    print("\nValidating model...")
    model_path = Path(os.path.expanduser(env.get('KOBOLDCPP_MODEL', '')))
    if not model_path.exists():
        errors.append(f"Model file not found: {model_path}")
        print(f"  [FAIL] Not found: {model_path}")
    else:
        model_size = model_path.stat().st_size / 1024 / 1024 / 1024
        print(f"  [OK] Model found: {model_path} ({model_size:.1f}GB)")
    
    # Check .gitignore
    print("\nValidating .gitignore...")
    gitignore_file = project_root / ".gitignore"
    if not gitignore_file.exists():
        warnings.append(".gitignore not found - .env might be committed")
        print(f"  [WARN] .gitignore not found")
    else:
        with open(gitignore_file) as f:
            gitignore_content = f.read()
        if '.env' not in gitignore_content and '*.env' not in gitignore_content:
            warnings.append(".env not in .gitignore - secrets might be committed")
            print(f"  [WARN] .env not in .gitignore")
        else:
            print(f"  [OK] .env properly ignored")
    
    # Summary
    print("\n" + "="*60)
    if errors:
        print(f"[FAIL] Validation failed with {len(errors)} error(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    elif warnings:
        print(f"[OK] Validation passed with {len(warnings)} warning(s)")
        for warning in warnings:
            print(f"  - {warning}")
        return 0
    else:
        print("[OK] All checks passed!")
        print("\nReady to use:")
        print("  python terractl.py build")
        print("  python terractl.py parse --date YYYY-M-D")
        print("  python terractl.py run --date YYYY-M-D")
        return 0

# ============================================================================
# RUN COMMAND
# ============================================================================

# Note: run command not timed (launches external KoboldCpp process)
def cmd_run(args):
    """Launch KoboldCpp"""
    # Generate context first
    cmd_inject(args)
    
    env = load_env()
    kobold_dir = env.get('KOBOLDCPP_DIR')
    
    # Determine model based on quality tier
    quality = args.quality if hasattr(args, 'quality') and args.quality else env.get('KOBOLDCPP_QUALITY', 'base')
    quality_upper = quality.upper()
    model_key = f'KOBOLDCPP_MODEL_{quality_upper}'
    model_path = env.get(model_key)
    
    if not model_path:
        logging.error(f"No model configured for quality '{quality}'")
        logging.error(f"Add {model_key} to .env")
        return 1
    
    port = env.get('KOBOLDCPP_PORT', '5001')
    gpu_backend = env.get('KOBOLDCPP_GPU_BACKEND', 'clblast')
    gpu_layers = env.get('KOBOLDCPP_GPU_LAYERS', '35')
    context_size = env.get('KOBOLDCPP_CONTEXT_SIZE', '16384')
    threads = env.get('KOBOLDCPP_THREADS', '8')
    
    if not kobold_dir or not model_path:
        logging.error("KOBOLDCPP_DIR or model path not set in .env")
        return 1
    
    # Expand ~ paths for Linux
    kobold_dir = os.path.expanduser(kobold_dir)
    model_path = os.path.expanduser(model_path)
    
    kobold_exe = Path(kobold_dir) / "koboldcpp.exe"
    if not kobold_exe.exists():
        kobold_exe = Path(kobold_dir) / "koboldcpp"  # Linux
    
    # Build command with GPU backend selection
    cmd = [
        str(kobold_exe),
        "--model", model_path,
        "--port", port,
        "--contextsize", context_size,
        "--threads", threads
    ]
    
    # Add GPU backend
    if gpu_backend == 'clblast':
        cmd.append("--useclblast")
    elif gpu_backend == 'vulkan':
        cmd.append("--usevulkan")
    elif gpu_backend == 'cublas':
        cmd.append("--usecublas")
    
    # Add GPU layers
    if gpu_layers:
        cmd.extend(["--gpulayers", gpu_layers])
    
    logging.info(f"Starting KoboldCpp on port {port}")
    logging.info(f"Quality: {quality} ({Path(model_path).name})")
    logging.info(f"GPU: {gpu_backend}, Layers: {gpu_layers}, Context: {context_size}")
    print(f"\nLaunching KoboldCpp (Quality: {quality})")
    print(f"  Model: {Path(model_path).name}")
    print(f"  GPU: {gpu_backend}, {gpu_layers} layers")
    print(f"  Port: {port}\n")
    
    subprocess.run(cmd, cwd=kobold_dir)

# ============================================================================
# PERF COMMAND
# ============================================================================

def cmd_perf(args):
    """Display performance statistics"""
    import csv
    from collections import defaultdict
    
    print("Terra Invicta Advisory System - Performance Report")
    print("="*60)
    
    project_root = Path(__file__).parent
    perf_log = project_root / "logs" / "performance.log"
    
    if not perf_log.exists():
        print("\nNo performance data available.")
        print("Performance tracking started automatically with this version.")
        return
    
    # Parse performance log
    stats = defaultdict(list)
    failures = defaultdict(int)
    
    with open(perf_log) as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 4:
                continue
            
            timestamp, command, elapsed, status = parts[:4]
            elapsed = float(elapsed)
            
            stats[command].append(elapsed)
            if status == "FAILED":
                failures[command] += 1
    
    if not stats:
        print("\nNo performance data available.")
        return
    
    # Display statistics
    print("\nCommand Performance:")
    print(f"{'Command':<12} {'Count':<8} {'Min':<10} {'Avg':<10} {'Max':<10} {'P95':<10} {'Failures'}")
    print("-" * 75)
    
    for command in sorted(stats.keys()):
        times = sorted(stats[command])
        count = len(times)
        min_time = min(times)
        avg_time = sum(times) / count
        max_time = max(times)
        p95_idx = int(count * 0.95)
        p95_time = times[p95_idx] if p95_idx < count else max_time
        fails = failures.get(command, 0)
        
        # Highlight slow commands
        warning = "!" if avg_time > 1.0 else " "
        
        print(f"{warning}{command:<11} {count:<8} {min_time:<10.3f} {avg_time:<10.3f} {max_time:<10.3f} {p95_time:<10.3f} {fails}")
    
    # Performance targets
    print("\n" + "="*60)
    print("Performance Targets:")
    print("  build:    <1.0s   (template + DB creation)")
    print("  parse:    <0.5s   (savegame decompression + DB insert)")
    print("  inject:   <0.02s  (context generation)")
    print("  validate: <0.5s   (path checking)")
    print("\nThreshold violations marked with !")

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Terra Invicta Advisory System')
    parser.add_argument('-v', '--verbose', action='count', default=0, 
                       help='Increase verbosity (-v INFO, -vv DEBUG)')
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    subparsers.add_parser('install', help='Interactive setup (auto-detect paths)')
    subparsers.add_parser('clean', help='Remove build directory')
    subparsers.add_parser('build', help='Build templates database')
    subparsers.add_parser('validate', help='Validate configuration and paths')
    subparsers.add_parser('perf', help='Display performance statistics')
    
    parse_parser = subparsers.add_parser('parse', help='Parse savegame')
    parse_parser.add_argument('--date', required=True, help='Date (YYYY-M-D)')
    
    inject_parser = subparsers.add_parser('inject', help='Generate context')
    inject_parser.add_argument('--date', required=True, help='Date (YYYY-M-D)')
    
    run_parser = subparsers.add_parser('run', help='Launch KoboldCpp')
    run_parser.add_argument('--date', required=True, help='Date (YYYY-M-D)')
    run_parser.add_argument('--quality', choices=['base', 'max', 'nuclear', 'ridiculous', 'ludicrous'],
                           help='Model quality tier (default: base or KOBOLDCPP_QUALITY from .env)')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    if not args.command:
        parser.print_help()
        return 1
    
    commands = {
        'install': cmd_install,
        'clean': cmd_clean,
        'build': cmd_build,
        'validate': cmd_validate,
        'perf': cmd_perf,
        'parse': cmd_parse,
        'inject': cmd_inject,
        'run': cmd_run
    }
    
    commands[args.command](args)

if __name__ == '__main__':
    main()
