#!/usr/bin/env python3
"""Tests for hex_floor.py"""

import unittest
import sys
import os
import json
import math
import tempfile
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


class TestPolygonFloor(unittest.TestCase):
    def setUp(self):
        self.outline = ((0, 0), (12, 0), (12, 10), (5, 10), (5, 16), (0, 16))

    def test_grout_increases_center_pitch(self):
        without_grout = hex_floor.PolygonFloor(self.outline, tile_width=2, grout_width=0)
        with_grout = hex_floor.PolygonFloor(self.outline, tile_width=2, grout_width=0.25)
        self.assertAlmostEqual(without_grout.center(0, 1)[0] - without_grout.center(0, 0)[0], 2)
        self.assertAlmostEqual(with_grout.center(0, 1)[0] - with_grout.center(0, 0)[0], 2.25)

    def test_flat_orientation_rotates_grid_pitch(self):
        floor = hex_floor.PolygonFloor(self.outline, tile_width=2, grout_width=0.25, orientation="flat")
        self.assertAlmostEqual(floor.center(1, 0)[1] - floor.center(0, 0)[1], 2.25)
        self.assertAlmostEqual(
            floor.center(0, 1)[0] - floor.center(0, 0)[0],
            math.sqrt(3) / 2 * 2.25,
        )

    def test_concave_polygon_generates_intersecting_cells(self):
        floor = hex_floor.PolygonFloor(self.outline, tile_width=2, grout_width=0.125)
        cells = floor.cells()
        self.assertGreater(len(cells), 0)
        self.assertEqual(len(cells), len(set(cells)))
        for cell in cells:
            self.assertTrue(hex_floor._polygons_intersect(floor.tile_polygon(*cell), floor.polygon))

    def test_polygon_solver_is_balanced_and_valid(self):
        floor = hex_floor.PolygonFloor(self.outline, tile_width=3, grout_width=0.125)
        cells = floor.cells()
        counts = hex_floor.balanced_counts(len(cells))
        grid, attempts = hex_floor.solve_cells(cells, counts)
        self.assertGreater(attempts, 0)
        self.assertTrue(hex_floor.validate_cells(grid, cells, counts))

    def test_loads_compact_json_and_cli_overrides(self):
        document = {
            "units": "inches",
            "polygon": self.outline,
            "tile_width": 2,
            "grout_width": 0.125,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as stream:
            json.dump(document, stream)
            path = stream.name
        try:
            floor = hex_floor.load_polygon_floor(path, tile_width=2.5, grout_width=0.25)
        finally:
            os.unlink(path)
        self.assertEqual(floor.tile_width, 2.5)
        self.assertEqual(floor.grout_width, 0.25)

    def test_invalid_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            hex_floor.PolygonFloor(((0, 0), (1, 1), (2, 2)), tile_width=1)
        with self.assertRaises(ValueError):
            hex_floor.PolygonFloor(((0, 0), (2, 2), (0, 2), (2, 0)), tile_width=1)

    def test_boundary_touch_alone_is_not_an_intersection(self):
        left = ((0, 0), (1, 0), (1, 1), (0, 1))
        right = ((1, 0), (2, 0), (2, 1), (1, 1))
        self.assertFalse(hex_floor._polygons_intersect(left, right))

    def test_optimizer_ranks_doorway_aware_alternatives(self):
        floor = hex_floor.PolygonFloor(self.outline, tile_width=3, grout_width=0.125)
        doorway = hex_floor.Doorway("entry", (0, 2), (0, 8), priority=2, alignment="tile")
        spec = hex_floor.LayoutSpec(floor, (doorway,))
        layouts = hex_floor.optimize_layout(spec, offset_steps=2, limit=2)
        self.assertEqual(len(layouts), 2)
        self.assertGreaterEqual(layouts[0]["score"], layouts[1]["score"])
        self.assertEqual(layouts[0]["doorways"][0]["name"], "entry")
        self.assertIn(layouts[0]["floor"].orientation, ("pointy", "flat"))

    def test_loads_doorways_concealed_areas_and_perimeter_joint(self):
        document = {
            "polygon": self.outline,
            "tile_width": 3,
            "grout_width": 0.125,
            "perimeter_joint": 0.25,
            "doorways": [{"name": "entry", "start": [0, 2], "end": [0, 8]}],
            "concealed_areas": [[[8, 0], [12, 0], [12, 3], [8, 3]]],
            "excluded_areas": [[[0, 10], [5, 10], [5, 16], [0, 16]]],
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as stream:
            json.dump(document, stream)
            path = stream.name
        try:
            spec = hex_floor.load_layout_spec(path)
        finally:
            os.unlink(path)
        self.assertEqual(spec.floor.perimeter_joint, 0.25)
        self.assertEqual(spec.doorways[0].name, "entry")
        self.assertEqual(len(spec.concealed_areas), 1)
        self.assertEqual(len(spec.excluded_areas), 1)

    def test_excluded_area_removes_only_fully_excluded_cells(self):
        floor = hex_floor.PolygonFloor(self.outline, tile_width=3, grout_width=0.125)
        excluded = (((0, 10), (5, 10), (5, 16), (0, 16)),)
        result = hex_floor.evaluate_layout(floor, excluded_areas=excluded)
        self.assertLess(len(result["cells"]), len(floor.cells()))
        self.assertTrue(
            all(hex_floor._tile_coverage(floor, cell, excluded) > 0 for cell in result["cells"])
        )

    def test_loads_color_inventory(self):
        document = {
            "polygon": self.outline,
            "tile_width": 3,
            "inventory": {"white": 50, "silver": 25, "ducados": 25, "aqua": 25},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as stream:
            json.dump(document, stream)
            path = stream.name
        try:
            spec = hex_floor.load_layout_spec(path)
        finally:
            os.unlink(path)
        self.assertEqual(spec.inventory["white"], 50)

    def test_inventory_purchase_plan_leaves_only_white(self):
        usage = {"white": 57, "silver": 25, "ducados": 25, "aqua": 25}
        inventory = {"white": 50, "silver": 25, "ducados": 25, "aqua": 25}
        shortage, packs, leftovers = hex_floor.inventory_purchase_plan(usage, inventory)
        self.assertEqual(shortage, {"white": 7, "silver": 0, "ducados": 0, "aqua": 0})
        self.assertEqual(packs["white"], 1)
        self.assertEqual(leftovers, {"white": 9, "silver": 0, "ducados": 0, "aqua": 0})

    def test_spatial_penalty_prefers_distributed_colors(self):
        floor = hex_floor.PolygonFloor(((0, 0), (20, 0), (20, 5), (0, 5)), 2)
        cells = [(0, col) for col in range(8)]
        concentrated = {
            cell: "white" if index < 4 else "silver"
            for index, cell in enumerate(cells)
        }
        distributed = {
            cell: "white" if index % 2 == 0 else "silver"
            for index, cell in enumerate(cells)
        }
        self.assertLess(
            hex_floor.spatial_color_penalty(distributed, floor),
            hex_floor.spatial_color_penalty(concentrated, floor),
        )

    def test_door_swings_inward_from_right_endpoint(self):
        floor = hex_floor.PolygonFloor(((0, 0), (20, 0), (20, 10), (0, 10)), 2)
        doorway = hex_floor.Doorway(
            "entry", (4, 0), (10, 0), hinge="end", swing="inward"
        )
        geometry = hex_floor.door_swing_geometry(floor, doorway)
        self.assertEqual(geometry["hinge"], (10, 0))
        self.assertAlmostEqual(geometry["open_end"][0], 10)
        self.assertAlmostEqual(geometry["open_end"][1], 6)
        self.assertEqual(len(geometry["arc"]), 31)


if __name__ == '__main__':
    unittest.main()
