#!/usr/bin/env python3
"""
RECOVER_AND_REASSEMBLE_COSRX_PROJECT:
COSRX x ULTA Zero-Gravity Master (1200x1200) & Sub-Assembly B (UI Dock) Reassembler

Generates:
  1. output/TASK_COSRX/sub_ui_typography_dock.png  (1200x1200 RGBA, embeds REV2 3D headline)
  2. output/TASK_COSRX/cosrx_master_1200x1200.png  (1200x1200 RGB master composite)
  3. output/TASK_COSRX/cosrx_master_1200x1200.psd  (Hierarchical editable PSD; Layer 10a independent)
  4. output/TASK_COSRX/cosrx_master_1200x1200.json (Full manifest + SSIM & Alpha Gatekeeper QA)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from psd_tools import PSDImage
from psd_tools.api.layers import Group, PixelLayer
from scipy.ndimage import (
    binary_dilation,
    binary_erosion,
    distance_transform_edt,
    gaussian_filter,
    maximum_filter,
    minimum_filter,
)

ROOT = Path(__file__).resolve().parent.parent
LAYERS_DIR = ROOT / "assets" / "brands" / "COSRX" / "layers"
LOGO_DIR = ROOT / "assets" / "brands" / "COSRX" / "LOGO"
FONT_BOLD = ROOT / "assets" / "fonts" / "Pretendard-ExtraBold.woff2"
OUT_DIR = ROOT / "output" / "TASK_COSRX"

CANVAS_W = 1200
CANVAS_H = 1200

BG_PATH = LAYERS_DIR / "00_bg_vanity_morning_light.png"
PEDESTAL_PATH = LAYERS_DIR / "00b_pedestal_wood_shelf.png"
STAGE_BURST_PATH = OUT_DIR / "sub_stage_burst_bag.png"
HEADLINE_3D_PATH = OUT_DIR / "10a_headline_3d_liquid_metal.png"
RIBBON_PATH = LAYERS_DIR / "02_ribbon_early_access.png"
CTA_PATH = LAYERS_DIR / "11_ui_cta_button.png"
COSRX_LOGO_PATH = LAYERS_DIR / "01a_logo_cosrx.png"
ULTA_LOGO_PATH = LAYERS_DIR / "01b_logo_ulta.png"

OUT_SUB_UI_PNG = OUT_DIR / "sub_ui_typography_dock.png"
OUT_MASTER_PNG = OUT_DIR / "cosrx_master_1200x1200.png"
OUT_MASTER_PSD = OUT_DIR / "cosrx_master_1200x1200.psd"
OUT_MASTER_JSON = OUT_DIR / "cosrx_master_1200x1200.json"


def load_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing required asset: {path}")
    with Image.open(path) as im:
        return im.convert("RGBA").copy()


def trim_rgba(im: Image.Image) -> Image.Image:
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def place_on_canvas(im: Image.Image, left: int, top: int) -> Image.Image:
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    canvas.alpha_composite(im, (left, top))
    return canvas


def defringe_rgba_layer(
    im: Image.Image,
    has_soft_shadows: bool = False,
    clean_white_notch: bool = True,
) -> Image.Image:
    """
    Eliminate zero-alpha RGB leaks, premultiplication dark halos, and studio white
    notches while preserving smooth anti-aliased alpha channels.
    """
    arr = np.array(im.convert("RGBA"), dtype=np.uint8)
    alpha_u8 = arr[:, :, 3]
    rgb_u8 = arr[:, :, :3].copy()

    # 1. Zero out RGB where alpha == 0
    rgb_u8[alpha_u8 == 0] = 0

    # 2. Clean studio white notches FIRST (before dark-halo pass)
    if clean_white_notch:
        solid_mask = alpha_u8 > 20
        eroded_2px = binary_erosion(solid_mask, structure=np.ones((3, 3), dtype=bool), iterations=2)
        outer_rim = solid_mask & (~eroded_2px)
        semi_mask = (alpha_u8 > 10) & (alpha_u8 < 250)
        transition_edge = outer_rim | semi_mask
        deep_core = binary_erosion(solid_mask, structure=np.ones((3, 3), dtype=bool), iterations=5)
        if not np.any(deep_core):
            deep_core = eroded_2px
        if np.any(transition_edge) and np.any(deep_core):
            ty, tx = np.where(transition_edge)
            rgb_i = rgb_u8[ty, tx].astype(np.int16)
            r, g, b = rgb_i[:, 0], rgb_i[:, 1], rgb_i[:, 2]
            sat = np.max(rgb_i, axis=1) - np.min(rgb_i, axis=1)
            bright = (r + g + b) / 3.0
            studio_white = ((r > 210) & (g > 210) & (b > 210) & (sat < 14)) | ((bright > 205.0) & (sat < 12))

            _, (ny, nx) = distance_transform_edt(~deep_core, return_indices=True)
            core_rgb = rgb_u8[ny[ty, tx], nx[ty, tx]].astype(np.int16)
            core_sat = np.max(core_rgb, axis=1) - np.min(core_rgb, axis=1)
            core_bright = np.mean(core_rgb, axis=1)
            adj_colored = (core_bright < 185.0) | (core_sat >= 25)
            bad = studio_white & adj_colored
            if np.any(bad):
                by, bx = ty[bad], tx[bad]
                rgb_u8[by, bx] = rgb_u8[ny[by, bx], nx[by, bx]]

    # 3. Clean premultiplication dark halos SECOND so replaced pixels never create dark halos
    a = alpha_u8.astype(np.float32) / 255.0
    opaque = a >= 0.99
    if np.any(opaque):
        near_op = binary_dilation(opaque, iterations=2)
        a_lo = 0.35 if has_soft_shadows else 0.05
        partial = (a > a_lo) & (a < 0.95) & near_op
        _, (ny, nx) = distance_transform_edt(~opaque, return_indices=True)
        for _ in range(2):
            rgb_f = rgb_u8.astype(np.float32) / 255.0
            luma = 0.2126 * rgb_f[:, :, 0] + 0.7152 * rgb_f[:, :, 1] + 0.0722 * rgb_f[:, :, 2]
            op_luma = np.where(opaque, luma, 1.0)
            nbr_min = minimum_filter(op_luma, size=3, mode="nearest")
            has_op_nbr = maximum_filter(opaque.astype(np.uint8), size=3, mode="nearest") > 0
            dark_halo = partial & has_op_nbr & (nbr_min > 0.15) & (luma < 0.50 * nbr_min)
            if not np.any(dark_halo):
                break
            hy, hx = np.where(dark_halo)
            rgb_u8[hy, hx] = rgb_u8[ny[hy, hx], nx[hy, hx]]

    rgb_u8[alpha_u8 == 0] = 0
    out = np.dstack([rgb_u8, alpha_u8])
    return Image.fromarray(out, mode="RGBA")


def build_dual_logo_layer() -> Tuple[Image.Image, Dict]:
    """Tier 1: COSRX left @ x=60, ULTA right @ x=1140, centered vertically @ y=69 (top >= 42px safe-zone)."""
    canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))

    cosrx = trim_rgba(load_rgba(COSRX_LOGO_PATH))
    cosrx_h = 34
    cosrx_w = int(round(cosrx.width * (cosrx_h / cosrx.height)))
    cosrx_rs = cosrx.resize((cosrx_w, cosrx_h), Image.Resampling.LANCZOS)
    cosrx_y = 69 - cosrx_h // 2
    canvas.alpha_composite(cosrx_rs, (60, cosrx_y))

    ulta = trim_rgba(load_rgba(ULTA_LOGO_PATH))
    ulta_h = 54
    ulta_w = int(round(ulta.width * (ulta_h / ulta.height)))
    ulta_rs = ulta.resize((ulta_w, ulta_h), Image.Resampling.LANCZOS)
    ulta_x = 1140 - ulta_w
    ulta_y = 69 - ulta_h // 2
    canvas.alpha_composite(ulta_rs, (ulta_x, ulta_y))

    return canvas, {
        "cosrx_bbox": [60, cosrx_y, 60 + cosrx_w, cosrx_y + cosrx_h],
        "ulta_bbox": [ulta_x, ulta_y, 1140, ulta_y + ulta_h],
    }


def build_headline_3d_layers() -> Tuple[Image.Image, Image.Image, Dict]:
    """
    Tier 2: Independent REV2 3D Liquid-Chrome 'BLACK FRIDAY' headline + soft contact shadow.
    Placed cleanly in y = 104..206 so it sits above the ribbon with zero collision.
    """
    raw = load_rgba(HEADLINE_3D_PATH)
    trimmed = trim_rgba(raw)
    target_w = 740
    scale = target_w / float(trimmed.width)
    target_h = int(round(trimmed.height * scale))
    headline_rs = trimmed.resize((target_w, target_h), Image.Resampling.LANCZOS)

    left = (CANVAS_W - target_w) // 2
    top = 104

    headline_layer = place_on_canvas(headline_rs, left, top)

    # Soft contact shadow beneath the 3D headline (kept as its own layer so Layer 10a stays pure PBR)
    alpha_np = np.array(headline_layer.getchannel("A"), dtype=np.float32) / 255.0
    shadow_a = np.roll(alpha_np, shift=6, axis=0)
    shadow_a[:6, :] = 0.0
    shadow_blur = gaussian_filter(shadow_a, sigma=7.0) * 0.28
    shadow_rgba = np.zeros((CANVAS_H, CANVAS_W, 4), dtype=np.uint8)
    shadow_rgba[..., 0] = 12
    shadow_rgba[..., 1] = 12
    shadow_rgba[..., 2] = 14
    shadow_rgba[..., 3] = np.round(np.clip(shadow_blur, 0.0, 1.0) * 255.0).astype(np.uint8)
    shadow_layer = Image.fromarray(shadow_rgba, mode="RGBA")

    return headline_layer, shadow_layer, {
        "bbox": [left, top, left + target_w, top + target_h],
        "source": str(HEADLINE_3D_PATH.relative_to(ROOT)),
    }


def build_ribbon_layer() -> Tuple[Image.Image, Dict]:
    """Tier 3: 3D Carrot Orange 'EARLY ACCESS' ribbon centered at y=214..286."""
    raw = trim_rgba(load_rgba(RIBBON_PATH))
    target_w = 500
    target_h = int(round(raw.height * (target_w / float(raw.width))))
    ribbon_rs = raw.resize((target_w, target_h), Image.Resampling.LANCZOS)
    left = (CANVAS_W - target_w) // 2
    top = 216
    layer = place_on_canvas(ribbon_rs, left, top)
    return layer, {"bbox": [left, top, left + target_w, top + target_h]}


def build_discount_layer() -> Tuple[Image.Image, Dict]:
    """Tier 4: 'UP TO 30% OFF' in Pretendard ExtraBold (#161616 + #F26B1C), y=306..356."""
    ss = 2
    img_hi = Image.new("RGBA", (CANVAS_W * ss, CANVAS_H * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_hi)
    font = ImageFont.truetype(str(FONT_BOLD), 46 * ss)

    parts = [
        ("UP TO ", (22, 22, 22, 255)),
        ("30%", (242, 107, 28, 255)),
        (" OFF", (22, 22, 22, 255)),
    ]
    widths = [font.getlength(t) for t, _ in parts]
    total_w = sum(widths)
    x = (CANVAS_W * ss - total_w) * 0.5
    y = 304 * ss
    for (text, color), w in zip(parts, widths):
        draw.text((x, y), text, fill=color, font=font)
        x += w

    layer = img_hi.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
    bbox = list(layer.getbbox() or (0, 0, 0, 0))
    return layer, {"bbox": bbox, "text": "UP TO 30% OFF"}


def build_cta_layer() -> Tuple[Image.Image, Dict]:
    """Tier 5: 'SHOP NOW >' CTA Pill anchored at y=1032..1180 (45px active pill bottom clearance)."""
    cta = load_rgba(CTA_PATH)
    left = (CANVAS_W - cta.width) // 2
    top = 1032
    layer = place_on_canvas(cta, left, top)
    return layer, {"bbox": [left, top, left + cta.width, top + cta.height]}


def alpha_gatekeeper(im: Image.Image, has_soft_shadows: bool = False) -> Dict:
    """Verify zero premultiplication dark-halo fringe pixels and clean native alpha transparency."""
    arr = np.array(im.convert("RGBA"), dtype=np.float32) / 255.0
    a = arr[..., 3]
    rgb = arr[..., :3]
    luma = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

    zero_a_rgb = int(np.sum((a <= 1e-5) & (np.max(rgb, axis=-1) > 1.0 / 255.0)))
    opaque = a >= 0.99
    if not opaque.any():
        return {"zero_alpha_rgb": zero_a_rgb, "fringe_pixels": zero_a_rgb, "pass": zero_a_rgb == 0}

    near_op = binary_dilation(opaque, iterations=2)
    stray = 0 if has_soft_shadows else int(np.sum((a > 1.0 / 255.0) & (~near_op)))

    # Dark-halo check on anti-aliased edge pixels adjacent to bright opaque regions
    # (for layers with dark contact shadows, ignore low-alpha shadow tails a < 0.35)
    a_lo = 0.35 if has_soft_shadows else 0.05
    partial = (a > a_lo) & (a < 0.95) & near_op
    ys, xs = np.where(partial)
    halo = 0
    h, w = a.shape
    for y, x in zip(ys, xs):
        y0, y1 = max(0, y - 1), min(h, y + 2)
        x0, x1 = max(0, x - 1), min(w, x + 2)
        nbr = opaque[y0:y1, x0:x1]
        if nbr.any():
            mn = float(luma[y0:y1, x0:x1][nbr].min())
            if mn > 0.15 and float(luma[y, x]) < 0.50 * mn:
                halo += 1
    total = zero_a_rgb + stray + halo
    return {"zero_alpha_rgb": zero_a_rgb, "stray_alpha": stray, "dark_halo": halo, "fringe_pixels": total, "pass": total == 0}


def compute_ssim(img_a: Image.Image, img_b: Image.Image) -> float:
    """Compute mean structural similarity (SSIM) between two equal-size RGB images."""
    a = np.array(img_a.convert("RGB"), dtype=np.float64)
    b = np.array(img_b.convert("RGB"), dtype=np.float64)
    c1 = (0.01 * 255.0) ** 2
    c2 = (0.03 * 255.0) ** 2
    scores = []
    for ch in range(3):
        x, y = a[..., ch], b[..., ch]
        mu_x = gaussian_filter(x, sigma=1.5)
        mu_y = gaussian_filter(y, sigma=1.5)
        sig_x2 = gaussian_filter(x * x, sigma=1.5) - mu_x * mu_x
        sig_y2 = gaussian_filter(y * y, sigma=1.5) - mu_y * mu_y
        sig_xy = gaussian_filter(x * y, sigma=1.5) - mu_x * mu_y
        num = (2.0 * mu_x * mu_y + c1) * (2.0 * sig_xy + c2)
        den = (mu_x * mu_x + mu_y * mu_y + c1) * (sig_x2 + sig_y2 + c2)
        scores.append(float(np.mean(num / np.maximum(den, 1e-12))))
    return float(np.mean(scores))


def make_pixel_layer(psd: PSDImage, name: str, im: Image.Image) -> PixelLayer:
    lyr = PixelLayer.frompil(im.convert("RGBA"), psd, top=0, left=0)
    lyr.name = name
    return lyr


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load Backdrop & Pedestal (Z1-Z2)
    bg_layer = load_rgba(BG_PATH).resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
    pedestal_layer = load_rgba(PEDESTAL_PATH).resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)

    # 2. Load & Defringe Sub-Assembly A: Stage Burst Bag (Z3-Z8)
    stage_burst_layer = defringe_rgba_layer(
        load_rgba(STAGE_BURST_PATH).resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS),
        has_soft_shadows=True,
        clean_white_notch=True,
    )
    stage_burst_layer.save(STAGE_BURST_PATH, "PNG")

    # 3. Build Sub-Assembly B: UI Dock & Independent REV2 3D Headline Layer (Z9-Z12)
    dual_logo_layer, logo_meta = build_dual_logo_layer()
    ribbon_layer, ribbon_meta = build_ribbon_layer()
    ribbon_layer = defringe_rgba_layer(ribbon_layer, has_soft_shadows=True, clean_white_notch=True)
    discount_layer, discount_meta = build_discount_layer()
    cta_layer, cta_meta = build_cta_layer()
    cta_layer = defringe_rgba_layer(cta_layer, has_soft_shadows=True, clean_white_notch=False)
    headline_3d_layer, headline_shadow_layer, headline_meta = build_headline_3d_layers()
    headline_3d_layer = defringe_rgba_layer(headline_3d_layer, has_soft_shadows=False, clean_white_notch=False)

    # Save Sub-Assembly B (1200x1200 RGBA with REV2 3D headline embedded for standalone visual completeness)
    sub_ui_canvas = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    for lyr in [dual_logo_layer, ribbon_layer, discount_layer, cta_layer, headline_shadow_layer, headline_3d_layer]:
        sub_ui_canvas.alpha_composite(lyr)
    sub_ui_canvas = defringe_rgba_layer(sub_ui_canvas, has_soft_shadows=True, clean_white_notch=False)
    sub_ui_canvas.save(OUT_SUB_UI_PNG, "PNG")

    # 4. Composite Master 1200x1200 PNG in exact bottom-to-top Z-order
    master_rgba = Image.new("RGBA", (CANVAS_W, CANVAS_H), (255, 255, 255, 255))
    ordered_layers = [
        bg_layer,
        pedestal_layer,
        stage_burst_layer,
        dual_logo_layer,
        ribbon_layer,
        discount_layer,
        cta_layer,
        headline_shadow_layer,
        headline_3d_layer,
    ]
    for lyr in ordered_layers:
        master_rgba.alpha_composite(lyr)
    master_rgb = master_rgba.convert("RGB")
    master_rgb.save(OUT_MASTER_PNG, "PNG")

    # 5. Build Hierarchical Master PSD (strictly keeping 10a_headline_3d_liquid_metal as independent layer)
    psd = PSDImage.new("RGBA", (CANVAS_W, CANVAS_H))

    g_bg = psd.create_group(name="01_Backdrop_and_Pedestal", open_folder=True)
    g_bg.append(make_pixel_layer(psd, "00_bg_vanity_morning_light", bg_layer))
    g_bg.append(make_pixel_layer(psd, "00b_pedestal_wood_shelf", pedestal_layer))

    g_stage = psd.create_group(name="02_Sub_Assembly_A_Stage_Burst", open_folder=True)
    g_stage.append(make_pixel_layer(psd, "sub_stage_burst_bag (13 Verified Layers)", stage_burst_layer))

    g_ui = psd.create_group(name="03_Sub_Assembly_B_UI_Dock_and_Typography", open_folder=True)
    g_ui.append(make_pixel_layer(psd, "01_header_dual_brand_logos", dual_logo_layer))
    g_ui.append(make_pixel_layer(psd, "02_ribbon_early_access", ribbon_layer))
    g_ui.append(make_pixel_layer(psd, "10b_discount_up_to_30_off", discount_layer))
    g_ui.append(make_pixel_layer(psd, "11_ui_cta_button", cta_layer))
    g_ui.append(make_pixel_layer(psd, "10a_headline_3d_liquid_metal_shadow", headline_shadow_layer))
    g_ui.append(make_pixel_layer(psd, "10a_headline_3d_liquid_metal", headline_3d_layer))

    psd.save(str(OUT_MASTER_PSD))

    # 6. QA Verification: Reload PSD, compute SSIM vs Master PNG, run Alpha Gatekeeper
    psd_reloaded = PSDImage.open(str(OUT_MASTER_PSD))
    psd_comp = psd_reloaded.composite().convert("RGB")
    ssim_psd_vs_png = compute_ssim(master_rgb, psd_comp)

    psd_groups = []
    for grp in psd_reloaded:
        psd_groups.append({
            "group": grp.name,
            "layers": [child.name for child in grp] if grp.is_group() else [],
        })

    qa_headline = alpha_gatekeeper(load_rgba(HEADLINE_3D_PATH), has_soft_shadows=False)
    qa_stage = alpha_gatekeeper(stage_burst_layer, has_soft_shadows=True)
    qa_ui_dock = alpha_gatekeeper(sub_ui_canvas, has_soft_shadows=True)

    manifest = {
        "directive_id": "RECOVER_AND_REASSEMBLE_COSRX_PROJECT",
        "banner_id": "cosrx_master_1200x1200",
        "dimensions": {"width": CANVAS_W, "height": CANVAS_H},
        "deliverables": {
            "master_png": str(OUT_MASTER_PNG.relative_to(ROOT)),
            "master_psd": str(OUT_MASTER_PSD.relative_to(ROOT)),
            "sub_ui_dock_png": str(OUT_SUB_UI_PNG.relative_to(ROOT)),
            "sub_stage_burst_png": str(STAGE_BURST_PATH.relative_to(ROOT)),
            "headline_3d_rev2_png": str(HEADLINE_3D_PATH.relative_to(ROOT)),
        },
        "psd_hierarchy": psd_groups,
        "layout_bboxes": {
            "dual_logos": logo_meta,
            "headline_3d_rev2": headline_meta,
            "ribbon": ribbon_meta,
            "discount": discount_meta,
            "cta_button": cta_meta,
        },
        "qa_audit": {
            "ssim_psd_vs_master_png": round(ssim_psd_vs_png, 6),
            "alpha_gatekeeper": {
                "10a_headline_3d_liquid_metal": qa_headline,
                "sub_stage_burst_bag": qa_stage,
                "sub_ui_typography_dock": qa_ui_dock,
            },
            "layer_10a_independent_in_psd": any(
                "10a_headline_3d_liquid_metal" in g["layers"] for g in psd_groups
            ),
        },
        "elapsed_sec": round(time.time() - t0, 2),
    }

    OUT_MASTER_JSON.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[MASTER-REASSEMBLY] Done in {manifest['elapsed_sec']}s | SSIM(PSD vs PNG)={ssim_psd_vs_png:.6f}")
    print(f"[MASTER-REASSEMBLY] Alpha Gatekeeper fringe: 10a={qa_headline['fringe_pixels']} stage={qa_stage['fringe_pixels']} ui_dock={qa_ui_dock['fringe_pixels']}")
    for g in psd_groups:
        print(f"  GROUP {g['group']}: {g['layers']}")


if __name__ == "__main__":
    main()
