# Lumber Optimizer Specification

## Requirements

### Core Functionality

1. **Load board lengths from files**
   - Support decimal inches (e.g., "12.5")
   - Support fractional inches (e.g., "12 1/4")
   - Handle comments (lines starting with #)
   - Convert inches to feet internally

2. **Best Fit Decreasing bin packing**
   - Sort pieces in descending order
   - Find best container (scrap or new stock) for each piece
   - Minimize new stock purchases

3. **Scrap-first optimization**
   - Try to fit pieces in available scrap first
   - Track remaining scrap after use
   - Only purchase new stock when needed

4. **Kerf accounting**
   - Account for saw blade width when calculating cuts
   - Adjust remaining space after each cut
   - Report accurate waste measurements

### Input

```
File format (inches):
  12        # integer
  12.5      # decimal
  12 1/4    # fraction
  12 3/8    # mixed

Command line:
  python3 lumber_optimizer.py <needed.txt> [scrap.txt] [kerf]
```

### Output

```
- Statistics (total needed, scrap used, new stock, waste)
- Stock orders (pieces grouped by stock)
- Remaining scrap (usable pieces)
- Recommended purchases (by stock length)
```

### Parameters

- **needed**: List of board lengths needed (feet)
- **scrap**: List of available scrap pieces (feet)
- **stock_lengths**: Available new stock (default: [16, 20] feet)
- **kerf**: Saw blade width (default: 1/8" = 0.0104' feet)

## Algorithm

### Best Fit Decreasing (BFD)

1. Sort needed pieces in descending order
2. Sort scrap in descending order
3. For each needed piece:
   - Try to fit in existing scrap (best fit)
   - If no scrap fits, create new stock order
4. Track remaining space in each stock after accounting for kerf
5. Report optimal arrangement

### Kerf Calculation

For each cut after the first piece in a stock:
- Available space = stock_length - sum(cuts_so_far) - (num_cuts * kerf)
- Each new piece requires: piece_length + (cuts_already_made * kerf)

## Test Cases

| Test | Expected |
|------|----------|
| Single piece fits in 16' | One stock order |
| Two pieces fit in 16' | One stock, two pieces |
| Two 19' pieces need two stocks | Two stock orders |
| Scrap available | Scrap used first, less new stock |
| Kerf accounted for | Correct space calculation |

## File Structure

```
lumber_optimizer/
├── lumber_optimizer.py     # Main implementation
├── test_lumber_optimizer.py # Unit tests
├── README.md              # User documentation
└── SPEC.md                # This specification
```
