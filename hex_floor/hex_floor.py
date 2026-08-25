#!/usr/bin/env python3
"""Lay out a bathroom floor of hexagonal tiles with no two same-color tiles touching.

Floor: 116 cells (L-shaped — a bathtub occupies the far corner, so the last rows are
short). We model the footprint as per-row lengths: tiled cells are the LEFT
`ROW_LENGTHS[r]` columns of each row.

Two-phase build, driven by how the tiles are actually SOLD (white in packs of 16, the
rest in packs of 25):
  1. Solve a balanced base — 29 each of white/silver/ducados/aqua — with no two
     same-color tiles touching.
  2. Randomly recolor 12 tiles to white (4 each from silver, ducados, aqua), giving a
     final 41 white / 25 silver / 25 ducados / 25 aqua. The recolor must not create a
     connected white blob of 3+ (isolated white PAIRS are allowed).

Placement walks the floor cells in reading order. At each cell we pick a color at
random, weighted by how many of that color REMAIN in the pool (a plentiful color is
likelier). A pick that would touch a same-color neighbor is rejected and we re-roll
among the colors still viable there. If a cell has no viable color, we backtrack: undo
the previous placement and forbid that choice, forcing a different path. If the pool
decays to only white, that's success and we stop.

Hex model: pointy-top hexagons in an "odd-r" offset grid (odd rows shoved right by
half a hex), so every interior cell has up to six neighbors — clipped to the floor
footprint, so short-row cells don't "touch" phantom tiles under the tub.
"""
import argparse
import json
import math
import random
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

# ── Pool ────────────────────────────────────────────────────────────────────
# name: (count, ascii-glyph, matplotlib color)
POOL = {
    # Colors sampled from Codicer "Basic Hex 25" product swatches.
    "white":   (29, "W", "#ffffff"),
    "silver":  (29, "S", "#acacac"),
    "ducados": (29, "D", "#5a6c7a"),   # muted denim blue-gray (darkened)
    "aqua":    (29, "A", "#82c4c5"),   # muted seafoam aqua
}
GLYPH = {c: g for c, (_, g, _) in POOL.items()}
FILL  = {c: f for c, (_, _, f) in POOL.items()}
EMPTY = "."

# ── Floor footprint ───────────────────────────────────────────────────────────
# The tiled cells are the LEFT ROW_LENGTHS[r] columns of each row; the rest is the
# bathtub cutout. 8 full rows of 12 + 4 short rows of 5 = 116 cells.
ROW_LENGTHS = [12] * 8 + [5] * 4


@dataclass(frozen=True)
class PolygonFloor:
    """A real-world floor outline and grout-aware hex grid candidate."""

    polygon: tuple[tuple[float, float], ...]
    tile_width: float
    grout_width: float = 0.0
    orientation: str = "pointy"
    offset_x: float = 0.0
    offset_y: float = 0.0
    perimeter_joint: float = 0.0

    def __post_init__(self):
        if len(self.polygon) < 3:
            raise ValueError("floor polygon needs at least three vertices")
        if self.tile_width <= 0:
            raise ValueError("tile_width must be positive")
        if self.grout_width < 0:
            raise ValueError("grout_width cannot be negative")
        if self.perimeter_joint < 0:
            raise ValueError("perimeter_joint cannot be negative")
        if self.orientation not in ("pointy", "flat"):
            raise ValueError("orientation must be 'pointy' or 'flat'")
        if abs(_signed_area(self.polygon)) < 1e-9:
            raise ValueError("floor polygon has zero area")
        edges = list(zip(self.polygon, self.polygon[1:] + self.polygon[:1]))
        for first_index, (a, b) in enumerate(edges):
            for second_index, (c, d) in enumerate(edges):
                if abs(first_index - second_index) <= 1 or {first_index, second_index} == {0, len(edges) - 1}:
                    continue
                if _segments_intersect(a, b, c, d):
                    raise ValueError("floor polygon edges cannot cross")

    @property
    def pitch(self):
        """Flat-to-flat center pitch, including grout."""
        return self.tile_width + self.grout_width

    @property
    def radius(self):
        """Tile center-to-corner radius, excluding grout."""
        return self.tile_width / math.sqrt(3)

    def center(self, row, col):
        min_x = min(point[0] for point in self.polygon)
        min_y = min(point[1] for point in self.polygon)
        if self.orientation == "pointy":
            x = self.pitch * (col + row / 2)
            y = self.pitch * math.sqrt(3) / 2 * row
        else:
            x = self.pitch * math.sqrt(3) / 2 * col
            y = self.pitch * (row + col / 2)
        return min_x + self.offset_x + x, min_y + self.offset_y + y

    def cells(self):
        """Grid cells whose physical tile intersects the floor polygon."""
        min_x = min(point[0] for point in self.polygon)
        max_x = max(point[0] for point in self.polygon)
        min_y = min(point[1] for point in self.polygon)
        max_y = max(point[1] for point in self.polygon)
        span = max(max_x - min_x, max_y - min_y)
        extent = math.ceil(span / (self.pitch * math.sqrt(3) / 2)) + 5
        result = []
        for row in range(-extent, extent + 1):
            for col in range(-extent, extent + 1):
                if _polygons_intersect(self.tile_polygon(row, col), self.polygon):
                    if _tile_coverage(self, (row, col)) > 0:
                        result.append((row, col))
        return sorted(result)

    def tile_polygon(self, row, col):
        cx, cy = self.center(row, col)
        start_angle = 30 if self.orientation == "pointy" else 0
        return tuple(
            (
                cx + self.radius * math.cos(math.radians(start_angle + 60 * index)),
                cy + self.radius * math.sin(math.radians(start_angle + 60 * index)),
            )
            for index in range(6)
        )


@dataclass(frozen=True)
class Doorway:
    name: str
    start: tuple[float, float]
    end: tuple[float, float]
    priority: float = 1.0
    alignment: str = "either"

    def __post_init__(self):
        if self.start == self.end:
            raise ValueError("doorway endpoints must differ")
        if self.priority <= 0:
            raise ValueError("doorway priority must be positive")
        if self.alignment not in ("tile", "grout", "either"):
            raise ValueError("doorway alignment must be tile, grout, or either")


@dataclass(frozen=True)
class LayoutSpec:
    floor: PolygonFloor
    doorways: tuple[Doorway, ...] = ()
    concealed_areas: tuple[tuple[tuple[float, float], ...], ...] = ()


def _signed_area(polygon):
    return sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1])
    ) / 2


def _point_in_polygon(point, polygon):
    """Return true for points inside or on the boundary of a simple polygon."""
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9:
            return True
        if (y1 > y) != (y2 > y):
            intersection_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < intersection_x:
                inside = not inside
    return inside


def _point_strictly_in_polygon(point, polygon):
    x, y = point
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) < 1e-9 and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9:
            return False
    return _point_in_polygon(point, polygon)


def _orientation(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(a, b, c, d):
    values = (_orientation(a, b, c), _orientation(a, b, d), _orientation(c, d, a), _orientation(c, d, b))
    if values[0] * values[1] < 0 and values[2] * values[3] < 0:
        return True
    return any(
        abs(value) < 1e-9 and min(p[0], q[0]) - 1e-9 <= r[0] <= max(p[0], q[0]) + 1e-9 and min(p[1], q[1]) - 1e-9 <= r[1] <= max(p[1], q[1]) + 1e-9
        for value, p, q, r in ((values[0], a, b, c), (values[1], a, b, d), (values[2], c, d, a), (values[3], c, d, b))
    )


def _polygons_intersect(first, second):
    if any(_point_strictly_in_polygon(point, second) for point in first):
        return True
    if any(_point_strictly_in_polygon(point, first) for point in second):
        return True
    first_edges = zip(first, first[1:] + first[:1])
    second_edges = list(zip(second, second[1:] + second[:1]))
    return any(
        _orientation(a, b, c) * _orientation(a, b, d) < 0
        and _orientation(c, d, a) * _orientation(c, d, b) < 0
        for a, b in first_edges for c, d in second_edges
    )


def _load_polygon_document(path):
    with Path(path).open(encoding="utf-8") as source:
        document = json.load(source)
    if document.get("units", "inches") not in ("inch", "inches", "in"):
        raise ValueError("floor coordinates must use inches")
    geometry = document.get("geometry", document)
    if geometry.get("type") == "Feature":
        geometry = geometry["geometry"]
    if geometry.get("type") == "Polygon":
        if len(geometry["coordinates"]) != 1:
            raise ValueError("polygon holes are not supported yet")
        coordinates = geometry["coordinates"][0]
    else:
        coordinates = document.get("polygon") or document.get("outline")
    if not coordinates:
        raise ValueError("floor JSON needs 'polygon'/'outline' or GeoJSON Polygon coordinates")
    if coordinates[0] == coordinates[-1]:
        coordinates = coordinates[:-1]
    return document, tuple((float(x), float(y)) for x, y in coordinates)


def load_polygon_floor(path, tile_width=None, grout_width=None):
    """Load a compact floor JSON document or a GeoJSON Polygon/Feature."""
    document, coordinates = _load_polygon_document(path)
    width = tile_width if tile_width is not None else document.get("tile_width")
    grout = grout_width if grout_width is not None else document.get("grout_width", 0.0)
    if width is None:
        raise ValueError("tile_width is required in the file or on the command line")
    return PolygonFloor(
        coordinates,
        float(width),
        float(grout),
        perimeter_joint=float(document.get("perimeter_joint", 0.0)),
    )


def load_layout_spec(path, tile_width=None, grout_width=None):
    """Load floor geometry plus doorway and concealed-area aesthetic metadata."""
    document, coordinates = _load_polygon_document(path)
    width = tile_width if tile_width is not None else document.get("tile_width")
    grout = grout_width if grout_width is not None else document.get("grout_width", 0.0)
    if width is None:
        raise ValueError("tile_width is required in the file or on the command line")
    floor = PolygonFloor(
        coordinates,
        float(width),
        float(grout),
        perimeter_joint=float(document.get("perimeter_joint", 0.0)),
    )
    doorways = tuple(
        Doorway(
            item.get("name", f"doorway-{index + 1}"),
            tuple(map(float, item["start"])),
            tuple(map(float, item["end"])),
            float(item.get("priority", 1)),
            item.get("alignment", "either"),
        )
        for index, item in enumerate(document.get("doorways", []))
    )
    concealed = tuple(
        tuple((float(x), float(y)) for x, y in polygon)
        for polygon in document.get("concealed_areas", [])
    )
    return LayoutSpec(floor, doorways, concealed)

def floor_cells():
    """Every (row, col) that gets a tile, in reading order."""
    return [(r, c) for r, n in enumerate(ROW_LENGTHS) for c in range(n)]

def on_floor(r, c):
    return 0 <= r < len(ROW_LENGTHS) and 0 <= c < ROW_LENGTHS[r]

# odd-r offset neighbors: even rows vs odd rows differ in the diagonal columns.
_NEIGH_EVEN = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
_NEIGH_ODD  = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]

def neighbors(r, c):
    """Neighbors clipped to the floor footprint (skips the bathtub cutout)."""
    deltas = _NEIGH_ODD if r % 2 else _NEIGH_EVEN
    for dr, dc in deltas:
        nr, nc = r + dr, c + dc
        if on_floor(nr, nc):
            yield nr, nc


def cell_neighbors(cell, cells):
    """Neighbors for an arbitrary, possibly concave polygon footprint."""
    r, c = cell
    # Polygon grids use axial coordinates for both pointy and flat orientations.
    deltas = ((0, 1), (0, -1), (1, 0), (-1, 0), (1, -1), (-1, 1))
    cell_set = cells if isinstance(cells, set) else set(cells)
    return [(r + dr, c + dc) for dr, dc in deltas if (r + dr, c + dc) in cell_set]


def balanced_counts(cell_count, colors=None):
    """Distribute an arbitrary tile count as evenly as possible across colors."""
    colors = tuple(colors or POOL)
    quotient, remainder = divmod(cell_count, len(colors))
    return {color: quotient + (index < remainder) for index, color in enumerate(colors)}


def solve_cells(cells, counts=None, max_attempts=10_000):
    """Color an arbitrary hex footprint with exact quotas and no equal neighbors."""
    order = sorted(set(cells), key=lambda cell: (cell[0], cell[1]))
    if not order:
        raise ValueError("floor polygon contains no tile cells")
    counts = dict(counts or balanced_counts(len(order)))
    if set(counts) - set(POOL):
        raise ValueError("counts contain an unknown color")
    if sum(counts.values()) != len(order) or any(value < 0 for value in counts.values()):
        raise ValueError("color counts must be non-negative and equal the cell count")
    cell_set = set(order)
    for attempt in range(1, max_attempts + 1):
        grid = {}
        remaining = counts.copy()
        banned = [set() for _ in order]
        index = steps = 0
        step_cap = max(1000, len(order) * 100)
        while index < len(order) and steps < step_cap:
            steps += 1
            cell = order[index]
            touching = {grid[neighbor] for neighbor in cell_neighbors(cell, cell_set) if neighbor in grid}
            color = weighted_pick(remaining, banned[index] | touching)
            if color is None:
                banned[index].clear()
                index -= 1
                if index < 0:
                    break
                previous = order[index]
                undone = grid.pop(previous)
                remaining[undone] += 1
                banned[index].add(undone)
                continue
            grid[cell] = color
            remaining[color] -= 1
            index += 1
        if index == len(order):
            return grid, attempt
    raise RuntimeError(f"no polygon layout found after {max_attempts} attempts")


def validate_cells(grid, cells, counts=None):
    cell_set = set(cells)
    if set(grid) != cell_set:
        raise ValueError("grid does not exactly cover the polygon cells")
    if any(color not in POOL for color in grid.values()):
        raise ValueError("grid contains an unknown color")
    for cell, color in grid.items():
        if any(grid[neighbor] == color for neighbor in cell_neighbors(cell, cell_set)):
            raise ValueError(f"adjacent {color} tiles at {cell}")
    if counts is not None and dict(Counter(grid.values())) != dict(counts):
        raise ValueError("grid does not match requested color counts")
    return True


def _distance(first, second):
    return math.hypot(first[0] - second[0], first[1] - second[1])


def _point_segment_distance(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    if dx == dy == 0:
        return _distance(point, start)
    ratio = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)))
    projection = start[0] + ratio * dx, start[1] + ratio * dy
    return _distance(point, projection)


def _inside_install_area(point, floor):
    if not _point_in_polygon(point, floor.polygon):
        return False
    if floor.perimeter_joint == 0:
        return True
    edges = zip(floor.polygon, floor.polygon[1:] + floor.polygon[:1])
    return min(_point_segment_distance(point, start, end) for start, end in edges) >= floor.perimeter_joint


def _tile_coverage(floor, cell):
    """Estimate the fraction of a tile lying inside the floor for cut scoring."""
    center = floor.center(*cell)
    vertices = floor.tile_polygon(*cell)
    samples = [center]
    samples.extend(vertices)
    samples.extend(((center[0] + x) / 2, (center[1] + y) / 2) for x, y in vertices)
    return sum(_inside_install_area(point, floor) for point in samples) / len(samples)


def _doorway_metrics(floor, doorway, cells):
    """Sample the threshold to assess jamb symmetry, slivers, and center alignment."""
    sample_count = 121
    labels = []
    for index in range(sample_count):
        ratio = index / (sample_count - 1)
        point = (
            doorway.start[0] + (doorway.end[0] - doorway.start[0]) * ratio,
            doorway.start[1] + (doorway.end[1] - doorway.start[1]) * ratio,
        )
        label = next(
            (cell for cell in cells if _point_in_polygon(point, floor.tile_polygon(*cell))),
            None,
        )
        labels.append(label)
    runs = []
    start = 0
    for index in range(1, len(labels) + 1):
        if index == len(labels) or labels[index] != labels[start]:
            runs.append((labels[start], start / (sample_count - 1), min(1.0, index / (sample_count - 1))))
            start = index
    tile_runs = [run for run in runs if run[0] is not None]
    doorway_length = _distance(doorway.start, doorway.end)
    widths = [(end - start) * doorway_length for _, start, end in tile_runs]
    end_widths = widths[:1] + widths[-1:] if widths else [0.0, 0.0]
    jamb_balance = 1.0 - min(1.0, abs(end_widths[0] - end_widths[-1]) / floor.tile_width)
    center_label = labels[sample_count // 2]
    center_in_grout = center_label is None
    centered_tile = 0.0
    if center_label is not None:
        run = next(run for run in tile_runs if run[0] == center_label and run[1] <= 0.5 <= run[2])
        centered_tile = 1.0 - min(1.0, abs((run[1] + run[2]) / 2 - 0.5) * 2)
    if doorway.alignment == "tile":
        alignment = centered_tile
    elif doorway.alignment == "grout":
        alignment = 1.0 if center_in_grout else 0.0
    else:
        alignment = max(centered_tile, 1.0 if center_in_grout else 0.0)
    return {
        "name": doorway.name,
        "alignment": alignment,
        "jamb_balance": jamb_balance,
        "threshold_pieces": len(tile_runs),
        "smallest_threshold_piece": min(widths, default=0.0),
        "center": "grout" if center_in_grout else "tile",
        "priority": doorway.priority,
    }


def evaluate_layout(floor, doorways=(), concealed_areas=()):
    """Score one grid phase/orientation, emphasizing visible edges and doorways."""
    cells = floor.cells()
    cut_coverages = {cell: _tile_coverage(floor, cell) for cell in cells}
    cut_cells = [cell for cell, coverage in cut_coverages.items() if coverage < 0.999]
    concealed = {
        cell for cell in cut_cells
        if any(_point_in_polygon(floor.center(*cell), area) for area in concealed_areas)
    }
    visible_cuts = [cell for cell in cut_cells if cell not in concealed]
    slivers = [cell for cell in visible_cuts if cut_coverages[cell] < 0.25]
    doorway_results = [_doorway_metrics(floor, doorway, cells) for doorway in doorways]
    score = 100.0
    score -= min(25.0, len(visible_cuts) * 0.35)
    score -= min(30.0, len(slivers) * 6.0)
    for result in doorway_results:
        weight = result["priority"]
        score -= (1 - result["alignment"]) * 12 * weight
        score -= (1 - result["jamb_balance"]) * 8 * weight
        if result["smallest_threshold_piece"] < floor.tile_width * 0.25:
            score -= 6 * weight
    interior_count = len(cells) - len(cut_cells)
    retained_cut_area = sum(cut_coverages[cell] for cell in cut_cells)
    reuse_purchase_estimate = interior_count + math.ceil(retained_cut_area * 1.15)
    cut_schedule = [
        {
            "cell": list(cell),
            "center": [round(value, 3) for value in floor.center(*cell)],
            "retained_percent_estimate": round(cut_coverages[cell] * 100),
            "visibility": "concealed" if cell in concealed else "visible",
        }
        for cell in sorted(cut_cells)
    ]
    return {
        "floor": floor,
        "cells": cells,
        "score": round(max(0.0, score), 2),
        "cut_tiles": len(cut_cells),
        "visible_cut_tiles": len(visible_cuts),
        "concealed_cut_tiles": len(concealed),
        "sliver_tiles": len(slivers),
        "estimated_offcut_tiles": round(sum(1 - cut_coverages[cell] for cell in cut_cells), 2),
        "tile_purchase_estimate": reuse_purchase_estimate,
        "potential_reuse_savings": max(0, len(cells) - reuse_purchase_estimate),
        "cut_schedule": cut_schedule,
        "doorways": doorway_results,
    }


def optimize_layout(spec, orientations=("pointy", "flat"), offset_steps=6, limit=3):
    """Rank grid orientation and phase candidates by edge and doorway aesthetics."""
    if offset_steps < 1:
        raise ValueError("offset_steps must be positive")
    candidates = []
    for orientation in orientations:
        for x_index in range(offset_steps):
            for y_index in range(offset_steps):
                floor = replace(
                    spec.floor,
                    orientation=orientation,
                    offset_x=spec.floor.pitch * x_index / offset_steps,
                    offset_y=spec.floor.pitch * y_index / offset_steps,
                )
                candidates.append(evaluate_layout(floor, spec.doorways, spec.concealed_areas))
    candidates.sort(
        key=lambda item: (
            item["score"], -item["sliver_tiles"], -item["visible_cut_tiles"],
            -item["estimated_offcut_tiles"],
        ),
        reverse=True,
    )
    return candidates[: max(1, limit)]

# ── ASCII render ──────────────────────────────────────────────────────────────
def render(grid):
    for r, n in enumerate(ROW_LENGTHS):
        indent = " " if r % 2 else ""          # shove odd rows right
        print(indent + "".join(f" {GLYPH.get(grid[r][c], EMPTY)} " for c in range(n)))

# ── Placement with backtracking ──────────────────────────────────────────────
def weighted_pick(remaining, banned):
    """Pick a color weighted by remaining count, excluding `banned` and empties."""
    choices = [(c, n) for c, n in remaining.items() if n > 0 and c not in banned]
    if not choices:
        return None
    colors, weights = zip(*choices)
    return random.choices(colors, weights=weights)[0]

def only_white_left(remaining):
    return remaining["white"] > 0 and all(n == 0 for c, n in remaining.items() if c != "white")

# Chronological backtracking occasionally paints into a far corner and then thrashes
# through an exponential number of unrelated undo/redo combinations. Since a fresh
# random attempt almost always succeeds in well under a millisecond, we cap the effort
# and RESTART rather than grind — far simpler and faster than smarter search ordering.
STEP_CAP = 1000                              # ~median×2000; bail past this and restart

def _attempt(allow_white_exit=False):
    """One backtracking attempt. Returns the filled grid, or None if it gave up
    (hit STEP_CAP or exhausted backtracking) — the caller restarts."""
    cols = max(ROW_LENGTHS)
    grid = [[None] * cols for _ in ROW_LENGTHS]
    remaining = {c: cnt for c, (cnt, _, _) in POOL.items()}
    order = floor_cells()

    banned = [set() for _ in order]          # per-cell colors already tried this visit
    i = steps = 0
    while i < len(order):
        steps += 1
        if steps > STEP_CAP:
            return None                      # thrashing — give up, restart fresh
        r, c = order[i]
        # Returning early here used to produce partially filled grids. Keep the
        # argument for API compatibility, but every successful result is complete.

        neigh = {grid[nr][nc] for nr, nc in neighbors(r, c)}
        color = weighted_pick(remaining, banned[i] | neigh)

        if color is None:                    # dead end: undo previous, forbid its choice
            banned[i] = set()
            i -= 1
            if i < 0:
                return None                  # no layout down this path
            pr, pc = order[i]
            undone = grid[pr][pc]
            grid[pr][pc] = None
            remaining[undone] += 1
            banned[i].add(undone)
            continue

        grid[r][c] = color
        remaining[color] -= 1
        i += 1
    return grid

def solve(allow_white_exit=False, max_attempts=10_000):
    """Solve via random restart and always return a completely filled grid."""
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        grid = _attempt(allow_white_exit)
        if grid is not None:
            return grid, attempts
    raise RuntimeError(f"no layout found after {max_attempts} attempts")

# ── Pack-driven recolor: swap some non-white tiles to white ───────────────────
# White is sold in packs of 16, the others in packs of 25. Starting from a balanced
# 29-each base, recoloring 4 each of silver/ducados/aqua to white yields the sellable
# 41 white (rounds up toward 3 packs) / 25 / 25 / 25 split — total unchanged at 116.
SWAP = {"silver": 4, "ducados": 4, "aqua": 4}

def _white_blob_size(grid, r, c):
    """Size of the connected white component containing (r,c), treating it as white."""
    seen, stack, size = {(r, c)}, [(r, c)], 0
    while stack:
        cr, cc = stack.pop()
        size += 1
        for nr, nc in neighbors(cr, cc):
            if (nr, nc) not in seen and ((nr, nc) == (r, c) or grid[nr][nc] == "white"):
                seen.add((nr, nc))
                stack.append((nr, nc))
    return size

def recolor_to_white(grid):
    """Randomly recolor SWAP[color] tiles of each color to white.

    A swap is rejected if it would grow a white component to 3+ (pairs are fine).
    Backtracks within each color's quota; returns the list of swapped (r,c,from_color)
    or None if this base layout can't absorb all the swaps (caller should re-solve).
    """
    swapped = []
    for color, quota in SWAP.items():
        cells = [(r, c) for r, c in floor_cells() if grid[r][c] == color]
        random.shuffle(cells)
        picked = _pick_swaps(grid, cells, 0, quota, color)
        if picked is None:                       # this color can't meet its quota
            for r, c, was in swapped:            # roll back all prior colors
                grid[r][c] = was
            return None
        swapped.extend((r, c, color) for r, c in picked)
    return swapped

def _pick_swaps(grid, cells, start, quota, from_color):
    """Backtracking choice of `quota` cells (from cells[start:]) to turn white without
    forming a white blob ≥ 3. Leaves picked cells set to 'white' on success."""
    if quota == 0:
        return []
    for idx in range(start, len(cells)):
        r, c = cells[idx]
        grid[r][c] = "white"                     # try it
        if _white_blob_size(grid, r, c) < 3:
            rest = _pick_swaps(grid, cells, idx + 1, quota - 1, from_color)
            if rest is not None:
                return [(r, c)] + rest
        grid[r][c] = from_color                  # undo, try next
    return None

# ── PNG output ────────────────────────────────────────────────────────────────
def save_png(grid, path="hex_floor.png"):
    import math
    import matplotlib.pyplot as plt
    from matplotlib.patches import RegularPolygon

    rows, cols = len(ROW_LENGTHS), max(ROW_LENGTHS)
    fig, ax = plt.subplots(figsize=(cols * 0.7 + 1, rows * 0.62 + 1))
    size = 1.0                                  # hex "radius" (center→vertex)
    w = math.sqrt(3) * size                     # pointy-top width
    vert = 1.5 * size                           # vertical row spacing
    for r, n in enumerate(ROW_LENGTHS):
        for c in range(n):                      # only draw tiled cells
            color = grid[r][c]
            if not color:
                continue
            x = c * w + (w / 2 if r % 2 else 0)
            y = -r * vert
            hexagon = RegularPolygon(
                (x, y), numVertices=6, radius=size,
                orientation=0, facecolor=FILL[color],
                edgecolor="#2b2b2b", linewidth=1.0,
            )
            ax.add_patch(hexagon)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def save_polygon_png(grid, floor, path="hex_floor.png", doorways=(), concealed_areas=()):
    """Render polygon tiles at real proportions and clip cuts to the boundary."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Polygon
    from matplotlib.path import Path as MatplotlibPath

    fig, ax = plt.subplots()
    clip_path = MatplotlibPath(floor.polygon + (floor.polygon[0],))
    clip_patch = PathPatch(clip_path, transform=ax.transData)
    for (row, col), color in grid.items():
        tile = Polygon(
            floor.tile_polygon(row, col),
            closed=True,
            facecolor=FILL[color],
            edgecolor="#2b2b2b",
            linewidth=0.8,
        )
        tile.set_clip_path(clip_patch)
        ax.add_patch(tile)
    outline = Polygon(floor.polygon, closed=True, fill=False, edgecolor="#111111", linewidth=2)
    ax.add_patch(outline)
    for area in concealed_areas:
        ax.add_patch(Polygon(area, closed=True, facecolor="none", edgecolor="#777777", hatch="///", linewidth=1))
    for doorway in doorways:
        ax.plot(
            (doorway.start[0], doorway.end[0]),
            (doorway.start[1], doorway.end[1]),
            color="#d1495b",
            linewidth=4,
            solid_capstyle="round",
        )
        midpoint = ((doorway.start[0] + doorway.end[0]) / 2, (doorway.start[1] + doorway.end[1]) / 2)
        ax.annotate(doorway.name, midpoint, color="#9b1c31", fontsize=8, xytext=(3, 3), textcoords="offset points")
    xs, ys = zip(*floor.polygon)
    margin = floor.tile_width
    ax.set_xlim(min(xs) - margin, max(xs) + margin)
    ax.set_ylim(min(ys) - margin, max(ys) + margin)
    ax.set_aspect("equal")
    if floor.perimeter_joint:
        # Matplotlib strokes use points, so convert the real-world joint width
        # from data inches after the axis transform has been established.
        fig.canvas.draw()
        origin_px = ax.transData.transform((0, 0))
        inch_px = ax.transData.transform((1, 0))[0] - origin_px[0]
        joint_points = floor.perimeter_joint * inch_px * 72 / fig.dpi
        boundary = floor.polygon + (floor.polygon[0],)
        bx, by = zip(*boundary)
        ax.plot(bx, by, color="white", linewidth=joint_points * 2, zorder=5)
        ax.plot(bx, by, color="#111111", linewidth=1.5, zorder=6)
        for doorway in doorways:
            ax.plot(
                (doorway.start[0], doorway.end[0]),
                (doorway.start[1], doorway.end[1]),
                color="#d1495b",
                linewidth=4,
                solid_capstyle="round",
                zorder=7,
            )
    ax.set_xlabel("inches")
    ax.set_ylabel("inches")
    ax.set_title(
        f"{floor.orientation.title()} hex · {floor.tile_width:g}\" tile · "
        f"{floor.grout_width:g}\" grout · {floor.perimeter_joint:g}\" perimeter joint"
    )
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")

# ── Main ────────────────────────────────────────────────────────────────────
def validate(grid, final=False):
    """Raise ``ValueError`` if a grid violates footprint or color constraints."""
    cells = floor_cells()
    if any(grid[r][c] not in POOL for r, c in cells):
        raise ValueError("grid has an empty or unknown tile")
    for r, c in cells:
        for nr, nc in neighbors(r, c):
            if grid[r][c] == grid[nr][nc] and (not final or grid[r][c] != "white"):
                raise ValueError(f"adjacent {grid[r][c]} tiles at {(r, c)} and {(nr, nc)}")
    if final:
        counts = Counter(grid[r][c] for r, c in cells)
        expected = {"white": 41, "silver": 25, "ducados": 25, "aqua": 25}
        if counts != expected:
            raise ValueError(f"unexpected final counts: {dict(counts)}")
        for r, c in cells:
            if grid[r][c] == "white" and _white_blob_size(grid, r, c) >= 3:
                raise ValueError("white component contains three or more tiles")
    return True


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--floor", help="polygon floor JSON or GeoJSON file")
    parser.add_argument("--tile-width", type=float, help="hex flat-to-flat width in inches")
    parser.add_argument("--grout-width", type=float, help="grout joint width in inches")
    parser.add_argument("--orientation", choices=("auto", "pointy", "flat"), default="auto")
    parser.add_argument("--offset-steps", type=int, default=6, help="grid phases per axis to evaluate")
    parser.add_argument("--alternatives", type=int, default=3, help="ranked layouts to display")
    parser.add_argument("--report", help="write detailed cut and scoring data as JSON")
    parser.add_argument("--seed", type=int, help="seed for a reproducible layout")
    parser.add_argument("--output", default="hex_floor.png", help="PNG output path")
    parser.add_argument("--no-png", action="store_true", help="skip PNG generation")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    random.seed(args.seed)
    if args.floor:
        try:
            spec = load_layout_spec(args.floor, args.tile_width, args.grout_width)
            orientations = ("pointy", "flat") if args.orientation == "auto" else (args.orientation,)
            layouts = optimize_layout(spec, orientations, args.offset_steps, args.alternatives)
            best = layouts[0]
            floor = best["floor"]
            cells = floor.cells()
            counts = balanced_counts(len(cells))
            grid, attempts = solve_cells(cells, counts)
            validate_cells(grid, cells, counts)
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"error: {exc}") from exc
        placed = Counter(grid.values())
        print(
            f"Polygon floor: {abs(_signed_area(floor.polygon)):.2f} sq in, "
            f"{len(cells)} tiles including perimeter cuts"
        )
        print(
            f"Tile width: {floor.tile_width:g}\"; grout: {floor.grout_width:g}\"; "
            f"pitch: {floor.pitch:g}\"; perimeter joint: {floor.perimeter_joint:g}\""
        )
        print("\nRanked layout options:")
        for index, layout in enumerate(layouts, 1):
            candidate = layout["floor"]
            print(
                f"  {index}. {candidate.orientation}, offset "
                f"({candidate.offset_x:.3f}, {candidate.offset_y:.3f})\": "
                f"score {layout['score']:.1f}, {layout['visible_cut_tiles']} visible cuts, "
                f"{layout['sliver_tiles']} slivers"
            )
            for doorway in layout["doorways"]:
                print(
                    f"     {doorway['name']}: center over {doorway['center']} "
                    f"({doorway['alignment'] * 100:.0f}% alignment), "
                    f"jamb balance {doorway['jamb_balance'] * 100:.0f}%, "
                    f"smallest threshold piece {doorway['smallest_threshold_piece']:.2f}\""
                )
        print(f"Solved in {attempts} attempt(s).")
        print("Placed:", ", ".join(f"{color}={placed[color]}" for color in POOL))
        print(
            f"Material estimate: {best['tile_purchase_estimate']} tiles with approximate "
            f"offcut reuse ({best['potential_reuse_savings']} potential tile savings)."
        )
        if args.report:
            report = {
                "floor_area_sq_in": abs(_signed_area(floor.polygon)),
                "selected": {
                    key: value for key, value in best.items()
                    if key not in ("floor", "cells")
                },
                "alternatives": [
                    {
                        "orientation": item["floor"].orientation,
                        "offset": [item["floor"].offset_x, item["floor"].offset_y],
                        **{key: value for key, value in item.items() if key not in ("floor", "cells", "cut_schedule")},
                    }
                    for item in layouts
                ],
            }
            Path(args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"Saved {args.report}")
        if not args.no_png:
            save_polygon_png(grid, floor, args.output, spec.doorways, spec.concealed_areas)
        return 0
    total = sum(cnt for cnt, _, _ in POOL.values())
    cells = len(floor_cells())
    if total != cells:
        print(f"⚠ pool has {total} tiles but floor has {cells} cells "
              f"({'surplus' if total > cells else 'shortfall'} of {abs(total - cells)}).")
    print(f"{total} tiles → L-shaped floor, {cells} cells\n")

    # Phase 1: balanced base (29 each), fully tiled — no white early-exit here.
    # Phase 2: pack-driven recolor to white. A rare base can't absorb the 12 swaps
    # without a white blob ≥ 3; re-solve until one can (converges in a try or two).
    attempts = 0
    while True:
        grid, tries = solve(allow_white_exit=False)
        attempts += tries
        swaps = recolor_to_white(grid)
        if swaps is not None:
            break
    validate(grid, final=True)
    render(grid)                                 # show the final floor
    print(f"Solved in {attempts} attempt(s).")

    placed = Counter(grid[r][c] for r, c in floor_cells())
    print(f"\nRecolored {len(swaps)} tiles to white "
          f"({', '.join(f'{k}×{v}' for k, v in SWAP.items())}).")
    print("Placed:", ", ".join(f"{c}={placed[c]}" for c in POOL))
    if not args.no_png:
        save_png(grid, args.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
