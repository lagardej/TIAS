#!/usr/bin/env python3
"""
TIAS - Terra Invicta Advisory System

Main entry point for the modular command system.
"""

import argparse
import sys

# Python version check
if sys.version_info < (3, 11):
    print("ERROR: Python 3.11+ required")
    print(f"Current version: {sys.version}")
    print("Please upgrade Python and try again.")
    sys.exit(1)

# Import core utilities
from src.core.core import setup_logging

# Import command functions
from src.clean.command    import cmd_clean
from src.install.command  import cmd_install
from src.load.command     import cmd_load
from src.validate.command import cmd_validate
from src.perf.command     import cmd_perf
from src.parse.command    import cmd_parse
from src.stage.command    import cmd_stage
from src.preset.command   import cmd_preset
from src.play.command     import cmd_play


def main():
    parser = argparse.ArgumentParser(description='Terra Invicta Advisory System')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='Increase verbosity (-v INFO, -vv DEBUG)')

    subparsers = parser.add_subparsers(dest='command', help='Command')

    subparsers.add_parser('install',  help='Interactive setup (auto-detect paths)')
    subparsers.add_parser('clean',    help='Remove build directory')
    subparsers.add_parser('load',     help='Import game templates into SQLite database')
    subparsers.add_parser('validate', help='Validate configuration and paths')
    subparsers.add_parser('perf',     help='Display performance statistics')
    stage_parser = subparsers.add_parser('stage', help='Parse savegame, evaluate tier, assemble actor context files')
    stage_parser.add_argument('--faction', required=True, help='Faction slug (e.g. resist, exodus, academy)')
    stage_parser.add_argument('--date', required=True, help='Date (YYYY-M-D or YYYY-MM-DD or DD/MM/YYYY)')
    stage_parser.add_argument('--force', action='store_true', help='Re-parse savegame even if DB is current')

    parse_parser = subparsers.add_parser('parse', help='Parse savegame into SQLite database')
    parse_parser.add_argument('--date', required=True, help='Date (YYYY-M-D or YYYY-MM-DD or DD/MM/YYYY)')

    preset_parser = subparsers.add_parser('preset', help='Combine actor contexts and game state into LLM context')
    preset_parser.add_argument('--faction', required=True, help='Faction slug (e.g. resist, exodus, academy)')
    preset_parser.add_argument('--date', required=True, help='Date (YYYY-M-D or YYYY-MM-DD or DD/MM/YYYY)')

    play_parser = subparsers.add_parser('play', help='Launch KoboldCpp')
    play_parser.add_argument('--faction', required=True, help='Faction slug (e.g. resist, exodus, academy)')
    play_parser.add_argument('--date', required=True, help='Date (YYYY-M-D or YYYY-MM-DD or DD/MM/YYYY)')
    play_parser.add_argument('--quality', choices=['base', 'max', 'nuclear', 'ridiculous', 'ludicrous'],
                             help='Model quality tier (default: base or KOBOLDCPP_QUALITY from .env)')

    args = parser.parse_args()

    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        'install':  cmd_install,
        'clean':    cmd_clean,
        'load':     cmd_load,
        'validate': cmd_validate,
        'perf':     cmd_perf,
        'parse':    cmd_parse,
        'stage':    cmd_stage,
        'preset':   cmd_preset,
        'play':     cmd_play,
    }

    commands[args.command](args)


if __name__ == '__main__':
    main()
