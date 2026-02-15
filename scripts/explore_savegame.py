#!/usr/bin/env python3
"""
Terra Invicta Savegame Explorer
Interactive exploration with CODEX advisor to build filter file

USAGE:
    python3 explore_savegame.py <savegame.json.gz>

COMMANDS:
    search <keyword>   - Find paths containing keyword
    select <path>      - Add path to filter list
    remove <path>      - Remove path from filter list
    show selected      - Show all selected paths
    save               - Save filter file and continue
    done/exit          - Save and exit

NATURAL LANGUAGE:
    You can also chat naturally with CODEX about the data structure:
    - "What data is available for nations?"
    - "Show me fleet-related paths"
    - "Which paths track resources?"

WORKFLOW:
    1. Run script with savegame file
    2. CODEX analyzes structure and shows overview
    3. Search for relevant paths or ask CODEX questions
    4. Select paths to include in filter
    5. Save and exit when complete

EXAMPLES:
    python3 explore_savegame.py game_save.json.gz
    
    You: search fleet
    CODEX: Found 15 paths matching 'fleet'...
    
    You: select fleets[].position
    CODEX: Added to filter list.
    
    You: done

REQUIREMENTS:
    - Python 3
    - Python requests library (pip3 install requests --user)
    - KoboldCPP running at http://localhost:5001

OUTPUT:
    Filter file: final_filters.txt
"""

import json
import gzip
import sys
from pathlib import Path
from collections import defaultdict
import requests

# Configuration
KOBOLDCPP_URL = "http://localhost:5001/api/v1/generate"
FILTER_OUTPUT = str(Path.home() / "terra_invicta" / "generated" / "final_filters.txt")

# Advisory Council Ruleset
RULESET = """## Advisory Council Ruleset

**CODEX — Chronological Operational Data & Event eXtractor**
Primary duty: Archive game state data.
Assist user in exploring savegame structure and identifying relevant data paths.
Logs confirmed state only. Chronological. No analysis.
Generates compact, lossless snapshots (yearly or on-demand).
Maintains versioned archives with turn timestamps.
Provides delta reports between snapshots when queried.

**Data Discipline**
Flag missing or inconsistent data.
Request required inputs before concluding.
Include units for numeric values.
"""


class SavegameExplorer:
    def __init__(self):
        self.data = None
        self.structure = {}
        self.selected_paths = []
        self.conversation_history = []
        
    def load_savegame(self, filepath):
        """Load and parse savegame"""
        try:
            print(f"Loading savegame: {filepath}")
            with gzip.open(filepath, 'rt') as f:
                self.data = json.load(f)
            print(f"Savegame loaded successfully")
            return True
        except Exception as e:
            print(f"ERROR: Failed to load savegame: {e}")
            return False
    
    def analyze_structure(self, obj, path="", max_depth=3, current_depth=0):
        """Recursively analyze JSON structure"""
        if current_depth >= max_depth:
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                self.structure[new_path] = type(value).__name__
                
                if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
                    self.analyze_structure(value, new_path, max_depth, current_depth + 1)
                    
        elif isinstance(obj, list) and len(obj) > 0:
            # Analyze first item as representative
            new_path = f"{path}[]"
            self.analyze_structure(obj[0], new_path, max_depth, current_depth + 1)
    
    def get_structure_summary(self, max_paths=100):
        """Get compact structure summary"""
        # Group by top-level keys
        grouped = defaultdict(list)
        for path in sorted(self.structure.keys())[:max_paths]:
            top_level = path.split('.')[0]
            grouped[top_level].append(path)
        
        summary = "Savegame structure (top-level keys):\n\n"
        for top_level, paths in grouped.items():
            summary += f"**{top_level}** ({len(paths)} paths)\n"
            for path in paths[:5]:  # Show first 5 paths per group
                summary += f"  - {path}\n"
            if len(paths) > 5:
                summary += f"  ... and {len(paths) - 5} more\n"
            summary += "\n"
        
        return summary
    
    def get_paths_by_keyword(self, keyword):
        """Find paths matching keyword"""
        keyword_lower = keyword.lower()
        matches = [
            path for path in self.structure.keys()
            if keyword_lower in path.lower()
        ]
        return matches
    
    def call_codex(self, user_message):
        """Send message to CODEX advisor"""
        # Build conversation context
        context = f"{RULESET}\n\n"
        
        # Add conversation history
        for msg in self.conversation_history[-10:]:  # Keep last 10 messages
            context += f"{msg['role']}: {msg['content']}\n\n"
        
        # Add current message
        context += f"User: {user_message}\n\nCODEX:"
        
        try:
            response = requests.post(KOBOLDCPP_URL, json={
                'prompt': context,
                'max_length': 500,
                'temperature': 0.7,
                'stop_sequence': ['\nUser:', '\nTERRA:', '\nASTRA:']
            }, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                codex_response = result['results'][0]['text'].strip()
                
                # Update conversation history
                self.conversation_history.append({
                    'role': 'User',
                    'content': user_message
                })
                self.conversation_history.append({
                    'role': 'CODEX',
                    'content': codex_response
                })
                
                return codex_response
            else:
                return f"ERROR: API returned status {response.status_code}"
                
        except Exception as e:
            return f"ERROR: {e}"
    
    def process_command(self, user_input):
        """Process user commands and queries"""
        cmd = user_input.lower().strip()
        
        # Special commands
        if cmd in ['exit', 'quit', 'done']:
            return 'EXIT'
        
        if cmd == 'show selected':
            if not self.selected_paths:
                return "CODEX: No paths selected yet."
            return f"CODEX: Selected paths ({len(self.selected_paths)}):\n" + "\n".join(f"  - {p}" for p in self.selected_paths)
        
        if cmd == 'save':
            return self.save_filters()
        
        if cmd.startswith('search '):
            keyword = cmd.replace('search ', '').strip()
            matches = self.get_paths_by_keyword(keyword)
            if not matches:
                return f"CODEX: No paths found matching '{keyword}'"
            
            result = f"CODEX: Found {len(matches)} paths matching '{keyword}':\n"
            for match in matches[:20]:  # Limit to 20 results
                result += f"  - {match}\n"
            if len(matches) > 20:
                result += f"  ... and {len(matches) - 20} more\n"
            return result
        
        if cmd.startswith('select '):
            path = cmd.replace('select ', '').strip()
            if path in self.structure:
                if path not in self.selected_paths:
                    self.selected_paths.append(path)
                    return f"CODEX: Added '{path}' to filter list."
                else:
                    return f"CODEX: '{path}' already selected."
            else:
                return f"CODEX: Path '{path}' not found in savegame structure."
        
        if cmd.startswith('remove '):
            path = cmd.replace('remove ', '').strip()
            if path in self.selected_paths:
                self.selected_paths.remove(path)
                return f"CODEX: Removed '{path}' from filter list."
            else:
                return f"CODEX: '{path}' not in filter list."
        
        # Otherwise, send to CODEX advisor
        # Add structure context for first message
        if len(self.conversation_history) == 0:
            structure_summary = self.get_structure_summary()
            enhanced_input = f"{structure_summary}\n\nUser question: {user_input}"
        else:
            enhanced_input = user_input
        
        return self.call_codex(enhanced_input)
    
    def save_filters(self):
        """Save selected paths to filter file"""
        if not self.selected_paths:
            return "CODEX: No paths selected. Nothing to save."
        
        try:
            filter_path = Path(FILTER_OUTPUT)
            # Ensure data directory exists
            filter_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filter_path, 'w') as f:
                f.write("# Terra Invicta Data Filters\n")
                f.write("# Generated by explore_savegame.py\n\n")
                for path in sorted(self.selected_paths):
                    f.write(f"{path}\n")
            
            return f"CODEX: Saved {len(self.selected_paths)} paths to {FILTER_OUTPUT}"
        except Exception as e:
            return f"ERROR: Failed to save filters: {e}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 explore_savegame.py <savegame.json.gz>")
        sys.exit(1)
    
    savegame_path = sys.argv[1]
    
    explorer = SavegameExplorer()
    
    # Load savegame
    if not explorer.load_savegame(savegame_path):
        sys.exit(1)
    
    # Analyze structure
    print("Analyzing savegame structure...")
    explorer.analyze_structure(explorer.data, max_depth=3)
    print(f"Found {len(explorer.structure)} data paths\n")
    
    print("=" * 60)
    print("CODEX Savegame Explorer")
    print("=" * 60)
    print("\nCommands:")
    print("  search <keyword>   - Find paths containing keyword")
    print("  select <path>      - Add path to filter list")
    print("  remove <path>      - Remove path from filter list")
    print("  show selected      - Show all selected paths")
    print("  save               - Save filter file and continue")
    print("  done/exit          - Save and exit")
    print("\nOr chat naturally with CODEX about the data structure.\n")
    
    # Interactive loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            response = explorer.process_command(user_input)
            
            if response == 'EXIT':
                # Save before exit
                save_result = explorer.save_filters()
                print(f"\n{save_result}")
                print("Goodbye!")
                break
            
            print(f"\n{response}")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Saving filters...")
            print(explorer.save_filters())
            break
        except Exception as e:
            print(f"\nERROR: {e}")


if __name__ == "__main__":
    main()
