#!/usr/bin/env python3
"""Prepare a source photo for ASCII-art generation.

This script loads a JPEG photo, removes its background with rembg,
composites the foreground onto a pure white background, enhances local
contrast with CLAHE, denoises while preserving edges, resizes to a maximum
width of 100 pixels (preserving aspect ratio), and saves the result as a PNG.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from rembg import remove

DEFAULT_INPUT = "assets/source-photo.jpg"
DEFAULT_OUTPUT = "assets/source-prepped.png"
MAX_WIDTH = 100


def load_image(path: str | Path) -> Image.Image:
    """Load a source image from disk and return it as an RGB PIL image.

    Args:
        path: Filesystem path to the input image.

    Returns:
        A PIL ``Image`` in RGB mode.

    Raises:
        FileNotFoundError: If the image file does not exist.
        ValueError: If the file is not a supported image format.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Source image not found: {path}")

    try:
        image = Image.open(path).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError(f"Unsupported or corrupted image: {path}") from exc

    return image


def remove_background(image: Image.Image) -> Image.Image:
    """Remove the background from an RGB image using rembg.

    Args:
        image: A PIL ``Image`` in RGB mode.

    Returns:
        A PIL ``Image`` in RGBA mode with a transparent background.

    Raises:
        RuntimeError: If rembg fails to produce a cutout.
    """
    try:
        cutout = remove(image)
    except Exception as exc:
        raise RuntimeError(f"Background removal failed: {exc}") from exc

    return cutout


def composite_white_background(image: Image.Image) -> Image.Image:
    """Composite an RGBA cutout onto a pure white background.

    Args:
        image: A PIL ``Image`` with an alpha channel.

    Returns:
        A PIL ``Image`` in RGB mode on a white background.
    """
    # Start with a solid white RGBA canvas of the same size.
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))

    if image.mode != "RGBA":
        image = image.convert("RGBA")

    # Alpha-composite the foreground onto the white canvas, then drop alpha.
    return Image.alpha_composite(white, image).convert("RGB")


def preprocess(image: Image.Image) -> Image.Image:
    """Enhance an RGB image: grayscale, CLAHE, and edge-preserving denoise.

    Args:
        image: A PIL ``Image`` in RGB mode.

    Returns:
        A PIL ``Image`` in L (grayscale) mode.
    """
    # Convert to a NumPy uint8 grayscale array for OpenCV processing.
    gray = np.array(image.convert("L"), dtype=np.uint8)

    # Apply CLAHE to improve local contrast without over-amplifying noise.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)

    # Non-local means denoising preserves edges while smoothing flat regions.
    denoised = cv2.fastNlMeansDenoising(
        contrast,
        None,
        h=10,
        templateWindowSize=7,
        searchWindowSize=21,
    )

    return Image.fromarray(denoised, mode="L")


def resize_image(image: Image.Image, max_width: int = MAX_WIDTH) -> Image.Image:
    """Resize an image so its width does not exceed ``max_width``.

    Args:
        image: A PIL ``Image``.
        max_width: Maximum allowed width in pixels.

    Returns:
        A resized PIL ``Image`` preserving the original aspect ratio.
    """
    width, height = image.size

    if width > max_width:
        ratio = max_width / width
        new_size = (max_width, int(height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    return image


def save_image(image: Image.Image, path: str | Path) -> None:
    """Save an image to disk, creating parent directories if needed.

    Args:
        image: A PIL ``Image`` to save.
        path: Destination path. The parent directory is created if absent.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def main(argv: list[str] | None = None) -> int:
    """Run the photo preparation pipeline.

    Args:
        argv: Optional command-line arguments. If ``None``, ``sys.argv`` is used.

    Returns:
        ``0`` on success, ``1`` on failure.
    """
    parser = argparse.ArgumentParser(
        description="Prepare a source photo for ASCII-art generation.",
    )
    parser.add_argument(
        "--input",
        "-i",
        default=DEFAULT_INPUT,
        help="Path to the source JPEG image.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help="Path to the output PNG image.",
    )
    args = parser.parse_args(argv)

    try:
        print("Loading image...")
        source = load_image(args.input)

        print("Removing background...")
        cutout = remove_background(source)

        print("Compositing onto white background...")
        filled = composite_white_background(cutout)

        print("Applying CLAHE...")
        prepped = preprocess(filled)

        print("Resizing...")
        resized = resize_image(prepped)

        save_image(resized, args.output)
        print(f"Saved {args.output}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - last-resort safety net
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
