# Multi-width Deck Layout Calculator

A Python tool for optimizing multi-width deck board layouts with visual design principles in mind.

## Overview

This tool calculates optimal deck board layouts that balance:
- **Minimal waste** - Use the deck width efficiently
- **Proper spacing** - Maintain consistent gaps between boards
- **Visual harmony** - Avoid patterns that draw attention to inconsistencies

## Visual Design Principles

The tool implements key principles for creating pleasing deck patterns:

### What Makes Patterns Look Good
1. **Consistent spacing** - Uniform gaps create visual rhythm
2. **Repetition** - Patterns that repeat are pleasing to the eye
3. **Balance** - Symmetrical or balanced arrangements feel stable
4. **Width consistency** - All boards of the same type should be identical width

### What Makes Patterns Look Out of Place
1. **Very thin trimmed boards** - Anything below ~2.5" looks weak/noticeable
2. **Inconsistent spacing** - Uneven gaps draw attention
3. **Too many board types in one row** - 4+ different widths looks chaotic
4. **Random placements without pattern** - Feels accidental

### Tablesaw Trimming
When spacing is out of the recommended range (0.25"-0.5"), the tool can trim boards on a tablesaw to achieve proper spacing. However, trim amounts are calculated to ensure:
- Trimmed boards remain within 1/8" of standard widths (3.5", 5.5", 7.25")
- Trimmed boards are never below 2.5" (which would look too thin)

## Features

- **Multi-width board support**: Narrow (3.5"), Standard (5.5"), Wide (7.25")
- **Pattern optimization**: Finds best patterns for your deck width
- **Spacing optimization**: Calculates optimal gaps between boards
- **Automatic border adjustment**: Handles border spacing requirements
- **Tablesaw trimming guidance**: Suggests trim amounts when needed

## Usage

```bash
# Find the best pattern for your deck width
python3 deck_layout.py 120

# Use a specific pattern with custom spacing
python3 deck_layout.py 120 N-S-W 0.375

# With border requirements
# (Border support will be added in future versions)
```

## Board Sizes

| Size | Width (inches) | Feet equivalent |
|------|---------------|-----------------|
| Narrow | 3.5" | 0' 3.5" |
| Standard | 5.5" | 0' 5.5" |
| Wide | 7.25" | 0' 7.25" |

## Available Patterns

```
N-S:    Narrow → Standard
S-N:    Standard → Narrow
N-S-W:  Narrow → Standard → Wide
W-S-N:  Wide → Standard → Narrow
S-W-N:  Standard → Wide → Narrow
W-N-S:  Wide → Narrow → Standard
N-W-S:  Narrow → Wide → Standard
S-N-W:  Standard → Narrow → Wide
W-N:    Wide → Narrow
N-W:    Narrow → Wide
S-W:    Standard → Wide
W-S:    Wide → Standard
```

## Example Output

```
======================================================================
DECK LAYOUT OPTIMIZATION FOR 120.0" WIDE DECK
======================================================================

Top Recommendations (sorted by quality score):

1. Pattern: S-W
   Spacing: 0.375" (0.375" actual)
   Score: 95.0/100
   Board count: 12 boards
   Breakdown:
     - 5.5" boards: 6
     - 7.25" boards: 6
   Waste: 0.00"

2. Pattern: N-S-W
   Spacing: 0.375" (0.375" actual)
   Score: 90.0/100
   ...
```

## Installation

```bash
git clone https://github.com/adamphunt/SiteCalc.git
cd SiteCalc/deck_layout

# Make executable (optional)
chmod +x deck_layout.py

# Run tests
python3 test_deck_layout.py
```

## Score Calculation

Patterns are scored (0-100) based on:

1. **Waste score (40%)** - How much material is wasted
2. **Spacing score (30%)** - How close to optimal spacing
3. **Board count score (30%)** - Appropriate number of boards (5-15 preferred)
4. **Trim penalty** - Additional penalty for patterns requiring tablesaw trimming

## License

MIT License
