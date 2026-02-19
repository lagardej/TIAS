"""
Tests for date parsing utilities

Tests flexible date format parsing.
"""

import pytest
from datetime import datetime

from src.core.date_utils import parse_flexible_date


class TestDateParsing:
    """Test date parsing with multiple formats"""
    
    def test_iso_format_with_zeros(self):
        """Test ISO format with leading zeros"""
        dt, normalized = parse_flexible_date('2027-07-14')

        assert dt.year == 2027
        assert dt.month == 7
        assert dt.day == 14
        assert normalized == '2027-07-14'

    def test_iso_format_without_zeros(self):
        """Test ISO format without leading zeros"""
        dt, normalized = parse_flexible_date('2027-7-14')

        assert dt.year == 2027
        assert dt.month == 7
        assert dt.day == 14
        assert normalized == '2027-07-14'

    def test_european_format_with_zeros(self):
        """Test European format with leading zeros"""
        dt, normalized = parse_flexible_date('14/07/2027')

        assert dt.year == 2027
        assert dt.month == 7
        assert dt.day == 14
        assert normalized == '2027-07-14'

    def test_european_format_without_zeros(self):
        """Test European format without leading zeros"""
        dt, normalized = parse_flexible_date('14/7/2027')

        assert dt.year == 2027
        assert dt.month == 7
        assert dt.day == 14
        assert normalized == '2027-07-14'

    def test_single_digit_day(self):
        """Test parsing with single-digit day"""
        dt, normalized = parse_flexible_date('2027-7-1')

        assert dt.day == 1
        assert normalized == '2027-07-01'

    def test_single_digit_month(self):
        """Test parsing with single-digit month"""
        dt, normalized = parse_flexible_date('2027-1-14')

        assert dt.month == 1
        assert normalized == '2027-01-14'
    
    def test_invalid_format(self):
        """Test that invalid formats raise ValueError"""
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_flexible_date('2027/07/14')  # Wrong separator
        
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_flexible_date('07-14-2027')  # US format (not supported)
        
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_flexible_date('not-a-date')
    
    def test_normalized_output_format(self):
        """Test that normalized output is always YYYY_M_D"""
        test_cases = [
            ('2027-07-14', '2027-07-14'),
            ('2027-7-14',  '2027-07-14'),
            ('14/07/2027', '2027-07-14'),
            ('14/7/2027',  '2027-07-14'),
            ('2027-1-1',   '2027-01-01'),
            ('2027-12-31', '2027-12-31'),
        ]
        
        for date_str, expected_normalized in test_cases:
            _, normalized = parse_flexible_date(date_str)
            assert normalized == expected_normalized


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
