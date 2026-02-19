# Terra Invicta Advisory System

## About This Project

This project is used as a **learning experience for AI-assisted development**.

The workflow is collaborative by design:
- **I take the decisions** - architecture, features, priorities, direction
- **Claude (Anthropic) suggests, corrects, codes, and documents** - implementation, refactoring, best practices

This means the codebase reflects real decisions made through conversation: some things were built wrong and fixed, some were over-engineered and simplified, some were discovered by doing. The git history and `.ai/` directory preserve that process.

If you're reading this as a fellow learner: the mistakes are intentional in the sense that they were real, and the corrections are where the learning happened.

---

LLM-powered advisory system for Terra Invicta campaign gameplay. Provides domain-specific guidance through 6 specialized councilor advisors plus CODEX state evaluator.

## Documentation

- **[Developer Guide](DEVELOPER_GUIDE.md)** - Complete reference for commands, workflows, and development
- **[Features](FEATURES.md)** - Feature list and roadmap
- **[Technical Details](docs/technical.md)** - Architecture and implementation
- **[Workflow Guide](docs/workflow.md)** - User workflows
- **[Performance](docs/performance.md)** - Performance targets and monitoring

## Overview

**Advisors (7 total):**
- **Wale** - Covert/Asymmetric Operations
- **Valentina** - Intelligence & Counter-Intelligence  
- **Lin** - Earth/Political Strategy
- **Jun-Ho** - Industrial & Energy Systems
- **Jonny** - Orbital Operations & Space Execution
- **Katya** - Military Doctrine & Ground Warfare
- **CODEX** - Data archivist, emotionless state evaluator

**Tier System:**
- Tier 1 (0-60%): Basic operations, individual targets
- Tier 2 (60-70%): Strategic operations, faction-level
- Tier 3 (70%+): Global operations, civilization-scale

## Quick Start

### Prerequisites
- Python 3.11+
- Terra Invicta v1.0.29 (Steam/GOG)
- KoboldCpp + Mistral 7B Q4 model (local LLM)
- AMD GPU: ROCm drivers (Linux) or Vulkan support (Windows/Linux)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd TIAS

# Install in editable mode
pip install -e .

# Verify installation
tias --help
```

### Initial Setup

```bash
# Interactive configuration wizard
tias install
```

This will:
- Auto-detect Terra Invicta installation
- Auto-detect savegame directory
- Configure KoboldCpp path
- Configure model path
- Set GPU backend (vulkan/clblast)
- Create `.env` file

### Load Game Templates

```bash
tias load
```

This extracts and indexes game data from Terra Invicta installation.

### Basic Usage

```bash
# Parse savegame, evaluate tier, assemble actor contexts
tias stage --date 2027-7-14

# Generate LLM context
tias preset --date 2027-7-14

# Launch KoboldCpp
tias play --date 2027-7-14

# Or chain them together
tias stage --date 2027-7-14 && \
tias preset --date 2027-7-14 && \
tias play --date 2027-7-14
```

**Date formats supported:**
- `YYYY-M-D` (e.g., `2027-7-14`)
- `YYYY-MM-DD` (e.g., `2027-07-14`)
- `DD/MM/YYYY` (e.g., `14/07/2027`)

## Commands

| Command | Description |
|---------|-------------|
| `tias install` | Interactive setup wizard |
| `tias clean` | Remove build directory |
| `tias load` | Import game templates into SQLite database |
| `tias validate` | Validate configuration |
| `tias parse --date DATE` | Parse savegame to database (explicit; stage does this automatically) |
| `tias stage --date DATE` | Parse savegame, evaluate tier, assemble actor context files |
| `tias preset --date DATE` | Combine actor contexts and game state |
| `tias play --date DATE` | Launch KoboldCpp |
| `tias perf` | Show performance statistics |

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for complete command reference.

## Common Workflows

### Full Clean Load
```bash
tias clean && tias load
```

### Complete Pipeline
```bash
tias stage --date 2027-7-14 && \
tias preset --date 2027-7-14 && \
tias play --date 2027-7-14
```

### Quick Context Update
```bash
# Skip parse if savegame unchanged
tias preset --date 2027-7-14 && tias play --date 2027-7-14
```

### Different Quality Tiers
```bash
tias play --date 2027-7-14 --quality base      # Fast (Mistral 7B Q4)
tias play --date 2027-7-14 --quality nuclear   # Better (Qwen 14B Q4)
tias play --date 2027-7-14 --quality ludicrous # Best (Qwen 72B Q2)
```

## Development

### Project Structure

```
TIAS/
├── src/                    # Source code (Python package)
│   ├── __main__.py        # Entry point (tias command)
│   ├── core/              # Core utilities
│   ├── load/              # Load command
│   ├── clean/             # Clean command
│   ├── parse/             # Parse command
│   ├── stage/             # Stage command
│   ├── preset/            # Preset command
│   ├── play/              # Play command
│   ├── validate/          # Validate command
│   └── perf/              # Performance tracking
├── resources/             # Game data
│   ├── actors/           # AI advisor definitions
│   └── prompts/          # LLM prompts
├── tests/                # Test suite
├── docs/                 # Documentation
└── build/                # Build output (gitignored)
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src

# Specific test file
pytest tests/preset/test_launch_windows.py

# Verbose output
pytest -v
```

### Adding New Advisors

1. Create directory: `resources/actors/newname/`
2. Add files:
   - `spec.toml` - Metadata
   - `background.txt` - Character background
   - `personality.txt` - Voice and speech patterns
   - `stage.txt` - Stage directions
   - `examples_tier1/2/3.md` - Example exchanges
   - `openers.csv` - Conversation openers
   - `reactions.csv` - Response patterns
3. Reload: `tias clean && tias load`

See `resources/actors/_template/` for structure.

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# KoboldCpp
KOBOLDCPP_DIR=/path/to/koboldcpp
KOBOLDCPP_MODEL_BASE=/path/to/mistral-7b-q4.gguf
KOBOLDCPP_PORT=5001
KOBOLDCPP_GPU_BACKEND=vulkan

# Terra Invicta
GAME_INSTALL_DIR=/path/to/Terra Invicta
GAME_SAVES_DIR=/path/to/saves

# System
LOG_LEVEL=INFO
```

### Quality Tiers

Configure in `.env`:

```bash
KOBOLDCPP_MODEL_BASE=/path/to/mistral-7b-q4.gguf
KOBOLDCPP_MODEL_MAX=/path/to/mistral-7b-q6.gguf
KOBOLDCPP_MODEL_NUCLEAR=/path/to/qwen2.5-14b-q4.gguf
KOBOLDCPP_MODEL_RIDICULOUS=/path/to/qwen2.5-32b-q4.gguf
KOBOLDCPP_MODEL_LUDICROUS=/path/to/qwen2.5-72b-q2.gguf
```

## Troubleshooting

### Import Errors
```bash
pip uninstall tias
pip install -e .
```

### Command Not Found
Ensure Python scripts directory is in PATH:
- Windows: `C:\Users\YourName\AppData\Local\Python\pythoncore-3.14-64\Scripts`
- Linux: `~/.local/bin`

### Performance Issues
Check logs: `logs/performance.log`

Run validation: `tias validate`
