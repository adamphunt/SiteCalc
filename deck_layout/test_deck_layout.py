#!/usr/bin/env python3
"""
Deck Layout Tests - Unit tests for deck_layout.py

Tests cover:
- Layout calculation with various lengths
- Border adjustments
- Different starting sizes
- Edge cases (very short decks, zero borders)
"""

import unittest
import tempfile
import os
import sys
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deck_layout


class TestCalculateLayout(unittest.TestCase):
    """Test calculate_layout function."""
    
    def test_basic_layout(self):
        """Test basic layout calculation."""
        result = deck_layout.calculate_layout(12.5)
        self.assertGreater(result['total_boards'], 0)
        self.assertIn('boards', result)
        self.assertIn('final_gap', result)
    
    def test_with_border(self):
        """Test layout with border adjustment."""
        result = deck_layout.calculate_layout(12.5, border=2)
        # Border should reduce available space
        self.assertLess(result['remaining'], 
                       deck_layout.calculate_layout(12.5, border=0)['remaining'])
    
    def test_with_start_index(self):
        """Test layout starting with different board sizes."""
        result_small = deck_layout.calculate_layout(15.0, start=0)
        result_large = deck_layout.calculate_layout(15.0, start=2)
        
        # Starting with large should use fewer total boards
        self.assertLessEqual(result_large['total_boards'], result_small['total_boards'])
    
    def test_short_deck(self):
        """Test very short deck layout."""
        result = deck_layout.calculate_layout(3.0)
        # Should handle short decks gracefully
        self.assertIsNotNone(result)
    
    def test_zero_border(self):
        """Test with explicit zero border."""
        result = deck_layout.calculate_layout(10.0, border=0)
        self.assertEqual(result['border'], 0)
    
    def test_board_counts(self):
        """Test that board counts are populated correctly."""
        result = deck_layout.calculate_layout(15.0)
        total = sum(result['boards'].values())
        self.assertEqual(result['total_boards'], total)
        self.assertGreater(total, 0)
    
    def test_gap_calculation(self):
        """Test that final gap is positive and reasonable."""
        result = deck_layout.calculate_layout(12.0)
        self.assertGreater(result['final_gap'], 0)
        # Gap should be reasonable (less than 2 inches typically)
        self.assertLess(result['final_gap'] * 12, 10)


class TestEntryPoint(unittest.TestCase):
    """Test main entry point behavior."""
    
    def test_no_arguments_shows_help(self):
        """Test that running without arguments shows help."""
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            # Simulate no arguments
            original_argv = sys.argv
            sys.argv = ['deck_layout.py']
            
            with self.assertRaises(SystemExit) as cm:
                deck_layout.main()
            
            self.assertEqual(cm.exception.code, 1)
        finally:
            sys.stdout = old_stdout
            sys.argv = original_argv
    
    def test_with_valid_length(self):
        """Test main with valid length argument."""
        old_stdout = sys.stdout
        old_argv = sys.argv
        sys.stdout = StringIO()
        sys.argv = ['deck_layout.py', '12.5']
        
        try:
            deck_layout.main()
            output = sys.stdout.getvalue()
            self.assertIn('DECK LAYOUT RESULTS', output)
            self.assertIn('Total deck length:', output)
        finally:
            sys.stdout = old_stdout
            sys.argv = old_argv


class TestIntegration(unittest.TestCase):
    """Integration tests for deck layout scenarios."""
    
    def test_realistic_deck_size(self):
        """Test a realistic 12-foot deck layout."""
        result = deck_layout.calculate_layout(12.0)
        
        # Should have at least 3 boards for a 12' deck
        self.assertGreaterEqual(result['total_boards'], 3)
        
        # All counts should be non-negative
        for size, count in result['boards'].items():
            self.assertGreaterEqual(count, 0)
    
    def test_long_deck(self):
        """Test a longer 20-foot deck layout."""
        result = deck_layout.calculate_layout(20.0)
        
        # Should scale appropriately
        self.assertGreater(result['total_boards'], 5)
    
    def test_layout_reproducibility(self):
        """Test that same inputs give same outputs."""
        result1 = deck_layout.calculate_layout(15.0, start=0, border=1)
        result2 = deck_layout.calculate_layout(15.0, start=0, border=1)
        
        self.assertEqual(result1['total_boards'], result2['total_boards'])
        self.assertEqual(result1['boards'], result2['boards'])


if __name__ == '__main__':
    unittest.main()
