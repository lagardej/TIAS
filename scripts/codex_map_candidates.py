#!/usr/bin/env python3
"""
CODEX Candidate Mapper
Analyzes savegame structure and generates candidate paths based on advisor requirements

USAGE:
    python3 codex_map_candidates.py <savegame.json.gz> <requirements.txt>

ARGUMENTS:
    savegame.json.gz   - Terra Invicta savegame file (gzip compressed JSON)
    requirements.txt   - Advisor requirements file

REQUIREMENTS FILE FORMAT:
    [TERRA]
    nation resources
    control points
    stability metrics
    
    [ASTRA]
    fleet positions
    station inventories

WORKFLOW:
    1. Chat with TERRA/ASTRA in KoboldCPP to gather requirements
    2. Create requirements.txt with advisor needs
    3. Run this script to map requirements to savegame paths
    4. Review candidates in KoboldCPP chat
    5. Use codex_validator.py to validate paths

EXAMPLES:
    python3 codex_map_candidates.py game_save.json.gz requirements.txt

REQUIREMENTS:
    - Python 3
    - Python requests library (pip3 install requests --user)
    - KoboldCPP running at http://localhost:5001

OUTPUT:
    - candidate_paths.txt (saved to disk)
    - Candidates injected into KoboldCPP chat context
"""

import json
import gzip
import sys
from pathlib import Path
from collections import defaultdict
import requests

# Configuration
KOBOLDCPP_URL = "http://localhost:5001/api/v1/generate"
CANDIDATES_FILE = str(Path.home() / "terra_invicta" / "generated" / "candidate_paths.txt")

# Advisory Council Ruleset
RULESET = """## Advisory Council Ruleset

**CODEX — Chronological Operational Data & Event eXtractor**
Primary duty: Archive game state data.
Analyze savegame structure and map advisor requirements to data paths.
Logs confirmed state only. No analysis.

**Data Discipline**
Flag missing or inconsistent data.
Include units for numeric values.
"""


class CODEXCandidateMapper:
    def __init__(self):
        self.data = None
        self.structure = {}
        self.requirements = {}
        
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
    
    def load_requirements(self, filepath):
        """Load advisor requirements file"""
        try:
            print(f"Loading requirements: {filepath}")
            with open(filepath, 'r') as f:
                current_advisor = None
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        current_advisor = line[1:-1]
                        self.requirements[current_advisor] = []
                    elif current_advisor:
                        self.requirements[current_advisor].append(line)
            
            print(f"Loaded requirements for: {', '.join(self.requirements.keys())}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to load requirements: {e}")
            return False
    
    def analyze_structure(self, obj, path="", max_depth=4, current_depth=0):
        """Recursively analyze JSON structure"""
        if current_depth >= max_depth:
            return
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                
                # Store type and sample value
                if isinstance(value, (str, int, float, bool)):
                    self.structure[new_path] = {
                        'type': type(value).__name__,
                        'sample': value if not isinstance(value, str) or len(str(value)) < 50 else str(value)[:50] + '...'
                    }
                elif isinstance(value, list):
                    self.structure[new_path] = {
                        'type': 'list',
                        'length': len(value)
                    }
                elif isinstance(value, dict):
                    self.structure[new_path] = {
                        'type': 'dict',
                        'keys': len(value)
                    }
                
                if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
                    self.analyze_structure(value, new_path, max_depth, current_depth + 1)
                    
        elif isinstance(obj, list) and len(obj) > 0:
            # Analyze first item as representative
            new_path = f"{path}[]"
            self.analyze_structure(obj[0], new_path, max_depth, current_depth + 1)
    
    def find_candidates_for_requirement(self, requirement):
        """Find candidate paths matching a requirement"""
        requirement_lower = requirement.lower()
        keywords = requirement_lower.split()
        
        candidates = []
        
        for path, info in self.structure.items():
            path_lower = path.lower()
            
            # Score path based on keyword matches
            score = 0
            for keyword in keywords:
                if keyword in path_lower:
                    score += 1
            
            if score > 0:
                candidates.append({
                    'path': path,
                    'score': score,
                    'info': info
                })
        
        # Sort by score (descending)
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates[:10]  # Return top 10 candidates
    
    def generate_candidates(self):
        """Generate candidate paths for all requirements"""
        print("\nAnalyzing savegame structure...")
        self.analyze_structure(self.data, max_depth=4)
        print(f"Found {len(self.structure)} data paths\n")
        
        all_candidates = {}
        
        for advisor, requirements in self.requirements.items():
            print(f"\nMapping {advisor} requirements:")
            all_candidates[advisor] = {}
            
            for req in requirements:
                candidates = self.find_candidates_for_requirement(req)
                all_candidates[advisor][req] = candidates
                
                print(f"\n  Requirement: {req}")
                if candidates:
                    print(f"  Found {len(candidates)} candidates:")
                    for i, cand in enumerate(candidates[:5], 1):
                        info_str = f"({cand['info']['type']}"
                        if 'sample' in cand['info']:
                            info_str += f", sample: {cand['info']['sample']}"
                        elif 'length' in cand['info']:
                            info_str += f", length: {cand['info']['length']}"
                        info_str += ")"
                        print(f"    {i}. {cand['path']} {info_str}")
                else:
                    print(f"  No candidates found")
        
        return all_candidates
    
    def save_candidates(self, candidates):
        """Save candidates to file"""
        try:
            candidates_path = Path(CANDIDATES_FILE)
            # Ensure data directory exists
            candidates_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(candidates_path, 'w') as f:
                f.write("# Terra Invicta Candidate Data Paths\n")
                f.write("# Generated by CODEX candidate mapper\n\n")
                
                for advisor, requirements in candidates.items():
                    f.write(f"\n[{advisor}]\n")
                    for req, cands in requirements.items():
                        f.write(f"\n# Requirement: {req}\n")
                        for cand in cands:
                            f.write(f"# {cand['path']}\n")
            
            print(f"\nCandidates saved to: {CANDIDATES_FILE}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to save candidates: {e}")
            return False
    
    def inject_to_chat(self, candidates):
        """Inject candidate paths into KoboldCPP chat for validation"""
        try:
            # Format candidates for chat
            message = f"{RULESET}\n\n"
            message += "CODEX: Candidate data paths mapped to advisor requirements:\n\n"
            
            for advisor, requirements in candidates.items():
                message += f"**{advisor}**\n"
                for req, cands in requirements.items():
                    message += f"\nRequirement: {req}\n"
                    if cands:
                        message += "Candidates:\n"
                        for i, cand in enumerate(cands[:5], 1):
                            message += f"  {i}. {cand['path']}\n"
                    else:
                        message += "  No candidates found\n"
                message += "\n"
            
            message += "\nCODEX: Ready for validation. Use validator to include/exclude paths."
            
            # Send to KoboldCPP
            response = requests.post(KOBOLDCPP_URL, json={
                'prompt': message,
                'max_length': 1,
                'temperature': 0.1,
            }, timeout=10)
            
            if response.status_code == 200:
                print("\n✓ Candidates injected into chat context")
                return True
            else:
                print(f"ERROR: API returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"ERROR: Failed to inject candidates: {e}")
            return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 codex_map_candidates.py <savegame.json.gz> <requirements.txt>")
        print("\nRequirements file format:")
        print("[TERRA]")
        print("nation resources")
        print("control points")
        print("\n[ASTRA]")
        print("fleet positions")
        print("station capacities")
        sys.exit(1)
    
    savegame_path = sys.argv[1]
    requirements_path = sys.argv[2]
    
    mapper = CODEXCandidateMapper()
    
    # Load inputs
    if not mapper.load_savegame(savegame_path):
        sys.exit(1)
    
    if not mapper.load_requirements(requirements_path):
        sys.exit(1)
    
    # Generate candidates
    candidates = mapper.generate_candidates()
    
    # Save to file
    mapper.save_candidates(candidates)
    
    # Inject to chat
    print("\nInjecting candidates to chat...")
    mapper.inject_to_chat(candidates)
    
    print("\nNext steps:")
    print("1. Review candidates in KoboldCPP chat")
    print("2. Run: python3 codex_validator.py")
    print("3. Validate paths using include/exclude commands")


if __name__ == "__main__":
    main()
