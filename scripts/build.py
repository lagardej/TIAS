#!/usr/bin/env python3
"""
Build script for Terra Invicta Advisory System

Processes source files and game templates into optimized runtime artifacts:
- src/actors/*/spec.toml + background.txt + CSVs → build/actors/*.json
- Game templates → build/.buildinfo (indexed, not copied)
- Generates build/.buildinfo with version tracking

Usage:
    python3 scripts/build.py [--force]
    
Options:
    --force    Force rebuild even if sources haven't changed
"""

import json
import os
import sys
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Python 3.11+ has tomllib built-in, earlier needs toml package
try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
        # toml package uses .load() not .loads()
        tomllib.loads = tomllib.loads if hasattr(tomllib, 'loads') else lambda s: tomllib.loads(s)
    except ImportError:
        print("ERROR: TOML parser not found")
        print("Python 3.11+: tomllib is built-in")
        print("Earlier Python: pip install toml --break-system-packages")
        sys.exit(1)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_env() -> Dict[str, str]:
    """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / ".env"
    env = {}
    
    if not env_path.exists():
        print(f"ERROR: .env file not found at {env_path}")
        print("Copy .env.dist to .env and configure your paths")
        sys.exit(1)
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
    
    return env


def get_file_hash(filepath: Path) -> str:
    """Calculate SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_actor_spec(actor_dir: Path) -> Dict:
    """Load actor specification from TOML file"""
    spec_path = actor_dir / "spec.toml"
    
    if not spec_path.exists():
        raise FileNotFoundError(f"Missing spec.toml in {actor_dir}")
    
    with open(spec_path, 'rb') as f:
        spec = tomllib.load(f)
    
    return spec


def load_actor_background(actor_dir: Path) -> str:
    """Load actor background prose"""
    bg_path = actor_dir / "background.txt"
    
    if not bg_path.exists():
        return ""
    
    with open(bg_path) as f:
        return f.read().strip()


def load_csv_data(csv_path: Path) -> List[Dict]:
    """Load CSV file into list of dicts"""
    if not csv_path.exists():
        return []
    
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_actor(actor_dir: Path) -> Dict:
    """
    Build complete actor data from directory
    
    Combines:
    - spec.toml (structured metadata)
    - background.txt (prose)
    - openers.csv (CODEX opener variations)
    - reactions.csv (spectator reactions)
    
    Returns optimized JSON structure
    """
    actor_name = actor_dir.name
    
    # Skip template directory
    if actor_name.startswith('_'):
        return None
    
    print(f"Building {actor_name}...")
    
    # Load all components
    spec = load_actor_spec(actor_dir)
    background = load_actor_background(actor_dir)
    openers = load_csv_data(actor_dir / "openers.csv")
    reactions = load_csv_data(actor_dir / "reactions.csv")
    
    # Build optimized structure
    actor_data = {
        "name": spec.get("name", actor_name),
        "display_name": spec.get("display_name", ""),
        "identity": {
            "age": spec.get("age", ""),
            "nationality": spec.get("nationality", ""),
            "profession": spec.get("profession", "")
        },
        "traits": [t.strip() for t in spec.get("traits", "").split(",") if t.strip()],
        "domain": {
            "primary": spec.get("domain_primary", ""),
            "secondary": spec.get("domain_secondary", ""),
            "keywords": [k.strip() for k in spec.get("domain_keywords", "").split(",") if k.strip()]
        },
        "spectator": {
            "probability": spec.get("spectator_probability", 0.15),
            "constraint": spec.get("spectator_constraint", ""),
            "style": spec.get("spectator_style", "")
        },
        "tiers": {
            "tier_1": {
                "scope": spec.get("tier_1_scope", ""),
                "can_discuss": spec.get("tier_1_can_discuss", ""),
                "cannot_discuss": spec.get("tier_1_cannot_discuss", "")
            },
            "tier_2": {
                "scope": spec.get("tier_2_scope", ""),
                "can_discuss": spec.get("tier_2_can_discuss", ""),
                "cannot_discuss": spec.get("tier_2_cannot_discuss", "")
            },
            "tier_3": {
                "scope": spec.get("tier_3_scope", ""),
                "can_discuss": spec.get("tier_3_can_discuss", ""),
                "cannot_discuss": spec.get("tier_3_cannot_discuss", "")
            }
        },
        "errors": {
            "missing_data": spec.get("error_missing_data", ""),
            "out_of_tier_1": spec.get("error_out_of_tier_1", ""),
            "out_of_tier_2": spec.get("error_out_of_tier_2", ""),
            "domain_mismatch": spec.get("error_domain_mismatch", "")
        },
        "background": background,
        "fluff": {
            "openers": openers,
            "reactions": reactions
        },
        "source_dir": str(actor_dir)
    }
    
    # Validate required fields
    if not actor_data["domain"]["primary"]:
        print(f"  WARNING: No primary domain defined")
    
    if not openers:
        print(f"  WARNING: No openers defined")
    
    if not reactions:
        print(f"  WARNING: No reactions defined")
    
    return actor_data


def build_actors(src_dir: Path, build_dir: Path) -> Dict[str, str]:
    """Build optimized actor JSON files from source directories"""
    actors_src = src_dir / "actors"
    actors_build = build_dir / "actors"
    actors_build.mkdir(parents=True, exist_ok=True)
    
    if not actors_src.exists():
        print(f"WARNING: Actor source directory not found: {actors_src}")
        return {}
    
    built_files = {}
    
    for actor_dir in sorted(actors_src.iterdir()):
        if not actor_dir.is_dir():
            continue
        
        try:
            actor_data = build_actor(actor_dir)
            
            if actor_data is None:
                continue  # Skip templates
            
            # Write optimized JSON
            output_file = actors_build / f"{actor_data['name']}.json"
            with open(output_file, 'w') as f:
                json.dump(actor_data, f, indent=2)
            
            built_files[str(actor_dir)] = get_file_hash(output_file)
            print(f"  -> {output_file}")
            
        except Exception as e:
            print(f"  ERROR building {actor_dir.name}: {e}")
            continue
    
    return built_files


def parse_localization_file(loc_file: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse .en localization file into dict[dataName][field] = value
    
    Format: TemplateType.field.dataName=value
    Example: TITraitTemplate.displayName.Criminal=Criminal
    """
    localizations = {}
    
    with open(loc_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            parts = key.split('.')
            
            if len(parts) >= 3:
                # template_type.field.dataName
                field = parts[1]  # displayName, description, etc.
                data_name = '.'.join(parts[2:])  # Handle dataNames with dots
                
                if data_name not in localizations:
                    localizations[data_name] = {}
                
                localizations[data_name][field] = value
    
    return localizations


def merge_localization(template_data, localizations: Dict[str, Dict[str, str]]):
    """
    Merge localization strings into template data recursively
    
    Replaces displayNameKey/descriptionKey with actual text
    """
    if isinstance(template_data, list):
        return [merge_localization(item, localizations) for item in template_data]
    
    if not isinstance(template_data, dict):
        return template_data
    
    merged = {}
    for key, value in template_data.items():
        # Recursively merge nested structures
        if isinstance(value, (dict, list)):
            merged[key] = merge_localization(value, localizations)
        else:
            merged[key] = value
    
    # Merge localization for this item if it has dataName
    data_name = merged.get('dataName')
    if data_name:
        if data_name in localizations:
            loc = localizations[data_name]
            
            # Add displayName from localization
            if 'displayName' in loc:
                merged['displayName'] = loc['displayName']
            
            # Add description from localization
            if 'description' in loc:
                merged['description'] = loc['description']
    
    return merged


def build_templates(game_install_dir: Path, build_dir: Path) -> Dict[str, str]:
    """
    Build optimized template files with merged localization
    
    Reads templates + localization, merges, outputs to build/templates/
    """
    templates_dir = game_install_dir / "TerraInvicta_Data/StreamingAssets/Templates"
    loc_dir = game_install_dir / "TerraInvicta_Data/StreamingAssets/Localization/en"
    templates_build = build_dir / "templates"
    templates_build.mkdir(parents=True, exist_ok=True)
    
    if not templates_dir.exists():
        print(f"WARNING: Templates directory not found: {templates_dir}")
        return {}
    
    if not loc_dir.exists():
        print(f"WARNING: Localization directory not found: {loc_dir}")
        return {}
    
    built_files = {}
    
    # Process each template
    for template_file in sorted(templates_dir.glob("*.json")):
        template_name = template_file.stem
        loc_file = loc_dir / f"{template_name}.en"
        
        try:
            # Load template
            with open(template_file, encoding='utf-8') as f:
                template_data = json.load(f)
            
            # Load corresponding localization if exists
            localizations = {}
            if loc_file.exists():
                localizations = parse_localization_file(loc_file)
                if template_name == "TITraitTemplate":
                    print(f"  DEBUG: Loaded {len(localizations)} localizations for {template_name}")
                    if 'Affluent' in localizations:
                        print(f"  DEBUG: Affluent loc = {localizations['Affluent']}")
                    else:
                        print(f"  DEBUG: Affluent NOT in localizations")
            
            # Merge
            merge_count = [0]  # Counter as list to modify in nested function
            
            def merge_with_count(data, locs):
                result = merge_localization(data, locs)
                # Count successful merges
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict) and 'dataName' in item and item['dataName'] in locs:
                            merge_count[0] += 1
                return result
            
            merged_data = merge_with_count(template_data, localizations)
            
            if template_name == "TITraitTemplate":
                print(f"  DEBUG: Merged {merge_count[0]} items with localization")
            
            # Write to build
            output_file = templates_build / template_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, indent=2, ensure_ascii=False)
            
            built_files[str(template_file)] = get_file_hash(output_file)
            print(f"  -> {template_name}")
            
        except Exception as e:
            print(f"  ERROR: {template_name}: {e}")
            continue
    
    return built_files


def create_buildinfo(build_dir: Path, env: Dict, built_files: Dict[str, str], 
                     template_index: Dict[str, Dict]):
    """Create .buildinfo file with version tracking"""
    buildinfo = {
        "build_timestamp": datetime.utcnow().isoformat() + "Z",
        "game_version": env.get('GAME_VERSION', 'unknown'),
        "game_install_path": env.get('GAME_INSTALL_DIR', 'unknown'),
        "dependencies": {
            "templates_dir": "TerraInvicta_Data/StreamingAssets/Templates",
            "localization_dir": "TerraInvicta_Data/StreamingAssets/Localization/en"
        },
        "built_files": built_files,
        "templates_indexed": len(template_index),
        "template_index": template_index,
        "note": "This file is auto-generated by build.py. Do not edit manually."
    }
    
    buildinfo_path = build_dir / ".buildinfo"
    with open(buildinfo_path, 'w') as f:
        json.dump(buildinfo, f, indent=2)
    
    print(f"\nOK Build info: {buildinfo_path}")


def main():
    """Main build process"""
    print("Terra Invicta Advisory System - Build Script")
    print("=" * 60)
    
    # Load environment
    env = load_env()
    
    # Setup paths
    project_root = Path(__file__).parent.parent
    src_dir = project_root / env.get('SRC_DIR', './src').lstrip('./')
    build_dir = project_root / env.get('BUILD_DIR', './build').lstrip('./')
    game_install_dir = Path(env.get('GAME_INSTALL_DIR', ''))
    
    if not src_dir.exists():
        print(f"ERROR: Source directory not found: {src_dir}")
        sys.exit(1)
    
    # Create build directory
    build_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSource: {src_dir}")
    print(f"Build:  {build_dir}")
    print(f"Game:   {game_install_dir}")
    print()
    
    # Build actors
    print("Building actors from source directories...")
    actor_files = build_actors(src_dir, build_dir)
    print(f"OK Built {len(actor_files)} actor files")
    
    # Build templates with merged localization
    print("\nBuilding templates with localization...")
    template_files = build_templates(game_install_dir, build_dir)
    print(f"OK Built {len(template_files)} template files")
    
    # Combine all built files
    all_built = {**actor_files, **template_files}
    
    # Create buildinfo
    print("\nCreating build metadata...")
    create_buildinfo(build_dir, env, all_built, {})
    
    print("\n" + "=" * 60)
    print(f"OK Build complete!")
    print(f"  Game version: {env.get('GAME_VERSION', 'unknown')}")
    print(f"  Artifacts: {build_dir}")
    print(f"  Actors: {len(actor_files)}")
    print(f"  Templates: {len(template_files)}")
    print(f"  Total: {len(all_built)} files")


if __name__ == '__main__':
    main()
