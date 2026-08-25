#!/usr/bin/env python3
"""Tests for hex_floor.py"""

import unittest
import sys
import os
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hex_floor


class TestFloorCells(unittest.TestCase):
    """Test floor_cells function."""
    
    def test_total_cells(self):
        """Test that we get the expected number of cells."""
        cells = hex_floor.floor_cells()
        expected = sum(hex_floor.ROW_LENGTHS)
        self.assertEqual(len(cells), expected)
    
    def test_cells_in_order(self):
        """Test that cells are in reading order (row by row)."""
        cells = hex_floor.floor_cells()
        self.assertEqual(cells, sorted(cells))
        for r, length in enumerate(hex_floor.ROW_LENGTHS):
            self.assertEqual(
                [cell for cell in cells if cell[0] == r],
                [(r, c) for c in range(length)],
            )
    
    def test_on_floor_validation(self):
        """Test on_floor function."""
        # Valid cells
        self.assertTrue(hex_floor.on_floor(0, 0))
        self.assertTrue(hex_floor.on_floor(7, 11))  # Last cell in full row
        
        # Invalid - beyond row length
        self.assertFalse(hex_floor.on_floor(0, 12))
        self.assertTrue(hex_floor.on_floor(8, 0))   # First short row
        self.assertFalse(hex_floor.on_floor(8, 5))  # Beyond short row
        self.assertFalse(hex_floor.on_floor(12, 0)) # Beyond final row


class TestNeighbors(unittest.TestCase):
    """Test neighbors function."""
    
    def test_center_cell_neighbors(self):
        """Test a center cell has 6 neighbors."""
        r, c = 4, 6
        neighbor_list = list(hex_floor.neighbors(r, c))
        self.assertEqual(len(neighbor_list), 6)
    
    def test_edge_cell_neighbors(self):
        """Test edge cells have fewer neighbors."""
        # First row, first column
        r, c = 0, 0
        neighbor_list = list(hex_floor.neighbors(r, c))
        self.assertLess(len(neighbor_list), 6)
    
    def test_neighbors_on_floor(self):
        """Test all neighbors are on floor."""
        for r, c in hex_floor.floor_cells():
            for nr, nc in hex_floor.neighbors(r, c):
                self.assertTrue(hex_floor.on_floor(nr, nc))


class TestWeightedPick(unittest.TestCase):
    """Test weighted_pick function."""
    
    def test_pick_from_non_empty(self):
        """Test picking from non-empty pool."""
        remaining = {"white": 10, "silver": 5}
        banned = set()
        color = hex_floor.weighted_pick(remaining, banned)
        self.assertIn(color, remaining.keys())
    
    def test_pick_excludes_banned(self):
        """Test banned colors are excluded."""
        remaining = {"white": 10, "silver": 5}
        banned = {"white"}
        color = hex_floor.weighted_pick(remaining, banned)
        self.assertNotEqual(color, "white")
    
    def test_empty_pool_returns_none(self):
        """Test empty pool returns None."""
        remaining = {"white": 0, "silver": 0}
        banned = set()
        color = hex_floor.weighted_pick(remaining, banned)
        self.assertIsNone(color)


class TestSolve(unittest.TestCase):
    """Test solve function."""
    
    def test_solve_finds_solution(self):
        """Test that solve returns a valid solution."""
        grid, attempts = hex_floor.solve(allow_white_exit=False)
        self.assertIsNotNone(grid)
        self.assertGreater(attempts, 0)
    
    def test_solution_has_correct_dimensions(self):
        """Test solution grid has correct dimensions."""
        grid, attempts = hex_floor.solve(allow_white_exit=False)
        self.assertEqual(len(grid), len(hex_floor.ROW_LENGTHS))
        for r, n in enumerate(hex_floor.ROW_LENGTHS):
            self.assertGreaterEqual(len(grid[r]), n)
    
    def test_solution_has_valid_colors(self):
        """Test all cells have valid colors."""
        grid, attempts = hex_floor.solve(allow_white_exit=False)
        valid_colors = set(hex_floor.POOL.keys())
        for r, c in hex_floor.floor_cells():
            self.assertIn(grid[r][c], valid_colors)
    
    def test_solution_no_adjacent_same(self):
        """Test no adjacent cells have same color."""
        grid, attempts = hex_floor.solve(allow_white_exit=False)
        for r, c in hex_floor.floor_cells():
            for nr, nc in hex_floor.neighbors(r, c):
                self.assertNotEqual(grid[r][c], grid[nr][nc])

    def test_default_solution_is_complete(self):
        grid, _ = hex_floor.solve()
        self.assertTrue(hex_floor.validate(grid))

    def test_final_recolor_is_valid(self):
        while True:
            grid, _ = hex_floor.solve()
            if hex_floor.recolor_to_white(grid) is not None:
                break
        self.assertTrue(hex_floor.validate(grid, final=True))


class TestWhiteBlobSize(unittest.TestCase):
    """Test _white_blob_size function."""
    
    def test_single_white_cell(self):
        """Test single white cell has blob size 1."""
        grid = [[None] * 12 for _ in hex_floor.ROW_LENGTHS]
        grid[0][0] = "white"
        size = hex_floor._white_blob_size(grid, 0, 0)
        self.assertEqual(size, 1)
    
    def test_two_connected_white_cells(self):
        """Test two connected white cells have blob size 2."""
        grid = [[None] * 12 for _ in hex_floor.ROW_LENGTHS]
        grid[0][0] = "white"
        grid[0][1] = "white"
        size = hex_floor._white_blob_size(grid, 0, 0)
        self.assertEqual(size, 2)


if __name__ == '__main__':
    unittest.main()
