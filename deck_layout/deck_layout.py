#!/usr/bin/env python3
"""
Deck Layout Calculator - Optimizes deck board layout with minimal cuts.

Given a deck length and border requirements, this tool calculates the optimal
arrangement of deck boards (small, medium, large) to achieve even spacing.
"""

import sys
import math


def calculate_layout(length, start=0, border=0):
    """
    Calculate optimal deck board layout.
    
    Args:
        length: Total deck length in feet (can include fractions like 7.25)
        start: Starting size index (0=small, 1=medium, 2=large)
        border: Border width in inches (default 0)
    
    Returns:
        Dictionary with layout calculations
    """
    # Board sizes in feet (standard deck board sizes)
    SIZES = {
        'small': 3 + 7/16,    # ~3.46 ft
        'medium': 5 + 7/16,   # ~5.44 ft  
        'large': 7 + 3/16     # ~7.19 ft
    }
    
    # Gap between boards (1/8 inch converted to feet)
    GAP = 1/8 / 12
    
    # Convert length to feet if input was in inches
    if length > 100:  # Assume inches if > 100
        length = length / 12.0
    
    # Convert border to feet
    border_ft = border / 12.0
    
    # Calculate available space for boards
    available = length - 2 * border_ft - GAP
    
    # Board sizes in order (small, medium, large)
    board_sizes = [SIZES['small'], SIZES['medium'], SIZES['large']]
    
    # Initialize counters
    counts = [0, 0, 0]
    remaining = available
    index = start
    num_gaps = 1
    
    # Place boards using greedy approach
    while remaining >= board_sizes[index]:
        print(f"Placing {board_sizes[index]:.2f}' board")
        counts[index] += 1
        remaining -= board_sizes[index]
        remaining -= GAP
        num_gaps += 1
        index = (index + 1) % len(board_sizes)
    
    # Calculate final gap adjustment
    final_gap = remaining / num_gaps
    
    return {
        'length': length,
        'border': border_ft,
        'boards': {
            'large': counts[2],
            'medium': counts[1],
            'small': counts[0]
        },
        'final_gap': final_gap + GAP,
        'remaining': remaining,
        'total_boards': sum(counts)
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python3 deck_layout.py <length_in_feet> [start_size] [border_in_inches]")
        print("\n  length: Total deck length in feet (e.g., 12.5 for 12'6\")")
        print("  start_size: Starting board size (0=small, 1=medium, 2=large)")
        print("  border: Border width on each side in inches (default: 0)")
        print("\n  Example: python3 deck_layout.py 12.5 0 2")
        print("           (12'6\" deck with 2\" borders, starting with small board)")
        sys.exit(1)
    
    length = float(sys.argv[1])
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    border = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    
    result = calculate_layout(length, start, border)
    
    print("\n" + "=" * 50)
    print("DECK LAYOUT RESULTS")
    print("=" * 50)
    print(f"\nTotal deck length: {length:.2f}'")
    print(f"Border each side:  {border:.1f}\"")
    print(f"Available space:   {length - 2 * border / 12 - 1/8/12:.2f}'")
    print(f"\nBoard counts:")
    print(f"  Large boards:   {result['boards']['large']}")
    print(f"  Medium boards:  {result['boards']['medium']}")
    print(f"  Small boards:   {result['boards']['small']}")
    print(f"  Total boards:   {result['total_boards']}")
    print(f"\nGap adjustment:    {result['final_gap'] * 12:.3f}\"")
    print("=" * 50)


if __name__ == "__main__":
    main()
