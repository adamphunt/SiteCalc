# Deck Layout Calculator

A Python tool for optimizing deck board layouts with minimal cuts and even spacing.

## Overview

This tool calculates the optimal arrangement of deck boards (small, medium, and large sizes) to cover a given deck length while maintaining even spacing between boards.

## Features

- **Automated Layout Calculation**: Determines optimal board arrangement based on deck length
- **Border Support**: Handles border adjustments on both sides of the deck
- **Flexible Board Sizes**: Works with standard deck board sizes (small, medium, large)
- **Gap Adjustment**: Calculates optimal gap spacing when boards don't divide evenly

## Usage

```bash
# Basic usage - no border, starting with small board
python3 deck_layout.py 12.5

# With border and custom starting size
python3 deck_layout.py 12.5 1 2

# Arguments:
#   length       - Deck length in feet (e.g., 12.5 for 12'6")
#   start_size   - Starting board size (0=small, 1=medium, 2=large)
#   border       - Border width in inches on each side (default: 0)
```

## Board Sizes

| Size | Length (feet) |
|------|---------------|
| Small | 3' 7" (3.46) |
| Medium | 5' 7" (5.44) |
| Large | 7' 3" (7.19) |

## Example Output

```
==================================================
DECK LAYOUT RESULTS
==================================================

Total deck length: 12.50'
Border each side:  2.0"
Available space:   12.00'

Board counts:
  Large boards:   1
  Medium boards:  2
  Small boards:   1
  Total boards:   4

Gap adjustment:    0.875"
==================================================
```

## Installation

```bash
# Clone the repository
git clone https://github.com/adamphunt/SiteCalc.git
cd SiteCalc/deck_layout

# Make executable (optional)
chmod +x deck_layout.py

# Run tests
python3 test_deck_layout.py
```

## Testing

Run the test suite to verify functionality:

```bash
python3 test_deck_layout.py
```

Tests cover:
- Layout calculation with various lengths
- Border adjustments
- Different starting sizes
- Edge cases

## License

MIT License - see LICENSE file for details.
