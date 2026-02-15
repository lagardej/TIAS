#!/usr/bin/env python3
"""
Migrate actor markdown files to TOML/CSV structure

Converts:
- actor_*.md → actor/spec.toml + background.txt
- actor_*_fluff.md → actor/openers.csv + reactions.csv
"""

import re
import csv
from pathlib import Path
from typing import Dict, List, Tuple

def extract_markdown_section(content: str, section_name: str) -> str:
    """Extract content of a markdown section"""
    pattern = rf'^## {re.escape(section_name)}$(.*?)(?=^## |\Z)'
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""

def parse_background(content: str) -> Dict:
    """Parse background section for identity and prose"""
    bg_section = extract_markdown_section(content, "Background")
    
    # Extract age, nationality, profession
    age_match = re.search(r'\*\*Age:\*\*\s*([^\n]+)', bg_section)
    nat_match = re.search(r'\*\*Nationality:\*\*\s*([^\n]+)', bg_section)
    prof_match = re.search(r'\*\*Profession:\*\*\s*([^\n]+)', bg_section)
    
    # Remove identity lines, keep prose
    prose = bg_section
    for pattern in [r'\*\*Age:\*\*[^\n]+\n?', r'\*\*Nationality:\*\*[^\n]+\n?', r'\*\*Profession:\*\*[^\n]+\n?']:
        prose = re.sub(pattern, '', prose)
    prose = prose.strip()
    
    return {
        'age': age_match.group(1).strip() if age_match else "",
        'nationality': nat_match.group(1).strip() if nat_match else "",
        'profession': prof_match.group(1).strip() if prof_match else "",
        'prose': prose
    }

def parse_traits(content: str) -> List[str]:
    """Extract trait names from Traits section"""
    traits_section = extract_markdown_section(content, "Traits")
    
    # Extract trait names from numbered list
    trait_pattern = r'^\d+\.\s+\*\*([^*]+)\*\*'
    traits = re.findall(trait_pattern, traits_section, re.MULTILINE)
    
    return [t.strip() for t in traits]

def parse_domain(content: str) -> Dict:
    """Extract domain information"""
    domain_section = extract_markdown_section(content, "Domain & Expertise")
    
    primary_match = re.search(r'\*\*Primary Domain:\*\*\s*([^\n]+)', domain_section)
    secondary_match = re.search(r'\*\*Secondary Domains:\*\*\s*([^\n]+)', domain_section)
    
    # Extract keywords from "Handles queries about" section
    keywords = []
    if "Handles queries about:" in domain_section:
        handles_section = domain_section.split("Handles queries about:")[1].split("**")[0]
        keywords = [line.strip("- ").strip() for line in handles_section.split('\n') if line.strip().startswith('-')]
    
    return {
        'primary': primary_match.group(1).strip() if primary_match else "",
        'secondary': secondary_match.group(1).strip() if secondary_match else "",
        'keywords': keywords
    }

def parse_tier(content: str, tier_num: int) -> Dict:
    """Extract tier information"""
    tier_names = {
        1: "Tier 1 - Early Consolidation",
        2: "Tier 2 - Industrial Expansion",
        3: "Tier 3 - Strategic Confrontation"
    }
    
    tier_section = extract_markdown_section(content, tier_names[tier_num])
    
    # Extract scope
    scope_match = re.search(r'\*\*Scope:\*\*(.*?)(?=\*\*|$)', tier_section, re.DOTALL)
    scope = scope_match.group(1).strip() if scope_match else ""
    scope = ' '.join([line.strip("- ").strip() for line in scope.split('\n') if line.strip()])
    
    # Extract can discuss
    can_match = re.search(r'\*\*Can discuss:\*\*(.*?)(?=\*\*|$)', tier_section, re.DOTALL)
    can = can_match.group(1).strip() if can_match else ""
    can = ' '.join([line.strip("- ").strip() for line in can.split('\n') if line.strip()])
    
    # Extract cannot discuss
    cannot_match = re.search(r'\*\*Cannot discuss:\*\*(.*?)(?=\*\*|$)', tier_section, re.DOTALL)
    cannot = cannot_match.group(1).strip() if cannot_match else ""
    cannot = ' '.join([line.strip("- ").strip() for line in cannot.split('\n') if line.strip()])
    
    return {
        'scope': scope,
        'can_discuss': can,
        'cannot_discuss': cannot
    }

def parse_spectator(content: str) -> Dict:
    """Extract spectator behavior"""
    spec_section = extract_markdown_section(content, "Spectator Behavior")
    
    # Extract probability
    prob_match = re.search(r'\*\*Reaction Probability:\*\*\s*([0-9.]+)', spec_section)
    probability = float(prob_match.group(1)) if prob_match else 0.15
    
    # Extract constraint
    constraint = ""
    if "cannot react two queries in a row" in spec_section or "not_consecutive" in spec_section:
        constraint = "not_consecutive"
    
    # Extract style description
    style_match = re.search(r'\*\*Reaction Style:\*\*(.*?)(?=\*\*|$)', spec_section, re.DOTALL)
    style = style_match.group(1).strip() if style_match else ""
    style = ' '.join([line.strip("- ").strip() for line in style.split('\n') if line.strip()])
    
    return {
        'probability': probability,
        'constraint': constraint,
        'style': style
    }

def parse_errors(content: str) -> Dict:
    """Extract error messages"""
    error_section = extract_markdown_section(content, "Error Handling")
    
    errors = {
        'missing_data': "",
        'out_of_tier_1': "",
        'out_of_tier_2': "",
        'domain_mismatch': ""
    }
    
    # Look for specific error types
    if "Missing Data:" in error_section:
        missing = error_section.split("Missing Data:")[1].split("**")[0]
        errors['missing_data'] = missing.strip().split('\n')[0].strip("- \"")
    
    if "Tier 1:" in error_section:
        tier1 = error_section.split("Tier 1:")[1].split("**")[0] if "Tier 1:" in error_section else ""
        errors['out_of_tier_1'] = tier1.strip().split('\n')[0].strip("- \"")
    
    if "Tier 2:" in error_section:
        tier2 = error_section.split("Tier 2:")[1].split("**")[0] if "Tier 2:" in error_section else ""
        errors['out_of_tier_2'] = tier2.strip().split('\n')[0].strip("- \"")
    
    if "Domain Mismatch:" in error_section:
        domain = error_section.split("Domain Mismatch:")[1].split("**")[0]
        errors['domain_mismatch'] = domain.strip().split('\n')[0].strip("- \"")
    
    return errors

def parse_openers(fluff_content: str) -> List[Tuple[str, str, str]]:
    """Extract opener variations from fluff file"""
    opener_section = extract_markdown_section(fluff_content, "Opener Variations")
    
    openers = []
    for line in opener_section.split('\n'):
        # Match: 1. "Text" [mood]
        match = re.match(r'^\d+\.\s+"([^"]+)"(?:\s+\[([^\]]+)\])?', line)
        if match:
            text = match.group(1)
            mood_raw = match.group(2) if match.group(2) else "neutral"
            # Extract just the mood word
            mood = mood_raw.split(',')[0].strip()
            openers.append((text, mood, ""))
    
    return openers

def parse_reactions(fluff_content: str) -> List[Tuple[str, str, str, str]]:
    """Extract spectator reactions from fluff file"""
    reaction_section = extract_markdown_section(fluff_content, "Spectator Reactions")
    
    reactions = []
    current_category = "general"
    
    for line in reaction_section.split('\n'):
        # Category header: **Category Name:**
        if line.startswith('**') and line.endswith(':**'):
            current_category = line.strip('*:').lower().replace(' ', '_')
            continue
        
        # Numbered reaction
        match = re.match(r'^\d+\.\s+"([^"]+)"(?:\s+\[([^\]]+)\])?', line)
        if match:
            text = match.group(1)
            mode_raw = match.group(2) if match.group(2) else "neutral"
            mode = mode_raw.split(',')[0].strip() if mode_raw else "neutral"
            
            # Infer trigger from category
            trigger = "any"
            if current_category == "professional":
                trigger = "domain"
            elif "trolling" in current_category:
                trigger = "valentina_present"
            
            reactions.append((text, current_category, mode, trigger))
        
        # Stage direction: [text]
        elif line.strip().startswith('[') and ']' in line:
            text = line.strip()
            reactions.append((text, current_category, "neutral", "any"))
    
    return reactions

def migrate_actor(actor_name: str, src_dir: Path):
    """Migrate one actor from markdown to TOML/CSV"""
    spec_file = src_dir / f"actor_{actor_name}.md"
    fluff_file = src_dir / f"actor_{actor_name}_fluff.md"
    
    if not spec_file.exists():
        print(f"  WARNING: {spec_file} not found, skipping")
        return
    
    print(f"Migrating {actor_name}...")
    
    # Read files
    with open(spec_file) as f:
        spec_content = f.read()
    
    fluff_content = ""
    if fluff_file.exists():
        with open(fluff_file) as f:
            fluff_content = f.read()
    
    # Extract display name from header
    header_match = re.search(r'^# (.+)$', spec_content, re.MULTILINE)
    display_name = header_match.group(1).strip() if header_match else actor_name.title()
    
    # Parse all sections
    bg_data = parse_background(spec_content)
    traits = parse_traits(spec_content)
    domain = parse_domain(spec_content)
    tier1 = parse_tier(spec_content, 1)
    tier2 = parse_tier(spec_content, 2)
    tier3 = parse_tier(spec_content, 3)
    spectator = parse_spectator(spec_content)
    errors = parse_errors(spec_content)
    
    # Create actor directory
    actor_dir = src_dir / actor_name
    actor_dir.mkdir(exist_ok=True)
    
    # Write spec.toml
    with open(actor_dir / "spec.toml", 'w') as f:
        f.write(f"# {display_name} - Actor Specification\n\n")
        f.write("# Identity\n")
        f.write(f'name = "{actor_name}"\n')
        f.write(f'display_name = "{display_name}"\n')
        f.write(f'age = "{bg_data["age"]}"\n')
        f.write(f'nationality = "{bg_data["nationality"]}"\n')
        f.write(f'profession = "{bg_data["profession"]}"\n\n')
        
        f.write("# Traits\n")
        f.write(f'traits = "{", ".join(traits)}"\n\n')
        
        f.write("# Domain\n")
        f.write(f'domain_primary = "{domain["primary"]}"\n')
        f.write(f'domain_secondary = "{domain.get("secondary", "")}"\n')
        keywords_str = ", ".join(domain["keywords"][:10])  # Limit keywords
        f.write(f'domain_keywords = "{keywords_str}"\n\n')
        
        f.write("# Spectator Behavior\n")
        f.write(f'spectator_probability = {spectator["probability"]}\n')
        f.write(f'spectator_constraint = "{spectator["constraint"]}"\n')
        f.write(f'spectator_style = "{spectator["style"]}"\n\n')
        
        f.write("# Tier 1 - Early Consolidation\n")
        f.write(f'tier_1_scope = "{tier1["scope"]}"\n')
        f.write(f'tier_1_can_discuss = "{tier1["can_discuss"]}"\n')
        f.write(f'tier_1_cannot_discuss = "{tier1["cannot_discuss"]}"\n\n')
        
        f.write("# Tier 2 - Industrial Expansion\n")
        f.write(f'tier_2_scope = "{tier2["scope"]}"\n')
        f.write(f'tier_2_can_discuss = "{tier2["can_discuss"]}"\n')
        f.write(f'tier_2_cannot_discuss = "{tier2["cannot_discuss"]}"\n\n')
        
        f.write("# Tier 3 - Strategic Confrontation\n")
        f.write(f'tier_3_scope = "{tier3["scope"]}"\n')
        f.write(f'tier_3_can_discuss = "{tier3["can_discuss"]}"\n')
        f.write(f'tier_3_cannot_discuss = "{tier3["cannot_discuss"]}"\n\n')
        
        f.write("# Error Messages\n")
        f.write(f'error_missing_data = "{errors["missing_data"]}"\n')
        f.write(f'error_out_of_tier_1 = "{errors["out_of_tier_1"]}"\n')
        f.write(f'error_out_of_tier_2 = "{errors["out_of_tier_2"]}"\n')
        f.write(f'error_domain_mismatch = "{errors["domain_mismatch"]}"\n')
    
    # Write background.txt
    with open(actor_dir / "background.txt", 'w') as f:
        f.write(bg_data['prose'])
    
    # Write openers.csv
    if fluff_content:
        openers = parse_openers(fluff_content)
        with open(actor_dir / "openers.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'mood', 'note'])
            writer.writerows(openers)
        
        # Write reactions.csv
        reactions = parse_reactions(fluff_content)
        with open(actor_dir / "reactions.csv", 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['text', 'category', 'mode', 'trigger'])
            writer.writerows(reactions)
        
        print(f"  ✓ Created {actor_name}/ with {len(openers)} openers, {len(reactions)} reactions")
    else:
        print(f"  ⚠ No fluff file found for {actor_name}")

def main():
    """Migrate all actors"""
    src_dir = Path(__file__).parent.parent / "src" / "actors"
    
    # Find all actor spec files
    actors = []
    for spec_file in src_dir.glob("actor_*.md"):
        if '_fluff' not in spec_file.name:
            actor_name = spec_file.stem.replace('actor_', '')
            actors.append(actor_name)
    
    print(f"Found {len(actors)} actors to migrate: {', '.join(actors)}")
    print()
    
    for actor_name in sorted(actors):
        if actor_name == 'chuck':
            print(f"Skipping {actor_name} (already migrated)")
            continue
        migrate_actor(actor_name, src_dir)
    
    print()
    print("Migration complete!")
    print("Run: python3 scripts/build.py")

if __name__ == '__main__':
    main()
