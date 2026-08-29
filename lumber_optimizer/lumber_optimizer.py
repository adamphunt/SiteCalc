#!/usr/bin/env python3
"""Optimize lumber cuts by consuming scrap before purchasing stock boards."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from html import escape
from pathlib import Path
import random
from typing import Iterable

DEFAULT_KERF = 0.125 / 12
DEFAULT_STOCK_LENGTHS = (16.0, 20.0)
EPSILON = 1e-9
SEARCH_ATTEMPTS = 512


def parse_length(value_str: str) -> float:
    """Parse a positive decimal, fraction, or mixed-number length."""
    value = value_str.strip()
    if not value:
        raise ValueError("length cannot be empty")
    try:
        parts = value.split()
        if len(parts) == 2:
            result = float(Fraction(parts[0])) + float(Fraction(parts[1]))
        elif len(parts) == 1:
            result = float(Fraction(value))
        else:
            raise ValueError
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f"invalid length: {value_str!r}") from exc
    if result <= 0:
        raise ValueError(f"length must be positive: {value_str!r}")
    return result


def inches_to_feet(inches: float) -> float:
    return inches / 12.0


def parse_measurement(value: str) -> float:
    """Parse a measurement and return inches.

    Unmarked values are inches. Explicit examples include ``10' 9 1/4\"``,
    ``10'``, and ``9 1/4\"``. Unicode prime symbols are accepted as well.
    """
    normalized = value.strip().replace("′", "'").replace("’", "'").replace("″", '"')
    if "'" in normalized:
        if normalized.count("'") != 1:
            raise ValueError(f"invalid feet-and-inches measurement: {value!r}")
        feet_text, inches_text = (part.strip() for part in normalized.split("'", 1))
        feet = parse_length(feet_text)
        if inches_text.endswith('"'):
            inches_text = inches_text[:-1].strip()
        elif '"' in inches_text:
            raise ValueError(f"invalid inch mark placement: {value!r}")
        inches = parse_length(inches_text) if inches_text else 0.0
        if inches >= 12:
            raise ValueError("inches after a foot mark must be less than 12")
        return feet * 12 + inches
    if normalized.endswith('"'):
        return parse_length(normalized[:-1].strip())
    if '"' in normalized:
        raise ValueError(f"invalid inch mark placement: {value!r}")
    return parse_length(normalized)


def parse_order_line(value: str) -> tuple[int, float]:
    """Parse ``length`` or ``quantity@length`` and return quantity and length."""
    if "@" not in value:
        return 1, parse_measurement(value)
    if value.count("@") != 1:
        raise ValueError(f"invalid quantity expression: {value!r}")
    quantity_text, length_text = (part.strip() for part in value.split("@", 1))
    try:
        quantity = int(quantity_text)
    except ValueError as exc:
        raise ValueError(f"quantity must be a whole number: {quantity_text!r}") from exc
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    return quantity, parse_measurement(length_text)


def load_lengths(filepath: str, in_inches: bool = True) -> list[float]:
    """Load lengths, supporting ``quantity@length`` and inline ``#`` comments."""
    lengths: list[float] = []
    path = Path(filepath)
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, 1):
            value = raw_line.partition("#")[0].strip()
            if not value:
                continue
            try:
                quantity, length = parse_order_line(value)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
            normalized = inches_to_feet(length) if in_inches else length
            lengths.extend([normalized] * quantity)
    return lengths


def _validate_lengths(name: str, values: Iterable[float]) -> list[float]:
    result = list(values)
    if any(value <= 0 for value in result):
        raise ValueError(f"{name} lengths must all be positive")
    return result


def best_fit_decreasing(
    needed: list[float],
    scrap: list[float],
    stock_lengths: Iterable[float] = DEFAULT_STOCK_LENGTHS,
    kerf: float = DEFAULT_KERF,
) -> tuple[list[list[float]], list[float], dict]:
    """Pack cuts with a deterministic scrap-first BFD heuristic.

    Kerf is charged between pieces cut from the same source board. Returned orders
    retain the historical list-of-lists API; selected board lengths are included
    in ``stats['order_stock_lengths']``.
    """
    pieces = sorted(_validate_lengths("needed", needed), reverse=True)
    scrap_lengths = _validate_lengths("scrap", scrap)
    stocks = sorted(set(_validate_lengths("stock", stock_lengths)))
    if not stocks:
        raise ValueError("at least one stock length is required")
    if kerf < 0:
        raise ValueError("kerf cannot be negative")
    oversized = [piece for piece in pieces if piece > stocks[-1] + EPSILON]
    if oversized:
        raise ValueError(
            f"needed piece {oversized[0]:.3f}' exceeds longest stock {stocks[-1]:.3f}'"
        )

    def make_scrap_plan(order: list[float]):
        bins = [
            {"length": length, "remaining": length, "pieces": []}
            for length in scrap_lengths
        ]
        unplaced = []
        for piece in order:
            candidates = []
            for index, bin_ in enumerate(bins):
                kerf_cost = kerf if bin_["pieces"] else 0.0
                after = bin_["remaining"] - piece - kerf_cost
                if after >= -EPSILON:
                    candidates.append((max(0.0, after), index))
            if candidates:
                after, index = min(candidates)
                bins[index]["remaining"] = after
                bins[index]["pieces"].append(piece)
            else:
                unplaced.append(piece)
        return bins, unplaced

    def make_stock_plan(unplaced: list[float]):
        orders: list[list[float]] = []
        capacities: list[float] = []
        for piece in sorted(unplaced, reverse=True):
            candidates = []
            for index, remaining in enumerate(capacities):
                after = remaining - piece - kerf
                if after >= -EPSILON:
                    candidates.append((max(0.0, after), index))
            if candidates:
                after, index = min(candidates)
                orders[index].append(piece)
                capacities[index] = after
            else:
                orders.append([piece])
                capacities.append(stocks[-1] - piece)

        order_stocks, remainders = [], []
        for order in orders:
            consumed = sum(order) + max(0, len(order) - 1) * kerf
            stock = next(length for length in stocks if consumed <= length + EPSILON)
            order_stocks.append(stock)
            remainders.append(max(0.0, stock - consumed))
        return orders, order_stocks, remainders

    # Scrap-first BFD is sensitive to the order in which otherwise valid cuts
    # are considered. Try repeatable alternative orders and retain the plan that
    # buys the least total stock, then the fewest boards and least offcut.
    candidate_orders = [pieces, list(reversed(pieces))]
    rng = random.Random(0)
    for _ in range(SEARCH_ATTEMPTS if len(pieces) > 1 and scrap_lengths else 0):
        candidate = pieces.copy()
        rng.shuffle(candidate)
        candidate_orders.append(candidate)

    best = None
    for candidate in candidate_orders:
        bins, unplaced = make_scrap_plan(candidate)
        orders, order_stocks, remainders = make_stock_plan(unplaced)
        scrap_used_for_plan = sum(sum(bin_["pieces"]) for bin_ in bins)
        score = (
            sum(order_stocks),
            len(order_stocks),
            -scrap_used_for_plan,
            sum(remainders),
        )
        if best is None or score < best[0]:
            best = (score, bins, orders, order_stocks, remainders)

    assert best is not None
    _, scrap_bins, orders, order_stocks, remainders = best
    scrap_used = sum(sum(bin_["pieces"]) for bin_ in scrap_bins)
    scrap_kerf = sum(max(0, len(bin_["pieces"]) - 1) * kerf for bin_ in scrap_bins)

    remaining_scrap = sorted(
        (bin_["remaining"] for bin_ in scrap_bins if bin_["remaining"] > EPSILON),
        reverse=True,
    )
    new_kerf = sum(max(0, len(order) - 1) * kerf for order in orders)
    stats = {
        "total_needed": sum(pieces),
        "total_scrap": sum(scrap_lengths),
        "scrap_used": scrap_used,
        "new_stock_used": sum(order_stocks),
        "waste": sum(remainders),
        "kerf_waste": scrap_kerf + new_kerf,
        "kerf_per_cut": kerf,
        "order_stock_lengths": order_stocks,
        "scrap_cut_lists": [
            (bin_["length"], bin_["pieces"], bin_["remaining"])
            for bin_ in scrap_bins
            if bin_["pieces"]
        ],
    }
    return orders, remaining_scrap, stats


def display_results(new_orders, remaining_scrap, stats, output_in_inches=False) -> None:
    scale, suffix = (12, '"') if output_in_inches else (1, "'")
    show = lambda value: f"{value * scale:.2f}{suffix}"
    print("\n" + "=" * 60)
    print("LUMBER ORDER OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"  Total length needed:   {show(stats['total_needed'])}")
    print(f"  Scrap available:       {show(stats['total_scrap'])}")
    print(f"  Scrap used:            {show(stats['scrap_used'])}")
    print(f"  New stock purchased:   {show(stats['new_stock_used'])}")
    print(f"  New-stock offcut:      {show(stats['waste'])}")
    print(f"  Kerf consumed:         {show(stats['kerf_waste'])}")
    if remaining_scrap:
        counts = Counter(round(value * scale, 8) for value in remaining_scrap)
        summary = ", ".join(
            f"{count} x {show(value / scale)}" if count > 1 else show(value / scale)
            for value, count in sorted(counts.items(), reverse=True)
        )
        print(f"  Remaining scrap ({len(remaining_scrap)}): {summary}")
    if stats["scrap_cut_lists"]:
        print("\nSCRAP CUT LIST")
        for number, (source, cuts, remainder) in enumerate(stats["scrap_cut_lists"], 1):
            pieces = " + ".join(show(piece) for piece in cuts)
            print(
                f"  Scrap {number} ({show(source)}): {pieces}"
                f" -> {show(remainder)} left"
            )
    print("\nCUT LIST")
    stocks = stats["order_stock_lengths"]
    for number, (stock, order) in enumerate(zip(stocks, new_orders), 1):
        pieces = " + ".join(show(piece) for piece in order)
        print(f"  Board {number} ({stock:g}'): {pieces}")
    counts = Counter(stocks)
    print("\nPURCHASES")
    if not counts:
        print("  No new boards required")
    for stock in sorted(counts):
        print(f"  {stock:g}' boards: {counts[stock]}")


def write_visualization(
    filepath: str | Path,
    new_orders: list[list[float]],
    stats: dict,
) -> Path:
    """Write a standalone HTML cutting diagram and return its path."""
    output_path = Path(filepath)
    kerf = stats["kerf_per_cut"]

    def inches(value: float) -> str:
        return f"{value * 12:.2f}\u2033"

    def board_svg(source: float, cuts: list[float], remainder: float) -> str:
        width, height = 1000.0, 52
        cursor = 0.0
        shapes = []

        def segment(length: float, css_class: str, label: str) -> None:
            nonlocal cursor
            segment_width = max(0.0, length / source * width)
            title = escape(f"{label}: {inches(length)}")
            shapes.append(
                f'<g><title>{title}</title><rect class="{css_class}" '
                f'x="{cursor:.3f}" y="0" width="{segment_width:.3f}" height="{height}"/>'
            )
            if segment_width >= 58:
                shapes.append(
                    f'<text x="{cursor + segment_width / 2:.3f}" y="31" '
                    f'text-anchor="middle">{escape(inches(length))}</text>'
                )
            shapes.append("</g>")
            cursor += segment_width

        for index, cut in enumerate(cuts):
            if index:
                segment(kerf, "kerf", "Saw kerf")
            segment(cut, f"cut cut-{index % 6}", f"Cut {index + 1}")
        if remainder > EPSILON:
            segment(remainder, "remainder", "Remaining")
        return (
            f'<svg viewBox="0 0 {width:g} {height}" role="img" '
            f'aria-label="{escape(inches(source))} board cutting diagram">'
            + "".join(shapes)
            + "</svg>"
        )

    rows = []
    for number, (source, cuts, remainder) in enumerate(stats["scrap_cut_lists"], 1):
        rows.append(
            '<section class="board"><h3>'
            f'Scrap {number} <span>{inches(source)} source \u00b7 {inches(remainder)} left</span>'
            f'</h3>{board_svg(source, cuts, remainder)}</section>'
        )

    purchase_rows = []
    for number, (source, cuts) in enumerate(
        zip(stats["order_stock_lengths"], new_orders), 1
    ):
        consumed = sum(cuts) + max(0, len(cuts) - 1) * kerf
        remainder = max(0.0, source - consumed)
        purchase_rows.append(
            '<section class="board"><h3>'
            f'Purchased board {number} <span>{source:g}\u2032 source \u00b7 '
            f'{inches(remainder)} left</span></h3>{board_svg(source, cuts, remainder)}</section>'
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lumber cutting plan</title>
<style>
  :root {{ color-scheme: light; font-family: system-ui, sans-serif; }}
  body {{ max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #20251f; }}
  h1 {{ margin-bottom: .25rem; }} h2 {{ margin-top: 2rem; }}
  .summary {{ display: flex; flex-wrap: wrap; gap: .75rem; margin: 1.25rem 0; }}
  .summary div {{ background: #f1f3ed; border-radius: .4rem; padding: .6rem .9rem; }}
  .board {{ break-inside: avoid; margin: 1rem 0 1.4rem; }}
  h3 {{ font-size: 1rem; margin: 0 0 .35rem; }} h3 span {{ color: #596157; font-weight: 400; }}
  svg {{ display: block; width: 100%; height: 52px; border: 1px solid #333; background: #fff; }}
  rect {{ stroke: #fff; stroke-width: 1; }} text {{ font-size: 14px; fill: #162015; pointer-events: none; }}
  .cut-0 {{ fill: #8ecae6; }} .cut-1 {{ fill: #ffb703; }} .cut-2 {{ fill: #90be6d; }}
  .cut-3 {{ fill: #f8961e; }} .cut-4 {{ fill: #b8a1d9; }} .cut-5 {{ fill: #4cc9a7; }}
  .kerf {{ fill: #d62828; }} .remainder {{ fill: #d9d9d9; }}
  .legend {{ display: flex; gap: 1rem; font-size: .9rem; }}
  .swatch {{ display: inline-block; width: .9rem; height: .9rem; margin-right: .3rem; vertical-align: -.1rem; }}
  @media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
<h1>Lumber cutting plan</h1>
<p>Lengths are shown in inches. Hover over a segment for its exact measurement.</p>
<div class="summary">
  <div><strong>{inches(stats['total_needed'])}</strong><br>required</div>
  <div><strong>{inches(stats['scrap_used'])}</strong><br>cut from scrap</div>
  <div><strong>{stats['new_stock_used']:g}\u2032</strong><br>new stock</div>
  <div><strong>{inches(stats['kerf_waste'])}</strong><br>total kerf</div>
</div>
<div class="legend"><span><i class="swatch cut-0"></i>Required cut</span><span><i class="swatch kerf"></i>Kerf</span><span><i class="swatch remainder"></i>Remaining</span></div>
<h2>Scrap used</h2>
{''.join(rows) if rows else '<p>No scrap used.</p>'}
<h2>Purchased boards</h2>
{''.join(purchase_rows) if purchase_rows else '<p>No new boards required.</p>'}
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
    return output_path


def parse_kerf(value: str) -> float:
    """Parse a kerf expressed in inches and return feet."""
    return inches_to_feet(parse_length(value))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("needed", help="file of required lengths in inches")
    parser.add_argument("scrap", nargs="?", help="optional file of scrap lengths in inches")
    parser.add_argument("--kerf", default="1/8", help="blade kerf in inches (default: 1/8)")
    parser.add_argument("--stock", nargs="+", default=["16", "20"], metavar="FEET")
    parser.add_argument("--inches", action="store_true", help="display cuts in inches")
    parser.add_argument(
        "--visualize",
        metavar="OUTPUT.html",
        help="write a standalone HTML cutting diagram",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        needed = load_lengths(args.needed)
        scrap = load_lengths(args.scrap) if args.scrap else []
        if not needed:
            parser.error("needed-length file contains no lengths")
        orders, remaining, stats = best_fit_decreasing(
            needed,
            scrap,
            [parse_length(value) for value in args.stock],
            parse_kerf(args.kerf),
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    display_results(orders, remaining, stats, args.inches)
    if args.visualize:
        try:
            output_path = write_visualization(args.visualize, orders, stats)
        except OSError as exc:
            parser.error(str(exc))
        print(f"\nVisualization written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
