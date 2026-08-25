# Hex Floor Layout

A Python tool for generating optimized hexagonal tile layouts with color balance and no adjacent same-color tiles.

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

## Usage

```bash
# Run with default settings
python3 hex_floor.py

# With a reproducible seed and custom image path
python3 hex_floor.py --seed 42 --output layout.png

# Validate and print a layout without requiring matplotlib
python3 hex_floor.py --seed 42 --no-png
```

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

### `solve(allow_white_exit=True)`
Runs the backtracking solver to find a valid tile layout.

**Returns:** `(grid, attempts)` - the filled grid and number of attempts

### `save_png(grid, path="hex_floor.png")`
Saves the layout as a PNG image with matplotlib.

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
