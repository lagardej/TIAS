#!/usr/bin/env python3
"""
CODEX Snapshot Manager for Terra Invicta
Automates snapshot generation, archival, and delta reporting

USAGE:
    python3 codex_manager.py

COMMANDS:
    snapshot <game_file.json.gz> <game_date>  - Generate and save snapshot
    delta <date_from> <date_to>                - Generate delta report between dates
    list                                       - Show all saved snapshots
    exit                                       - Quit

EXAMPLES:
    snapshot terra_invicta_save.json.gz "2025-03-15"
    delta "2025-03-10" "2025-03-15"
    list

REQUIREMENTS:
    - KoboldCPP running at http://localhost:5001
    - Python requests library (pip3 install requests --user)

OUTPUT:
    Snapshots saved to: ~/terra_invicta_snapshots/
"""

import json
import gzip
import os
import sys
from datetime import datetime
from pathlib import Path
import requests

# Configuration
KOBOLDCPP_URL = "http://localhost:5001/api/v1/generate"
SNAPSHOT_DIR = Path.home() / "terra_invicta" / "snapshots"
RULESET_FILE = Path.home() / "terra_invicta" / "reference" / "ruleset.txt"

# Advisory Council Ruleset
RULESET = """## Advisory Council Ruleset

**Entities**
AI advisors. Direct output. No filler.

**TERRA — Terrestrial Economic & Regime Resource Arbiter**
Earth domain: nations, CPs, investments, stability, unification, missions.

**ASTRA — Advanced Space Tactics & Resource Allocation**
Space domain: Boost, MC, stations, bases, fleets, mining, construction.

**CODEX — Chronological Operational Data & Event eXtractor**
Primary duty: Archive game state data.
Logs confirmed state only. Chronological. No analysis.
Generates compact, lossless snapshots (yearly or on-demand).
Maintains versioned archives with turn timestamps.
Provides delta reports between snapshots when queried.

**No Cheating Rule**
CRITICAL: Only use data visible to the player at query time.
- No future events or unrevealed mechanics
- No enemy intel unless obtained through espionage/detection
- Flag when insufficient intel prevents analysis
- State "INSUFFICIENT DATA" rather than guess

**Accuracy**
No speculation. Separate fact from projection. State limits. Quantify constraints. Challenge false claims.

**Sources**
Primary: TI Wiki, user-provided game state.
Secondary: validated image data.
Primary overrides secondary.

**Data Discipline**
Flag missing or inconsistent data.
Request required inputs before concluding.
Include units for numeric values.
"""


class CODEXManager:
    def __init__(self):
        self.snapshot_dir = SNAPSHOT_DIR
        self.snapshot_dir.mkdir(exist_ok=True)
        self.ruleset = RULESET
        
    def load_game_data(self, filepath):
        """Load game data from gzip JSON file"""
        try:
            with gzip.open(filepath, 'rt') as f:
                return json.load(f)
        except Exception as e:
            return None
            
    def call_koboldcpp(self, prompt, max_length=2000):
        """Send request to KoboldCPP API"""
        try:
            response = requests.post(KOBOLDCPP_URL, json={
                'prompt': prompt,
                'max_length': max_length,
                'temperature': 0.7,
                'top_p': 0.9,
            }, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                return result['results'][0]['text']
            else:
                return None
        except Exception as e:
            return None
    
    def generate_snapshot(self, game_data, game_date):
        """Generate snapshot via CODEX"""
        # Prepare compact game data representation
        data_str = json.dumps(game_data, indent=2)[:5000]  # Limit size
        
        prompt = f"""{self.ruleset}

Current game state (date: {game_date}):
{data_str}

CODEX: Generate compact snapshot for {game_date}. Include only essential state data."""
        
        snapshot = self.call_koboldcpp(prompt, max_length=3000)
        
        if snapshot:
            # Save snapshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Clean game_date for filename (remove spaces, slashes)
            date_clean = game_date.replace(' ', '_').replace('/', '-')
            filename = self.snapshot_dir / f"snapshot_{date_clean}_{timestamp}.json.gz"
            
            with gzip.open(filename, 'wt') as f:
                json.dump({
                    'game_date': game_date,
                    'snapshot_timestamp': timestamp,
                    'snapshot': snapshot,
                    'raw_data': game_data
                }, f, indent=2)
            
            return f"Snapshot {game_date} saved: {filename.name}"
        else:
            return f"ERROR: Failed to generate snapshot for {game_date}"
    
    def generate_delta(self, date_from, date_to):
        """Generate delta report between two snapshots"""
        # Find snapshot files
        snapshots = sorted(self.snapshot_dir.glob(f"snapshot_*.json.gz"))
        
        snap_from = None
        snap_to = None
        
        for snap_file in snapshots:
            with gzip.open(snap_file, 'rt') as f:
                data = json.load(f)
                if data['game_date'] == date_from:
                    snap_from = data
                if data['game_date'] == date_to:
                    snap_to = data
        
        if not snap_from or not snap_to:
            return f"ERROR: Missing snapshots ({date_from} or {date_to} not found)"
        
        prompt = f"""{self.ruleset}

Snapshot at {date_from}:
{snap_from['snapshot']}

Snapshot at {date_to}:
{snap_to['snapshot']}

CODEX: Generate delta report showing changes from {date_from} to {date_to}."""
        
        delta = self.call_koboldcpp(prompt, max_length=2000)
        
        if delta:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            date_from_clean = date_from.replace(' ', '_').replace('/', '-')
            date_to_clean = date_to.replace(' ', '_').replace('/', '-')
            filename = self.snapshot_dir / f"delta_{date_from_clean}_to_{date_to_clean}_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write(delta)
            
            return f"Delta report {date_from}→{date_to} archived: {filename.name}"
        else:
            return f"ERROR: Failed to generate delta report"
    
    def list_snapshots(self):
        """List all available snapshots"""
        snapshots = sorted(self.snapshot_dir.glob("snapshot_*.json.gz"))
        
        if not snapshots:
            return "No snapshots found"
        
        result = ["Available snapshots:"]
        for snap_file in snapshots:
            with gzip.open(snap_file, 'rt') as f:
                data = json.load(f)
                result.append(f"  {data['game_date']} - {snap_file.name}")
        
        return "\n".join(result)
    
def main():
    manager = CODEXManager()
    
    print("CODEX Manager for Terra Invicta")
    print("=" * 50)
    print("\nCommands:")
    print("  snapshot <game_file.json.gz> <game_date>")
    print("  delta <date_from> <date_to>")
    print("  list")
    print("  exit")
    print()
    
    while True:
        try:
            cmd = input("\n> ").strip().split(maxsplit=2)
            
            if not cmd:
                continue
                
            action = cmd[0].lower()
            
            if action == "exit":
                break
                
            elif action == "snapshot":
                if len(cmd) < 3:
                    print("Usage: snapshot <game_file.json.gz> <game_date>")
                    print("Example: snapshot savegame.json.gz '2025-03-15'")
                    continue
                
                game_file = cmd[1]
                game_date = cmd[2]
                
                game_data = manager.load_game_data(game_file)
                if game_data is None:
                    print(f"ERROR: Failed to load {game_file}")
                    continue
                
                print(manager.generate_snapshot(game_data, game_date))
                
            elif action == "delta":
                if len(cmd) < 3:
                    print("Usage: delta <date_from> <date_to>")
                    print("Example: delta '2025-03-10' '2025-03-15'")
                    continue
                    
                date_from = cmd[1]
                date_to = cmd[2]
                
                print(manager.generate_delta(date_from, date_to))
                
            elif action == "list":
                print(manager.list_snapshots())
                
            else:
                print(f"Unknown command: {action}")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    main()
