#!/usr/bin/env python3
"""
Multi-width Deck Layout Calculator

Optimizes multi-width deck board layouts with patterns like:
- Narrow: 3.5" width
- Standard: 5.5" width
- Wide: 7.25" width

Supports various patterns with different board sequences and spacing requirements.
"""

import sys
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class BoardWidth(Enum):
    """Deck board width options in inches."""
    NARROW = 3.5
    STANDARD = 5.5
    WIDE = 7.25


@dataclass
class Pattern:
    """A repeating board pattern."""
    name: str
    sequence: List[BoardWidth]
    min_spacing: float = 0.125  # inches
    max_spacing: float = 0.375  # inches (prefer smaller)
    default_spacing: float = 0.125  # inches (preference toward smaller gap)
    trim_on_tablesaw: bool = True  # Allow trimming boards to achieve spacing

    def total_width(self, spacing: float) -> float:
        """Calculate total width of one pattern cycle."""
        board_widths = sum(w.value for w in self.sequence)
        gap_widths = (len(self.sequence) - 1) * spacing
        return board_widths + gap_widths


# Predefined patterns
PATTERNS = {
    # Classic alternating patterns
    "N-S": Pattern("Narrow-Standard", [BoardWidth.NARROW, BoardWidth.STANDARD]),
    "S-N": Pattern("Standard-Narrow", [BoardWidth.STANDARD, BoardWidth.NARROW]),
    "N-S-W": Pattern("Narrow-Standard-Wide", [BoardWidth.NARROW, BoardWidth.STANDARD, BoardWidth.WIDE]),
    "W-S-N": Pattern("Wide-Standard-Narrow", [BoardWidth.WIDE, BoardWidth.STANDARD, BoardWidth.NARROW]),
    "S-W-N": Pattern("Standard-Wide-Narrow", [BoardWidth.STANDARD, BoardWidth.WIDE, BoardWidth.NARROW]),
    "W-N-S": Pattern("Wide-Narrow-Standard", [BoardWidth.WIDE, BoardWidth.NARROW, BoardWidth.STANDARD]),
    "N-W-S": Pattern("Narrow-Wide-Standard", [BoardWidth.NARROW, BoardWidth.WIDE, BoardWidth.STANDARD]),
    "S-N-W": Pattern("Standard-Narrow-Wide", [BoardWidth.STANDARD, BoardWidth.NARROW, BoardWidth.WIDE]),
    "W-N": Pattern("Wide-Narrow", [BoardWidth.WIDE, BoardWidth.NARROW]),
    "N-W": Pattern("Narrow-Wide", [BoardWidth.NARROW, BoardWidth.WIDE]),
    "S-W": Pattern("Standard-Wide", [BoardWidth.STANDARD, BoardWidth.WIDE]),
    "W-S": Pattern("Wide-Standard", [BoardWidth.WIDE, BoardWidth.STANDARD]),
}

# Standard patterns from common decking manufacturers
STANDARD_PATTERNS = {
    "3-board mix": Pattern("3-Board Mix", [BoardWidth.NARROW, BoardWidth.STANDARD, BoardWidth.WIDE]),
    "2-board mix": Pattern("2-Board Mix", [BoardWidth.NARROW, BoardWidth.WIDE]),
}


def calculate_layout(
    total_width: float,
    pattern: Pattern,
    spacing: float = 0.125,
    min_border: float = 0,
    max_border: float = 0,
    overlap_allowed: bool = True,
    trim_on_tablesaw: bool = True
) -> Dict:
    """
    Calculate deck layout for a given pattern.

    Args:
        total_width: Total deck width to cover (inches)
        pattern: Board pattern to use
        spacing: Target gap size (optional, default: 0.125")
        min_border: Minimum border width on each side (inches)
        max_border: Maximum border width on each side (inches)
        overlap_allowed: If True, allow pattern to overlap border
        trim_on_tablesaw: If True, trim boards on tablesaw to achieve spacing

    Returns:
        Dictionary with layout details
    """
    # Calculate board widths and gap widths for the pattern
    board_widths = sum(w.value for w in pattern.sequence)
    num_boards = len(pattern.sequence)

    available_width = total_width - min_border - max_border

    # Find optimal spacing that minimizes waste while staying in range
    best_result = None
    best_waste = float('inf')

    for test_spacing in [0.125, 0.1875, 0.25, 0.3125, 0.375]:
        pattern_width = board_widths + (num_boards - 1) * test_spacing
        num_cycles = int(available_width / pattern_width)
        remaining_width = available_width - (num_cycles * pattern_width)

        # Count boards for this spacing
        board_counts = {w: num_cycles for w in pattern.sequence}

        # Handle any partial pattern at the end
        space_left = remaining_width
        partial_sequence = []
        for board in pattern.sequence:
            if space_left >= board.value:
                partial_sequence.append(board)
                space_left -= board.value + test_spacing

        for board in partial_sequence:
            board_counts[board] = board_counts.get(board, 0) + 1

        # Calculate actual spacing based on remaining width
        total_board_width = sum(w.value * count for w, count in board_counts.items())
        total_gap_width = available_width - total_board_width
        num_gaps = len(board_counts) - 1 if len(board_counts) > 1 else 1

        if num_gaps > 0:
            actual_spacing = total_gap_width / num_gaps
        else:
            actual_spacing = test_spacing

        waste = total_width - (total_board_width + total_gap_width)

        # Check if this spacing is acceptable
        if 0.125 <= actual_spacing <= 0.375 and waste < best_waste:
            best_waste = waste
            best_result = {
                'board_counts': board_counts,
                'num_cycles': num_cycles,
                'partial_sequence': partial_sequence,
                'remaining_after_cycles': remaining_width,
                'total_board_width': total_board_width,
                'total_gap_width': total_gap_width,
                'actual_spacing': actual_spacing,
                'waste': waste,
            }

    # If no good spacing found, use default spacing
    if best_result is None:
        pattern_width = board_widths + (num_boards - 1) * pattern.default_spacing
        num_cycles = int(available_width / pattern_width)
        remaining_width = available_width - (num_cycles * pattern_width)

        board_counts = {w: num_cycles for w in pattern.sequence}

        space_left = remaining_width
        partial_sequence = []
        for board in pattern.sequence:
            if space_left >= board.value:
                partial_sequence.append(board)
                space_left -= board.value + pattern.default_spacing

        for board in partial_sequence:
            board_counts[board] = board_counts.get(board, 0) + 1

        total_board_width = sum(w.value * count for w, count in board_counts.items())
        total_gap_width = available_width - total_board_width
        num_gaps = len(board_counts) - 1 if len(board_counts) > 1 else 1

        if num_gaps > 0:
            actual_spacing = total_gap_width / num_gaps
        else:
            actual_spacing = pattern.default_spacing

        waste = total_width - (total_board_width + total_gap_width)

        best_result = {
            'board_counts': board_counts,
            'num_cycles': num_cycles,
            'partial_sequence': partial_sequence,
            'remaining_after_cycles': remaining_width,
            'total_board_width': total_board_width,
            'total_gap_width': total_gap_width,
            'actual_spacing': actual_spacing,
            'waste': waste,
        }

    # Handle border adjustments
    if overlap_allowed:
        border_adjustment = min_border + best_result['remaining_after_cycles'] / 2
        actual_border = min(max_border, border_adjustment)
    else:
        actual_border = min_border

    best_result['border'] = actual_border

    # Check if spacing is out of range and trim is needed
    best_result['spacing_out_of_range'] = False
    best_result['trim_info'] = None

    if not (0.125 <= best_result['actual_spacing'] <= 0.375):
        best_result['spacing_out_of_range'] = True

        if trim_on_tablesaw and best_result['actual_spacing'] > 0.375:
            # Calculate trim needed
            target_spacing = 0.375
            num_gaps = len(best_result['board_counts']) - 1
            target_gap_width = num_gaps * target_spacing
            trim_needed = best_result['total_gap_width'] - target_gap_width
            trim_per_board = trim_needed / len(best_result['board_counts'])

            # Calculate new board widths after trimming
            new_board_widths = {}
            for board, count in best_result['board_counts'].items():
                new_width = board.value - trim_per_board
                new_board_widths[board] = new_width

            # Check if trimmed width is acceptable
            MIN_WIDTH = 2.5
            WIDTH_TOLERANCE = 0.125
            acceptable_trim = True
            for board, new_width in new_board_widths.items():
                if new_width < MIN_WIDTH:
                    acceptable_trim = False
                    break
                standard_widths = [3.5, 5.5, 7.25]
                closest_standard = min(standard_widths, key=lambda x: abs(x - new_width))
                if abs(new_width - closest_standard) > WIDTH_TOLERANCE:
                    acceptable_trim = False
                    break

            if acceptable_trim:
                best_result['trim_info'] = {
                    'trim_amount': trim_needed,
                    'trim_per_board': trim_per_board,
                    'new_board_widths': new_board_widths,
                }

    return {
        'pattern': pattern.name,
        'spacing': pattern.default_spacing,
        'board_counts': best_result['board_counts'],
        'total_board_width': best_result['total_board_width'],
        'total_gap_width': best_result['total_gap_width'],
        'num_cycles': best_result['num_cycles'],
        'partial_sequence': best_result['partial_sequence'],
        'remaining_after_cycles': best_result['remaining_after_cycles'],
        'actual_spacing': best_result['actual_spacing'],
        'border': best_result['border'],
        'total_width_used': best_result['total_board_width'] + best_result['total_gap_width'],
        'waste': best_result['waste'],
        'spacing_out_of_range': best_result['spacing_out_of_range'],
        'trim_on_tablesaw': trim_on_tablesaw,
        'trim_info': best_result['trim_info'],
    }


def find_best_pattern(
    total_width: float,
    patterns: Dict[str, Pattern] = PATTERNS,
    spacing_range: Tuple[float, float] = (0.125, 0.375),
    min_boards: int = 3,
    max_boards: int = 20
) -> List[Dict]:
    """
    Find the best pattern(s) for a given width.

    Args:
        total_width: Total deck width (inches)
        patterns: Dictionary of patterns to evaluate
        spacing_range: (min, max) spacing in inches (unused, spacing is geometry-based)
        min_boards: Minimum boards per row
        max_boards: Maximum boards per row

    Returns:
        List of layout results sorted by quality score
    """
    results = []

    for pattern_name, pattern in patterns.items():
        # Calculate layout - spacing is determined by geometry
        layout = calculate_layout(total_width, pattern)

        # Calculate quality score
        board_count = sum(layout['board_counts'].values())

        # Score based on:
        # 1. Minimal waste (weight: 40%)
        # 2. Good spacing (weight: 30%)
        # 3. Appropriate board count (weight: 30%)

        # Waste score: 0 if waste > 2", 100 if waste = 0
        waste_score = max(0, 100 - (layout['waste'] * 50))

        # Spacing score: 100 if at 0.125, 0 if outside 0.125-0.375
        # Score decreases gradually from 0.125 to 0.375
        if layout['actual_spacing'] <= 0.125:
            spacing_score = 100
        elif layout['actual_spacing'] <= 0.375:
            # Decreasing score as spacing gets larger
            spacing_score = 100 - ((layout['actual_spacing'] - 0.125) / 0.25) * 60
        else:
            # Outside acceptable range
            spacing_score = max(0, 40 - (layout['actual_spacing'] - 0.375) * 100)

        # Board count score: prefer 5-15 boards
        if min_boards <= board_count <= max_boards:
            board_score = 100 - abs(board_count - 10) * 5
        else:
            board_score = max(0, 100 - abs(board_count - 10) * 10)

        # Trim penalty: patterns requiring tablesaw trimming get a score reduction
        # (not impossible, but less ideal than no trimming needed)
        trim_penalty = 0
        if layout.get('trim_info'):
            # Apply penalty based on how much needs trimming
            trim_penalty = min(20, layout['trim_info']['trim_per_board'] * 40)

        total_score = (waste_score * 0.4 + spacing_score * 0.3 + board_score * 0.3) - trim_penalty

        results.append({
            'pattern': pattern_name,
            'spacing': pattern.default_spacing,
            'score': total_score,
            'waste': layout['waste'],
            'board_count': board_count,
            'board_counts': layout['board_counts'],
            'actual_spacing': layout['actual_spacing'],
            'waste_score': waste_score,
            'spacing_score': spacing_score,
            'board_score': board_score,
        })

    # Sort by score (descending)
    results.sort(key=lambda x: x['score'], reverse=True)

    return results


def display_results(results: List[Dict], total_width: float):
    """Display layout results in a readable format."""
    print("\n" + "=" * 70)
    print(f"DECK LAYOUT OPTIMIZATION FOR {total_width:.1f}\" WIDE DECK")
    print("=" * 70)

    if not results:
        print("No suitable patterns found.")
        return

    print("\nTop Recommendations (sorted by quality score):\n")

    for i, result in enumerate(results[:5], 1):  # Show top 5
        print(f"{i}. Pattern: {result['pattern']}")
        print(f"   Spacing: {result['actual_spacing']:.3f}\" (target: 0.125\"-0.375\")")
        print(f"   Score: {result['score']:.1f}/100")

        # Show trim penalty if applicable
        if result.get('trim_info'):
            trim_per_board = result['trim_info']['trim_per_board']
            penalty = min(20, trim_per_board * 40)
            print(f"   (Trim penalty: -{penalty:.1f} for {trim_per_board:.3f}\" per board)")

        print(f"   Board count: {result['board_count']} boards")
        print(f"   Breakdown:")

        for board, count in sorted(result['board_counts'].items(),
                                   key=lambda x: -x[1]):
            width = board.value if isinstance(board, BoardWidth) else 0
            print(f"     - {width:.1f}\" boards: {count}")

        print(f"   Waste: {result['waste']:.2f}\"")

        # Show trim info if applicable
        if result.get('trim_info'):
            trim = result['trim_info']
            print(f"   Tablesaw trimming: {trim['trim_amount']:.3f}\" total")
            print(f"     Per board: {trim['trim_per_board']:.3f}\"")
            print("     -> New widths:")
            for board, new_width in sorted(trim['new_board_widths'].items(),
                                           key=lambda x: -x[1]):
                width = board.value if isinstance(board, BoardWidth) else 0
                print(f"       - {width:.1f}\" -> {new_width:.3f}\"")

        print(f"   Breakdown:")
        print(f"     - Waste score: {result['waste_score']:.1f}/100")
        print(f"     - Spacing score: {result['spacing_score']:.1f}/100")
        print(f"     - Board count score: {result['board_score']:.1f}/100")
        print()


def calculate_picture_frame_layout(
    total_width: float,
    frame_boards: List[BoardWidth] = None,
    pattern: Pattern = None
) -> Dict:
    """
    Calculate deck layout with picture framing.

    Picture framing adds a border around the deck using any combination of boards.
    The pattern inside can start with any board type (N, S, or W) and should be
    optimized to achieve spacing as close to 0.125" as possible.

    Args:
        total_width: Total deck width including picture frame (inches)
        frame_boards: List of board widths for picture frame on each side
                      e.g., [BoardWidth.STANDARD, BoardWidth.NARROW] for double frame
                      Defaults to [NARROW, STANDARD] (3.5" + 5.5" = 9")
        pattern: Pattern to use for the field (default: N-S-W)

    Returns:
        Dictionary with picture frame layout details
    """
    # Default frame: double picture frame (Standard outer, Narrow inner)
    if frame_boards is None:
        frame_boards = [BoardWidth.STANDARD, BoardWidth.NARROW]

    # Default pattern for field
    if pattern is None:
        pattern = PATTERNS['N-S-W']

    # Calculate frame width (sum of frame boards on each side + spacing between them)
    # Spacing between frame boards is 0.25" (standard gap)
    INTER_BOARD_SPACING = 0.25
    num_gaps_in_frame = len(frame_boards) - 1
    frame_width = sum(w.value for w in frame_boards) + (num_gaps_in_frame * INTER_BOARD_SPACING)

    # Available width for the pattern field
    field_width = total_width - 2 * frame_width

    if field_width <= 0:
        return {
            'error': 'Total width too small for picture frame',
            'total_width': total_width,
            'frame_width': frame_width,
            'field_width': field_width,
            'frame_boards': [w.value for w in frame_boards]
        }

    # Find best starting board to optimize spacing
    board_widths = sum(w.value for w in pattern.sequence)

    # Try different spacings (0.125 to 0.375, targeting 0.125)
    best_result = None
    best_spacing = 0.125  # Target closest to 0.125
    best_waste = float('inf')

    for test_spacing in [0.125, 0.1875, 0.25, 0.3125, 0.375]:
        # Number of full cycles that fit
        pattern_width = board_widths + (len(pattern.sequence) - 1) * test_spacing
        num_cycles = int(field_width / pattern_width)
        remaining = field_width - (num_cycles * pattern_width)

        # Count full pattern boards
        board_counts = {}
        for board in pattern.sequence:
            board_counts[board] = num_cycles

        # Try to fit partial pattern at end
        space_left = remaining
        partial_sequence = []

        for board in pattern.sequence:
            if space_left >= board.value:
                partial_sequence.append(board)
                space_left -= board.value + test_spacing

        # Add partial pattern boards to counts
        for board in partial_sequence:
            board_counts[board] = board_counts.get(board, 0) + 1

        # Calculate total board width
        total_board_width = sum(w.value * count for w, count in board_counts.items())
        num_boards = sum(board_counts.values())

        # Calculate actual spacing
        total_gap_width = field_width - total_board_width
        num_gaps = num_boards - 1 if num_boards > 1 else 1
        actual_spacing = total_gap_width / num_gaps if num_gaps > 0 else test_spacing

        # Calculate waste (boards outside pattern field)
        waste = total_width - (2 * frame_width + field_width)

        # Score this spacing (prefer closer to 0.125)
        spacing_deviation = abs(actual_spacing - 0.125)

        # Check if this is a better fit
        is_valid = 0.125 <= actual_spacing <= 0.375
        is_better = False

        if is_valid and best_result is None:
            is_better = True
        elif is_valid and best_result is not None and not best_result.get('valid', False):
            is_better = True
        elif is_valid and best_result is not None and is_valid:
            # Prefer closer to 0.125
            best_deviation = abs(best_result['actual_spacing'] - 0.125)
            if spacing_deviation < best_deviation:
                is_better = True
        elif not is_valid and best_result is None:
            # Accept out-of-range if nothing else available
            is_better = True

        if is_better:
            best_waste = waste
            best_spacing = actual_spacing
            best_result = {
                'field_width': field_width,
                'board_counts': board_counts,
                'total_boards': num_boards,
                'actual_spacing': actual_spacing,
                'waste': waste,
                'valid': is_valid,
            }

    if best_result is None:
        return {
            'error': 'Could not find valid layout with picture frame',
            'total_width': total_width,
            'frame_width': frame_width,
            'field_width': field_width,
        }

    return {
        **best_result,
        'picture_frame': {
            'boards': [w.value for w in frame_boards],
            'board_names': [w.name for w in frame_boards],
            'total': frame_width,
        },
    }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Multi-width Deck Layout Calculator")
        print("\nUsage:")
        print("  python3 deck_layout.py <deck_width_in_inches>")
        print("  python3 deck_layout.py <deck_width_in_inches> <frame_pattern>")
        print("  python3 deck_layout.py <deck_width_in_inches> <frame_pattern> <main_pattern>")
        print("\nPicture Frame Patterns (each side):")
        print("  3.5              - Single narrow board (3.5\")")
        print("  5.5              - Single standard board (5.5\")")
        print("  7.25             - Single wide board (7.25\")")
        print("  5.5-3.5          - Double frame (standard + narrow)")
        print("  7.25-5.5-3.5     - Triple frame (wide + standard + narrow)")
        print("\nMain Deck Patterns:")
        print("  N-S, S-N, N-S-W, W-S-N, S-W-N, W-N-S, N-W-S, S-N-W, W-N, N-W, S-W, W-S")
        print("\nExamples:")
        print("  python3 deck_layout.py 120")
        print("  python3 deck_layout.py 164.75 5.5-3.5 N-S-W")
        print("  python3 deck_layout.py 120 7.25-5.5-3.5 S-N")
        print("\nAvailable patterns:")
        for name in PATTERNS:
            p = PATTERNS[name]
            print(f"  - {name}: {p.sequence[0].value:.1f}\" -> {p.sequence[-1].value:.1f}\"")
        sys.exit(1)

    # Parse arguments
    total_width = float(sys.argv[1])
    frame_arg = sys.argv[2] if len(sys.argv) > 2 else "5.5-3.5"
    pattern_name = sys.argv[3] if len(sys.argv) > 3 else 'N-S-W'

    # Parse frame boards (e.g., "5.5-3.5" or "7.25")
    frame_boards = []
    if '-' in frame_arg:
        for width_str in frame_arg.split('-'):
            width = float(width_str)
            if width == 3.5:
                frame_boards.append(BoardWidth.NARROW)
            elif width == 5.5:
                frame_boards.append(BoardWidth.STANDARD)
            elif width == 7.25:
                frame_boards.append(BoardWidth.WIDE)
            else:
                print(f"Unknown board width: {width}. Using nearest standard width.")
                nearest = min([3.5, 5.5, 7.25], key=lambda x: abs(x - width))
                if nearest == 3.5:
                    frame_boards.append(BoardWidth.NARROW)
                elif nearest == 5.5:
                    frame_boards.append(BoardWidth.STANDARD)
                else:
                    frame_boards.append(BoardWidth.WIDE)
    else:
        width = float(frame_arg)
        if width == 3.5:
            frame_boards = [BoardWidth.NARROW]
        elif width == 5.5:
            frame_boards = [BoardWidth.STANDARD]
        elif width == 7.25:
            frame_boards = [BoardWidth.WIDE]
        else:
            print(f"Unknown board width: {width}. Using nearest standard width.")
            nearest = min([3.5, 5.5, 7.25], key=lambda x: abs(x - width))
            if nearest == 3.5:
                frame_boards = [BoardWidth.NARROW]
            elif nearest == 5.5:
                frame_boards = [BoardWidth.STANDARD]
            else:
                frame_boards = [BoardWidth.WIDE]

    # Validate pattern
    if pattern_name not in PATTERNS:
        print(f"Unknown pattern: {pattern_name}")
        print("Available patterns:", ", ".join(PATTERNS.keys()))
        sys.exit(1)

    pattern = PATTERNS[pattern_name]
    result = calculate_picture_frame_layout(total_width, frame_boards, pattern)

    # Display results
    print("\n" + "=" * 60)
    print(f"LAYOUT RESULTS: Picture Frame Deck")
    print("=" * 60)
    print(f"\nTotal deck width: {total_width:.1f}\"")

    frame_info = result.get('picture_frame', {})
    frame_boards_actual = frame_info.get('boards', [w.value for w in frame_boards])
    num_gaps_in_frame = len(frame_boards_actual) - 1
    actual_frame_width = sum(frame_boards_actual) + (num_gaps_in_frame * 0.25)

    print(f"Picture frame: 2 x {actual_frame_width:.1f}\" = {2*actual_frame_width:.1f}\"")
    board_names = frame_info.get('board_names', [w.name for w in frame_boards])
    board_widths = frame_info.get('boards', [w.value for w in frame_boards])
    for i, (name, width) in enumerate(zip(board_names, board_widths)):
        side = "outer" if i == 0 else "inner" if i == len(board_names) - 1 else "middle"
        print(f"  - {side.title()}: {name} ({width}\")")

    if 'error' in result:
        print(f"Error: {result['error']}")
        sys.exit(1)

    print(f"Pattern field: {result['field_width']:.1f}\"")
    print(f"Pattern: {pattern_name} ({pattern.name})")
    print(f"\nBoard counts:")
    for board, count in sorted(result['board_counts'].items(), key=lambda x: -x[1]):
        print(f"  {board.value:.1f}\" boards: {count}")
    print(f"Total boards: {result['total_boards']}")
    print(f"\nActual spacing: {result['actual_spacing']:.3f}\"")
    print(f"Waste: {result['waste']:.2f}\"")
    print("=" * 60)


if __name__ == "__main__":
    main()
