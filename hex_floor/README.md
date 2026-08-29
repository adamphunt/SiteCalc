# Hex Floor Layout

A Python tool for generating optimized hexagonal tile layouts with color balance and no adjacent same-color tiles.

It supports both the original row-based bathroom footprint and real-world floor
polygons measured in inches. Polygon layouts include partially cut perimeter tiles
and use grout width when calculating hex center spacing.

## Overview

This tool creates balanced layouts for L-shaped bathroom floors with hexagonal tiles. It ensures:
- No two adjacent tiles have the same color
- Color distribution matches tile pack sizes (white in 16-packs, others in 25-packs)
- No large connected white areas (pairs allowed, 3+ blobs avoided)

## Features

- **Hexagonal grid layout**: Models pointy-top hexagons in odd-r offset grid
- **Backtracking solver**: Finds valid color arrangements
- **Balanced color distribution**: 41 white / 25 each of 3 other colors
- **Avoids white clusters**: Prevents connected white areas of 3+ tiles
- **PNG output**: Generates visual output with matplotlib
- **Aesthetic optimization**: Ranks pointy/flat orientations and grid offsets
- **Doorway-aware scoring**: Favors centered thresholds, balanced jamb cuts, and no slivers
- **Visibility weighting**: De-emphasizes cuts hidden beneath cabinets and fixtures
- **Cut report**: Exports retained-area estimates and approximate offcut reuse

## Usage

```bash
# Run with default settings
python3 hex_floor.py

# With a reproducible seed and custom image path
python3 hex_floor.py --seed 42 --output layout.png

# Validate and print a layout without requiring matplotlib
python3 hex_floor.py --seed 42 --no-png

# Generate an L-shaped floor from measured coordinates
python3 hex_floor.py --floor example_floor.json --seed 42 --output polygon_floor.png

# Override tile and grout dimensions from the command line
python3 hex_floor.py --floor example_floor.json --tile-width 8 --grout-width 0.1875

# Compare more grid phases and write the detailed cut report
python3 hex_floor.py --floor example_floor.json --offset-steps 8 --alternatives 5 \
  --report layout_report.json
```

## Polygon input

JSON coordinates are the recommended input because they are readable, diffable,
and use the same `[x, y]` structure as GeoJSON. Measure vertices around the finished
floor boundary in order—clockwise or counterclockwise—without crossing edges:

```json
{
  "units": "inches",
  "polygon": [[0, 0], [96, 0], [96, 60], [36, 60], [36, 108], [0, 108]],
  "tile_width": 8,
  "grout_width": 0.125,
  "perimeter_joint": 0.25,
  "inventory": {"white": 50, "silver": 25, "ducados": 25, "aqua": 25},
  "doorways": [
    {
      "name": "hall doorway",
      "start": [4, 108],
      "end": [34, 108],
      "priority": 2,
      "alignment": "either",
      "hinge": "end",
      "swing": "inward"
    }
  ],
  "concealed_areas": [
    [[72, 0], [96, 0], [96, 24], [72, 24]]
  ],
  "excluded_areas": [
    [[0, 60], [30, 60], [30, 108], [0, 108]]
  ]
}
```

`tile_width` is the physical flat-to-flat hex width. `grout_width` is added to
the grid pitch, so an 8-inch tile with 1/8-inch grout has an 8.125-inch pitch.
Tiles that intersect the outline are counted, including perimeter tiles that must
be cut. The PNG clips those tiles to the floor boundary.

Doorway endpoints should follow the threshold segment along the polygon boundary.
Set `alignment` to `tile`, `grout`, or `either`; higher numeric `priority` values
give important entrances more influence. To draw a door leaf and swing arc, set
`hinge` to `start` or `end` and `swing` to `inward` or `outward`; start/end refer to
the two doorway coordinates. `concealed_areas` mark cabinets, vanities,
or other places that are tiled underneath but where edge cuts are not visually
important. `excluded_areas` mark permanent untiled footprints such as bathtubs or
shower bases; intersecting perimeter tiles are cut to their edges. `perimeter_joint`
reserves movement space along walls and excluded-area boundaries.

An optional `inventory` object enables material-aware layout ranking and coloring.
The solver estimates same-color offcut reuse, consumes the colored inventory first,
assigns any unavoidable shortage to white, and reports packs to buy and projected
leftovers. White is assumed to come in packs of 16; the three colors use packs of 25.
Candidate colorings are compared across horizontal and vertical room bands to avoid
color drift toward one end of the room. The strongest feasible adjacency rule is
used: isolated whites first, then pairs, with larger groups only as a last resort.

By default, the optimizer compares pointy- and flat-top grids across six offsets
per axis. It ranks layouts using visible cut count, severe slivers, doorway-center
alignment, jamb symmetry, threshold piece width, and approximate material reuse.
The first option is rendered. More offset steps improve resolution but increase
runtime quadratically.

The JSON report includes every perimeter tile's grid cell, center point, estimated
retained percentage, and visibility. Offcut reuse is an area-based planning estimate,
not a guaranteed cutting plan; irregular shapes and saw losses can reduce real reuse.

See [ROADMAP.md](ROADMAP.md) for proposed geometry, editor, installation, inventory,
and export improvements.

The loader also accepts a GeoJSON `Polygon` or `Feature` with Polygon geometry.
Only the exterior ring is currently used; holes are not yet supported. Coordinates
are interpreted as inches, so projected longitude/latitude GeoJSON is not suitable.

## Example Output

```
29 white tiles, 29 silver, 29 ducados, 29 aqua = 116 total

W S W S W S
 S W S W S W
W D A W D A
 A W D A W D
W S W S W S
 S W S W S W
W D A W D A
 A W D A W W
    W S W
    S W S
    W D A
    A W S

Recolored 12 tiles to white (silver×4, ducados×4, aqua×4).
Placed: white=41, silver=25, ducados=25, aqua=25

Saved hex_floor.png
```

## Installation

```bash
# Clone the repository
git clone https://github.com/adamphunt/SiteCalc.git
cd SiteCalc/hex_floor

# Install dependencies
pip install matplotlib

# Run
python3 -m unittest -v test_hex_floor.py
```

## Tile Colors

| Color | Pack Size | Glyph |
|-------|-----------|-------|
| White | 16 tiles | W |
| Silver | 25 tiles | S |
| Ducados | 25 tiles | D |
| Aqua | 25 tiles | A |

## Floor Layout

The tool is configured for an L-shaped floor with:
- 8 full rows of 12 tiles
- 4 short rows of 5 tiles (bathtub cutout)
- Total: 116 tiles

The floor model is in `ROW_LENGTHS` and can be customized.

## API

### `solve(allow_white_exit=False)`
Runs the backtracking solver to find a valid tile layout.

**Returns:** `(grid, attempts)` - the filled grid and number of attempts

### `save_png(grid, path="hex_floor.png")`
Saves the layout as a PNG image with matplotlib.

### `load_polygon_floor(path, tile_width=None, grout_width=None)`
Loads compact JSON or a GeoJSON Polygon and returns grout-aware geometry.

### `solve_cells(cells, counts=None)`
Colors an arbitrary polygon-derived footprint with balanced color quantities.

### `optimize_layout(spec, orientations=("pointy", "flat"), offset_steps=6, limit=3)`
Ranks orientation and grid-phase alternatives using edge and doorway aesthetics.

### `render(grid)`
Prints ASCII representation to stdout.

## Testing

```bash
# Run the tool (includes self-validation)
python3 hex_floor.py

# Import and test in Python
python3 -c "
import hex_floor
grid, attempts = hex_floor.solve()
print(f'Solved in {attempts} attempts')
"
```

## License

MIT License
