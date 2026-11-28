#!/usr/bin/env python3
"""
DIR-AN-SUB-A-RECALIBRATION-094 — Recalibrated Isolated Sub-Assembly A Stage Compositor
Composites all 13 canonical layers (Cụm 2 Gloss-Laminated Bag Frame + Cụm 3 6-Item
V-Burst Hero Cluster + Cụm 4 5 Depth & Interactive Textures) + Non-Destructive
Optical FX Layer (2 auto-snapped 4-point sparkle glints in Screen blend mode on
the Holiday Kit lid corners) onto a 1200x1200 32-bit RGBA transparent canvas.

Exports:
  1. `output/TASK_COSRX/sub_stage_burst_bag.png`       (1200x1200 RGBA transparent)
  2. `output/TASK_COSRX/preview_stage_burst_audit.png` (2-panel QA card: Clean Studio + 100px Coordinate Grid Audit)
  3. `output/TASK_COSRX/sub_stage_burst_bag.json`      (13-layer + FX manifest with measured bboxes, angles, QA checks)
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
LAYERS_DIR = REPO_ROOT / "assets" / "brands" / "COSRX" / "layers"
OUT_DIR = REPO_ROOT / "output" / "TASK_COSRX"

OUT_STAGE_PNG = OUT_DIR / "sub_stage_burst_bag.png"
OUT_STAGE_JSON = OUT_DIR / "sub_stage_burst_bag.json"
OUT_AUDIT_PNG = OUT_DIR / "preview_stage_burst_audit.png"

INTER_FONT_PATH = "/Users/macbookpro/Library/Fonts/InterVariable.ttf"

# Master-aligned 1200x1200 RGBA transparent canvas
CANVAS_W = 1200
CANVAS_H = 1200

# Seam-locked 1024x768 bag anchor inside 1200x1200 Master space:
# - Bag horizontal center: 512 + 88 = 600px
# - Bag base (Y_bag=705): 705 + 355 = 1060px (flush with wooden shelf contact Y=1060)
# - Bag front rim (Y_bag=330): 330 + 355 = 685px
# - Bag rear rim (Y_bag=240): 240 + 355 = 595px
BAG_OFFSET_X = 88
BAG_OFFSET_Y = 355
BAG_FRONT_RIM_Y = 685
BAG_REAR_RIM_Y = 595
BAG_BASE_Y = 1060
INTERIOR_FLOOR_CLIP_Y = 1020
STAGE_CEILING_Y = 430

REQUIRED_13_LAYERS = [
    # Cụm 2: Khung túi giấy 3D (2)
    "03_decor_bag_back.png",
    "09_decor_bag_front.png",
    # Cụm 3: Sản phẩm cắm túi (6)
    "04_product_holiday_kit.png",
    "05_product_snail_essence.png",
    "06_product_peptide_serum.png",
    "07_product_snail_cream.png",
    "08_product_pdrn_pack.png",
    "08b_accessory_brush_applicator.png",
    # Cụm 4: Texture & phụ kiện hiệu ứng (5)
    "01_swatch_snail_cream.png",
    "02_droplets_aqueous_serum.png",
    "07b_swatch_pdrn_serum.png",
    "00c_molecular_crystals_back.png",
    "00c_molecular_crystals_front.png",
]


def assert_required_layers() -> None:
    missing = [f for f in REQUIRED_13_LAYERS if not os.path.exists(LAYERS_DIR / f)]
    assert not missing, f"Missing required Sub-Assembly A layers in {LAYERS_DIR}: {missing}"


def measure_principal_axis_cw(img: Image.Image) -> float:
    """Measure visual principal-axis tilt in degrees (0=vertical, +CW right, -CCW left)."""
    thumb = img.copy()
    thumb.thumbnail((420, 420))
    arr = np.array(thumb.convert("RGBA"))
    ys, xs = np.where(arr[..., 3] > 128)
    if len(xs) < 10:
        return 0.0
    x = xs - xs.mean()
    y = -(ys - ys.mean())
    cov = np.cov(np.vstack([x, y]))
    _, eigvecs = np.linalg.eigh(cov)
    principal = eigvecs[:, -1]
    if principal[1] < 0:
        principal = -principal
    return float(math.degrees(math.atan2(principal[0], principal[1])))


def rotate_premul_cw(img: Image.Image, deg_cw: float) -> Image.Image:
    """Rotate RGBA clockwise by deg_cw using premultiplied alpha to avoid edge halos."""
    if abs(deg_cw) < 0.05:
        return img
    arr = np.array(img.convert("RGBA"), dtype=np.float32) / 255.0
    a = arr[..., 3:4]
    premul = np.concatenate([arr[..., :3] * a, a], axis=-1)
    pm_u8 = np.clip(np.round(premul * 255.0), 0, 255).astype(np.uint8)
    pm_img = Image.fromarray(pm_u8, mode="RGBA")
    rot_pm = pm_img.rotate(-deg_cw, resample=Image.Resampling.BICUBIC, expand=True)
    r_arr = np.array(rot_pm, dtype=np.float32) / 255.0
    ra = r_arr[..., 3:4]
    rgb = np.where(ra > 1e-4, r_arr[..., :3] / np.maximum(ra, 1e-4), 0.0)
    out = np.zeros_like(r_arr)
    out[..., :3] = np.clip(rgb, 0.0, 1.0)
    out[..., 3] = np.clip(r_arr[..., 3], 0.0, 1.0)
    out_u8 = np.round(out * 255.0).astype(np.uint8)
    out_u8[out_u8[..., 3] == 0] = 0
    return Image.fromarray(out_u8, mode="RGBA")


def crop_tight(img: Image.Image, alpha_thresh: int = 4) -> Image.Image:
    arr = np.array(img.convert("RGBA"))
    ys, xs = np.where(arr[..., 3] > alpha_thresh)
    if len(xs) == 0:
        return img
    return img.crop((int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)))


def prepare_product(
    path: Path,
    target_h: int,
    target_visual_deg_cw: float,
    crop_bottom_frac: float = 1.0,
) -> Tuple[Image.Image, dict[str, Any]]:
    """Tight-crop, optionally trim bottom reflection, scale, and rotate to exact visual CW tilt."""
    im = Image.open(path).convert("RGBA")
    im = crop_tight(im)
    if crop_bottom_frac < 0.999:
        w0, h0 = im.size
        im = im.crop((0, 0, w0, int(round(h0 * crop_bottom_frac))))
        im = crop_tight(im)

    native_cw = measure_principal_axis_cw(im)
    delta_cw = target_visual_deg_cw - native_cw

    w, h = im.size
    scale = target_h / float(h)
    im_scaled = im.resize(
        (max(1, int(round(w * scale))), target_h), Image.Resampling.LANCZOS
    )
    im_rot = rotate_premul_cw(im_scaled, delta_cw)
    im_rot = crop_tight(im_rot)

    measured_cw = measure_principal_axis_cw(im_rot)
    return im_rot, {
        "native_cw_deg": round(native_cw, 2),
        "applied_delta_cw_deg": round(delta_cw, 2),
        "target_visual_cw_deg": round(target_visual_deg_cw, 2),
        "measured_visual_cw_deg": round(measured_cw, 2),
    }


def apply_cavity_shadow(prod: Image.Image, paste_y: int, rim_y: int = BAG_FRONT_RIM_Y) -> Image.Image:
    """Apply subtle warm ambient occlusion darkening on lower product stems inside the bag cavity."""
    arr = np.array(prod.convert("RGBA"), dtype=np.float32)
    h, _, _ = arr.shape
    ys = np.arange(h, dtype=np.float32) + paste_y
    t = np.clip((ys - (rim_y - 12.0)) / 130.0, 0.0, 1.0)[:, None, None]
    shade = 1.0 - 0.24 * (t * t * (3.0 - 2.0 * t))
    arr[..., :3] = np.clip(arr[..., :3] * shade, 0.0, 255.0)
    return Image.fromarray(np.round(arr).astype(np.uint8), mode="RGBA")


def measure_placed_bbox(img: Image.Image, px: int, py: int) -> dict[str, int]:
    tmp = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    tmp.alpha_composite(img, (px, py))
    arr = np.array(tmp)
    ys, xs = np.where(arr[..., 3] > 10)
    if len(xs) == 0:
        return {"x_min": px, "y_min": py, "x_max": px, "y_max": py, "width": 0, "height": 0}
    return {
        "x_min": int(xs.min()),
        "y_min": int(ys.min()),
        "x_max": int(xs.max() + 1),
        "y_max": int(ys.max() + 1),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
    }


def measure_box_lid_corners(img: Image.Image, px: int, py: int) -> dict[str, Tuple[int, int]]:
    """Measure exact 3D lid corners of 04_product_holiday_kit on the 1200x1200 canvas."""
    arr = np.array(img.convert("RGBA"))
    a = arr[..., 3]
    col_valid = np.where(a.max(axis=0) > 128)[0]
    lx = int(col_valid[0])
    rx = int(col_valid[-1])

    left_y = int(np.where(a[:, lx : min(lx + 12, arr.shape[1]),].max(axis=1) > 128)[0][0])
    right_back_y = int(np.where(a[:, max(0, rx - 12) : rx + 1].max(axis=1) > 128)[0][0])

    # Top-most front-right apex corner of the 3D box lid
    apex_y = int(np.where(a.max(axis=1) > 128)[0][0])
    apex_xs = np.where(a[apex_y : min(apex_y + 4, arr.shape[0]), :].max(axis=0) > 128)[0]
    apex_x = int(round(float(apex_xs.mean())))

    return {
        "top_left": (px + lx + 3, py + left_y + 2),
        "top_right_apex": (px + apex_x, py + apex_y + 2),
        "top_right_back": (px + rx - 2, py + right_back_y + 2),
    }


def paste_product_in_pocket(
    canvas: Image.Image,
    prod: Image.Image,
    center_x: int,
    top_y: int,
    floor_clip_y: int = INTERIOR_FLOOR_CLIP_Y,
    cast_shadow: bool = True,
) -> Tuple[dict[str, int], int, int]:
    """Composite a product centered at center_x with apex at top_y, clipped cleanly inside the bag."""
    px = int(round(center_x - prod.width / 2.0))
    py = int(round(top_y))
    p = prod.copy()

    # Clip strictly above interior floor so nothing leaks past Y=1060 bag base
    if py + p.height > floor_clip_y:
        crop_h = max(1, floor_clip_y - py)
        p = p.crop((0, 0, p.width, crop_h))

    p = apply_cavity_shadow(p, py, rim_y=BAG_FRONT_RIM_Y)

    if cast_shadow:
        sh_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        sh_alpha = p.split()[3].point(lambda v: int(v * 0.22))
        sh_solid = Image.new("RGBA", p.size, (34, 16, 6, 255))
        sh_solid.putalpha(sh_alpha)
        sh_layer.alpha_composite(sh_solid, (px + 8, py + 7))
        sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=9))
        bg_a = np.array(canvas.split()[3], dtype=np.float32) / 255.0
        sh_arr = np.array(sh_layer, dtype=np.float32)
        sh_arr[..., 3] *= bg_a
        canvas.alpha_composite(Image.fromarray(np.round(sh_arr).astype(np.uint8), mode="RGBA"))

    canvas.alpha_composite(p, (px, py))
    return measure_placed_bbox(p, px, py), px, py


def paste_rim_swatch(
    canvas: Image.Image,
    bag_front_full: Image.Image,
    swatch: Image.Image,
    center_x: int,
    center_y: int,
    shadow_offset: Tuple[int, int] = (3, 6),
    shadow_alpha_scale: float = 0.28,
) -> dict[str, int]:
    """Drape a cosmetic swatch across the bag lip with a warm contact shadow masked onto bag_front."""
    px = int(round(center_x - swatch.width / 2.0))
    py = int(round(center_y - swatch.height / 2.0))

    sh_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    sw_a = swatch.split()[3].point(lambda v: int(v * shadow_alpha_scale))
    sh_solid = Image.new("RGBA", swatch.size, (76, 28, 6, 255))
    sh_solid.putalpha(sw_a)
    sh_layer.alpha_composite(sh_solid, (px + shadow_offset[0], py + shadow_offset[1]))
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(radius=7))

    # Mask shadow onto bag front kraft surface
    bf_a = np.array(bag_front_full.split()[3], dtype=np.float32) / 255.0
    sh_arr = np.array(sh_layer, dtype=np.float32)
    sh_arr[..., 3] *= bf_a
    canvas.alpha_composite(Image.fromarray(np.round(sh_arr).astype(np.uint8), mode="RGBA"))

    canvas.alpha_composite(swatch, (px, py))
    return measure_placed_bbox(swatch, px, py)


def match_studio_whitepoint(img: Image.Image, target_p95: float = 232.0) -> Image.Image:
    """Normalize underexposed studio cutout whitepoint while keeping crisp dark blacks."""
    arr = np.array(img.convert("RGBA"), dtype=np.float32)
    mask = arr[..., 3] > 200
    if not np.any(mask):
        return img
    fg_lum = (
        0.299 * arr[..., 0][mask]
        + 0.587 * arr[..., 1][mask]
        + 0.114 * arr[..., 2][mask]
    )
    p95 = float(np.percentile(fg_lum, 95))
    if p95 >= target_p95 - 5.0 or p95 < 40.0:
        return img
    p05 = float(np.percentile(fg_lum, 3))
    gain = (target_p95 - p05 * 0.75) / max(1.0, (p95 - p05))
    rgb = (arr[..., :3] - p05) * gain + p05 * 0.75
    arr[..., :3] = np.clip(rgb, 0.0, 255.0)
    return Image.fromarray(np.round(arr).astype(np.uint8), mode="RGBA")


def style_pdrn_floating_biogel(img: Image.Image) -> Image.Image:
    """
    Transform raw PDRN swatch into a luminous translucent pearlescent bio-gel swirl
    (DIR-AN-SUB-A-RECALIBRATION-094 Step 4):
      - Translucent refractive gel body (~78-84% alpha in midtones)
      - Crisp opaque specular white-pearl crests along sunlit ridges
      - Subtle iridescent rose-pearl / glass-serum refraction sheen
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32) / 255.0
    a = arr[..., 3]
    lum = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]

    # Normalize ridge luminance within foreground to isolate shadow troughs vs bright crests
    fg = a > 0.2
    if np.any(fg):
        lo = float(np.percentile(lum[fg], 8))
        hi = float(np.percentile(lum[fg], 96))
        norm_l = np.clip((lum - lo) / max(0.05, hi - lo), 0.0, 1.0)
    else:
        norm_l = lum

    # Specular glossy ridge highlight & subtle pearlescent iridescent sheen (warm pink-pearl to cool crystal)
    spec = np.clip((norm_l - 0.52) / 0.48, 0.0, 1.0) ** 1.5
    h, w = a.shape
    yy, xx = np.indices((h, w), dtype=np.float32)
    irid_t = np.clip((xx / max(1.0, w)) * 0.65 + (yy / max(1.0, h)) * 0.35, 0.0, 1.0)

    # Base pearlescent bio-gel tone: crisp 3D translucent gel with cool-pearl troughs & bright white-rose specular crests
    # Strong tonal separation in gel ridges ensures frozen-motion legibility over BOTH light vanity sky & brush head
    r_col = 0.62 + 0.30 * norm_l + 0.08 * (1.0 - irid_t) + 0.24 * spec
    g_col = 0.58 + 0.30 * norm_l + 0.04 * irid_t + 0.24 * spec
    b_col = 0.68 + 0.26 * norm_l + 0.10 * irid_t + 0.22 * spec

    # Subtle crisp rim highlight along the top-left sunlit gel edges
    a_blur = np.array(
        Image.fromarray(np.round(a * 255.0).astype(np.uint8), mode="L").filter(
            ImageFilter.GaussianBlur(radius=2.0)
        ),
        dtype=np.float32,
    ) / 255.0
    gx = np.zeros_like(a_blur)
    gy = np.zeros_like(a_blur)
    gx[:, 1:-1] = (a_blur[:, 2:] - a_blur[:, :-2]) * 0.5
    gy[1:-1, :] = (a_blur[2:, :] - a_blur[:-2, :]) * 0.5
    rim = np.clip((-gx * -0.75) + (-gy * -0.66), 0.0, 1.0) * 4.2 * a
    rim = np.clip(rim, 0.0, 1.0)

    r_col = np.clip(r_col + rim * 0.26, 0.0, 1.0)
    g_col = np.clip(g_col + rim * 0.26, 0.0, 1.0)
    b_col = np.clip(b_col + rim * 0.28, 0.0, 1.0)

    # Semi-translucent refractive alpha: glossy gel body ~82% translucent, specular crests & rim ~98% crisp
    gel_alpha = a * np.clip(0.80 + 0.18 * spec + 0.18 * rim, 0.0, 0.98)

    out = np.zeros((h, w, 4), dtype=np.uint8)
    out[..., 0] = np.clip(np.round(r_col * 255.0), 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(np.round(g_col * 255.0), 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(np.round(b_col * 255.0), 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(np.round(gel_alpha * 255.0), 0, 255).astype(np.uint8)
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, mode="RGBA")


def render_sparkle_4pt(diameter_px: int, opacity: float = 1.0) -> Tuple[Image.Image, Image.Image]:
    """
    Generate a dual-pass procedural 4-point optical sparkle glint designed to pop clearly on
    BOTH holographic boxes AND light/white vanity backgrounds (L* > 92):
      1. `halo_img`: subtle warm champagne-pearl diffraction contrast bloom (normal alpha composite)
      2. `star_img`: blazing #FFFFFF pinpoint core & razor-sharp 4-point diamond needles (Screen blend)
    """
    size = max(48, int(round(diameter_px * 2.8)))
    if size % 2 == 0:
        size += 1
    c = size // 2
    yy, xx = np.indices((size, size), dtype=np.float32)
    dx = xx - c
    dy = yy - c
    r = np.sqrt(dx * dx + dy * dy)
    rad = max(6.0, diameter_px * 0.56)

    # 1. Blazing #FFFFFF pinpoint core & razor-sharp 4-point star spikes
    core = np.exp(-((r / (rad * 0.20)) ** 2))
    h_ray = np.exp(-np.abs(dx) / (rad * 0.72)) * np.exp(-((dy / max(1.0, rad * 0.085)) ** 2))
    v_ray = np.exp(-np.abs(dy) / (rad * 0.72)) * np.exp(-((dx / max(1.0, rad * 0.085)) ** 2))
    u45 = (dx + dy) * 0.70710678
    v45 = (dx - dy) * 0.70710678
    d1_ray = np.exp(-np.abs(u45) / (rad * 0.30)) * np.exp(-((v45 / max(0.85, rad * 0.075)) ** 2)) * 0.42
    d2_ray = np.exp(-np.abs(v45) / (rad * 0.30)) * np.exp(-((u45 / max(0.85, rad * 0.075)) ** 2)) * 0.42

    star_intensity = np.clip(core * 1.25 + np.maximum(h_ray, v_ray) * 1.0 + np.maximum(d1_ray, d2_ray), 0.0, 1.0)
    edge_fade = np.clip(1.0 - (r / (c - 1.0)) ** 3, 0.0, 1.0)
    star_alpha = np.clip(star_intensity * edge_fade * opacity, 0.0, 1.0)

    star_out = np.zeros((size, size, 4), dtype=np.uint8)
    star_out[..., 0] = 255
    star_out[..., 1] = 255
    star_out[..., 2] = 255
    star_out[..., 3] = np.round(star_alpha * 255.0).astype(np.uint8)
    star_out[star_out[..., 3] == 0] = 0

    # 2. Warm champagne-gold / holographic pearl diffraction halo so white needles pop on bright white backgrounds!
    h_halo = np.exp(-np.abs(dx) / (rad * 0.85)) * np.exp(-((dy / max(2.2, rad * 0.22)) ** 2))
    v_halo = np.exp(-np.abs(dy) / (rad * 0.85)) * np.exp(-((dx / max(2.2, rad * 0.22)) ** 2))
    ring_halo = np.exp(-((r / (rad * 0.54)) ** 2)) * 0.65
    halo_alpha = np.clip((np.maximum(h_halo, v_halo) * 0.62 + ring_halo) * edge_fade * opacity * 0.72, 0.0, 1.0)

    # Rich sunlit champagne-gold (#D8A054) outer diffraction glow transitioning into luminous pearl
    halo_out = np.zeros((size, size, 4), dtype=np.uint8)
    halo_out[..., 0] = 218
    halo_out[..., 1] = 162
    halo_out[..., 2] = 96
    halo_out[..., 3] = np.round(halo_alpha * 255.0).astype(np.uint8)
    halo_out[halo_out[..., 3] == 0] = 0

    return Image.fromarray(halo_out, mode="RGBA"), Image.fromarray(star_out, mode="RGBA")


def screen_composite_centered(
    canvas: Image.Image, fx_img: Image.Image, center_xy: Tuple[int, int]
) -> dict[str, int]:
    """Non-destructive optical Screen blend composite centered at (cx, cy) onto RGBA canvas."""
    cx, cy = center_xy
    px = int(round(cx - fx_img.width / 2.0))
    py = int(round(cy - fx_img.height / 2.0))

    # Clip region safely to canvas bounds
    x0 = max(0, px)
    y0 = max(0, py)
    x1 = min(CANVAS_W, px + fx_img.width)
    y1 = min(CANVAS_H, py + fx_img.height)
    if x1 <= x0 or y1 <= y0:
        return {"x_min": cx, "y_min": cy, "x_max": cx, "y_max": cy, "width": 0, "height": 0}

    sx0, sy0 = x0 - px, y0 - py
    sx1, sy1 = sx0 + (x1 - x0), sy0 + (y1 - y0)

    dst = np.array(canvas.crop((x0, y0, x1, y1)), dtype=np.float32) / 255.0
    src = np.array(fx_img.crop((sx0, sy0, sx1, sy1)), dtype=np.float32) / 255.0

    da = dst[..., 3:4]
    sa = src[..., 3:4]
    d_rgb = dst[..., :3]
    s_rgb = src[..., :3]

    # Optical Screen blend on overlapping area + direct white glow over transparent regions
    screen_rgb = 1.0 - (1.0 - d_rgb) * (1.0 - s_rgb * sa)
    out_a = np.clip(sa + da * (1.0 - sa), 0.0, 1.0)
    # Weight RGB properly where destination is transparent (da -> 0 => pure src RGB)
    out_rgb = np.where(
        out_a > 1e-4,
        (screen_rgb * da + s_rgb * sa * (1.0 - da)) / np.maximum(da + sa * (1.0 - da), 1e-4),
        0.0,
    )
    out_arr = np.zeros_like(dst)
    out_arr[..., :3] = np.clip(out_rgb, 0.0, 1.0)
    out_arr[..., 3:4] = out_a
    patch = Image.fromarray(np.round(out_arr * 255.0).astype(np.uint8), mode="RGBA")
    canvas.paste(patch, (x0, y0))
    return measure_placed_bbox(fx_img, px, py)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(INTER_FONT_PATH, size)
    except Exception:
        return ImageFont.load_default()


def build_stage_burst() -> dict[str, Any]:
    assert_required_layers()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    layer_records: list[dict[str, Any]] = []

    # Prepare full-canvas 1200x1200 bag back & upgraded gloss-laminated bag front frames (0.0px seam)
    bag_back_raw = Image.open(LAYERS_DIR / "03_decor_bag_back.png").convert("RGBA")
    bag_front_raw = Image.open(LAYERS_DIR / "09_decor_bag_front.png").convert("RGBA")
    assert bag_back_raw.size == (1024, 768) and bag_front_raw.size == (1024, 768)

    bag_back_full = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    bag_back_full.alpha_composite(bag_back_raw, (BAG_OFFSET_X, BAG_OFFSET_Y))

    bag_front_full = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    bag_front_full.alpha_composite(bag_front_raw, (BAG_OFFSET_X, BAG_OFFSET_Y))

    # =========================================================================
    # Z=1: Back Bag Container (Center X=600, Base Y=1060, Rear Rim Y=595)
    # =========================================================================
    canvas.alpha_composite(bag_back_full, (0, 0))
    layer_records.append({
        "z_index": 1,
        "layer": "03_decor_bag_back.png",
        "cluster": "CUM_2_BAG_3D_FRAME",
        "bbox": measure_placed_bbox(bag_back_raw, BAG_OFFSET_X, BAG_OFFSET_Y),
    })

    # =========================================================================
    # Z=2: Molecular Crystals Back (soft translucent depth behind left shoulder, y_min>=430)
    # =========================================================================
    cryst_b_raw = crop_tight(Image.open(LAYERS_DIR / "00c_molecular_crystals_back.png").convert("RGBA"))
    cb_w = 244
    cb_h = int(round(cryst_b_raw.height * (cb_w / float(cryst_b_raw.width))))
    cryst_b = cryst_b_raw.resize((cb_w, cb_h), Image.Resampling.LANCZOS)
    pad = 14
    cb_padded = Image.new("RGBA", (cb_w + pad * 2, cb_h + pad * 2), (0, 0, 0, 0))
    cb_padded.alpha_composite(cryst_b, (pad, pad))
    cb_padded = cb_padded.filter(ImageFilter.GaussianBlur(radius=1.5))
    cb_arr = np.array(cb_padded, dtype=np.float32)
    cb_arr[..., 3] = np.clip(cb_arr[..., 3] * 0.85, 0, 255)
    cryst_b_final = Image.fromarray(np.round(cb_arr).astype(np.uint8), mode="RGBA")
    cb_px = int(round(186 - cryst_b_final.width / 2.0))
    cb_py = max(STAGE_CEILING_Y, int(round(496 - cryst_b_final.height / 2.0)))
    canvas.alpha_composite(cryst_b_final, (cb_px, cb_py))
    layer_records.append({
        "z_index": 2,
        "layer": "00c_molecular_crystals_back.png",
        "cluster": "CUM_4_TEXTURES_AND_EFFECTS",
        "bbox": measure_placed_bbox(cryst_b_final, cb_px, cb_py),
    })

    # =========================================================================
    # Z=3..Z=8: Recalibrated 6-Item V-Burst Hero Cluster
    # - 04 Holiday Kit: Center X=600, Y=430 (measured lid corners captured for non-destructive Z14 glints!)
    # - 08b Brush: Tucked cleanly INSIDE bag mouth (X=246, -11°, x_min>175) beside PDRN tube (X=318, -7.5°)
    # - 05 Snail Essence (X=414, -5°) & 06 Peptide (X=774, +5°) clear Holiday Kit text completely
    # - 07 Mini Snail (X=895, +12.5°) stepped cleanly on right rim
    # =========================================================================
    hero_specs = [
        # (z_index, filename, center_x, top_y, target_h, target_deg_cw, crop_bottom_frac, cast_shadow, norm_wp)
        (3, "04_product_holiday_kit.png",         602, 430, 392,   0.0, 1.00, False, True),
        (4, "05_product_snail_essence.png",       410, 465, 415,  -5.0, 1.00, True,  False),
        (5, "06_product_peptide_serum.png",       776, 472, 396,  +5.0, 1.00, True,  False),
        (6, "08_product_pdrn_pack.png",           318, 508, 342,  -7.5, 0.72, True,  False),
        (7, "08b_accessory_brush_applicator.png", 246, 532, 286, -11.0, 1.00, True,  False),
        (8, "07_product_snail_cream.png",         898, 524, 236, +12.5, 1.00, True,  False),
    ]

    product_records: dict[str, dict[str, Any]] = {}
    holiday_lid_corners: dict[str, Tuple[int, int]] = {}

    for z_idx, fname, cx, ty, th, deg, cbf, shadow, norm_wp in hero_specs:
        prod_img, meta = prepare_product(
            LAYERS_DIR / fname,
            target_h=th,
            target_visual_deg_cw=deg,
            crop_bottom_frac=cbf,
        )
        if norm_wp:
            prod_img = match_studio_whitepoint(prod_img, target_p95=232.0)
        bbox, px, py = paste_product_in_pocket(
            canvas, prod_img, center_x=cx, top_y=ty, cast_shadow=shadow
        )
        if fname == "04_product_holiday_kit.png":
            holiday_lid_corners = measure_box_lid_corners(prod_img, px, py)

        rec = {
            "z_index": z_idx,
            "layer": fname,
            "cluster": "CUM_3_HERO_PRODUCTS_AND_ACCESSORY",
            "anchor_center_x": cx,
            "anchor_top_y": ty,
            "target_h": th,
            **meta,
            "bbox": bbox,
        }
        layer_records.append(rec)
        product_records[fname] = rec

    # =========================================================================
    # Z=9: Gloss-Laminated Front Bag Container (Y=685..1060, seam-locked with Z=1)
    # =========================================================================
    canvas.alpha_composite(bag_front_full, (0, 0))
    bag_front_bbox = measure_placed_bbox(bag_front_raw, BAG_OFFSET_X, BAG_OFFSET_Y)
    layer_records.append({
        "z_index": 9,
        "layer": "09_decor_bag_front.png",
        "cluster": "CUM_2_BAG_3D_FRAME",
        "bbox": bag_front_bbox,
    })

    # =========================================================================
    # Z=10: Zero-Gravity Floating Pearlescent Bio-Gel PDRN Swirl (Step 4)
    # Detached completely from bag body; floats gracefully beside brush paddle & PDRN tube
    # without covering "PDRN EXOSOME Skinplaning Glaze Mask" label!
    # =========================================================================
    pdrn_sw = crop_tight(Image.open(LAYERS_DIR / "07b_swatch_pdrn_serum.png").convert("RGBA"))
    pdrn_sw = style_pdrn_floating_biogel(pdrn_sw)
    psw_w = 102
    psw_h = int(round(pdrn_sw.height * (psw_w / float(pdrn_sw.width))))
    pdrn_sw = pdrn_sw.resize((psw_w, psw_h), Image.Resampling.LANCZOS)
    pdrn_sw = rotate_premul_cw(pdrn_sw, -24.0)
    pdrn_sw = crop_tight(pdrn_sw)
    # Float in zero-gravity foreground beside silicone brush head (X~244, Y~596 -> completely above bag front Y=685!)
    psw_px = int(round(234 - pdrn_sw.width / 2.0))
    psw_py = int(round(594 - pdrn_sw.height / 2.0))
    # Delicate airy luminous bloom (NOT a kraft contact shadow!) for translucent floating gel depth
    glow_layer = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    glow_a = pdrn_sw.split()[3].point(lambda v: int(v * 0.22))
    glow_solid = Image.new("RGBA", pdrn_sw.size, (255, 248, 252, 255))
    glow_solid.putalpha(glow_a)
    glow_layer.alpha_composite(glow_solid, (psw_px, psw_py))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=6))
    canvas.alpha_composite(glow_layer, (0, 0))
    canvas.alpha_composite(pdrn_sw, (psw_px, psw_py))
    pdrn_sw_bbox = measure_placed_bbox(pdrn_sw, psw_px, psw_py)
    layer_records.append({
        "z_index": 10,
        "layer": "07b_swatch_pdrn_serum.png",
        "cluster": "CUM_4_TEXTURES_AND_EFFECTS",
        "mode": "ZERO_GRAVITY_FLOATING_BIOGEL",
        "bbox": pdrn_sw_bbox,
    })

    # =========================================================================
    # Z=11: Snail Cream Swatch draped across right front bag rim (X~862, Y~756)
    # =========================================================================
    snail_sw = crop_tight(Image.open(LAYERS_DIR / "01_swatch_snail_cream.png").convert("RGBA"))
    ssw_w = 128
    ssw_h = int(round(snail_sw.height * (ssw_w / float(snail_sw.width))))
    snail_sw = snail_sw.resize((ssw_w, ssw_h), Image.Resampling.LANCZOS)
    snail_sw = rotate_premul_cw(snail_sw, 24.0)
    snail_sw = crop_tight(snail_sw)
    snail_sw_bbox = paste_rim_swatch(
        canvas, bag_front_full, snail_sw, center_x=862, center_y=756, shadow_offset=(4, 6)
    )
    layer_records.append({
        "z_index": 11,
        "layer": "01_swatch_snail_cream.png",
        "cluster": "CUM_4_TEXTURES_AND_EFFECTS",
        "bbox": snail_sw_bbox,
    })

    # =========================================================================
    # Z=12: Aqueous Gel Droplets orbiting Snail Essence pump (clear of "THE GLAZED" text)
    # =========================================================================
    drop_raw = crop_tight(Image.open(LAYERS_DIR / "02_droplets_aqueous_serum.png").convert("RGBA"))
    dr_w = 144
    dr_h = int(round(drop_raw.height * (dr_w / float(drop_raw.width))))
    drop_img = drop_raw.resize((dr_w, dr_h), Image.Resampling.LANCZOS)
    dr_arr = np.array(drop_img, dtype=np.float32)
    dr_arr[..., 3] = np.clip(dr_arr[..., 3] * 0.90, 0, 255)
    drop_img = Image.fromarray(np.round(dr_arr).astype(np.uint8), mode="RGBA")
    dr_px = int(round(382 - drop_img.width / 2.0))
    dr_py = max(STAGE_CEILING_Y, int(round(484 - drop_img.height / 2.0)))
    canvas.alpha_composite(drop_img, (dr_px, dr_py))
    layer_records.append({
        "z_index": 12,
        "layer": "02_droplets_aqueous_serum.png",
        "cluster": "CUM_4_TEXTURES_AND_EFFECTS",
        "bbox": measure_placed_bbox(drop_img, dr_px, dr_py),
    })

    # =========================================================================
    # Z=13: Molecular Crystals Front — sharp foreground right rim corner
    # =========================================================================
    cryst_f_raw = crop_tight(Image.open(LAYERS_DIR / "00c_molecular_crystals_front.png").convert("RGBA"))
    cf_w = 132
    cf_h = int(round(cryst_f_raw.height * (cf_w / float(cryst_f_raw.width))))
    cryst_f = cryst_f_raw.resize((cf_w, cf_h), Image.Resampling.LANCZOS)
    cf_px = int(round(1004 - cryst_f.width / 2.0))
    cf_py = int(round(706 - cryst_f.height / 2.0))
    canvas.alpha_composite(cryst_f, (cf_px, cf_py))
    layer_records.append({
        "z_index": 13,
        "layer": "00c_molecular_crystals_front.png",
        "cluster": "CUM_4_TEXTURES_AND_EFFECTS",
        "bbox": measure_placed_bbox(cryst_f, cf_px, cf_py),
    })

    # =========================================================================
    # Z=14 (Procedural Non-Destructive Optical FX): 2 Auto-Snapped 4-Point Sparkle Glints
    # Anchored 0.0px to measured top-left & top-right lid corners of 04_product_holiday_kit
    # Dual-pass (champagne diffraction halo + Screen #FFFFFF needles) so glints pop on light backgrounds!
    # =========================================================================
    left_corner = holiday_lid_corners["top_left"]
    right_apex = holiday_lid_corners["top_right_apex"]

    halo_primary, star_primary = render_sparkle_4pt(diameter_px=36, opacity=1.0)
    halo_secondary, star_secondary = render_sparkle_4pt(diameter_px=22, opacity=0.80)

    canvas.alpha_composite(
        halo_primary,
        (int(round(left_corner[0] - halo_primary.width / 2.0)), int(round(left_corner[1] - halo_primary.height / 2.0))),
    )
    glint_left_bbox = screen_composite_centered(canvas, star_primary, left_corner)

    canvas.alpha_composite(
        halo_secondary,
        (int(round(right_apex[0] - halo_secondary.width / 2.0)), int(round(right_apex[1] - halo_secondary.height / 2.0))),
    )
    glint_right_bbox = screen_composite_centered(canvas, star_secondary, right_apex)

    fx_records = [
        {
            "z_index": 14,
            "fx_id": "fx_sparkle_glint_lid_left",
            "blend_mode": "screen",
            "diameter_px": 36,
            "opacity": 1.0,
            "snapped_corner_xy": list(left_corner),
            "bbox": glint_left_bbox,
        },
        {
            "z_index": 14,
            "fx_id": "fx_sparkle_glint_lid_right",
            "blend_mode": "screen",
            "diameter_px": 22,
            "opacity": 0.80,
            "snapped_corner_xy": list(right_apex),
            "bbox": glint_right_bbox,
        },
    ]

    # Save 1200x1200 RGBA transparent deliverable
    canvas.save(OUT_STAGE_PNG, "PNG")
    print(f"[SUB-A] Saved 1200x1200 RGBA transparent stage: {OUT_STAGE_PNG}")

    # Overall ink measurements & QA
    c_arr = np.array(canvas)
    ys, xs = np.where(c_arr[..., 3] > 10)
    overall_bbox = {
        "x_min": int(xs.min()),
        "y_min": int(ys.min()),
        "x_max": int(xs.max() + 1),
        "y_max": int(ys.max() + 1),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
    }

    prod_top_ys = [r["bbox"]["y_min"] for r in product_records.values()]
    prod_x_min = min(r["bbox"]["x_min"] for r in product_records.values())
    prod_x_max = max(r["bbox"]["x_max"] for r in product_records.values())
    peak_product_y = min(prod_top_ys)
    stagger_range_px = max(prod_top_ys) - min(prod_top_ys)

    brush_bbox = product_records["08b_accessory_brush_applicator.png"]["bbox"]
    brush_inside_bag = (
        brush_bbox["x_min"] >= bag_front_bbox["x_min"]
        and brush_bbox["x_max"] <= bag_front_bbox["x_max"]
    )
    pdrn_detached_above_rim = pdrn_sw_bbox["y_max"] < BAG_FRONT_RIM_Y

    corner_alpha_max = int(
        max(
            c_arr[0, 0, 3],
            c_arr[0, -1, 3],
            c_arr[-1, 0, 3],
            c_arr[-1, -1, 3],
        )
    )

    manifest = {
        "directive_id": "DIR-AN-SUB-A-RECALIBRATION-094",
        "execution_mode": "LINEAR_SEQUENTIAL_REFINEMENT",
        "canvas": {"width": CANVAS_W, "height": CANVAS_H, "mode": "RGBA"},
        "bag_geometry": {
            "offset_x": BAG_OFFSET_X,
            "offset_y": BAG_OFFSET_Y,
            "center_x": 600,
            "rear_rim_y": BAG_REAR_RIM_Y,
            "front_rim_y": BAG_FRONT_RIM_Y,
            "base_y": BAG_BASE_Y,
            "measured_base_y": bag_front_bbox["y_max"],
            "mouth_x_span": [bag_front_bbox["x_min"], bag_front_bbox["x_max"]],
        },
        "total_layers_composited": len(layer_records),
        "procedural_fx_layers": fx_records,
        "overall_ink_bbox": overall_bbox,
        "layers": layer_records,
        "qa_checks": {
            "exact_13_layers_verified": len(layer_records) == 13,
            "procedural_glints_snapped": len(fx_records) == 2,
            "transparent_corners_verified": corner_alpha_max == 0,
            "peak_product_y_px": peak_product_y,
            "peak_ceiling_430_passed": peak_product_y >= STAGE_CEILING_Y,
            "clearance_from_discount_376_px": peak_product_y - 376,
            "bag_base_1060_passed": abs(bag_front_bbox["y_max"] - BAG_BASE_Y) <= 1,
            "zero_leak_below_bag_base": overall_bbox["y_max"] <= BAG_BASE_Y + 1,
            "vertical_stagger_range_px": stagger_range_px,
            "v_burst_stagger_passed": stagger_range_px >= 100,
            "brush_inside_bag_mouth_passed": brush_inside_bag,
            "brush_x_span": [brush_bbox["x_min"], brush_bbox["x_max"]],
            "pdrn_swirl_floating_above_bag_rim": pdrn_detached_above_rim,
            "product_mouth_span_x": [prod_x_min, prod_x_max],
            "product_mouth_coverage_pct": round(
                100.0 * (prod_x_max - prod_x_min) / float(bag_front_bbox["width"]), 1
            ),
        },
    }

    OUT_STAGE_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[SUB-A] Manifest written: {OUT_STAGE_JSON}")
    print(f"[SUB-A] QA Summary: {json.dumps(manifest['qa_checks'])}")

    render_audit_preview(canvas, manifest)
    return manifest


def make_checkerboard(w: int, h: int, cell: int = 24) -> Image.Image:
    ys, xs = np.indices((h, w))
    pat = ((xs // cell) + (ys // cell)) % 2
    bg = np.where(pat[..., None] == 0, 246, 234).astype(np.uint8)
    rgb = np.repeat(bg, 3, axis=2)
    alpha = np.full((h, w, 1), 255, dtype=np.uint8)
    return Image.fromarray(np.concatenate([rgb, alpha], axis=2), mode="RGBA")


def render_audit_preview(stage_rgba: Image.Image, manifest: dict[str, Any]) -> None:
    """Export 2400x1200 2-panel audit image: Left=Clean Studio, Right=100px Coordinate Grid + Z1..Z14 Labels."""
    f_title = load_font(16)
    f_small = load_font(13)
    f_tiny = load_font(11)

    # Left panel: Clean Sub-A over subtle transparency checkerboard
    left = make_checkerboard(CANVAS_W, CANVAS_H, cell=20)
    left.alpha_composite(stage_rgba, (0, 0))
    ld = ImageDraw.Draw(left)
    ld.rounded_rectangle((18, 18, 675, 56), radius=8, fill=(15, 23, 42, 230))
    ld.text(
        (32, 28),
        "SUB-ASSEMBLY A RECALIBRATED-094 (1200x1200 RGBA — 13 LAYERS + 2 FX)",
        fill=(255, 255, 255, 255),
        font=f_title,
    )

    # Right panel: Coordinate Grid Audit (100px major / 50px minor grid)
    right = Image.new("RGBA", (CANVAS_W, CANVAS_H), (252, 251, 248, 255))
    rd = ImageDraw.Draw(right)

    for x in range(0, CANVAS_W, 50):
        col = (226, 232, 240, 255) if x % 100 != 0 else (203, 213, 225, 255)
        rd.line((x, 0, x, CANVAS_H), fill=col, width=1)
    for y in range(0, CANVAS_H, 50):
        col = (226, 232, 240, 255) if y % 100 != 0 else (203, 213, 225, 255)
        rd.line((0, y, CANVAS_W, y), fill=col, width=1)

    right.alpha_composite(stage_rgba, (0, 0))

    hud = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hud)

    for x in range(100, CANVAS_W, 100):
        hd.line((x, 0, x, 14), fill=(51, 65, 85, 220), width=2)
        hd.text((x - 14, 16), f"X={x}", fill=(51, 65, 85, 230), font=f_tiny)
    for y in range(100, CANVAS_H, 100):
        hd.line((0, y, 14, y), fill=(51, 65, 85, 220), width=2)
        hd.text((18, y - 6), f"Y={y}", fill=(51, 65, 85, 230), font=f_tiny)

    def dashed_h(y_val: int, color: Tuple[int, int, int, int], label: str, right_align: bool = False) -> None:
        for x0 in range(0, CANVAS_W, 14):
            hd.line((x0, y_val, min(x0 + 8, CANVAS_W - 1), y_val), fill=color, width=2)
        tw = int(hd.textlength(label, font=f_small))
        bx = (CANVAS_W - tw - 18) if right_align else 64
        by = max(4, y_val - 24)
        hd.rounded_rectangle((bx, by, bx + tw + 12, by + 20), radius=4, fill=(15, 23, 42, 225))
        hd.text((bx + 6, by + 2), label, fill=color[:3] + (255,), font=f_small)

    for y0 in range(0, CANVAS_H, 14):
        hd.line((600, y0, 600, min(y0 + 8, CANVAS_H - 1)), fill=(99, 102, 241, 160), width=2)

    dashed_h(376, (239, 68, 68, 210), "Y=376 Master Discount Bottom (Reference)", right_align=True)
    dashed_h(430, (139, 92, 246, 235), f"Y=430 Stage Ceiling Lock (Peak={manifest['qa_checks']['peak_product_y_px']}px)")
    dashed_h(595, (245, 158, 11, 200), "Y=595 Bag Rear Rim", right_align=True)
    dashed_h(685, (16, 185, 129, 235), "Y=685 Bag Front Rim (Width=888px)")
    dashed_h(1060, (14, 165, 233, 240), f"Y=1060 Bag Base Shelf Contact (Meas={manifest['bag_geometry']['measured_base_y']}px)", right_align=True)

    palette = {
        "CUM_3_HERO_PRODUCTS_AND_ACCESSORY": (37, 99, 235, 200),
        "CUM_4_TEXTURES_AND_EFFECTS": (217, 70, 239, 210),
    }
    for rec in manifest["layers"]:
        cl = rec["cluster"]
        if cl not in palette:
            continue
        col = palette[cl]
        bb = rec["bbox"]
        hd.rectangle((bb["x_min"], bb["y_min"], bb["x_max"], bb["y_max"]), outline=col, width=2)
        tag = f"Z{rec['z_index']}"
        if "measured_visual_cw_deg" in rec:
            tag += f" ({rec['measured_visual_cw_deg']:+.1f}°)"
        tw = int(hd.textlength(tag, font=f_tiny))
        tx = max(4, min(CANVAS_W - tw - 10, bb["x_min"]))
        ty = max(4, bb["y_min"] - 16)
        hd.rounded_rectangle((tx, ty, tx + tw + 8, ty + 15), radius=3, fill=col[:3] + (235,))
        hd.text((tx + 4, ty + 1), tag, fill=(255, 255, 255, 255), font=f_tiny)

    # Mark auto-snapped FX sparkle anchors in bright gold crosshairs
    for fx in manifest["procedural_fx_layers"]:
        gx, gy = fx["snapped_corner_xy"]
        hd.ellipse((gx - 12, gy - 12, gx + 12, gy + 12), outline=(250, 204, 21, 240), width=2)
        label = f"FX ({gx},{gy})"
        tw = int(hd.textlength(label, font=f_tiny))
        hd.rounded_rectangle((gx - tw // 2 - 4, gy - 30, gx + tw // 2 + 4, gy - 15), radius=3, fill=(161, 98, 7, 235))
        hd.text((gx - tw // 2, gy - 29), label, fill=(255, 255, 255, 255), font=f_tiny)

    qa = manifest["qa_checks"]
    summary_lines = [
        "DIR-AN-SUB-A-RECALIBRATION-094 AUDIT",
        f"Layers: {manifest['total_layers_composited']}/13 + 2 Screen FX | RGBA Corners: {'PASS' if qa['transparent_corners_verified'] else 'FAIL'}",
        f"Brush Inside Bag: {'PASS' if qa['brush_inside_bag_mouth_passed'] else 'FAIL'} (X={qa['brush_x_span'][0]}..{qa['brush_x_span'][1]}) | PDRN Floating: {'PASS' if qa['pdrn_swirl_floating_above_bag_rim'] else 'FAIL'}",
        f"Mouth Coverage: {qa['product_mouth_coverage_pct']}% | V-Burst Stagger: {qa['vertical_stagger_range_px']}px | Peak Y={qa['peak_product_y_px']}px",
    ]
    hd.rounded_rectangle((18, 1094, 595, 1184), radius=8, fill=(15, 23, 42, 232))
    for i, line in enumerate(summary_lines):
        hd.text(
            (30, 1102 + i * 19),
            line,
            fill=(167, 243, 208, 255) if i > 0 else (255, 255, 255, 255),
            font=f_small if i == 0 else f_tiny,
        )

    right.alpha_composite(hud)

    combined = Image.new("RGB", (CANVAS_W * 2, CANVAS_H), (255, 255, 255))
    combined.paste(left.convert("RGB"), (0, 0))
    combined.paste(right.convert("RGB"), (CANVAS_W, 0))
    cd = ImageDraw.Draw(combined)
    cd.line((CANVAS_W, 0, CANVAS_W, CANVAS_H), fill=(148, 163, 184), width=3)
    combined.save(OUT_AUDIT_PNG, "PNG")
    print(f"[SUB-A] Saved 2-panel coordinate audit preview: {OUT_AUDIT_PNG} ({combined.size})")


if __name__ == "__main__":
    build_stage_burst()
