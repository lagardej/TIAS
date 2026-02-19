"""
Play command - Launch KoboldCpp and start interactive advisory session (V2)

Flow:
  1. Run preset to generate gamestate files
  2. Launch KoboldCpp as background process
  3. Delegate chat loop to orchestrator.turn()
"""

import logging
import os
import subprocess
import time
from pathlib import Path

import requests

from src.core.core import load_env, get_project_root
from src.orchestrator.orchestrator import OrchestratorState, turn


def _wait_for_server(port: str, timeout: int = 60) -> bool:
    """Wait until KoboldCpp API is ready. Returns True if ready, False if timeout."""
    url = f"http://localhost:{port}/api/v1/info/version"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def cmd_play(args):
    """Launch KoboldCpp and start interactive advisory session."""
    from src.preset.command import cmd_preset
    from src.core.date_utils import parse_flexible_date
    

    # Phase 1: generate gamestate files
    cmd_preset(args)

    env = load_env()
    project_root = get_project_root()

    _, iso_date = parse_flexible_date(args.date)

    quality    = args.quality if hasattr(args, 'quality') and args.quality else env.get('KOBOLDCPP_QUALITY', 'base')
    model_path = env.get(f'KOBOLDCPP_MODEL_{quality.upper()}')

    if not model_path:
        logging.error(f"No model configured for quality '{quality}'. Add KOBOLDCPP_MODEL_{quality.upper()} to .env")
        return 1

    kobold_dir   = os.path.expanduser(env.get('KOBOLDCPP_DIR', ''))
    model_path   = os.path.expanduser(model_path)
    port         = env.get('KOBOLDCPP_PORT', '5001')
    gpu_backend  = env.get('KOBOLDCPP_GPU_BACKEND', 'vulkan')
    gpu_layers   = env.get('KOBOLDCPP_GPU_LAYERS', '35')
    context_size = env.get('KOBOLDCPP_CONTEXT_SIZE', '32768')
    threads      = env.get('KOBOLDCPP_THREADS', '8')

    kobold_exe = Path(kobold_dir) / "koboldcpp.exe"
    if not kobold_exe.exists():
        kobold_exe = Path(kobold_dir) / "koboldcpp"

    # Phase 2: launch KoboldCpp
    cmd = [
        str(kobold_exe),
        "--model", model_path,
        "--port", port,
        "--contextsize", context_size,
        "--threads", threads,
        "--skiplauncher",
        "--quiet",
    ]
    if gpu_backend == 'vulkan':
        cmd.append("--usevulkan")
    elif gpu_backend == 'cublas':
        cmd.append("--usecuda")
    if gpu_layers:
        cmd.extend(["--gpulayers", gpu_layers])

    print(f"\nStarting KoboldCpp ({Path(model_path).name})...")
    print(f"  GPU: {gpu_backend}, {gpu_layers} layers | Context: {context_size} | Port: {port}\n")

    proc = subprocess.Popen(cmd, cwd=kobold_dir,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Waiting for server...", end='', flush=True)
    if not _wait_for_server(port):
        print(" TIMEOUT")
        proc.terminate()
        return 1
    print(" ready.\n")

    # Phase 3: initialise orchestrator state
    tier_state_path = project_root / "generated" / iso_date / "tier_state.json"
    tier = 1
    if tier_state_path.exists():
        import json
        tier = json.loads(tier_state_path.read_text(encoding="utf-8")).get("current_tier", 1)
    state = OrchestratorState(date=iso_date, tier=tier)

    print("=" * 60)
    print("TIAS — Terra Invicta Advisory System")
    print(f"Tier {tier} | {iso_date} | {Path(model_path).name}")
    print("Type 'quit' or Ctrl+C to exit.")
    print("=" * 60)
    print()

    # Phase 4: chat loop
    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            if user_input.lower() in ('quit', 'exit', 'q'):
                break

            print()
            response = turn(user_input, state)
            print(response)
            print()

    except KeyboardInterrupt:
        print("\n\nSession ended.")
    finally:
        print("Shutting down KoboldCpp...")
        proc.terminate()
        proc.wait(timeout=10)
