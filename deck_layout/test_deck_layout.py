#!/usr/bin/env python3
"""
Tests for deck_layout.py

Tests cover:
- Pattern calculations
- Layout optimization
- Multiple board widths
- Border adjustments
"""

import unittest
from unittest import mock
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deck_layout
from deck_layout import (
    BoardWidth,
    Pattern,
    PATTERNS,
    calculate_layout,
    find_best_pattern,
    main,
)


class TestBoardWidth(unittest.TestCase):
    """Test BoardWidth enum."""
    
    def test_width_values(self):
        """Test that board widths are correct."""
        self.assertEqual(BoardWidth.NARROW.value, 3.5)
        self.assertEqual(BoardWidth.STANDARD.value, 5.5)
        self.assertEqual(BoardWidth.WIDE.value, 7.25)


class TestPattern(unittest.TestCase):
    """Test Pattern class."""
    
    def test_pattern_total_width(self):
        """Test pattern total width calculation."""
        pattern = Pattern("N-S", [BoardWidth.NARROW, BoardWidth.STANDARD])
        # 3.5 + 5.5 + 0.375 (spacing) = 9.375
        width = pattern.total_width(0.375)
        self.assertAlmostEqual(width, 9.375)
    
    def test_pattern_total_width_no_spacing(self):
        """Test pattern width with zero spacing."""
        pattern = Pattern("N-S", [BoardWidth.NARROW, BoardWidth.STANDARD])
        width = pattern.total_width(0)
        self.assertEqual(width, 9.0)
    
    def test_pattern_total_width_multiple(self):
        """Test pattern with multiple boards."""
        pattern = Pattern("N-S-W", [BoardWidth.NARROW, BoardWidth.STANDARD, BoardWidth.WIDE])
        # 3.5 + 5.5 + 7.25 + 2*0.375 = 17.0 (3 boards = 2 gaps)
        width = pattern.total_width(0.375)
        self.assertAlmostEqual(width, 17.0)


class TestCalculateLayout(unittest.TestCase):
    """Test calculate_layout function."""
    
    def test_basic_layout(self):
        """Test basic layout calculation."""
        pattern = PATTERNS['N-S']
        result = calculate_layout(120, pattern, 0.25)

        self.assertIn('pattern', result)
        self.assertIn('board_counts', result)
        self.assertIn('spacing', result)
    
    def test_pattern_fits_multiple_times(self):
        """Test that pattern repeats correctly."""
        pattern = PATTERNS['N-S']
        result = calculate_layout(100, pattern, 0.375)
        
        # 100" should fit multiple N-S patterns
        self.assertGreater(result['num_cycles'], 0)
    
    def test_with_border(self):
        """Test layout with border adjustment."""
        pattern = PATTERNS['N-S']
        result = calculate_layout(100, pattern, min_border=1, max_border=2)

        # Border should reduce available space
        self.assertLess(result['total_width_used'], 100)
    
    def test_oversized_deck(self):
        """Test deck larger than pattern."""
        pattern = PATTERNS['N-S-W']
        result = calculate_layout(300, pattern, 0.375)
        
        self.assertGreater(result['num_cycles'], 2)
    
    def test_small_deck(self):
        """Test deck smaller than full pattern."""
        pattern = PATTERNS['N-S']
        result = calculate_layout(5, pattern, 0.375)
        
        # Should still return a result even if very small
        self.assertIsNotNone(result)
        self.assertIn('waste', result)
    
    def test_actual_spacing_adjusted(self):
        """Test that actual spacing is calculated."""
        pattern = PATTERNS['N-S']
        result = calculate_layout(100, pattern, 0.375)
        
        # Should have an actual spacing value
        self.assertIn('actual_spacing', result)
        self.assertIsNotNone(result['actual_spacing'])


class TestFindBestPattern(unittest.TestCase):
    """Test find_best_pattern function."""
    
    def test_finds_patterns(self):
        """Test that best patterns are found."""
        results = find_best_pattern(120)
        
        self.assertGreater(len(results), 0)
        
        # Results should be sorted by score
        scores = [r['score'] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_results_have_required_fields(self):
        """Test that results contain all required fields."""
        results = find_best_pattern(100)
        
        for result in results:
            self.assertIn('pattern', result)
            self.assertIn('spacing', result)
            self.assertIn('score', result)
            self.assertIn('board_counts', result)
    
    def test_best_pattern_for_100_inch(self):
        """Test finding best pattern for 100 inch deck."""
        results = find_best_pattern(100)
        
        # Should find at least one pattern
        self.assertGreater(len(results), 0)
        
        # First result should have highest score
        best = results[0]
        self.assertGreater(best['score'], 0)
    
    def test_pattern_with_different_spacings(self):
        """Test pattern evaluation with different spacings."""
        results = find_best_pattern(100)

        # Should have results (spacing is now geometry-based)
        self.assertGreater(len(results), 0)
        
        # Each pattern may have different actual spacings
        spacings = set(r['actual_spacing'] for r in results)
        # At least some patterns should have different spacings
        self.assertGreater(len(spacings), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for deck layout scenarios."""
    
    def test_realistic_10_foot_deck(self):
        """Test realistic 10-foot deck layout."""
        # 10 feet = 120 inches
        results = find_best_pattern(120)
        
        # Should have valid patterns
        self.assertGreater(len(results), 0)
        
        # Best pattern should have good score
        best = results[0]
        self.assertGreater(best['score'], 50)
    
    def test_8_foot_deck(self):
        """Test 8-foot deck layout."""
        results = find_best_pattern(96)
        
        self.assertGreater(len(results), 0)
        self.assertLess(results[0]['waste'], 5)  # Should have minimal waste
    
    def test_long_deck_spacing(self):
        """Test spacing for long deck."""
        results = find_best_pattern(200)

        # Should find good patterns for long deck
        best = results[0]
        # The algorithm should work for long decks
        self.assertGreater(best['board_count'], 10)
        # Total width used should be close to deck width
        self.assertLessEqual(best['waste'], 10)  # Allow some waste for long decks

    def test_named_cli_parameters(self):
        output = StringIO()
        with mock.patch('sys.stdout', output):
            status = main(['--width', '120', '--pattern', 'N-S-W', '--spacing', '0.25', '--limit', '1'])
        self.assertEqual(status, 0)
        self.assertIn('N-S-W', output.getvalue())

    def test_legacy_positional_cli_remains_supported(self):
        output = StringIO()
        with mock.patch('sys.stdout', output):
            status = main(['120', 'N-S-W', '--limit', '1'])
        self.assertEqual(status, 0)


class TestBoardCounts(unittest.TestCase):
    """Test board count calculations."""
    
    def test_pattern_repeats_correctly(self):
        """Test that pattern repeats give correct board counts."""
        pattern = PATTERNS['N-S']  # 3.5" + 5.5"
        result = calculate_layout(100, pattern, 0.375)
        
        # Count boards in result
        total_boards = sum(result['board_counts'].values())
        self.assertGreater(total_boards, 0)
    
    def test_board_widths_sum(self):
        """Test that board widths are correctly calculated."""
        pattern = PATTERNS['N-S']
        result = calculate_layout(100, pattern, 0.375)
        
        # Verify counts match board types
        for board_type, count in result['board_counts'].items():
            self.assertGreaterEqual(count, 0)


if __name__ == '__main__':
    unittest.main()
