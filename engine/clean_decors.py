#!/usr/bin/env python3
"""Clean 3x3 decor grid cutouts using corner-gradient background distance and component isolation."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    binary_erosion,
    binary_fill_holes,
    label,
    sobel,
)

DEFAULT_INPUT = Path("assets/brands/gsshop/raw/9 christmas items azure blue.jpg")
ALT_INPUT = Path("assets/brands/gsshop/raw/9_christmas_items_azure_blue.jpg")
DEFAULT_OUTPUT_DIR = Path("assets/brands/gsshop/decors")

ITEM_MAPPING = [
    {"index": 0, "name": "decor_snowman.png", "row": 0, "col": 0},
    {"index": 1, "name": "decor_snowflake.png", "row": 0, "col": 1},
    {"index": 2, "name": "decor_gift_box.png", "row": 0, "col": 2},
    {"index": 3, "name": "decor_bauble.png", "row": 1, "col": 0},
    {"index": 4, "name": "decor_tree.png", "row": 1, "col": 1},
    {"index": 5, "name": "decor_candy_cane.png", "row": 1, "col": 2},
    {"index": 6, "name": "decor_santa_hat.png", "row": 2, "col": 0},
    {"index": 7, "name": "decor_gingerbread.png", "row": 2, "col": 1},
    {"index": 8, "name": "decor_stocking.png", "row": 2, "col": 2},
]


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert uint8 RGB array (H, W, 3) to approximate CIE LAB float32."""
    srgb = rgb.astype(np.float32) / 255.0
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)

    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: np.ndarray) -> np.ndarray:
        return np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16.0 / 116.0)

    fx, fy, fz = f(x), f(y), f(z)
    l_chan = 116.0 * fy - 16.0
    a_chan = 500.0 * (fx - fy)
    b_chan = 200.0 * (fy - fz)
    return np.stack([l_chan, a_chan, b_chan], axis=-1)


def _bilinear_corner_background(arr: np.ndarray, margin: int = 10) -> np.ndarray:
    """Sample 4 outer corner margins (10px) and bilinearly interpolate studio gradient."""
    h, w = arr.shape[:2]
    m = min(margin, h // 4, w // 4)
    tl = np.median(arr[:m, :m].reshape(-1, 3), axis=0)
    tr = np.median(arr[:m, -m:].reshape(-1, 3), axis=0)
    bl = np.median(arr[-m:, :m].reshape(-1, 3), axis=0)
    br = np.median(arr[-m:, -m:].reshape(-1, 3), axis=0)

    ys = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    top = tl * (1.0 - xs) + tr * xs
    bot = bl * (1.0 - xs) + br * xs
    return top * (1.0 - ys) + bot * ys


def _isolate_central_component(mask: np.ndarray, min_area: int = 150) -> np.ndarray:
    """Keep connected components connected to or near the subject center, dropping floor noise."""
    labeled, num_features = label(mask)
    if num_features == 0:
        return mask

    h, w = mask.shape
    cy, cx = h / 2.0, w / 2.0
    areas = np.bincount(labeled.ravel())
    areas[0] = 0

    best_label = int(np.argmax(areas))
    # Also keep large components near the center (e.g., separated parts of same object).
    keep = np.zeros_like(mask, dtype=bool)
    for comp_id in range(1, num_features + 1):
        if areas[comp_id] < min_area:
            continue
        if comp_id == best_label:
            keep |= labeled == comp_id
            continue
        ys, xs = np.where(labeled == comp_id)
        dist = np.hypot(ys.mean() - cy, xs.mean() - cx)
        if dist < min(h, w) * 0.42 and areas[comp_id] > areas[best_label] * 0.05:
            keep |= labeled == comp_id

    return keep


def _segment_standard(rgb: np.ndarray, lab_dist: np.ndarray) -> np.ndarray:
    """Segment colored/3D items using LAB distance + edge boundary + hole fill."""
    gray = (
        0.299 * rgb[..., 0].astype(np.float32)
        + 0.587 * rgb[..., 1].astype(np.float32)
        + 0.114 * rgb[..., 2].astype(np.float32)
    )
    grad = np.hypot(sobel(gray, axis=1), sobel(gray, axis=0))

    # Sample corner noise floor from 10px outer corners.
    corner_dists = np.concatenate(
        [
            lab_dist[:10, :10].ravel(),
            lab_dist[:10, -10:].ravel(),
            lab_dist[-10:, :10].ravel(),
            lab_dist[-10:, -10:].ravel(),
        ]
    )
    noise_floor = float(np.percentile(corner_dists, 98))
    thresh = max(noise_floor * 2.0, 5.5)

    # Combine LAB distance with edge contours so bright white highlights on
    # white subjects (e.g. snowman, gift box) stay enclosed for hole filling.
    core = (lab_dist > thresh) | (grad > 11.0)
    core[:10, :] = False
    core[-10:, :] = False
    core[:, :10] = False
    core[:, -10:] = False

    core = binary_closing(core, structure=np.ones((5, 5), dtype=bool))
    core = _isolate_central_component(core, min_area=200)
    core = binary_fill_holes(core)
    return core


def _segment_snowflake(rgb: np.ndarray, lab_dist: np.ndarray) -> np.ndarray:
    """Segment white 3D snowflake using edge detection + small-kernel closing."""
    gray = (
        0.299 * rgb[..., 0].astype(np.float32)
        + 0.587 * rgb[..., 1].astype(np.float32)
        + 0.114 * rgb[..., 2].astype(np.float32)
    )
    grad = np.hypot(sobel(gray, axis=1), sobel(gray, axis=0))

    # Keep closing kernel small (3x3) so gaps between snowflake branches stay transparent.
    combined = (grad > 11.0) | (lab_dist > 2.8)
    combined[:10, :] = False
    combined[-10:, :] = False
    combined[:, :10] = False
    combined[:, -10:] = False

    closed = binary_closing(combined, structure=np.ones((3, 3), dtype=bool))
    isolated = _isolate_central_component(closed, min_area=300)
    return binary_fill_holes(isolated)


def _build_smooth_alpha(
    core_mask: np.ndarray, lab_dist: np.ndarray, feather_radius: float = 1.5
) -> np.ndarray:
    """Create smoothly antialiased alpha matte with 0 outer margin and solid 255 core."""
    # Soft ramp near object boundary based on LAB distance.
    soft_band = binary_dilation(core_mask, structure=np.ones((3, 3), dtype=bool)) & ~core_mask
    alpha_f = np.where(core_mask, 255.0, 0.0).astype(np.float32)

    if np.any(soft_band):
        band_vals = np.clip((lab_dist - 2.0) / 8.0, 0.0, 1.0) * 255.0
        alpha_f = np.where(soft_band, band_vals, alpha_f)

    alpha_img = Image.fromarray(np.clip(alpha_f, 0, 255).astype(np.uint8), "L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=feather_radius))
    alpha = np.asarray(alpha_img, dtype=np.uint8)

    # Keep interior core strictly 255 and clip faint residual halo (<12) to 0.
    inner_core = binary_erosion(core_mask, structure=np.ones((3, 3), dtype=bool))
    alpha = np.where(inner_core, 255, alpha)
    alpha = np.where(alpha < 12, 0, alpha)

    # Guarantee 10px outer margins are 100% transparent (alpha = 0).
    alpha[:10, :] = 0
    alpha[-10:, :] = 0
    alpha[:, :10] = 0
    alpha[:, -10:] = 0
    return alpha.astype(np.uint8)


def _decontaminate_edges(rgb: np.ndarray, bg_rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Un-premultiply light studio background color on semi-transparent border pixels."""
    a = alpha.astype(np.float32) / 255.0
    semi = (alpha > 0) & (alpha < 255)
    out = rgb.astype(np.float32).copy()
    if np.any(semi):
        # Recover foreground color: fg = (observed - (1 - a) * bg) / a
        denom = np.maximum(a[..., None], 0.15)
        recovered = (out - (1.0 - a[..., None]) * bg_rgb) / denom
        out = np.where(semi[..., None], np.clip(recovered, 0.0, 255.0), out)
    # Zero RGB on fully transparent pixels for clean PNG compression.
    out[alpha == 0] = 0.0
    return out.astype(np.uint8)


def clean_cell(crop: Image.Image, item_name: str) -> Image.Image:
    rgb = np.asarray(crop.convert("RGB"), dtype=np.uint8)
    bg_rgb = _bilinear_corner_background(rgb.astype(np.float32), margin=10)

    lab_fg = _rgb_to_lab(rgb)
    lab_bg = _rgb_to_lab(np.clip(bg_rgb, 0, 255).astype(np.uint8))
    lab_dist = np.linalg.norm(lab_fg - lab_bg, axis=2)

    if "snowflake" in item_name:
        core_mask = _segment_snowflake(rgb, lab_dist)
    else:
        core_mask = _segment_standard(rgb, lab_dist)

    alpha = _build_smooth_alpha(core_mask, lab_dist, feather_radius=1.5)
    clean_rgb = _decontaminate_edges(rgb, bg_rgb, alpha)
    return Image.fromarray(np.dstack((clean_rgb, alpha)), "RGBA")


def run(input_path: Path, output_dir: Path) -> list[dict]:
    if not input_path.is_file() and ALT_INPUT.is_file():
        input_path = ALT_INPUT
    if not input_path.is_file():
        raise FileNotFoundError(f"Source grid image not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with Image.open(input_path) as grid_img:
        w, h = grid_img.size
        cell_w = w / 3.0
        cell_h = h / 3.0

        for item in ITEM_MAPPING:
            x0 = int(round(item["col"] * cell_w))
            y0 = int(round(item["row"] * cell_h))
            x1 = int(round((item["col"] + 1) * cell_w))
            y1 = int(round((item["row"] + 1) * cell_h))

            crop = grid_img.crop((x0, y0, x1, y1))
            cleaned = clean_cell(crop, item["name"])
            dest = output_dir / item["name"]
            cleaned.save(dest, "PNG", optimize=True)

            alpha = np.asarray(cleaned, dtype=np.uint8)[:, :, 3]
            zero_pct = float((alpha == 0).mean() * 100.0)
            semi_pct = float(((alpha > 0) & (alpha < 255)).mean() * 100.0)
            solid_pct = float((alpha == 255).mean() * 100.0)
            corner_max = int(alpha[:10, :10].max())

            results.append(
                {
                    "name": item["name"],
                    "size": cleaned.size,
                    "zero_pct": zero_pct,
                    "semi_pct": semi_pct,
                    "solid_pct": solid_pct,
                    "corner_max": corner_max,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean 3x3 decor cutouts with smooth alpha mattes.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    stats = run(args.input, args.output_dir)
    for s in stats:
        print(
            f"{s['name']}: size={s['size']}, transparent={s['zero_pct']:.1f}%, "
            f"antialiased={s['semi_pct']:.2f}%, solid={s['solid_pct']:.1f}%, "
            f"corner_0_10_max_alpha={s['corner_max']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
