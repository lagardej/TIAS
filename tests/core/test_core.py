"""
Tests for core utilities

Tests environment loading, logging setup, and path management.
"""

import pytest
from pathlib import Path

from src.core.core import get_project_root


class TestEnvironmentLoading:
    """Test .env file loading"""
    
    def test_load_env_with_valid_file(self, tmp_path):
        """Test loading a valid .env file"""
        # Note: This test needs refactoring to inject path
        pytest.skip("Needs dependency injection for path")


class TestPathManagement:
    """Test path utilities"""
    
    def test_get_project_root(self):
        """Test project root detection"""
        root = get_project_root()
        
        # Should return TIAS directory
        assert root.name == "TIAS"
        assert (root / "src").exists()
        assert (root / "resources").exists()
    
    def test_project_structure(self):
        """Verify expected project structure"""
        root = get_project_root()
        
        # Core directories
        assert (root / "resources").exists()
        assert (root / "src").exists()
        assert (root / "tests").exists()
        assert (root / "docs").exists()
        
        # Config files
        assert (root / ".env.linux.dist").exists()
        assert (root / ".env.win.dist").exists()
        assert (root / "README.md").exists()
        assert (root / "setup.py").exists()
        assert (root / "pyproject.toml").exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
