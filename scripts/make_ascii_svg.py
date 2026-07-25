#!/usr/bin/env python3
"""Generate an animated monochrome ASCII-art SVG from a prepped photo.

The input image is converted to a grid of ASCII characters using a density
ramp. Each row is revealed left-to-right with SMIL animation, and a terminal
style cursor travels along the reveal. The final SVG is self-contained,
monochrome, and safe for GitHub README rendering.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image, UnidentifiedImageError

# File paths ------------------------------------------------------------------
DEFAULT_INPUT = "assets/source-prepped.png"
DEFAULT_OUTPUT = "anudeep-ascii.svg"

# ASCII density ramp (bright -> dark) ------------------------------------------
DENSITY_RAMP = " .`:-=+*cs#%@"

# Visual constants -----------------------------------------------------------
TARGET_COLUMNS = 100
FONT_SIZE = 10
CHAR_WIDTH = 6
LINE_HEIGHT = 10
BG_COLOR = "#000000"
TEXT_COLOR = "#d0d0d0"
FONT_FAMILY = "JetBrains Mono, Cascadia Code, Consolas, monospace"
CURSOR_WIDTH = 2
ROW_REVEAL_DURATION = 0.20  # seconds spent revealing each row

# SVG namespace --------------------------------------------------------------
SVG_NS = "http://www.w3.org/2000/svg"
XML_NS = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("xml", XML_NS)


def load_image(path: str | Path) -> Image.Image:
    """Load a grayscale-ready image from disk.

    Args:
        path: Filesystem path to the input image.

    Returns:
        A PIL ``Image`` in grayscale (``L``) mode.

    Raises:
        FileNotFoundError: If the image file does not exist.
        ValueError: If the file is not a supported image format.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input image not found: {path}")

    try:
        image = Image.open(path).convert("L")
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupted image: {path}") from exc

    return image


def resize_to_columns(image: Image.Image, target_columns: int = TARGET_COLUMNS) -> Image.Image:
    """Resize an image so its width is roughly ``target_columns`` pixels.

    Args:
        image: A PIL ``Image``.
        target_columns: Desired width in pixels.

    Returns:
        A resized PIL ``Image`` preserving the original aspect ratio.
    """
    width, height = image.size
    if width != target_columns:
        ratio = target_columns / width
        new_size = (target_columns, max(1, int(height * ratio)))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
    return image


def convert_to_ascii(image: Image.Image) -> list[str]:
    """Map a grayscale image to ASCII rows using the density ramp.

    Args:
        image: A PIL ``Image`` in ``L`` mode.

    Returns:
        A list of strings, one per image row.
    """
    pixels = np.array(image, dtype=np.int16)

    # DENSITY_RAMP[0] is the brightest character, so we invert the intensity.
    ramp_len = len(DENSITY_RAMP)
    indices = ((255 - pixels) * (ramp_len - 1) // 255).astype(np.uint8)

    return ["".join(DENSITY_RAMP[idx] for idx in row) for row in indices]


def _view_dimensions(rows: int, cols: int) -> tuple[int, int]:
    """Compute the SVG viewBox size from the ASCII grid dimensions."""
    view_width = cols * CHAR_WIDTH
    view_height = rows * LINE_HEIGHT
    return view_width, view_height


def build_svg(ascii_rows: list[str]) -> str:
    """Build the animated ASCII SVG from a list of ASCII rows.

    Args:
        ascii_rows: ASCII art rows, one string per row.

    Returns:
        The SVG document as a UTF-8 string.
    """
    rows = len(ascii_rows)
    cols = len(ascii_rows[0]) if rows else 0
    view_width, view_height = _view_dimensions(rows, cols)
    total_duration = rows * ROW_REVEAL_DURATION

    svg = ET.Element(
        "svg",
        {
            "xmlns": SVG_NS,
            "viewBox": f"0 0 {view_width} {view_height}",
            "preserveAspectRatio": "xMidYMid meet",
        },
    )

    # Solid black background.
    ET.SubElement(
        svg,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(view_width),
            "height": str(view_height),
            "fill": BG_COLOR,
        },
    )

    # Shared definitions for per-row clip-path animations.
    defs = ET.SubElement(svg, "defs")

    # Group that holds all ASCII rows.
    ascii_group = ET.SubElement(svg, "g", {"class": "ascii-art"})

    x_positions = ",".join(str(c * CHAR_WIDTH) for c in range(cols))

    for row_index, row_text in enumerate(ascii_rows):
        baseline = (row_index + 1) * LINE_HEIGHT
        row_start = row_index * ROW_REVEAL_DURATION
        clip_id = f"clip-row-{row_index}"

        # Clip path that grows from left to right, revealing the row.
        clip_path = ET.SubElement(defs, "clipPath", {"id": clip_id})
        clip_rect = ET.SubElement(
            clip_path,
            "rect",
            {
                "x": "0",
                "y": str(row_index * LINE_HEIGHT),
                "width": "0",
                "height": str(LINE_HEIGHT),
            },
        )
        ET.SubElement(
            clip_rect,
            "animate",
            {
                "attributeName": "width",
                "from": "0",
                "to": str(view_width),
                "begin": f"{row_start:.1f}s",
                "dur": f"{ROW_REVEAL_DURATION}s",
                "fill": "freeze",
                "calcMode": "linear",
            },
        )

        # The row text itself.
        text_element = ET.SubElement(
            ascii_group,
            "text",
            {
                "x": x_positions,
                "y": str(baseline),
                "fill": TEXT_COLOR,
                "font-family": FONT_FAMILY,
                "font-size": str(FONT_SIZE),
                "clip-path": f"url(#{clip_id})",
                "{%s}space" % XML_NS: "preserve",
            },
        )
        text_element.text = row_text

    # Terminal cursor that follows the reveal path row by row.
    cursor_path = " ".join(
        f"M 0,{(i + 1) * LINE_HEIGHT} L {view_width},{(i + 1) * LINE_HEIGHT}"
        for i in range(rows)
    )
    cursor = ET.SubElement(
        svg,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(CURSOR_WIDTH),
            "height": str(LINE_HEIGHT),
            "fill": TEXT_COLOR,
        },
    )
    ET.SubElement(
        cursor,
        "animateMotion",
        {
            "path": cursor_path,
            "begin": "0s",
            "dur": f"{total_duration}s",
            "fill": "freeze",
            "calcMode": "linear",
        },
    )

    # Add a small copyright/style comment (optional, kept minimal).
    ET.SubElement(svg, "desc").text = "Animated ASCII portrait generated by make_ascii_svg.py"

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
    """Run the ASCII SVG generation pipeline.

    Args:
        argv: Optional command-line arguments. If ``None``, ``sys.argv`` is used.

    Returns:
        ``0`` on success, ``1`` on failure.
    """
    parser = argparse.ArgumentParser(
        description="Generate an animated ASCII-art SVG from a prepped photo.",
    )
    parser.add_argument(
        "--input",
        "-i",
        default=DEFAULT_INPUT,
        help="Path to the prepped PNG image.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help="Path to the output SVG file.",
    )
    args = parser.parse_args(argv)

    try:
        print("Loading image...")
        image = load_image(args.input)

        print("Generating ASCII...")
        image = resize_to_columns(image)
        ascii_rows = convert_to_ascii(image)

        print("Building SVG...")
        svg_content = build_svg(ascii_rows)

        save_svg(svg_content, args.output)
        print(f"Saved {args.output}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
