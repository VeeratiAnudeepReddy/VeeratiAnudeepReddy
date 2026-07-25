#!/usr/bin/env python3
"""Generate an animated terminal-style info card SVG for a GitHub profile.

The card mimics a modern Linux terminal / neofetch look: dark background,
rounded border, title bar with traffic lights, and content rows that fade and
slide in sequentially using pure SVG SMIL animations.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_OUTPUT = "info-card.svg"
SVG_NS = "http://www.w3.org/2000/svg"

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------
WIDTH = 720
TITLE_BAR_HEIGHT = 34
BORDER_RADIUS = 12
PADDING_X = 28
PADDING_Y = 24
FONT_SIZE = 14
LINE_HEIGHT = 22
STAGGER = 0.10  # seconds between row reveals
ANIMATION_DURATION = 0.35

# Colors
BG_COLOR = "#0d1117"
BORDER_COLOR = "#30363d"
TITLE_BAR_COLOR = "#161b22"
TEXT_COLOR = "#c9d1d9"
DIM_TEXT_COLOR = "#8b949e"
LABEL_COLOR = "#79c0ff"      # blue-ish label
HEADER_COLOR = "#7ee787"     # green section headers
LINK_COLOR = "#58a6ff"       # link blue
DOT_RED = "#ff5f56"
DOT_YELLOW = "#ffbd2e"
DOT_GREEN = "#27c93f"

# Content rows: (label, value). value=None renders label as a standalone line.
PROFILE_ROWS: list[tuple[str | None, str | None]] = [
    ("Name", "Anudeep Reddy Veerati"),
    ("Role", "Computer Science Student"),
    ("College", "VNR VJIET"),
    ("CGPA", "9.35"),
    (None, None),
    ("Languages", "C++, Python, Java, JavaScript"),
    ("Frontend", "React, Next.js, Flutter, Tailwind CSS"),
    ("Backend", "Node.js, Express"),
    ("Databases", "MongoDB, PostgreSQL, Firebase, Supabase"),
    ("AI", "YOLO, OpenCV, Transformers, Pandas"),
    ("Competitive Programming", "CodeChef ★★, Codeforces"),
    (None, None),
    ("Projects", None),
    ("  • Civix", None),
    ("  • StudyAI", None),
    ("  • Pothole Mapper", None),
    ("  • VoIP Caller", None),
    (None, None),
    ("Current Focus", None),
    ("  • AI", None),
    ("  • System Design", None),
    ("  • Competitive Programming", None),
    (None, None),
    ("GitHub", "github.com/VeeratiAnudeepReddy"),
]


def _estimate_text_width(text: str, font_size: int = FONT_SIZE) -> float:
    """Roughly estimate text width using a monospace character ratio."""
    return len(text) * font_size * 0.6


def render_line(
    parent: ET.Element,
    label: str | None,
    value: str | None,
    x: int,
    y: int,
    delay_index: int,
    label_column_width: float,
    label_color: str = LABEL_COLOR,
    value_color: str = TEXT_COLOR,
) -> None:
    """Add an animated terminal line to the SVG parent.

    Args:
        parent: The SVG group/element to append the line to.
        label: Label text. If ``value`` is ``None`` the label is rendered
            standalone (e.g. section headers or bullets).
        value: Value text. When provided, it is rendered after the label column.
        x: Left padding position.
        y: Baseline y position.
        delay_index: Row index used to stagger the entrance animation.
        label_column_width: Pixel width reserved for the label column.
        label_color: Fill color for the label.
        value_color: Fill color for the value.
    """
    group = ET.SubElement(parent, "g", {"opacity": "0"})

    text_element = ET.SubElement(
        group,
        "text",
        {
            "x": str(x),
            "y": str(y),
            "fill": TEXT_COLOR,
            "font-family": "JetBrains Mono, Cascadia Code, Consolas, monospace",
            "font-size": str(FONT_SIZE),
            "font-weight": "normal",
        },
    )

    if value is None:
        # Standalone line (blank rows are skipped by the caller).
        text_element.set("fill", label_color)
        text_element.text = label or ""
    else:
        # Label tspan
        label_tspan = ET.SubElement(
            text_element,
            "tspan",
            {
                "fill": label_color,
                "font-weight": "bold",
            },
        )
        label_tspan.text = f"{label}:"

        # Value tspan, positioned after the aligned label column.
        value_x = x + label_column_width + 16
        value_tspan = ET.SubElement(
            text_element,
            "tspan",
            {
                "x": str(value_x),
                "fill": value_color,
            },
        )
        value_tspan.text = value

    delay = delay_index * STAGGER

    # Fade in
    ET.SubElement(
        group,
        "animate",
        {
            "attributeName": "opacity",
            "from": "0",
            "to": "1",
            "begin": f"{delay:.2f}s",
            "dur": f"{ANIMATION_DURATION:.2f}s",
            "fill": "freeze",
            "calcMode": "linear",
        },
    )

    # Slide in from the left
    ET.SubElement(
        group,
        "animateTransform",
        {
            "attributeName": "transform",
            "type": "translate",
            "from": "-15 0",
            "to": "0 0",
            "begin": f"{delay:.2f}s",
            "dur": f"{ANIMATION_DURATION:.2f}s",
            "fill": "freeze",
            "calcMode": "linear",
            "additive": "sum",
        },
    )


def build_svg(rows: list[tuple[str | None, str | None]] = PROFILE_ROWS) -> str:
    """Build the animated terminal info-card SVG.

    Args:
        rows: List of ``(label, value)`` tuples describing the card content.

    Returns:
        SVG document as a UTF-8 string.
    """
    # Compute card height from rows.
    visible_rows = [row for row in rows if row != (None, None)]
    content_height = len(visible_rows) * LINE_HEIGHT
    height = TITLE_BAR_HEIGHT + PADDING_Y + content_height + PADDING_Y

    # Compute aligned label column width for rows that have both label and value.
    labeled_rows = [
        label for label, value in rows if label and value is not None and not label.lstrip().startswith("•")
    ]
    max_label_len = max((len(label) for label in labeled_rows), default=0)
    label_column_width = _estimate_text_width("X" * max_label_len, FONT_SIZE)

    svg = ET.Element(
        "svg",
        {
            "xmlns": SVG_NS,
            "viewBox": f"0 0 {WIDTH} {height}",
            "preserveAspectRatio": "xMidYMid meet",
        },
    )

    # Clip path keeps child elements inside the rounded terminal window.
    defs = ET.SubElement(svg, "defs")
    clip = ET.SubElement(defs, "clipPath", {"id": "terminal-clip"})
    ET.SubElement(
        clip,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(WIDTH),
            "height": str(height),
            "rx": str(BORDER_RADIUS),
            "ry": str(BORDER_RADIUS),
        },
    )

    # Terminal window group.
    terminal = ET.SubElement(svg, "g", {"clip-path": "url(#terminal-clip)"})

    # Background fill.
    ET.SubElement(
        terminal,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(WIDTH),
            "height": str(height),
            "fill": BG_COLOR,
        },
    )

    # Title bar.
    ET.SubElement(
        terminal,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(WIDTH),
            "height": str(TITLE_BAR_HEIGHT),
            "fill": TITLE_BAR_COLOR,
        },
    )

    # Traffic-light dots.
    dot_y = TITLE_BAR_HEIGHT // 2
    dot_r = 5
    dot_spacing = 18
    for color, offset in [(DOT_RED, 1), (DOT_YELLOW, 2), (DOT_GREEN, 3)]:
        ET.SubElement(
            terminal,
            "circle",
            {
                "cx": str(PADDING_X + offset * dot_spacing),
                "cy": str(dot_y),
                "r": str(dot_r),
                "fill": color,
            },
        )

    # Title text.
    title = ET.SubElement(
        terminal,
        "text",
        {
            "x": str(PADDING_X + 4 * dot_spacing),
            "y": str(dot_y + 4),
            "fill": DIM_TEXT_COLOR,
            "font-family": "JetBrains Mono, Cascadia Code, Consolas, monospace",
            "font-size": "12",
        },
    )
    title.text = "user@github: ~$ neofetch"

    # Border outline.
    ET.SubElement(
        svg,
        "rect",
        {
            "x": "0.5",
            "y": "0.5",
            "width": str(WIDTH - 1),
            "height": str(height - 1),
            "rx": str(BORDER_RADIUS),
            "ry": str(BORDER_RADIUS),
            "fill": "none",
            "stroke": BORDER_COLOR,
            "stroke-width": "1",
        },
    )

    # Content rows.
    content_group = ET.SubElement(svg, "g")
    start_y = TITLE_BAR_HEIGHT + PADDING_Y + FONT_SIZE

    delay_index = 0
    for label, value in rows:
        if label is None and value is None:
            continue

        # Section headers get a distinct accent color.
        if value is None and not label.lstrip().startswith("•"):
            line_label_color = HEADER_COLOR
        elif label == "GitHub":
            line_label_color = LABEL_COLOR
            value_color = LINK_COLOR
        else:
            line_label_color = LABEL_COLOR
            value_color = TEXT_COLOR

        render_line(
            parent=content_group,
            label=label,
            value=value,
            x=PADDING_X,
            y=start_y + delay_index * LINE_HEIGHT,
            delay_index=delay_index,
            label_column_width=label_column_width,
            label_color=line_label_color,
            value_color=value_color,
        )
        delay_index += 1

    return ET.tostring(svg, encoding="unicode")


def save_svg(svg_content: str, path: str | Path) -> None:
    """Write the SVG document to disk.

    Args:
        svg_content: The SVG XML string.
        path: Destination filesystem path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg_content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the info-card generation pipeline.

    Args:
        argv: Optional command-line arguments. If ``None``, ``sys.argv`` is used.

    Returns:
        ``0`` on success, ``1`` on failure.
    """
    parser = argparse.ArgumentParser(
        description="Generate an animated terminal-style info card SVG.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help="Path to the output SVG file.",
    )
    args = parser.parse_args(argv)

    try:
        print("Generating info card...")
        svg_content = build_svg()
        save_svg(svg_content, args.output)
        print(f"Saved {args.output}")
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
