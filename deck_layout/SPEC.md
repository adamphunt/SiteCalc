# Deck Layout Specification

## Requirements

### Core Functionality

1. **Calculate deck board layout**
   - Given a deck width, determine optimal board arrangement
   - Handle multiple board widths (3.5", 5.5", 7.25")

2. **Support multi-width patterns**
   - N-S: Narrow-Standard alternating
   - N-S-W: Three-board patterns
   - W-S: Wide-Standard alternating
   - And more...

3. **Calculate optimal spacing**
   - Target spacing: 0.125" (prefer smaller)
   - Acceptable range: 0.125" to 0.375"
   - Optimize to be as close to 0.125" as possible

4. **Tablesaw trimming support**
   - Calculate trim amounts when spacing is out of range
   - Ensure trimmed widths remain visually acceptable (>= 2.5", within 1/8" of standard)

### Picture Framing

**Single Picture Frame:**
- Single board border on each side
- Board width can be any standard width (3.5", 5.5", or 7.25")

**Double Picture Frame:**
- Outer: Standard width board (5.5")
- Inner: Narrow width board (3.5")
- Pattern inside can start with any board type (N, S, or W)

**Triple Picture Frame:**
- Outer: Wide board (7.25")
- Middle: Standard board (5.5")
- Inner: Narrow board (3.5")
- Pattern inside can start with any board type (N, S, or W)

**Custom Picture Frames:**
- Any combination of board widths
- Format: "5.5-3.5" or "7.25-5.5-3.5"
- Pattern inside can start with any board type (N, S, or W)

**Pattern Inside Picture Frame:**
- Pattern can start with any board type (N, S, or W)
- Pattern repeats to fill the field
- Optimize spacing to be as close to 0.125" as possible
- Target spacing range: 0.125" to 0.375"

### Visual Design Principles

**Optimal Layout Characteristics:**
- Consistent spacing across all gaps
- Repetition of patterns creates rhythm
- Balance (symmetrical or asymmetrical)
- No boards < 2.5" (too thin, draws attention)
- Trimmed boards within 1/8" of standard widths

**Visual Red Flags (to avoid):**
- Inconsistent spacing
- Boards < 2.5" wide
- Random placements without pattern
- 4+ different widths in one row

### Input

```
Arguments:
  width        - Deck width in inches
  pattern      - Pattern name (optional)
  spacing      - Target gap size (optional)

For picture framing:
  --picture-frame <width> [frame_type] [pattern]
  frame_type: single, double, triple, or custom (e.g., 5.5-3.5)
```

### Output

```
- Pattern name
- Board counts by type
- Actual spacing achieved
- Total waste
- Quality score (0-100)
- Trim requirements (if any)
- Picture frame configuration (if applicable)
```

## Algorithm

### Pattern Evaluation

1. **Calculate pattern width** for each pattern type
2. **Determine number of full cycles** that fit in deck width
3. **Handle partial pattern** at ends (if any)
4. **Calculate actual spacing** based on remaining width

### Picture Frame Algorithm

1. **Calculate frame width** from frame boards (each side)
2. **Calculate field width** (total width - 2 × frame width)
3. **Try different spacings** (0.125" to 0.375") to find best fit
4. **Optimize for spacing** closest to 0.125"
5. **Count boards** for full patterns and partial pattern at end

### Tablesaw Trimming Logic

When actual spacing exceeds max (0.375"):

1. Calculate trim needed to achieve max spacing:
   ```
   trim_needed = total_gap_width - (num_gaps * max_spacing)
   ```

2. Calculate trim per board:
   ```
   trim_per_board = trim_needed / num_boards
   ```

3. Check if trimmed width is acceptable:
   - Width >= 2.5" (minimum to avoid looking too thin)
   - Within 1/8" of standard width (3.5", 5.5", or 7.25")

4. If acceptable, apply trim; otherwise, mark as requiring attention

### Scoring

```
Score = (waste_score * 0.4) + (spacing_score * 0.3) + (board_score * 0.3) - trim_penalty

Where:
- waste_score: 100 if waste = 0, decreases linearly
- spacing_score: 100 if within range, 0 if very far
- board_score: 100 for 5-15 boards, decreases for more/fewer
- trim_penalty: 0 if no trim, up to -20 for significant trimming
```

## Test Cases

| Test | Expected Behavior |
|------|-------------------|
| 120" deck, N-S pattern | Should find ~12 boards with proper spacing |
| 96" deck with 1" borders | Should adjust for borders |
| 150" deck, W-S-N pattern | Should scale appropriately |
| Pattern requiring trim | Trim info included in results |
| Picture frame, double (9" each side) | Should calculate field width and pattern layout |
| Picture frame, single (5.5" each side) | Should work with single board frame |
| Picture frame, triple (16.25" each side) | Should work with triple frame |
| Picture frame, custom (7.25-5.5-3.5) | Should work with custom board combination |

## File Structure

```
deck_layout/
├── deck_layout.py      # Main implementation
├── test_deck_layout.py # Unit tests
├── README.md           # User documentation
├── SPEC.md            # This specification
└── example_*.txt      # Example input files
```
