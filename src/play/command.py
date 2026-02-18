"""
Play command - Launch KoboldCpp and start interactive chat session

Flow:
  1. Run preset to generate gamestate files
  2. Assemble all context files into system prompt
  3. Launch KoboldCpp as background process
  4. Start interactive chat loop via OpenAI-compatible API
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

from src.core.core import load_env, get_project_root


def _assemble_context(generated_dir: Path) -> str:
    """Concatenate all context and gamestate files into one string."""
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

    return "\n\n---\n\n".join(parts)


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


def _chat(system_prompt: str, history: list, user_msg: str, port: str) -> str:
    """Send a chat request to KoboldCpp OpenAI API. Returns assistant reply."""
    url = f"http://localhost:{port}/v1/chat/completions"
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": user_msg})

    payload = {
        "model": "koboldcpp",
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.7,
    }

    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def cmd_play(args):
    """Launch KoboldCpp and start interactive advisory session"""
    from src.preset.command import cmd_preset
    from src.core.date_utils import parse_flexible_date

    # Phase 1: generate gamestate files
    cmd_preset(args)

    env = load_env()
    project_root = get_project_root()

    _, iso_date = parse_flexible_date(args.date)
    generated_dir = project_root / "generated" / iso_date
    kobold_dir = env.get('KOBOLDCPP_DIR')

    # Model selection
    quality = args.quality if hasattr(args, 'quality') and args.quality else env.get('KOBOLDCPP_QUALITY', 'base')
    model_path = env.get(f'KOBOLDCPP_MODEL_{quality.upper()}')

    if not model_path:
        logging.error(f"No model configured for quality '{quality}'. Add KOBOLDCPP_MODEL_{quality.upper()} to .env")
        return 1

    port          = env.get('KOBOLDCPP_PORT', '5001')
    gpu_backend   = env.get('KOBOLDCPP_GPU_BACKEND', 'vulkan')
    gpu_layers    = env.get('KOBOLDCPP_GPU_LAYERS', '35')
    context_size  = env.get('KOBOLDCPP_CONTEXT_SIZE', '16384')
    threads       = env.get('KOBOLDCPP_THREADS', '8')

    kobold_dir  = os.path.expanduser(kobold_dir)
    model_path  = os.path.expanduser(model_path)
    kobold_exe  = Path(kobold_dir) / "koboldcpp.exe"
    if not kobold_exe.exists():
        kobold_exe = Path(kobold_dir) / "koboldcpp"

    # Phase 2: assemble system prompt
    logging.info("Assembling context files...")
    system_prompt = _assemble_context(generated_dir)
    total_kb = len(system_prompt.encode('utf-8')) // 1024
    logging.info(f"System prompt: {total_kb}KB")

    # Phase 3: launch KoboldCpp in background
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
    print(f"  GPU: {gpu_backend}, {gpu_layers} layers | Context: {context_size} | Port: {port}")
    print(f"  System prompt: {total_kb}KB\n")

    proc = subprocess.Popen(cmd, cwd=kobold_dir,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for API ready
    print("Waiting for server...", end='', flush=True)
    if not _wait_for_server(port):
        print(" TIMEOUT")
        proc.terminate()
        return 1
    print(" ready.\n")

    # Phase 4: interactive chat loop
    print("=" * 60)
    print("Terra Invicta Advisory Council")
    print(f"Tier 1 | {iso_date} | {Path(model_path).name}")
    print("Type 'quit' or Ctrl+C to exit.")
    print("=" * 60)
    print()

    history = []
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

            print("\nCouncil: ", end='', flush=True)
            try:
                reply = _chat(system_prompt, history, user_input, port)
                print(reply)
                print()
                # Keep rolling history (last 10 exchanges to avoid context overflow)
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": reply})
                history = history[-20:]
            except requests.exceptions.RequestException as e:
                print(f"\n[API error: {e}]")

    except KeyboardInterrupt:
        print("\n\nSession ended.")
    finally:
        print("Shutting down KoboldCpp...")
        proc.terminate()
        proc.wait(timeout=10)
