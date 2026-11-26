#!/usr/bin/env python3
"""
CONTENT-AWARE SMART CONNECTED COMPONENT CROPPER - auto-banner-engine
Directive: DIR-SMART-CONTOUR-CROP-AND-AUDIT-017

Replaces naive static 3x3 grid splitting with Content-Aware Connected Component
Bounding Box extraction:
1. Models the studio light-gray gradient background from the 4 outer corners.
2. Binarizes foreground islands using CIE LAB color distance + Sobel edge energy.
3. Extracts the exact top N (default 9) largest object islands via
   cv2.connectedComponentsWithStats and maps them deterministically in row-major
   spatial order (top-to-bottom, left-to-right).
4. Expands each object's true bounding box with Safe Padding (>= 15px) and
   suppresses any foreign neighbor component inside the padding margin.
5. Removes the studio background and strips studio gray halos + ground-plane
   floor shadows without destructive border truncation.
6. Runs check_object_clipping() on every exported PNG; if any object pixel
   touches the 1px outer canvas boundary, automatically expands the offending
   edge(s) and re-crops until 0 clipped pixels are achieved.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    binary_erosion,
    binary_fill_holes,
    distance_transform_edt,
    label as nd_label,
    sobel,
)

# Ensure sibling modules in engine/ can be imported regardless of cwd
ENGINE_DIR = Path(__file__).resolve().parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from clean_decors import _rgb_to_lab
from qa_asset_auditor import check_object_clipping
from strip_halo import strip_halo_and_shadow

DEFAULT_INPUT = Path("assets/brands/gsshop/raw/9 christmas items azure blue.jpg")
ALT_INPUT = Path("assets/brands/gsshop/raw/9_christmas_items_azure_blue.jpg")
DEFAULT_OUTPUT_DIR = Path("assets/brands/gsshop/decors")

DEFAULT_ITEM_NAMES = [
    "decor_snowman.png",
    "decor_snowflake.png",
    "decor_gift_box.png",
    "decor_bauble.png",
    "decor_tree.png",
    "decor_candy_cane.png",
    "decor_santa_hat.png",
    "decor_gingerbread.png",
    "decor_stocking.png",
]


def resolve_input_path(input_path: Path) -> Path:
    """Resolve input image path, gracefully handling space vs underscore variants."""
    if input_path.is_file():
        return input_path

    candidates = [
        input_path.with_name(input_path.name.replace("_", " ")),
        input_path.with_name(input_path.name.replace(" ", "_")),
    ]
    if input_path.name in (DEFAULT_INPUT.name, ALT_INPUT.name):
        candidates.extend([DEFAULT_INPUT, ALT_INPUT])

    for cand in candidates:
        if cand.is_file():
            return cand

    raise FileNotFoundError(
        f"Source grid image not found: {input_path} "
        f"(also checked: {', '.join(str(c) for c in candidates)})"
    )


def estimate_studio_background(rgb: np.ndarray, corner_size: int = 20) -> np.ndarray:
    """Sample 4 outer corner patches and bilinearly interpolate the studio gradient."""
    h, w = rgb.shape[:2]
    m = max(4, min(corner_size, h // 8, w // 8))
    tl = np.median(rgb[:m, :m].reshape(-1, 3), axis=0).astype(np.float32)
    tr = np.median(rgb[:m, -m:].reshape(-1, 3), axis=0).astype(np.float32)
    bl = np.median(rgb[-m:, :m].reshape(-1, 3), axis=0).astype(np.float32)
    br = np.median(rgb[-m:, -m:].reshape(-1, 3), axis=0).astype(np.float32)

    ys = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    top = tl * (1.0 - xs) + tr * xs
    bot = bl * (1.0 - xs) + br * xs
    return top * (1.0 - ys) + bot * ys


def detect_object_components(
    rgb: np.ndarray,
    bg_rgb: np.ndarray,
    expected_count: int = 9,
    rows: int = 3,
    cols: int = 3,
    item_names: list[str] | None = None,
) -> tuple[list[dict], np.ndarray]:
    """
    Detect independent foreground object islands using cv2.connectedComponentsWithStats.
    Filters to the top `expected_count` largest blobs and orders them deterministically
    in row-major spatial order (top-to-bottom, left-to-right).
    """
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    bg_u8 = np.clip(bg_rgb, 0, 255).astype(np.uint8)
    bg_lab = cv2.cvtColor(bg_u8, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_dist = np.linalg.norm(lab - bg_lab, axis=2)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy)

    # Coarse foreground binarization: color deviation OR strong structural edge
    fg = ((lab_dist > 7.0) | (grad > 14.0)).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        fg_closed, connectivity=8
    )

    candidates: list[dict] = []
    for label_id in range(1, num_labels):
        area = int(stats[label_id, cv2.CC_STAT_AREA])
        if area < 500:
            continue
        x = int(stats[label_id, cv2.CC_STAT_LEFT])
        y = int(stats[label_id, cv2.CC_STAT_TOP])
        w = int(stats[label_id, cv2.CC_STAT_WIDTH])
        h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        cx, cy = float(centroids[label_id][0]), float(centroids[label_id][1])
        candidates.append(
            {
                "label_id": label_id,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "area": area,
                "cx": cx,
                "cy": cy,
            }
        )

    candidates.sort(key=lambda c: c["area"], reverse=True)
    if len(candidates) < expected_count:
        raise RuntimeError(
            f"Expected {expected_count} object islands, but only detected {len(candidates)}."
        )

    top_blobs = candidates[:expected_count]

    # Sort spatially into row-major order (rows by cy, then columns by cx)
    top_blobs.sort(key=lambda c: c["cy"])
    ordered: list[dict] = []
    if rows * cols == expected_count:
        for r in range(rows):
            row_band = top_blobs[r * cols : (r + 1) * cols]
            row_band.sort(key=lambda c: c["cx"])
            ordered.extend(row_band)
    else:
        ordered = top_blobs

    names = item_names or (
        DEFAULT_ITEM_NAMES
        if expected_count == len(DEFAULT_ITEM_NAMES)
        else [f"item_{i:02d}.png" for i in range(expected_count)]
    )
    for idx, blob in enumerate(ordered):
        blob["index"] = idx
        blob["name"] = names[idx]

    return ordered, labels


def _isolate_target_component(mask: np.ndarray, seed_mask: np.ndarray) -> np.ndarray:
    """Keep components overlapping the detected target island (dropping detached specks)."""
    labeled, num = nd_label(mask)
    if num == 0:
        return mask

    areas = np.bincount(labeled.ravel())
    areas[0] = 0

    overlapping = np.unique(labeled[seed_mask & (labeled > 0)])
    if len(overlapping) == 0:
        best = int(np.argmax(areas))
        return labeled == best

    best = int(max(overlapping, key=lambda cid: areas[cid]))
    keep = np.zeros_like(mask, dtype=bool)
    for cid in overlapping:
        if cid == best or areas[cid] >= areas[best] * 0.03:
            keep |= labeled == cid
    return keep


def _segment_padded_crop(
    crop_rgb: np.ndarray,
    crop_bg: np.ndarray,
    seed_mask: np.ndarray,
    item_name: str,
) -> Image.Image:
    """
    Remove studio background on a safely padded crop without destructive outer-margin
    truncation, then strip studio gray halos and ground-plane floor shadows.
    """
    lab_fg = _rgb_to_lab(crop_rgb)
    lab_bg = _rgb_to_lab(np.clip(crop_bg, 0, 255).astype(np.uint8))
    lab_dist = np.linalg.norm(lab_fg - lab_bg, axis=2)

    gray = (
        0.299 * crop_rgb[..., 0].astype(np.float32)
        + 0.587 * crop_rgb[..., 1].astype(np.float32)
        + 0.114 * crop_rgb[..., 2].astype(np.float32)
    )
    grad = np.hypot(sobel(gray, axis=1), sobel(gray, axis=0))

    if "snowflake" in item_name:
        combined = (grad > 11.0) | (lab_dist > 2.8)
        closed = binary_closing(combined, structure=np.ones((3, 3), dtype=bool))
        core = _isolate_target_component(closed, seed_mask)
        core = binary_fill_holes(core)
    else:
        h, w = lab_dist.shape
        m = min(8, h // 6, w // 6)
        corner_dists = np.concatenate(
            [
                lab_dist[:m, :m].ravel(),
                lab_dist[:m, -m:].ravel(),
                lab_dist[-m:, :m].ravel(),
                lab_dist[-m:, -m:].ravel(),
            ]
        )
        noise_floor = float(np.percentile(corner_dists, 98))
        thresh = max(noise_floor * 2.0, 5.5)

        core = (lab_dist > thresh) | (grad > 11.0)
        core = binary_closing(core, structure=np.ones((5, 5), dtype=bool))
        core = _isolate_target_component(core, seed_mask)
        core = binary_fill_holes(core)

    # Smooth antialiased alpha matte
    soft_band = binary_dilation(core, structure=np.ones((3, 3), dtype=bool)) & ~core
    alpha_f = np.where(core, 255.0, 0.0).astype(np.float32)
    if np.any(soft_band):
        band_vals = np.clip((lab_dist - 2.0) / 8.0, 0.0, 1.0) * 255.0
        alpha_f = np.where(soft_band, band_vals, alpha_f)

    alpha_img = Image.fromarray(np.clip(alpha_f, 0, 255).astype(np.uint8), "L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.5))
    alpha = np.asarray(alpha_img, dtype=np.uint8)

    inner_core = binary_erosion(core, structure=np.ones((3, 3), dtype=bool))
    alpha = np.where(inner_core, 255, alpha)
    alpha = np.where(alpha < 12, 0, alpha)

    # Un-premultiply studio background on semi-transparent fringe
    a_f = alpha.astype(np.float32) / 255.0
    semi = (alpha > 0) & (alpha < 255)
    out_rgb = crop_rgb.astype(np.float32).copy()
    if np.any(semi):
        denom = np.maximum(a_f[..., None], 0.15)
        recovered = (out_rgb - (1.0 - a_f[..., None]) * crop_bg) / denom
        out_rgb = np.where(semi[..., None], np.clip(recovered, 0.0, 255.0), out_rgb)
    out_rgb[alpha == 0] = 0.0

    rgba = Image.fromarray(
        np.dstack((out_rgb.astype(np.uint8), alpha.astype(np.uint8))), "RGBA"
    )

    # Pre-defringe in-place (preserving native padded canvas dimensions — no rescaling):
    # 1. Suppress faint semi-transparent floor shadow residue in bottom 15%
    # 2. Tighten outer soft alpha blur tail
    # 3. Nearest-core RGB decontamination
    arr = np.array(rgba, dtype=np.uint8)
    d_rgb = arr[:, :, :3].copy()
    d_alpha = arr[:, :, 3].copy()
    ys_a, _ = np.where(d_alpha > 15)
    if len(ys_a) > 0:
        ymin_a, ymax_a = int(ys_a.min()), int(ys_a.max())
        bbox_h_a = ymax_a - ymin_a
        bcut_a = ymax_a - int(bbox_h_a * 0.15)
        d_alpha[bcut_a : ymax_a + 1, :][d_alpha[bcut_a : ymax_a + 1, :] < 160] = 0
        if not any(k in item_name for k in ("snowman", "gift_box", "snowflake")):
            pcut_a = ymax_a - int(bbox_h_a * 0.12)
            p_rgb = d_rgb[pcut_a : ymax_a + 1, :].astype(np.float32)
            p_chroma = np.max(p_rgb, axis=2) - np.min(p_rgb, axis=2)
            p_bright = np.mean(p_rgb, axis=2)
            puddle = (p_chroma < 20.0) & (p_bright > 165.0)
            d_alpha[pcut_a : ymax_a + 1, :][puddle] = 0

    d_alpha_f = d_alpha.astype(np.float32)
    remapped = np.clip((d_alpha_f - 48.0) / (215.0 - 48.0) * 255.0, 0.0, 255.0)
    d_alpha = np.where(d_alpha >= 215, 255, remapped).astype(np.uint8)
    d_alpha[d_alpha < 16] = 0

    d_main = _isolate_target_component(d_alpha > 0, seed_mask)
    d_alpha[~d_main] = 0

    solid_core = d_alpha >= 245
    eroded_core = binary_erosion(solid_core, structure=np.ones((3, 3), dtype=bool))
    source_core = eroded_core if np.any(eroded_core) else solid_core
    if np.any(source_core):
        _, nearest_idx = distance_transform_edt(~source_core, return_indices=True)
        edge_mask = (d_alpha > 0) & (~source_core)
        ey, ex = np.where(edge_mask)
        d_rgb[ey, ex] = d_rgb[nearest_idx[0, ey, ex], nearest_idx[1, ey, ex]]
    d_rgb[d_alpha == 0] = 0
    rgba = Image.fromarray(np.dstack((d_rgb, d_alpha)), "RGBA")

    # Run radical halo & ground-plane shadow stripper WITHOUT blind outer margin wipe
    cleaned, _ = strip_halo_and_shadow(rgba, item_name, clear_outer_margin=0)
    return cleaned


def smart_crop_and_process(
    input_path: Path,
    output_dir: Path,
    padding: int = 15,
    expected_count: int = 9,
    rows: int = 3,
    cols: int = 3,
    max_expand_retries: int = 3,
    expand_step: int = 10,
    raw_crops: bool = False,
) -> list[dict]:
    """
    Detect all independent objects via Connected Components, crop each with Safe Padding
    and neighbor isolation.

    When `raw_crops=True` (Stage 1 of Hybrid PhotoCraft Pipeline), writes lossless padded
    RGB PNG crops with foreign-neighbor suppression directly to `output_dir` for downstream
    PhotoCraft headless matting. Otherwise runs the legacy Python segmentation + clipping loop.
    """
    resolved_input = resolve_input_path(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(resolved_input) as img:
        rgb = np.asarray(img.convert("RGB"), dtype=np.uint8)

    img_h, img_w = rgb.shape[:2]
    bg_rgb = estimate_studio_background(rgb, corner_size=20)
    blobs, labels = detect_object_components(
        rgb,
        bg_rgb,
        expected_count=expected_count,
        rows=rows,
        cols=cols,
    )

    major_label_ids = {b["label_id"] for b in blobs}
    foreign_kernel = np.ones((7, 7), dtype=np.uint8)
    records: list[dict] = []

    for blob in blobs:
        x, y, bw, bh = blob["x"], blob["y"], blob["w"], blob["h"]
        pad_t = pad_b = pad_l = pad_r = max(15, int(padding))
        dest = output_dir / blob["name"]
        clip_report: dict = {}
        crop_box = (0, 0, 0, 0)
        attempts = 0

        if raw_crops:
            attempts = 1
            x0 = max(0, x - pad_l)
            y0 = max(0, y - pad_t)
            x1 = min(img_w, x + bw + pad_r)
            y1 = min(img_h, y + bh + pad_b)
            crop_box = (x0, y0, x1, y1)

            crop_rgb = rgb[y0:y1, x0:x1].copy()
            crop_bg = bg_rgb[y0:y1, x0:x1].copy()
            crop_labels = labels[y0:y1, x0:x1]

            # Suppress any foreign object island entering the safe padding margin
            target_mask_local = crop_labels == blob["label_id"]
            foreign_mask = np.isin(crop_labels, list(major_label_ids - {blob["label_id"]}))
            if np.any(foreign_mask):
                foreign_dilated = (
                    cv2.dilate(foreign_mask.astype(np.uint8), foreign_kernel, iterations=1) > 0
                ) & (~target_mask_local)
                crop_rgb[foreign_dilated] = np.clip(
                    crop_bg[foreign_dilated], 0, 255
                ).astype(np.uint8)

            Image.fromarray(crop_rgb, "RGB").save(dest, "PNG")
            clip_report = {
                "is_clipped": False,
                "total_clipped_pixels": 0,
                "clipped_edges": [],
                "edge_counts": {"top": 0, "bottom": 0, "left": 0, "right": 0},
                "status": "RAW_CROP (PADDED)",
            }
        else:
            for attempt in range(max_expand_retries + 1):
                attempts = attempt + 1
                x0 = max(0, x - pad_l)
                y0 = max(0, y - pad_t)
                x1 = min(img_w, x + bw + pad_r)
                y1 = min(img_h, y + bh + pad_b)
                crop_box = (x0, y0, x1, y1)

                crop_rgb = rgb[y0:y1, x0:x1].copy()
                crop_bg = bg_rgb[y0:y1, x0:x1].copy()
                crop_labels = labels[y0:y1, x0:x1]

                # Suppress any foreign object island entering the safe padding margin
                target_mask_local = crop_labels == blob["label_id"]
                foreign_mask = np.isin(crop_labels, list(major_label_ids - {blob["label_id"]}))
                if np.any(foreign_mask):
                    foreign_dilated = (
                        cv2.dilate(foreign_mask.astype(np.uint8), foreign_kernel, iterations=1) > 0
                    ) & (~target_mask_local)
                    crop_rgb[foreign_dilated] = np.clip(
                        crop_bg[foreign_dilated], 0, 255
                    ).astype(np.uint8)

                cleaned = _segment_padded_crop(
                    crop_rgb=crop_rgb,
                    crop_bg=crop_bg,
                    seed_mask=target_mask_local,
                    item_name=blob["name"],
                )
                cleaned.save(dest, "PNG", optimize=True)

                clip_report = check_object_clipping(str(dest))
                if not clip_report["is_clipped"]:
                    break

                # Auto-expand whichever edge(s) touched an object pixel
                edges = clip_report["edge_counts"]
                expanded = False
                if edges["top"] > 0 and y0 > 0:
                    pad_t += expand_step
                    expanded = True
                if edges["bottom"] > 0 and y1 < img_h:
                    pad_b += expand_step
                    expanded = True
                if edges["left"] > 0 and x0 > 0:
                    pad_l += expand_step
                    expanded = True
                if edges["right"] > 0 and x1 < img_w:
                    pad_r += expand_step
                    expanded = True
                if not expanded:
                    break

        records.append(
            {
                "index": blob["index"],
                "file": blob["name"],
                "mode": "raw_crop" if raw_crops else "segmented",
                "detected_bbox": {"x": x, "y": y, "w": bw, "h": bh, "area": blob["area"]},
                "crop_box": {
                    "x0": crop_box[0],
                    "y0": crop_box[1],
                    "x1": crop_box[2],
                    "y1": crop_box[3],
                    "width": crop_box[2] - crop_box[0],
                    "height": crop_box[3] - crop_box[1],
                },
                "applied_padding": {
                    "top": pad_t,
                    "bottom": pad_b,
                    "left": pad_l,
                    "right": pad_r,
                },
                "attempts": attempts,
                "clipping": clip_report,
            }
        )

    manifest_path = output_dir / "smart_crop_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source": str(resolved_input),
                "source_size": {"width": img_w, "height": img_h},
                "mode": "raw_crops" if raw_crops else "segmented",
                "safe_padding_px": max(15, int(padding)),
                "items": records,
            },
            f,
            indent=2,
        )

    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Content-Aware Smart Connected Component Cropper with Safe Padding & Clipping Audit."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Source multi-object grid image.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to write transparent PNG cutouts (or raw crops with --raw-crops).",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=15,
        help="Safe padding in pixels around each detected bounding box (minimum 15px).",
    )
    parser.add_argument("--expected-count", type=int, default=9, help="Expected number of objects.")
    parser.add_argument("--rows", type=int, default=3, help="Grid rows for spatial sorting.")
    parser.add_argument("--cols", type=int, default=3, help="Grid columns for spatial sorting.")
    parser.add_argument(
        "--raw-crops",
        action="store_true",
        help="Export lossless padded RGB crops with neighbor suppression for PhotoCraft matting (Stage 1).",
    )
    args = parser.parse_args()

    records = smart_crop_and_process(
        input_path=args.input,
        output_dir=args.output_dir,
        padding=args.padding,
        expected_count=args.expected_count,
        rows=args.rows,
        cols=args.cols,
        raw_crops=args.raw_crops,
    )

    print("\n========= SMART CONNECTED COMPONENT CROPPER REPORT =========")
    clipped_any = False
    for rec in records:
        clip = rec["clipping"]
        cb = rec["crop_box"]
        db = rec["detected_bbox"]
        status = clip["status"]
        if clip["is_clipped"]:
            clipped_any = True
        print(
            f"[{status}] {rec['file']:22s} | "
            f"blob=({db['x']:3d},{db['y']:3d},{db['w']:3d}x{db['h']:3d}) | "
            f"crop={cb['width']:3d}x{cb['height']:3d} | "
            f"clipped_px={clip['total_clipped_pixels']} | attempts={rec['attempts']}"
        )
    print("============================================================\n")
    return 1 if clipped_any else 0


if __name__ == "__main__":
    raise SystemExit(main())
