#!/usr/bin/env python3
"""Calculate repeating multi-width deck-board layouts in inches."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from enum import Enum

MIN_GAP = 0.125
MAX_GAP = 0.375


class BoardWidth(Enum):
    NARROW = 3.5
    STANDARD = 5.5
    WIDE = 7.25

    @property
    def code(self) -> str:
        return self.name[0]


@dataclass(frozen=True)
class Pattern:
    name: str
    boards: tuple[BoardWidth, ...]

    def __init__(self, name: str, boards):
        if not boards:
            raise ValueError("a pattern needs at least one board")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "boards", tuple(boards))

    def total_width(self, spacing: float) -> float:
        return sum(board.value for board in self.boards) + spacing * (len(self.boards) - 1)


def _pattern(name: str) -> Pattern:
    lookup = {"N": BoardWidth.NARROW, "S": BoardWidth.STANDARD, "W": BoardWidth.WIDE}
    return Pattern(name, [lookup[part] for part in name.split("-")])


PATTERNS = {
    name: _pattern(name)
    for name in (
        "N-S", "S-N", "N-S-W", "W-S-N", "S-W-N", "W-N-S",
        "N-W-S", "S-N-W", "W-N", "N-W", "S-W", "W-S",
    )
}


def _boards_for(pattern: Pattern, count: int) -> list[BoardWidth]:
    return [pattern.boards[index % len(pattern.boards)] for index in range(count)]


def calculate_layout(
    width: float,
    pattern: Pattern,
    spacing: float = MIN_GAP,
    min_border: float = 0.0,
    max_border: float | None = None,
) -> dict:
    """Find the best prefix of a repeating pattern for a deck width.

    Widths, gaps, and borders are inches. Borders represent reserved space on
    each side. The chosen border may vary within the supplied range to produce
    a valid gap without trimming boards.
    """
    if width <= 0:
        raise ValueError("deck width must be positive")
    if not MIN_GAP <= spacing <= MAX_GAP:
        raise ValueError(f"spacing must be between {MIN_GAP} and {MAX_GAP} inches")
    if min_border < 0:
        raise ValueError("border cannot be negative")
    max_border = min_border if max_border is None else max_border
    if max_border < min_border:
        raise ValueError("max_border cannot be smaller than min_border")
    if width <= 2 * min_border:
        raise ValueError("borders leave no room for deck boards")

    max_count = int((width - 2 * min_border) / min(board.value for board in pattern.boards)) + 1
    candidates = []
    for count in range(1, max_count + 1):
        boards = _boards_for(pattern, count)
        board_width = sum(board.value for board in boards)
        gaps = count - 1
        if board_width > width - 2 * min_border + 1e-9:
            continue
        if gaps:
            ideal_border = (width - board_width - gaps * spacing) / 2
            border = min(max(ideal_border, min_border), max_border)
            actual_spacing = (width - 2 * border - board_width) / gaps
        else:
            border = min(max((width - board_width) / 2, min_border), max_border)
            actual_spacing = 0.0
        valid_gap = count == 1 or MIN_GAP - 1e-9 <= actual_spacing <= MAX_GAP + 1e-9
        used = board_width + gaps * (actual_spacing if valid_gap else spacing) + 2 * border
        waste = max(0.0, width - used)
        gap_error = 0.0 if count == 1 else abs(actual_spacing - spacing)
        score = 100.0 - min(60.0, waste * 8) - min(30.0, gap_error * 80)
        if not valid_gap:
            score -= 35
        candidates.append((valid_gap, score, -waste, count, boards, border, actual_spacing, used))

    if not candidates:
        # The deck is narrower than the first board; report the required trim.
        board = pattern.boards[0]
        trim = board.value - (width - 2 * min_border)
        return {
            "pattern": pattern.name, "board_counts": {board.name.lower(): 1},
            "spacing": spacing, "actual_spacing": 0.0, "num_cycles": 0,
            "board_count": 1, "border": min_border, "total_width_used": width,
            "waste": 0.0, "trim": trim, "score": max(0.0, 50 - trim * 10),
            "sequence": [board.code],
        }

    _, score, _, count, boards, border, actual_spacing, used = max(candidates, key=lambda item: item[:4])
    counts = Counter(board.name.lower() for board in boards)
    return {
        "pattern": pattern.name,
        "board_counts": dict(counts),
        "spacing": spacing,
        "actual_spacing": actual_spacing,
        "num_cycles": count // len(pattern.boards),
        "board_count": count,
        "border": border,
        "total_width_used": min(width - 2 * border, used - 2 * border),
        "waste": max(0.0, width - used),
        "trim": 0.0,
        "score": round(max(0.0, min(100.0, score)), 2),
        "sequence": [board.code for board in boards],
    }


def find_best_pattern(
    width: float,
    spacing: float = MIN_GAP,
    min_border: float = 0.0,
    max_border: float | None = None,
) -> list[dict]:
    results = [
        calculate_layout(width, pattern, spacing, min_border, max_border)
        for pattern in PATTERNS.values()
    ]
    return sorted(results, key=lambda result: (result["score"], -result["waste"]), reverse=True)


def _parse_frame(value: str) -> list[float]:
    presets = {"single": [5.5], "double": [5.5, 3.5], "triple": [7.25, 5.5, 3.5]}
    if value in presets:
        return presets[value]
    try:
        widths = [float(part) for part in value.split("-")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("frame must be single, double, triple, or widths like 5.5-3.5") from exc
    if not widths or any(width <= 0 for width in widths):
        raise argparse.ArgumentTypeError("frame widths must be positive")
    return widths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_width", nargs="?", type=float, help=argparse.SUPPRESS)
    parser.add_argument("legacy_pattern", nargs="?", choices=PATTERNS, help=argparse.SUPPRESS)
    parser.add_argument("--width", type=float, help="overall deck width in inches")
    parser.add_argument("--pattern", choices=PATTERNS, help="specific repeating pattern")
    parser.add_argument("--spacing", type=float, default=MIN_GAP, help="target gap in inches")
    parser.add_argument("--border", type=float, default=0.0, help="reserved border on each side")
    parser.add_argument("--frame", type=_parse_frame, help="picture frame preset or hyphenated widths")
    parser.add_argument("--limit", type=int, default=5, help="recommendations to display")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.width is not None and args.legacy_width is not None:
        parser.error("specify width once, preferably with --width")
    if args.pattern is not None and args.legacy_pattern is not None:
        parser.error("specify pattern once, preferably with --pattern")
    width = args.width if args.width is not None else args.legacy_width
    pattern_name = args.pattern if args.pattern is not None else args.legacy_pattern
    if width is None:
        parser.error("--width is required")
    frame_width = sum(args.frame or [])
    field_width = width - 2 * frame_width
    if field_width <= 0:
        parser.error("picture frame leaves no field width")
    try:
        results = (
            [calculate_layout(field_width, PATTERNS[pattern_name], args.spacing, args.border)]
            if pattern_name
            else find_best_pattern(field_width, args.spacing, args.border)
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Deck: {width:g}\"; field: {field_width:g}\"")
    if args.frame:
        print("Picture frame per side: " + " + ".join(f'{width:g}\"' for width in args.frame))
    for index, result in enumerate(results[: max(1, args.limit)], 1):
        counts = ", ".join(f"{name}={count}" for name, count in result["board_counts"].items())
        print(
            f"{index}. {result['pattern']}: {result['board_count']} boards ({counts}), "
            f"gap {result['actual_spacing']:.3f}\", score {result['score']:.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
