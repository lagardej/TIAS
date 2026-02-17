"""
Play command - Launch KoboldCpp with selected model quality
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

from src.core.core import load_env, get_project_root


def _assemble_context(generated_dir: Path) -> str:
    """Concatenate all context and gamestate files into one string for KoboldCpp."""
    pinned_first = ['context_system.txt']
    pinned_last  = ['context_codex.txt',
                    'gamestate_earth.txt',
                    'gamestate_space.txt',
                    'gamestate_intel.txt',
                    'gamestate_research.txt']
    pinned = set(pinned_first + pinned_last)

    all_context = sorted(generated_dir.glob('context_*.txt'))
    middle = [f for f in all_context if f.name not in pinned]

    ordered = (
        [generated_dir / n for n in pinned_first if (generated_dir / n).exists()] +
        middle +
        [generated_dir / n for n in pinned_last if (generated_dir / n).exists()]
    )

    parts = []
    for path in ordered:
        content = path.read_text(encoding='utf-8').strip()
        if content:
            parts.append(content)
            logging.info(f"  + {path.name} ({len(content)} chars)")

    return "\n\n".join(parts)


def cmd_play(args):
    """Launch KoboldCpp"""
    # Import preset here to avoid circular dependency
    from src.preset.command import cmd_preset
    from src.core.date_utils import parse_flexible_date

    # Generate domain context files first
    cmd_preset(args)

    env = load_env()
    project_root = get_project_root()
    
    # Read from date-specific directory: generated/{iso_date}/
    _, iso_date = parse_flexible_date(args.date)
    generated_dir = project_root / "generated" / iso_date
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

    # Assemble context into a temp file for KoboldCpp --memf
    logging.info("Assembling context files...")
    context_text = _assemble_context(generated_dir)
    total_kb = len(context_text.encode('utf-8')) // 1024

    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', suffix='.txt',
        prefix='tias_context_', delete=False
    ) as tmp:
        tmp.write(context_text)
        context_file = tmp.name

    logging.info(f"Context assembled: {total_kb}KB -> {context_file}")

    cmd = [
        str(kobold_exe),
        "--model", model_path,
        "--port", port,
        "--contextsize", context_size,
        "--threads", threads,
        "--memf", context_file,
    ]

    if gpu_backend == 'clblast':
        cmd.append("--useclblast")
    elif gpu_backend == 'vulkan':
        cmd.append("--usevulkan")
    elif gpu_backend == 'cublas':
        cmd.append("--usecublas")

    if gpu_layers:
        cmd.extend(["--gpulayers", gpu_layers])

    logging.info(f"Starting KoboldCpp on port {port}")
    logging.info(f"Quality: {quality} ({Path(model_path).name})")
    logging.info(f"GPU: {gpu_backend}, Layers: {gpu_layers}, Context: {context_size}")
    print(f"\nLaunching KoboldCpp (Quality: {quality})")
    print(f"  Model: {Path(model_path).name}")
    print(f"  GPU: {gpu_backend}, {gpu_layers} layers")
    print(f"  Port: {port}")
    print(f"  Context: {total_kb}KB ({len(context_text.splitlines())} lines)\n")

    try:
        subprocess.run(cmd, cwd=kobold_dir)
    finally:
        Path(context_file).unlink(missing_ok=True)
