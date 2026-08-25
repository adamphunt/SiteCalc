#!/usr/bin/env python3
"""Optimize lumber cuts by consuming scrap before purchasing stock boards."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Iterable

DEFAULT_KERF = 0.125 / 12
DEFAULT_STOCK_LENGTHS = (16.0, 20.0)
EPSILON = 1e-9


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

    scrap_bins = [{"remaining": length, "cuts": 0} for length in scrap_lengths]
    unplaced: list[float] = []
    scrap_used = 0.0
    scrap_kerf = 0.0
    for piece in pieces:
        candidates = []
        for index, bin_ in enumerate(scrap_bins):
            kerf_cost = kerf if bin_["cuts"] else 0.0
            after = bin_["remaining"] - piece - kerf_cost
            if after >= -EPSILON:
                candidates.append((max(0.0, after), index, kerf_cost))
        if not candidates:
            unplaced.append(piece)
            continue
        after, index, kerf_cost = min(candidates)
        scrap_bins[index]["remaining"] = after
        scrap_bins[index]["cuts"] += 1
        scrap_used += piece
        scrap_kerf += kerf_cost

    orders: list[list[float]] = []
    remainders: list[float] = []
    for piece in unplaced:
        candidates = []
        for index, remaining in enumerate(remainders):
            after = remaining - piece - kerf
            if after >= -EPSILON:
                candidates.append((max(0.0, after), index))
        if candidates:
            after, index = min(candidates)
            orders[index].append(piece)
            remainders[index] = after
            continue
        orders.append([piece])
        remainders.append(max(0.0, stocks[-1] - piece))

    # Pack with the largest available capacity, then buy the smallest stock that
    # can supply each finished order. This avoids prematurely opening 16' boards
    # when a 20' board could combine cuts and reduce the board count.
    order_stocks = []
    remainders = []
    for order in orders:
        consumed = sum(order) + max(0, len(order) - 1) * kerf
        stock = next(length for length in stocks if consumed <= length + EPSILON)
        order_stocks.append(stock)
        remainders.append(max(0.0, stock - consumed))

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
    }
    return orders, remaining_scrap, stats


def display_results(new_orders, remaining_scrap, stats, output_in_inches=False) -> None:
    scale, suffix = (12, '"') if output_in_inches else (1, "'")
    show = lambda value: f"{value * scale:.2f}{suffix}"
    print("\n" + "=" * 60)
    print("LUMBER ORDER OPTIMIZATION RESULTS")
    print("=" * 60)
    print(f"  Total length needed:   {show(stats['total_needed'])}")
    print(f"  Scrap used:            {show(stats['scrap_used'])}")
    print(f"  New stock purchased:   {show(stats['new_stock_used'])}")
    print(f"  New-stock offcut:      {show(stats['waste'])}")
    print(f"  Kerf consumed:         {show(stats['kerf_waste'])}")
    if remaining_scrap:
        print(f"  Remaining scrap:       {', '.join(show(x) for x in remaining_scrap)}")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
