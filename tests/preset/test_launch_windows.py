"""
Tests for launch window calculations

Verifies against known game data points.
"""

import pytest
from datetime import datetime
from pathlib import Path

from src.preset.launch_windows import calculate_launch_windows
from src.core.core import get_project_root


class TestMarsLaunchWindows:
    """Test Mars launch window calculations against verified game data"""

    def test_mars_window_2027_08_01(self):
        """Test Mars window from 2027-08-01"""
        game_date = datetime(2027, 8, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        # Skip if templates not built
        if not templates_file.exists():
            pytest.skip("Templates not built - run: tias load")

        windows = calculate_launch_windows(game_date, templates_file)

        assert 'Mars' in windows
        assert windows['Mars']['next_window'] == '2029-01-01'
        assert windows['Mars']['days_away'] == 519
        # Penalty should be 32-33% (game shows 33%)
        assert 31 <= windows['Mars']['current_penalty'] <= 34

    def test_mars_window_2026_02_01(self):
        """Test Mars window from 2026-02-01"""
        game_date = datetime(2026, 2, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        assert 'Mars' in windows
        assert windows['Mars']['next_window'] == '2026-11-13'
        assert windows['Mars']['days_away'] == 285
        # Penalty should be 36-38% (game shows 37%)
        assert 35 <= windows['Mars']['current_penalty'] <= 39

    def test_mars_optimal_window(self):
        """Test Mars at optimal window (should be 0% penalty)"""
        game_date = datetime(2026, 11, 13)  # Known optimal
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        assert 'Mars' in windows
        # At optimal, penalty should be near 0
        assert windows['Mars']['current_penalty'] <= 1


class TestNEALaunchWindows:
    """Test Near-Earth Asteroid launch windows"""

    def test_sisyphus_window_2027_08_01(self):
        """Test Sisyphus window from 2027-08-01 (near optimal)"""
        game_date = datetime(2027, 8, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        assert 'Sisyphus' in windows
        # Should be very close to optimal (next day)
        assert windows['Sisyphus']['days_away'] <= 2

    def test_hephaistos_window_2027_08_01(self):
        """Test Hephaistos window from 2027-08-01 (at optimal)"""
        game_date = datetime(2027, 8, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        assert 'Hephaistos' in windows
        # Should be at optimal
        assert windows['Hephaistos']['days_away'] <= 1

    def test_nea_synodic_periods(self):
        """Verify NEA synodic periods match game observations"""
        game_date = datetime(2027, 8, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        # Test next windows after optimal dates
        # Sisyphus: 2027-08-02 + 592 days = 2029-03-16
        # Hephaistos: 2027-08-01 + 533 days = 2029-01-15

        # From 2027-09-01, check days to next window
        game_date_later = datetime(2027, 9, 1)
        windows_later = calculate_launch_windows(game_date_later, templates_file)

        # Sisyphus: should be ~562 days (verified in game)
        assert 560 <= windows_later['Sisyphus']['days_away'] <= 565

        # Hephaistos: should be ~502 days
        assert 500 <= windows_later['Hephaistos']['days_away'] <= 505


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_missing_templates_file(self):
        """Test graceful handling of missing templates"""
        game_date = datetime(2027, 8, 1)
        fake_path = Path("/nonexistent/path.json")

        windows = calculate_launch_windows(game_date, fake_path)

        # Should return empty dict, not crash
        assert windows == {}

    def test_dates_far_in_future(self):
        """Test calculations work for future dates"""
        game_date = datetime(2035, 1, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        # Should still calculate windows
        assert 'Mars' in windows
        assert windows['Mars']['days_away'] > 0

    def test_dates_in_past(self):
        """Test calculations work for past dates"""
        game_date = datetime(2020, 1, 1)
        templates_file = get_project_root() / "build" / "templates" / "TISpaceBodyTemplate.json"

        if not templates_file.exists():
            pytest.skip("Templates not built")

        windows = calculate_launch_windows(game_date, templates_file)

        # Should still calculate windows
        assert 'Mars' in windows
        assert windows['Mars']['days_away'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
