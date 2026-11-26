#!/usr/bin/env python3
"""Batch background removal with optional rembg and deterministic local fallbacks."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import binary_fill_holes


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_ALPHA_BYPASS_THRESHOLD = 0.05


def _has_clean_transparency(
    img: Image.Image, threshold: float = DEFAULT_ALPHA_BYPASS_THRESHOLD
) -> tuple[bool, float]:
    """Return (should_bypass, transparent_ratio) if the image already has a transparent background."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        alpha = np.asarray(img.convert("RGBA"), dtype=np.uint8)[:, :, 3]
        transparent_ratio = float((alpha == 0).sum()) / float(alpha.size)
        return transparent_ratio > threshold, transparent_ratio
    return False, 0.0


def solidify_alpha_mask(alpha_channel: np.ndarray) -> np.ndarray:
    binary_mask = alpha_channel > 0
    filled_mask = binary_fill_holes(binary_mask)
    return np.where(filled_mask, np.maximum(alpha_channel, 255), 0).astype(np.uint8)


def _list_images(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported input format: {input_path.suffix}")
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        )
    raise FileNotFoundError(f"Input does not exist: {input_path}")


def _corner_background_color(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    size = max(8, min(h, w) // 20)
    patches = [
        rgb[:size, :size].reshape(-1, 3),
        rgb[:size, -size:].reshape(-1, 3),
        rgb[-size:, :size].reshape(-1, 3),
        rgb[-size:, -size:].reshape(-1, 3),
    ]
    corners = np.concatenate(patches, axis=0).astype(np.float32)
    return np.median(corners, axis=0)


def _threshold_alpha(rgb: np.ndarray) -> np.ndarray:
    """Remove a consistently colored background while retaining soft edge detail."""
    bg = _corner_background_color(rgb)
    bg = np.broadcast_to(bg, rgb.shape[:2] + (3,))
    distance = np.linalg.norm(rgb.astype(np.float32) - bg, axis=2)
    near = np.percentile(distance, 20)
    far = max(float(near * 2.5), 18.0)
    alpha = np.clip((distance - near) / max(1.0, far - near), 0.0, 1.0)

    # Saturated, spatially regular subjects need an edge-aware clamp instead of hard keying.
    alpha = np.uint8(np.clip(alpha * 255.0, 0, 255))
    mask = Image.fromarray(alpha, "L").filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=0.7))
    return np.asarray(mask, dtype=np.uint8)


def _decontaminate(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Remove edge spill by replacing fringe RGB from neighboring foreground colors."""
    alpha_f = alpha.astype(np.float32) / 255.0
    eroded = np.asarray(
        Image.fromarray(alpha, "L").filter(ImageFilter.MinFilter(5)),
        dtype=np.float32,
    ) / 255.0
    spill = np.clip((alpha_f - eroded) * 6.0, 0.0, 1.0)

    blurred = np.asarray(
        Image.fromarray(rgb, "RGB").filter(ImageFilter.GaussianBlur(radius=2.0)),
        dtype=np.float32,
    )
    eroded_rgb = np.asarray(
        Image.fromarray(rgb, "RGB").filter(ImageFilter.MinFilter(5)),
        dtype=np.float32,
    )
    cleaned = rgb.astype(np.float32) * (1.0 - spill[..., None]) + eroded_rgb * spill[..., None]

    # Color fringes only exist near partially transparent borders.
    edge_weight = np.clip(alpha_f * (1.0 - eroded) * 8.0, 0.0, 1.0)
    cleaned = cleaned * (1.0 - edge_weight[..., None]) + blurred * edge_weight[..., None]
    return np.clip(cleaned, 0, 255).astype(np.uint8)


def _rembg_alpha(image: Image.Image, model: str) -> np.ndarray | None:
    try:
        from rembg import new_session, remove
    except ImportError:
        return None

    try:
        session = new_session(model)
        result = remove(image, session=session, only_mask=True)
        if result.mode != "L":
            result = result.convert("L")
        return np.asarray(result, dtype=np.uint8)
    except Exception as exc:
        print(f"  rembg unavailable ({exc}); using local threshold fallback", file=sys.stderr)
        return None


def _feather_alpha(alpha: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return alpha
    mask = Image.fromarray(alpha, "L")
    if radius > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=float(radius)))
    return np.asarray(mask, dtype=np.uint8)


def remove_background(
    input_path: Path,
    output_path: Path,
    model: str,
    feather: int,
    alpha_threshold: float = DEFAULT_ALPHA_BYPASS_THRESHOLD,
) -> dict:
    with Image.open(input_path) as source:
        should_bypass, transparent_ratio = _has_clean_transparency(source, alpha_threshold)
        if should_bypass:
            print(
                f"[BYPASS] {input_path} already has a clean transparent background "
                f"({transparent_ratio * 100:.1f}% alpha). Skipping AI segmentation."
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            out_img = source if source.mode == "RGBA" else source.convert("RGBA")
            out_img.save(output_path, "PNG")
            return {
                "input": str(input_path),
                "output": str(output_path),
                "format": "RGBA",
                "rembg": False,
                "bypassed": True,
                "transparent_ratio": transparent_ratio,
            }
        image = source.convert("RGBA")

    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    rembg_mask = _rembg_alpha(image, model)
    alpha = rembg_mask if rembg_mask is not None else _threshold_alpha(rgb)
    alpha = _feather_alpha(alpha, max(0, feather))

    cleaned_rgb = _decontaminate(rgb, alpha)
    result = Image.fromarray(np.dstack((cleaned_rgb, alpha)), "RGBA")
    solidified_alpha = solidify_alpha_mask(np.asarray(result.getchannel("A"), dtype=np.uint8))
    result.putalpha(Image.fromarray(solidified_alpha, "L"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, "PNG", optimize=True)
    return {
        "input": str(input_path),
        "output": str(output_path),
        "format": "RGBA",
        "rembg": rembg_mask is not None,
        "bypassed": False,
    }


def _output_path(input_path: Path, source_root: Path, output: Path) -> Path:
    if output.is_dir() or not output.suffix:
        relative = input_path.relative_to(source_root) if input_path != source_root else input_path.name
        rel_path = Path(relative)
        stem = rel_path.stem
        return output / rel_path.parent / f"{stem}_alpha.png"
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove backgrounds and export antialiased transparent RGBA PNG cutouts."
    )
    parser.add_argument("--input", required=True, help="A single image or input directory.")
    parser.add_argument("--output", required=True, help="Output PNG file or destination directory.")
    parser.add_argument("--model", default="u2net", help="rembg segmentation model identifier.")
    parser.add_argument("--feather", type=int, default=1, help="Edge feathering radius in pixels.")
    parser.add_argument(
        "--alpha-threshold",
        type=float,
        default=DEFAULT_ALPHA_BYPASS_THRESHOLD,
        help="Transparent pixel ratio above which segmentation is bypassed.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    try:
        images = _list_images(input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not images:
        print(f"No supported images found in: {input_path}", file=sys.stderr)
        return 1

    output_was_directory = input_path.is_dir() or not output.suffix
    if output_was_directory:
        output.mkdir(parents=True, exist_ok=True)

    success = 0
    for source in images:
        destination = _output_path(source, input_path, output) if output_was_directory else output
        try:
            remove_background(
                source, destination, args.model, args.feather, args.alpha_threshold
            )
            print(f"Processed: {source} -> {destination}")
            success += 1
        except Exception as exc:
            print(f"Failed: {source}: {exc}", file=sys.stderr)

    return 0 if success == len(images) else 1


if __name__ == "__main__":
    raise SystemExit(main())
