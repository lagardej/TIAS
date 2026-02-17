"""
Research domain extractor: finished techs, global research state.
"""

from pathlib import Path


def write_research(db_path: Path, out: Path, helpers: dict):
    """Extract research game state.
    
    Args:
        db_path: Path to savegame DB
        out: Output file path
        helpers: Dict of shared helper functions
    """
    _load_gs = helpers['load_gs']
    
    grs_list = _load_gs(db_path, 'PavonisInteractive.TerraInvicta.TIGlobalResearchState')
    grs = grs_list[0]['Value'] if grs_list else {}

    lines = ["# RESEARCH STATE", ""]

    finished = grs.get('finishedTechsNames', [])
    lines.append(f"## Completed Technologies ({len(finished)} total)")
    for tech in sorted(finished):
        lines.append(f"  {tech}")

    projects = grs.get('finishedOneTimeOnlyProjectNames', [])
    if projects:
        lines += ["", f"## Completed One-Time Projects ({len(projects)})"]
        for p in sorted(projects):
            lines.append(f"  {p}")

    out.write_text("\n".join(lines), encoding='utf-8')
    return out.stat().st_size // 1024
