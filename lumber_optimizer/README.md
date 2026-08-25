# Lumber Optimizer

A Python tool that minimizes new lumber purchases by using scrap first, then optimizing bin packing for new stock.

## Overview

The Lumber Optimizer uses the Best Fit Decreasing (BFD) heuristic for bin packing to:
- Use available scrap lumber first
- Optimize cutting from new stock boards
- Account for blade kerf (saw width) when calculating cuts
- Provide detailed optimization results

## Features

- **Scrap-first optimization**: Uses scrap pieces before buying new stock
- **Bin packing algorithm**: Best Fit Decreasing (BFD) heuristic
- **Kerf accounting**: Accounts for saw blade width when calculating cuts
- **Flexible stock sizes**: Supports custom stock lengths (default: 16', 20')

## Usage

```bash
# Basic usage - just needed lengths
python3 lumber_optimizer.py needed_lengths.txt

# With scrap and custom kerf
python3 lumber_optimizer.py needed_lengths.txt scrap.txt --kerf 1/8

# Custom available stock lengths and inch-based output
python3 lumber_optimizer.py needed_lengths.txt --stock 8 10 12 --inches
```

### Input Files

**needed_lengths.txt** - Board lengths needed (in inches, one per line):
```
# My fence boards (all values in inches)
102    # 8.5 feet
144    # 12 feet
75     # 6.25 feet
2@164 3/4  # two pieces, each 164 3/4 inches
10' 9 1/4" # explicit feet and inches; equal to 129 1/4 inches
```

Prefix a length with `quantity@` to request repeated identical pieces. Whitespace
around `@` is optional. Quantities must be positive whole numbers.

Values without unit marks are interpreted as inches. Architectural notation accepts
feet-only (`10'`), inches-only (`9 1/4"`), combined feet and inches (`10' 9 1/4"`),
and Unicode prime marks (`10′ 9 1/4″`).

**scrap.txt** - Available scrap pieces (optional, in inches):
```
# Available scrap pieces
120
96
72
```

### Arguments

```
needed_lengths.txt  - File with needed board lengths (inches)
scrap.txt           - File with scrap lengths (optional)
--kerf              - Saw blade width in inches (default: 1/8)
--stock             - Available stock lengths in feet (default: 16 20)
--inches            - Display cut lengths in inches
```

## Example Output

```
============================================================
LUMBER ORDER OPTIMIZATION RESULTS
============================================================

📊 Statistics:
  Total length needed:      58.00'
  Total scrap available:    21.00'
  Scrap used:               18.00'
  New stock purchased:      48.00'
  Total waste:              6.00'
  New stock pieces:         3

  Remaining scrap:          3 pieces
    Remaining length:       8.50'
    - 10.00' piece
    - 5.00' piece
    - 3.50' piece

📋 New Stock Orders (each line shows pieces from one stock):
  Stock 1 (14.50'): 10.00" + 8.50"
    Kerf waste (2 cuts): 0.167"
    Total material used: 14.667"

💡 Recommended Purchases:
  - 16' boards: 2
  - 20' boards: 1

⚙️  Settings:
  Blade kerf (saw width): 0.125" (1/8" default)
```

## Installation

```bash
# Clone the repository
git clone https://github.com/adamphunt/SiteCalc.git
cd SiteCalc/lumber_optimizer

# Make executable (optional)
chmod +x lumber_optimizer.py

# Run tests
python3 -m unittest -v test_lumber_optimizer.py
```

## Testing

```bash
python3 test_lumber_optimizer.py
```

## License

MIT License
