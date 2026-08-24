#!/usr/bin/env python3
"""
Lumber Optimizer - Minimizes new lumber purchases by using scrap first.
Uses Best Fit Decreasing (BFD) heuristic for bin packing.
"""

import sys
from typing import List, Tuple


def load_lengths(filepath: str, in_inches: bool = True) -> List[float]:
    """Load board lengths from a file (one length per line).
    
    Args:
        filepath: Path to the input file
        in_inches: If True, converts inches to feet; if False, assumes feet
    
    Returns:
        List of lengths in feet
    """
    lengths = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line[0] != '#':  # Skip empty lines and comment lines
                    # Remove inline comments
                    if ' #' in line:
                        line = line.split(' #')[0].strip()
                    if '\t#' in line:
                        line = line.split('\t#')[0].strip()
                    # Handle fractional inches like "12 1/4" or "12.25"
                    value = parse_length(line)
                    if in_inches:
                        lengths.append(inches_to_feet(value))
                    else:
                        lengths.append(value)
    except FileNotFoundError:
        return []
    return lengths


def parse_length(value_str: str) -> float:
    """Parse a length value that may be decimal or fractional inches.
    
    Examples:
        "12" -> 12.0
        "12.5" -> 12.5
        "12 1/4" -> 12.25
        "12 3/8" -> 12.375
    """
    value_str = value_str.strip()
    
    # Try simple float first
    try:
        return float(value_str)
    except ValueError:
        pass
    
    # Handle fractional inches like "12 1/4"
    if '/' in value_str:
        parts = value_str.split()
        whole = 0.0
        if len(parts) > 1:
            try:
                whole = float(parts[0])
                parts = parts[1:]
            except ValueError:
                pass
        
        # Parse fraction(s)
        fraction = 0.0
        for part in parts:
            if '/' in part:
                num, denom = part.split('/')
                try:
                    fraction += float(num) / float(denom)
                except (ValueError, ZeroDivisionError):
                    pass
        
        return whole + fraction
    
    return 0.0


def inches_to_feet(inches: float) -> float:
    """Convert inches to feet."""
    return inches / 12.0


def best_fit_decreasing(
    needed: List[float],
    scrap: List[float],
    stock_lengths: List[float] = [16.0, 20.0],
    kerf: float = inches_to_feet(0.125)  # Default: 1/8" blade width in feet
) -> Tuple[List[List[float]], List[float], dict]:
    """
    Optimize lumber order using scrap first, then bin packing for new stock.
    Accounts for blade kerf (saw width) when cutting.

    Args:
        needed: List of board lengths needed (in feet)
        scrap: List of available scrap pieces (in feet)
        stock_lengths: Available new stock lengths (default: 16', 20')
        kerf: Width of saw blade in feet (default: 1/8" = 0.0104')

    Returns:
        - new_orders: List of lists, each containing pieces cut from one new stock
        - remaining_scrap: List of remaining scrap lengths (usable pieces)
        - stats: Dictionary of statistics
    """
    # Sort needed pieces in descending order (Best Fit Decreasing)
    needed_sorted = sorted(needed, reverse=True)

    # Sort scrap in descending order for easier matching
    scrap_sorted = sorted(scrap, reverse=True)

    # Track remaining scrap (pieces that can still be used)
    remaining_scrap = list(scrap_sorted)

    # List of new stock orders (each list contains pieces cut from that stock)
    new_orders = []

    # Track statistics
    stats = {
        'total_needed': sum(needed),
        'total_scrap': sum(scrap),
        'new_stock_used': 0,
        'scrap_used': 0,
        'waste': 0,
        'kerf_per_cut': kerf
    }

    def find_best_fit(piece_length: float, available: List[float]) -> Tuple[int, float, int]:
        """
        Find the best container (scrap or new stock) for a piece.
        Returns (container_index, remaining_space_after_fit, cuts_needed).
        -1 means no suitable container found (need new stock).
        """
        best_idx = -1
        best_remaining = float('inf')
        cuts_needed = 0

        for i, remaining in enumerate(available):
            # Account for kerf: each cut after the first piece needs additional space
            if remaining >= piece_length + (cuts_needed * kerf):
                after_fit = remaining - piece_length - (cuts_needed * kerf)
                if after_fit < best_remaining:
                    best_remaining = after_fit
                    best_idx = i

        return best_idx, best_remaining, cuts_needed

    def cut_from_stock(pieces: List[float], stock_length: float) -> Tuple[List[List[float]], float]:
        """
        Cut multiple pieces from a single stock using Best Fit.
        Returns list of cut pieces (grouped by cut) and remaining waste.
        """
        remaining = stock_length
        cuts = []
        pieces_remaining = list(pieces)
        
        while pieces_remaining and remaining >= pieces_remaining[-1]:
            # Find best fit for current remaining
            best_idx = -1
            best_size = 0
            
            for i, p in enumerate(pieces_remaining):
                # Account for kerf: pieces after the first need extra space for the cut
                required = p + (len(cuts) * kerf)
                if p <= remaining:
                    if best_idx == -1 or p > best_size:
                        best_idx = i
                        best_size = p
            
            if best_idx == -1:
                break
                
            # Cut the piece
            cut_piece = pieces_remaining.pop(best_idx)
            remaining -= cut_piece + (len(cuts) * kerf)
            cuts.append(cut_piece)
        
        return cuts, max(0, remaining - len(cuts) * kerf)

    # Process all needed pieces
    # We'll use a different approach: group pieces by which stock they'll come from
    all_needed = list(needed_sorted)
    
    # First, try to use scrap - just check if piece fits in any scrap piece
    while all_needed and remaining_scrap:
        piece = all_needed[-1]  # Look at the smallest needed piece first (BFD works best this way)
        placed = False
        for i, remaining in enumerate(remaining_scrap):
            if remaining >= piece:
                remaining_scrap[i] -= piece
                if remaining_scrap[i] < kerf:
                    remaining_scrap[i] = 0
                stats['scrap_used'] += piece
                all_needed.pop()
                placed = True
                break
        
        if not placed:
            break  # Can't fit this piece, move on to new stock
    
    # Now handle remaining pieces with new stock orders
    # Group pieces into optimal stock orders
    while all_needed:
        # Start with the largest remaining piece
        piece = all_needed.pop(0)
        
        # Find which existing stock to add to, or create new
        best_stock_idx = -1
        best_remaining = float('inf')
        
        for idx, order in enumerate(new_orders):
            used = sum(order)
            remaining_capacity = max(stock_lengths) - used
            # Need capacity for piece + kerf for cuts
            needed_space = piece + (len(order) * kerf)
            if remaining_capacity >= needed_space:
                # Calculate remaining after this cut
                proj_remaining = remaining_capacity - needed_space
                if proj_remaining < best_remaining:
                    best_remaining = proj_remaining
                    best_stock_idx = idx
        
        if best_stock_idx >= 0:
            new_orders[best_stock_idx].append(piece)
        else:
            # Create new stock - use smallest that fits
            new_stock = min(stock_lengths)
            if piece > new_stock:
                new_stock = max(stock_lengths)
            new_orders.append([piece])
            stats['new_stock_used'] += new_stock
    
    # Re-sort pieces within each order for optimal cutting (descending)
    for order in new_orders:
        order.sort(reverse=True)

    # Calculate waste with kerf accounted for
    for order in new_orders:
        total_used = sum(order)
        # Kerf waste: (number of cuts) * kerf = (len - 1) * kerf for each stock
        kerf_waste = (len(order) - 1) * kerf if len(order) > 1 else 0
        stock_length = max(stock_lengths) if sum(order) > 16 else 16
        stats['waste'] += (stock_length - total_used - kerf_waste)

    # Filter out zero-length scrap pieces
    remaining_scrap = [s for s in remaining_scrap if s > kerf]

    return new_orders, remaining_scrap, stats


def display_results(new_orders: List[List[float]], remaining_scrap: List[float], stats: dict, output_in_inches: bool = False):
    """Display the optimized order in a readable format."""
    print("\n" + "="*60)
    print("LUMBER ORDER OPTIMIZATION RESULTS")
    print("="*60)
    
    # Convert to display units
    def to_unit(val, unit='ft'):
        if unit == 'in':
            return val * 12
        return val

    kerf = stats.get('kerf_per_cut', inches_to_feet(0.125))
    unit_label = 'in' if output_in_inches else 'ft'
    unit_label_short = '"' if output_in_inches else "'"

    print(f"\n📊 Statistics:")
    print(f"  Total length needed:      {to_unit(stats['total_needed'], unit_label):.2f}{unit_label_short}")
    print(f"  Total scrap available:    {to_unit(stats['total_scrap'], unit_label):.2f}{unit_label_short}")
    print(f"  Scrap used:               {to_unit(stats['scrap_used'], unit_label):.2f}{unit_label_short}")
    print(f"  New stock purchased:      {to_unit(stats['new_stock_used'], unit_label):.2f}{unit_label_short}")
    print(f"  Total waste:              {to_unit(stats['waste'], unit_label):.2f}{unit_label_short}")
    print(f"  New stock pieces:         {len(new_orders)}")

    if remaining_scrap:
        print(f"  Remaining scrap:          {len(remaining_scrap)} pieces")
        print(f"    Remaining length:       {to_unit(sum(remaining_scrap), unit_label):.2f}{unit_label_short}")
        for i, s in enumerate(sorted(remaining_scrap, reverse=True)):
            if s > inches_to_feet(6):  # Only show pieces > 6"
                print(f"    - {to_unit(s, unit_label):.2f}{unit_label_short} piece")

    print("\n📋 New Stock Orders (each line shows pieces from one stock):")
    for i, order in enumerate(new_orders, 1):
        total = sum(order)
        kerf_waste = (len(order) - 1) * kerf if len(order) > 1 else 0
        pieces_str = " + ".join(f"{to_unit(p, unit_label):.2f}{unit_label_short}" for p in order)
        print(f"  Stock {i} ({to_unit(total, unit_label):.2f}{unit_label_short}): {pieces_str}")
        print(f"    Kerf waste ({len(order)} cuts): {to_unit(kerf_waste, unit_label):.3f}{unit_label_short}")
        print(f"    Total material used: {to_unit(total + kerf_waste, unit_label):.2f}{unit_label_short}")

    print("\n💡 Recommended Purchases:")
    stock_16_count = sum(1 for order in new_orders if sum(order) <= inches_to_feet(16))
    stock_20_count = len(new_orders) - stock_16_count
    print(f"  - 16' boards: {stock_16_count}")
    print(f"  - 20' boards: {stock_20_count}")
    
    print(f"\n⚙️  Settings:")
    print(f"  Blade kerf (saw width): {kerf * 12:.3f}\" (1/8\" default)")


def parse_kerf(kerf_arg: str) -> float:
    """Parse kerf argument (can be in inches or feet)."""
    try:
        value = float(kerf_arg)
        # If value is reasonable (e.g., 0.125, 0.5, 1.0), assume inches
        # Values like 0.083 (1") would be in feet, but that's unusual input
        if value > 0 and value <= 12:  # Likely inches
            return inches_to_feet(value)
        return value  # Already in feet
    except ValueError:
        # Try parsing as fraction (e.g., "1/8")
        if '/' in kerf_arg:
            parts = kerf_arg.split('/')
            if len(parts) == 2:
                num, denom = float(parts[0]), float(parts[1])
                result = num / denom
                if result <= 12:  # Likely inches
                    return inches_to_feet(result)
                return result  # Already in feet
        return inches_to_feet(0.125)  # Default 1/8"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 lumber_optimizer.py <needed_lengths.txt> [scrap.txt] [kerf]")
        print("\n  Input files: Board lengths in INCHES (one per line)")
        print("  scrap.txt:   (Optional) Existing scrap pieces in INCHES")
        print("  kerf:        (Optional) Saw blade width in INCHES (default: 0.125\" = 1/8\")")
        print("\n  Example needed.txt:")
        print("    # My fence boards (all values in inches)")
        print("    102    # 8.5 feet")
        print("    144    # 12 feet")
        print("    75     # 6.25 feet")
        sys.exit(1)

    needed_file = sys.argv[1]
    scrap_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Parse kerf (default 1/8")
    kerf = inches_to_feet(0.125)
    if len(sys.argv) > 3:
        kerf = parse_kerf(sys.argv[3])

    # Load needed lengths (assumes inches input)
    needed = load_lengths(needed_file, in_inches=True)
    if not needed:
        print(f"Error: Could not load needed lengths from '{needed_file}' or file is empty")
        sys.exit(1)

    # Load scrap if provided (assumes inches input)
    scrap = load_lengths(scrap_file, in_inches=True) if scrap_file else []

    print(f"Loaded {len(needed)} needed pieces")
    if scrap:
        print(f"Loaded {len(scrap)} scrap pieces")
    print(f"Using blade kerf: {kerf * 12:.3f}\"")

    # Run optimization
    new_orders, remaining_scrap, stats = best_fit_decreasing(needed, scrap, kerf=kerf)

    # Display results
    display_results(new_orders, remaining_scrap, stats)


if __name__ == "__main__":
    main()
