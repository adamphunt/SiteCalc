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
python3 lumber_optimizer.py needed_lengths.txt scrap.txt 0.125
```

### Input Files

**needed_lengths.txt** - Board lengths needed (in inches, one per line):
```
# My fence boards (all values in inches)
102    # 8.5 feet
144    # 12 feet
75     # 6.25 feet
```

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
kerf                - Saw blade width in inches (default: 0.125 = 1/8")
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
python3 test_lumber_optimizer.py
```

## Testing

```bash
python3 test_lumber_optimizer.py
```

## License

MIT License
