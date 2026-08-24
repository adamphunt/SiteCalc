# Hex Floor Layout Specification

## Requirements

### Core Functionality

1. **Tile placement on hexagonal grid**
   - Pointy-top hexagons in odd-r offset grid
   - Each tile has up to 6 neighbors (clipped to floor footprint)
   - Tiles placed in reading order (row by row, left to right)

2. **Color constraints**
   - No two adjacent tiles can have the same color
   - Color pool: 29 each of white/silver/ducados/aqua
   - Final distribution: 41 white / 25 each of other colors

3. **Pack-driven recoloring**
   - Start with balanced 29-each pool
   - Recolor 4 tiles of each non-white color to white
   - Recoloring must not create white blobs of 3+ tiles

4. **Output**
   - ASCII rendering of layout
   - PNG image with matplotlib
   - Final color counts

### Hex Grid Model

**Odd-r offset coordinates:**
- Even rows: normal x coordinates
- Odd rows: shifted right by half a hex width

**Neighbors:**
- Even rows: [(-1,-1), (-1,0), (0,-1), (0,1), (1,-1), (1,0)]
- Odd rows: [(-1,0), (-1,1), (0,-1), (0,1), (1,0), (1,1)]

### Algorithm

**Phase 1: Base Layout**
1. Pick colors weighted by remaining count (plentiful colors more likely)
2. Reject colors that would touch same-color neighbors
3. Backtrack on dead ends (limit: 1000 steps, then restart)
4. Exit early when only white remains (no conflicts possible)

**Phase 2: Pack-Driven Recolor**
1. For each non-white color (silver, ducados, aqua):
   - Randomly select tiles to recolor to white
   - Reject swaps that would create white blobs of 3+
   - Backtrack within each color's quota
2. If recoloring fails, restart Phase 1

### Input

No user input required. Configuration is in code:
- `POOL`: Color definitions (count, glyph, matplotlib color)
- `ROW_LENGTHS`: Floor footprint (tiles per row)
- `SWAP`: Tiles to recolor to white per color

### Output

```
ASCII rendering (W=white, S=silver, D=ducados, A=aqua)
Final color counts
PNG image (optional)
```

## Test Cases

| Scenario | Expected |
|----------|----------|
| 116 cells, 116 tiles | Perfect fit |
| No adjacent same colors | Valid layout |
| 41 white tiles | Pack-driven recolor successful |
| No white blob ≥ 3 | Recoloring constraint satisfied |

## File Structure

```
hex_floor/
├── hex_floor.py     # Main implementation
├── README.md        # User documentation
└── SPEC.md          # This specification
```

## Dependencies

- Python 3.6+
- matplotlib (for PNG output)

## Configuration

The floor layout is defined by `ROW_LENGTHS`:
```python
ROW_LENGTHS = [12] * 8 + [5] * 4  # 8 rows of 12, 4 rows of 5
```

Modify this to change the floor shape.
