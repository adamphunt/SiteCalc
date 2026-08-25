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
import random
from collections import Counter

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
    parser.add_argument("--seed", type=int, help="seed for a reproducible layout")
    parser.add_argument("--output", default="hex_floor.png", help="PNG output path")
    parser.add_argument("--no-png", action="store_true", help="skip PNG generation")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    random.seed(args.seed)
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
