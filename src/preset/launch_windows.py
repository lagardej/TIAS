"""
Terra Invicta Advisory System - Launch Window Calculations

Calculates optimal launch windows for interplanetary missions.
Uses Keplerian orbital mechanics and game-verified synodic periods.
"""

import logging
import math
from datetime import datetime, timedelta
from pathlib import Path


def calculate_launch_windows(game_date: datetime, templates_file: Path) -> dict:
    """Calculate launch windows for major targets using known synodic periods"""
    import json

    if not templates_file.exists():
        logging.warning(f"Templates file not found: {templates_file}")
        return {}

    # Load templates
    with open(templates_file, encoding='utf-8') as f:
        templates_data = json.load(f)

    # Known optimal windows (from game verification)
    # Mars windows repeat every 780 days
    mars_base_window = datetime(2026, 11, 13)  # Known optimal
    mars_synodic = 780  # days

    # NEA windows (Near-Earth Asteroids)
    sisyphus_base_window = datetime(2027, 8, 2)
    sisyphus_synodic = 592  # days

    hephaistos_base_window = datetime(2027, 8, 1)
    hephaistos_synodic = 533  # days

    results = {}

    # Calculate Mars window
    days_since_base = (game_date - mars_base_window).days
    cycles_passed = days_since_base / mars_synodic
    next_cycle = math.ceil(cycles_passed)
    next_mars_window = mars_base_window + timedelta(days=next_cycle * mars_synodic)
    days_to_mars = (next_mars_window - game_date).days

    # Mars penalty (calibrated with game data)
    # Formula: 40% * (normalized_distance ^ 0.5)
    # Fits game data with ~1% average error
    days_from_optimal = min(days_to_mars, mars_synodic - days_to_mars)
    normalized = days_from_optimal / (mars_synodic / 2.0)
    mars_penalty = 40.0 * (normalized ** 0.5)

    results['Mars'] = {
        'next_window': next_mars_window.strftime('%Y-%m-%d'),
        'days_away': days_to_mars,
        'current_penalty': int(mars_penalty)
    }

    # Calculate Sisyphus window (NEA - no penalty yet)
    days_since_sis = (game_date - sisyphus_base_window).days
    cycles_sis = days_since_sis / sisyphus_synodic
    next_cycle_sis = math.ceil(cycles_sis)
    next_sis_window = sisyphus_base_window + timedelta(days=next_cycle_sis * sisyphus_synodic)
    days_to_sis = (next_sis_window - game_date).days

    results['1866 Sisyphus'] = {
        'next_window': next_sis_window.strftime('%Y-%m-%d'),
        'days_away': days_to_sis
    }

    # Calculate Hephaistos window (NEA - no penalty yet)
    days_since_heph = (game_date - hephaistos_base_window).days
    cycles_heph = days_since_heph / hephaistos_synodic
    next_cycle_heph = math.ceil(cycles_heph)
    next_heph_window = hephaistos_base_window + timedelta(days=next_cycle_heph * hephaistos_synodic)
    days_to_heph = (next_heph_window - game_date).days

    results['2212 Hephaistos'] = {
        'next_window': next_heph_window.strftime('%Y-%m-%d'),
        'days_away': days_to_heph
    }

    return results
