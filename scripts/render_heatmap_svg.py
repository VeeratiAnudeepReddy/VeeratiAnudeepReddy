#!/usr/bin/env python3
"""Render an animated GitHub-style contribution heatmap as an SVG.

Reads ``data/contributions.json`` (produced by ``fetch_contributions.py``)
and writes ``contrib-heatmap.svg``. The heatmap uses GitHub's 53-week by
7-day layout with SMIL-driven diagonal reveal animation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_INPUT = "data/contributions.json"
DEFAULT_OUTPUT = "contrib-heatmap.svg"
DEFAULT_USERNAME = "VeeratiAnudeepReddy"

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------
CELL_SIZE = 11
CELL_GAP = 3
CELL_RADIUS = 4
WEEKS = 53
DAYS = 7

# Professional slate → teal palette (replaces the default GitHub blue-green)
PALETTE = ["#1c2128", "#1a3a4a", "#1e6b7a", "#1f9baa", "#56c2cc"]
BACKGROUND = "#0d1117"
TEXT_COLOR = "#c9d1d9"
SUBTEXT_COLOR = "#8b949e"
FONT_FAMILY = "'JetBrains Mono', 'Cascadia Code', Consolas, monospace"

SVG_WIDTH = 820
MARGIN_LEFT = 80
MARGIN_TOP = 80
GRID_Y0 = MARGIN_TOP + 20
GRID_X0 = MARGIN_LEFT

DIAGONAL_DELAY = 0.04  # seconds per diagonal step
CELL_ANIMATION_DURATION = 0.35  # seconds


def load_contribution_data(path: str | Path) -> dict:
    """Load contribution data from a JSON file.

    Args:
        path: Path to the JSON file produced by ``fetch_contributions.py``.

    Returns:
        Parsed contribution data.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Contribution data not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_grid(days: list[dict]) -> list[list[dict]]:
    """Map a flat list of contribution days into a 7x53 grid.

    GitHub's public contribution graph starts each week on Sunday and has
    7 rows (Sunday -> Saturday). The returned grid is indexed as
    ``grid[row][column]``.

    Args:
        days: Contribution-day dictionaries sorted by date.

    Returns:
        A 7x53 grid where each cell is a contribution-day dictionary or
        ``None`` for missing days.
    """
    grid: list[list[dict | None]] = [[None for _ in range(WEEKS)] for _ in range(DAYS)]

    if not days:
        return grid

    start_date = datetime.strptime(days[0]["date"], "%Y-%m-%d").date()

    for day in days:
        date_obj = datetime.strptime(day["date"], "%Y-%m-%d").date()
        delta_days = (date_obj - start_date).days
        col = delta_days // DAYS
        # GitHub rows: Sunday = 0, Monday = 1, ..., Saturday = 6.
        row = (date_obj.weekday() + 1) % DAYS

        if 0 <= col < WEEKS and 0 <= row < DAYS:
            grid[row][col] = day

    return grid


def _add_text(
    parent: ET.Element,
    x: float,
    y: float,
    text: str,
    *,
    fill: str = TEXT_COLOR,
    font_size: int = 12,
    font_weight: str = "normal",
    text_anchor: str = "start",
) -> ET.Element:
    """Add a text element to the SVG parent."""
    element = ET.SubElement(parent, "text")
    element.set("x", str(x))
    element.set("y", str(y))
    element.set("fill", fill)
    element.set("font-family", FONT_FAMILY)
    element.set("font-size", str(font_size))
    element.set("font-weight", font_weight)
    element.set("text-anchor", text_anchor)
    element.text = text
    return element


def _add_rounded_rect(
    parent: ET.Element,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
    fill: str,
) -> ET.Element:
    """Add a rounded rectangle to the SVG parent."""
    element = ET.SubElement(parent, "rect")
    element.set("x", str(x))
    element.set("y", str(y))
    element.set("width", str(width))
    element.set("height", str(height))
    element.set("rx", str(radius))
    element.set("ry", str(radius))
    element.set("fill", fill)
    return element


def _month_label_x_positions(days: list[dict]) -> list[tuple[str, float]]:
    """Compute month label positions above the heatmap grid.

    Args:
        days: Contribution-day dictionaries sorted by date.

    Returns:
        List of ``(month_label, x)`` tuples for the first week of each month.
    """
    labels: list[tuple[str, float]] = []
    if not days:
        return labels

    start_date = datetime.strptime(days[0]["date"], "%Y-%m-%d").date()
    seen_months: set[str] = set()

    for day in days:
        date_obj = datetime.strptime(day["date"], "%Y-%m-%d").date()
        month_key = date_obj.strftime("%Y-%m")
        if month_key in seen_months:
            continue
        seen_months.add(month_key)

        delta_days = (date_obj - start_date).days
        col = delta_days // DAYS
        x = GRID_X0 + col * (CELL_SIZE + CELL_GAP)
        label = date_obj.strftime("%b")
        labels.append((label, x))

    return labels


def render_heatmap_svg(data: dict) -> ET.Element:
    """Build the animated SVG heatmap element.

    Args:
        data: Parsed contribution data containing ``days`` and ``stats``.

    Returns:
        The root ``<svg>`` element.
    """
    days = data.get("days", [])
    stats = data.get("stats", {})
    grid = build_grid(days)

    # Calculate SVG height based on grid and footer content.
    grid_height = DAYS * (CELL_SIZE + CELL_GAP) - CELL_GAP
    legend_y = GRID_Y0 + grid_height + 35
    footer_y = legend_y + 55
    svg_height = footer_y + 50

    svg = ET.Element("svg")
    svg.set("xmlns", "http://www.w3.org/2000/svg")
    svg.set("width", str(SVG_WIDTH))
    svg.set("height", str(svg_height))
    svg.set("viewBox", f"0 0 {SVG_WIDTH} {svg_height}")
    svg.set("role", "img")
    svg.set("aria-label", "Contribution heatmap")

    # Background.
    _add_rounded_rect(svg, 0, 0, SVG_WIDTH, svg_height, 12, BACKGROUND)

    # Title.
    username = data.get("username", DEFAULT_USERNAME)
    _add_text(
        svg,
        MARGIN_LEFT,
        45,
        f"{username}'s Contribution Activity",
        font_size=18,
        font_weight="bold",
    )

    # Month labels.
    for label, x in _month_label_x_positions(days):
        _add_text(svg, x, GRID_Y0 - 10, label, fill=SUBTEXT_COLOR, font_size=11)

    # Weekday labels (left side).
    weekday_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for row, label in enumerate(weekday_labels):
        if row % 2 == 1:  # GitHub only labels every other day.
            y = GRID_Y0 + row * (CELL_SIZE + CELL_GAP) + CELL_SIZE - 1
            _add_text(
                svg,
                MARGIN_LEFT - 12,
                y,
                label,
                fill=SUBTEXT_COLOR,
                font_size=10,
                text_anchor="end",
            )

    # Heatmap cells.
    for row in range(DAYS):
        for col in range(WEEKS):
            day = grid[row][col]
            level = day["level"] if day else 0
            fill = PALETTE[level]

            x = GRID_X0 + col * (CELL_SIZE + CELL_GAP)
            y = GRID_Y0 + row * (CELL_SIZE + CELL_GAP)

            cell = _add_rounded_rect(svg, x, y, CELL_SIZE, CELL_SIZE, CELL_RADIUS, fill)
            cell.set("opacity", "0")
            cell.set("style", "cursor:pointer")

            # Tooltip: show date + contribution count on hover/touch.
            title_el = ET.SubElement(cell, "title")
            if day:
                count = day.get("count", 0)
                date_str = day.get("date", "")
                label = "contribution" if count == 1 else "contributions"
                title_el.text = f"{date_str}  ·  {count} {label}"
            else:
                title_el.text = "No contributions"

            # Diagonal reveal: delay based on distance from top-left corner.
            diagonal_index = col + row
            begin = diagonal_index * DIAGONAL_DELAY

            animate = ET.SubElement(cell, "animate")
            animate.set("attributeName", "opacity")
            animate.set("from", "0")
            animate.set("to", "1")
            animate.set("dur", f"{CELL_ANIMATION_DURATION}s")
            animate.set("begin", f"{begin:.3f}s")
            animate.set("fill", "freeze")
            animate.set("calcMode", "spline")
            animate.set("keySplines", "0.4 0 0.2 1")
            animate.set("keyTimes", "0;1")

    # Legend.
    legend_x = MARGIN_LEFT
    _add_text(svg, legend_x, legend_y, "Less", fill=SUBTEXT_COLOR, font_size=11)

    legend_square_x = legend_x + 45
    for level, color in enumerate(PALETTE):
        _add_rounded_rect(
            svg,
            legend_square_x + level * (CELL_SIZE + CELL_GAP),
            legend_y - 8,
            CELL_SIZE,
            CELL_SIZE,
            CELL_RADIUS,
            color,
        )
    _add_text(
        svg,
        legend_square_x + 5 * (CELL_SIZE + CELL_GAP) + 10,
        legend_y,
        "More",
        fill=SUBTEXT_COLOR,
        font_size=11,
    )

    # Footer statistics.
    stats_items = [
        ("Total Contributions", str(stats.get("total_contributions", 0))),
        ("Current Streak", f"{stats.get('current_streak', 0)} days"),
        ("Longest Streak", f"{stats.get('longest_streak', 0)} days"),
    ]

    footer_x_start = MARGIN_LEFT
    footer_x_end = SVG_WIDTH - MARGIN_LEFT
    available_width = footer_x_end - footer_x_start
    section_width = available_width / len(stats_items)

    for index, (label, value) in enumerate(stats_items):
        center_x = footer_x_start + section_width * (index + 0.5)
        _add_text(
            svg,
            center_x,
            footer_y,
            label,
            fill=SUBTEXT_COLOR,
            font_size=11,
            text_anchor="middle",
        )
        _add_text(
            svg,
            center_x,
            footer_y + 22,
            value,
            fill=TEXT_COLOR,
            font_size=18,
            font_weight="bold",
            text_anchor="middle",
        )

    return svg


def save_svg(svg: ET.Element, path: str | Path) -> None:
    """Serialize an SVG element to disk.

    Args:
        svg: The root ``<svg>`` element.
        path: Destination path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.ElementTree(svg)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main(argv: list[str] | None = None) -> int:
    """Run the heatmap SVG generation pipeline.

    Args:
        argv: Optional command-line arguments. If ``None``, ``sys.argv`` is used.

    Returns:
        ``0`` on success, ``1`` on failure.
    """
    parser = argparse.ArgumentParser(
        description="Render an animated contribution heatmap SVG.",
    )
    parser.add_argument(
        "--input",
        "-i",
        default=DEFAULT_INPUT,
        help="Path to the contribution JSON file.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help="Path to the output SVG file.",
    )
    args = parser.parse_args(argv)

    try:
        print("Loading contribution data...")
        data = load_contribution_data(args.input)

        print("Generating SVG...")
        svg = render_heatmap_svg(data)

        save_svg(svg, args.output)
        print(f"Saved {args.output}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
