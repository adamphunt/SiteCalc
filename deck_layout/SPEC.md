# Deck Layout Specification

## Requirements

### Core Functionality

1. **Calculate deck board layout**
   - Given a deck length, determine optimal board arrangement
   - Handle fractional lengths (e.g., 12.5 for 12'6")

2. **Support three board sizes**
   - Small: 3' 7" (3.46 feet)
   - Medium: 5' 7" (5.44 feet)
   - Large: 7' 3" (7.19 feet)

3. **Handle border adjustments**
   - Support border width on each side
   - Adjust available space accordingly

4. **Calculate gap adjustment**
   - When boards don't divide evenly, calculate uniform gap
   - Account for board gaps (1/8" default)

### Input

```
Arguments:
  length       - Deck length in feet
  start_size   - Starting board size index (0, 1, or 2)
  border       - Border width in inches (default: 0)
```

### Output

```
- Total deck length
- Border width (each side)
- Board counts by size
- Total boards used
- Final gap adjustment
- Remaining space (should be < smallest board)
```

## Implementation Details

### Algorithm

1. Calculate available space: `length - 2 * border - gap`
2. Start with specified board size index
3. Place boards in sequence (small → medium → large → repeat)
4. For each board:
   - Check if remaining space >= board size
   - If yes, place board and reduce remaining space
   - Subtract board size + gap from remaining
5. When remaining < smallest board:
   - Calculate final gap: `remaining / num_gaps`
   - Return results

### Edge Cases

- **Very short decks** (< smallest board): Should handle gracefully
- **Zero border**: Should work without adjustment
- **Exact fit**: Remaining should be 0 or very small
- **Large deck**: Should scale appropriately

### Test Cases

| Input | Expected Behavior |
|-------|-------------------|
| 12.0 ft, no border | Should produce multiple boards with gap |
| 3.0 ft, no border | Should handle short deck |
| 20.0 ft, 2" border | Should adjust for border |
| 15.0 ft, start=2 | Should start with large board |
| 10.0 ft, start=0, border=1 | Should handle all parameters |

## File Structure

```
deck_layout/
├── deck_layout.py      # Main implementation
├── test_deck_layout.py # Unit tests
├── README.md           # User documentation
└── SPEC.md            # This specification
```
