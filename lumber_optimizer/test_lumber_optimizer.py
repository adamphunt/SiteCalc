#!/usr/bin/env python3
"""Tests for lumber_optimizer.py"""

import unittest
import tempfile
import os
from io import StringIO
import sys
from pathlib import Path

# Import the module to test
import lumber_optimizer


class TestParseLength(unittest.TestCase):
    """Test parse_length function."""

    def test_integer(self):
        self.assertEqual(lumber_optimizer.parse_length("12"), 12.0)

    def test_decimal(self):
        self.assertEqual(lumber_optimizer.parse_length("12.5"), 12.5)

    def test_fraction(self):
        self.assertEqual(lumber_optimizer.parse_length("1/4"), 0.25)
        self.assertEqual(lumber_optimizer.parse_length("1/8"), 0.125)
        self.assertEqual(lumber_optimizer.parse_length("3/8"), 0.375)

    def test_mixed_fraction(self):
        self.assertEqual(lumber_optimizer.parse_length("12 1/4"), 12.25)
        self.assertEqual(lumber_optimizer.parse_length("12 3/8"), 12.375)
        self.assertEqual(lumber_optimizer.parse_length("10 1/2"), 10.5)

    def test_whitespace(self):
        self.assertEqual(lumber_optimizer.parse_length("  12 1/4  "), 12.25)

    def test_invalid_length_rejected(self):
        with self.assertRaises(ValueError):
            lumber_optimizer.parse_length("not-a-length")
        with self.assertRaises(ValueError):
            lumber_optimizer.parse_length("0")


class TestParseMeasurement(unittest.TestCase):
    def test_feet_and_fractional_inches(self):
        self.assertEqual(lumber_optimizer.parse_measurement("10' 9 1/4\""), 129.25)

    def test_feet_only_and_inches_only(self):
        self.assertEqual(lumber_optimizer.parse_measurement("10'"), 120)
        self.assertEqual(lumber_optimizer.parse_measurement('9 1/4"'), 9.25)

    def test_unicode_prime_marks(self):
        self.assertEqual(lumber_optimizer.parse_measurement("10′ 9 1/4″"), 129.25)

    def test_explicit_inches_must_be_less_than_twelve(self):
        with self.assertRaisesRegex(ValueError, "less than 12"):
            lumber_optimizer.parse_measurement("10' 12\"")


class TestLoadLengths(unittest.TestCase):
    """Test load_lengths function."""

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("# Comment only\n")
            f.write("\n")
            temp_path = f.name
        try:
            lengths = lumber_optimizer.load_lengths(temp_path)
            self.assertEqual(lengths, [])
        finally:
            os.unlink(temp_path)

    def test_simple_values(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("12\n")
            f.write("24.5\n")
            temp_path = f.name
        try:
            lengths = lumber_optimizer.load_lengths(temp_path)
            self.assertEqual(lengths, [1.0, 2.0416666666666665])  # feet
        finally:
            os.unlink(temp_path)

    def test_fractional_inches(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("12 1/4\n")  # 12.25 inches = 1.020833... feet
            temp_path = f.name
        try:
            lengths = lumber_optimizer.load_lengths(temp_path)
            self.assertAlmostEqual(lengths[0], 12.25 / 12.0, places=5)
        finally:
            os.unlink(temp_path)

    def test_comments(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("# This is a comment\n")
            f.write("12  # inline comment\n")
            temp_path = f.name
        try:
            lengths = lumber_optimizer.load_lengths(temp_path)
            self.assertEqual(len(lengths), 1)
            self.assertAlmostEqual(lengths[0], 1.0, places=5)
        finally:
            os.unlink(temp_path)

    def test_quantity_at_mixed_fraction(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("2@164 3/4\n")
            f.write("3 @ 12 1/2  # repeated pieces\n")
            temp_path = f.name
        try:
            lengths = lumber_optimizer.load_lengths(temp_path)
        finally:
            os.unlink(temp_path)
        self.assertEqual(len(lengths), 5)
        self.assertEqual(lengths[:2], [164.75 / 12] * 2)
        self.assertEqual(lengths[2:], [12.5 / 12] * 3)

    def test_quantity_at_feet_and_inches(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("2@10' 9 1/4\"\n")
            temp_path = f.name
        try:
            lengths = lumber_optimizer.load_lengths(temp_path)
        finally:
            os.unlink(temp_path)
        self.assertEqual(lengths, [129.25 / 12] * 2)

    def test_invalid_quantity_reports_line(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("2.5@12\n")
            temp_path = f.name
        try:
            with self.assertRaisesRegex(ValueError, r":1: quantity must be a whole number"):
                lumber_optimizer.load_lengths(temp_path)
        finally:
            os.unlink(temp_path)


class TestBestFitDecreasing(unittest.TestCase):
    """Test best_fit_decreasing function."""

    def test_single_piece_fits_in_16(self):
        needed = [lumber_optimizer.inches_to_feet(100)]  # 8'4"
        scrap = []
        orders, remaining, stats = lumber_optimizer.best_fit_decreasing(needed, scrap)
        self.assertEqual(len(orders), 1)
        self.assertAlmostEqual(orders[0][0], lumber_optimizer.inches_to_feet(100), places=5)

    def test_two_pieces_fit_in_16(self):
        needed = [lumber_optimizer.inches_to_feet(60), lumber_optimizer.inches_to_feet(60)]  # 5' + 5'
        scrap = []
        orders, remaining, stats = lumber_optimizer.best_fit_decreasing(needed, scrap)
        self.assertEqual(len(orders), 1)
        self.assertEqual(len(orders[0]), 2)

    def test_two_pieces_need_two_stocks(self):
        # 19' + 19' needs two 20' stocks even with kerf
        needed = [lumber_optimizer.inches_to_feet(228), lumber_optimizer.inches_to_feet(228)]  # 19' + 19'
        scrap = []
        orders, remaining, stats = lumber_optimizer.best_fit_decreasing(needed, scrap)
        self.assertEqual(len(orders), 2)

    def test_scrap_used_first(self):
        needed = [lumber_optimizer.inches_to_feet(100)]  # 8'4"
        scrap = [lumber_optimizer.inches_to_feet(120)]  # 10' scrap
        orders, remaining, stats = lumber_optimizer.best_fit_decreasing(needed, scrap)
        self.assertEqual(len(orders), 0)  # No new stock needed
        self.assertGreater(stats['scrap_used'], 0)

    def test_kerf_accounted_for(self):
        needed = [lumber_optimizer.inches_to_feet(100), lumber_optimizer.inches_to_feet(100)]
        scrap = []
        kerf = lumber_optimizer.inches_to_feet(0.125)
        orders, remaining, stats = lumber_optimizer.best_fit_decreasing(needed, scrap, kerf=kerf)
        self.assertEqual(len(orders), 1)
        self.assertAlmostEqual(stats['kerf_waste'], kerf)
        self.assertEqual(stats['order_stock_lengths'], [20.0])

    def test_uses_smallest_stock_that_fits(self):
        orders, _, stats = lumber_optimizer.best_fit_decreasing([15.0, 19.0], [])
        self.assertEqual(len(orders), 2)
        self.assertEqual(stats['order_stock_lengths'], [20.0, 16.0])

    def test_oversized_piece_is_rejected(self):
        with self.assertRaises(ValueError):
            lumber_optimizer.best_fit_decreasing([21.0], [])

    def test_larger_stock_can_reduce_board_count(self):
        orders, _, stats = lumber_optimizer.best_fit_decreasing([10.0, 10.0, 6.0, 6.0], [])
        self.assertEqual(len(orders), 2)
        self.assertEqual(stats['order_stock_lengths'], [20.0, 20.0])

    def test_deck_data_improves_on_single_pass_greedy_result(self):
        data_dir = Path(__file__).parent
        needed = lumber_optimizer.load_lengths(data_dir / "deck_order_3_5.txt")
        scrap = lumber_optimizer.load_lengths(data_dir / "deck_scrap_3_5.txt")
        _, _, stats = lumber_optimizer.best_fit_decreasing(needed, scrap)
        self.assertEqual(stats["order_stock_lengths"], [16.0] * 4)
        self.assertEqual(len(stats["scrap_cut_lists"]), 13)


class TestInchesToFeet(unittest.TestCase):
    """Test inches_to_feet function."""

    def test_conversion(self):
        self.assertEqual(lumber_optimizer.inches_to_feet(12), 1.0)
        self.assertEqual(lumber_optimizer.inches_to_feet(24), 2.0)
        self.assertAlmostEqual(lumber_optimizer.inches_to_feet(6), 0.5)


class TestVisualization(unittest.TestCase):
    def test_writes_scrap_and_purchase_diagrams(self):
        orders, _, stats = lumber_optimizer.best_fit_decreasing(
            [10.0, 6.0, 4.0], [6.5]
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "plan.html"
            result = lumber_optimizer.write_visualization(output, orders, stats)
            contents = output.read_text(encoding="utf-8")
        self.assertEqual(result, output)
        self.assertIn("Scrap 1", contents)
        self.assertIn("Purchased board 1", contents)
        self.assertIn("Saw kerf", contents)
        self.assertIn("Remaining", contents)


if __name__ == '__main__':
    unittest.main()
