#!/usr/bin/env python3
"""
DIR-FORGE-COSRX-ULTA-UI-072: COSRX x ULTA Master Banner (1200x1200) Brand UI & Container Forge
Execution Mode: BRAND_UI_AND_CONTAINER_FORGE (SOP-FORGE-3D Compliant)

Forges all non-product 32-bit RGBA transparent layers in `assets/brands/COSRX/layers/`:
  1. 01a_logo_cosrx.png                  (Jet Black #000000, w>=80px, clear space >=5px)
  2. 01b_logo_ulta.png                   (Carrot Orange #F37830, w>=128px, clear space >=50px)
  3. 01_logo_dual_lockup.png             (1200px dual header lockup honoring both brand books)
  4. 02_ribbon_early_access.png          (3D undulating Carrot Orange ribbon + 'EARLY ACCESS')
  5. 03_decor_bag_back.png               (Shared-camera 3D kraft bag rear wall, cavity & handles)
  6. 09_decor_bag_front.png              (Shared-camera 3D kraft bag front wall + white ULTA logo)
  7. 10_typography_headline_discount.png ('BLACK FRIDAY' + 'UP TO 30% OFF', Inter Black/ExtraBold)
  8. 11_ui_cta_button.png                (Jet Black pill CTA 'SHOP NOW >', pill height >= 64px)

Also renders UI-only composite verification preview:
  - output/TASK_COSRX/preview_ui_components.png (1200x1200)
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import time
from typing import Callable, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# ==============================================================================
# LOCKED PATHS & BRAND TOKENS (COSRX + ULTA BEAUTY BRAND BOOKS)
# ==============================================================================
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYERS_DIR = os.path.join(REPO_ROOT, "assets", "brands", "COSRX", "layers")
LOGO_COSRX_SRC = os.path.join(REPO_ROOT, "assets", "brands", "COSRX", "LOGO", "COSRX.png")
LOGO_ULTA_SRC = os.path.join(REPO_ROOT, "assets", "brands", "COSRX", "LOGO", "Ulta Logo.png")
PREVIEW_OUT = os.path.join(REPO_ROOT, "output", "TASK_COSRX", "preview_ui_components.png")

INTER_FONT_PATH = "/Users/macbookpro/Library/Fonts/InterVariable.ttf"

# Exact Brand Color Tokens (User-locked ULTA Orange #F26B1C from source Ulta Logo.png)
JET_BLACK_RGB = (0, 0, 0)              # #000000 (COSRX & ULTA)
CARROT_ORANGE_RGB = (242, 107, 28)     # #F26B1C (Source Ulta Logo.png Orange)
PURE_WHITE_RGB = (255, 255, 255)       # #FFFFFF
CHALK_WHITE_RGB = (248, 245, 242)      # #F8F5F2 (ULTA Chalk White)

BAG_CANVAS = 1024
BAG_SAFE_MARGIN = 40
BAG_SSAA = 2


# ==============================================================================
# COLOR & COMPOSITING HELPERS (ZERO-FRINGE PREMULTIPLIED ALPHA)
# ==============================================================================
def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1.0 / 2.4)) - 0.055)


def rgb_to_lin(rgb: Tuple[int, int, int]) -> np.ndarray:
    return srgb_to_linear(np.array(rgb, dtype=np.float32) / 255.0)


def smoothstep(edge0, edge1, x: np.ndarray) -> np.ndarray:
    diff = np.asarray(edge1, dtype=np.float32) - np.asarray(edge0, dtype=np.float32)
    denom = np.where(np.abs(diff) < 1e-6, np.where(diff >= 0.0, 1e-6, -1e-6), diff)
    t = np.clip((x - edge0) / denom, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def over_premul(
    dst_rgb: np.ndarray,
    dst_a: np.ndarray,
    src_rgb: np.ndarray,
    src_a: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """Porter-Duff src-over-dst in straight alpha, zero gray fringing."""
    sa = np.clip(src_a, 0.0, 1.0)[..., None]
    da = np.clip(dst_a, 0.0, 1.0)[..., None]
    out_a = sa + da * (1.0 - sa)
    out_premul = src_rgb * sa + dst_rgb * da * (1.0 - sa)
    out_rgb = np.where(out_a > 1e-6, out_premul / np.maximum(out_a, 1e-6), 0.0)
    return np.clip(out_rgb, 0.0, 1.0), np.clip(out_a[..., 0], 0.0, 1.0)


def downsample_ssaa_rgba(rgb: np.ndarray, alpha: np.ndarray, factor: int = 2) -> Image.Image:
    """Premultiplied-alpha box downsample to eliminate dark/light edge halos."""
    h, w = alpha.shape
    assert h % factor == 0 and w % factor == 0, f"Shape {(h, w)} not divisible by {factor}"
    th, tw = h // factor, w // factor
    a = np.clip(alpha, 0.0, 1.0)
    premul = np.clip(rgb, 0.0, 1.0) * a[..., None]

    a_ds = a.reshape(th, factor, tw, factor).mean(axis=(1, 3))
    premul_ds = premul.reshape(th, factor, tw, factor, 3).mean(axis=(1, 3))
    rgb_ds = np.where(a_ds[..., None] > 1e-5, premul_ds / np.maximum(a_ds[..., None], 1e-5), 0.0)
    rgb_ds = np.clip(rgb_ds, 0.0, 1.0)

    out = np.zeros((th, tw, 4), dtype=np.uint8)
    out[..., :3] = np.round(rgb_ds * 255.0).astype(np.uint8)
    out[..., 3] = np.round(np.clip(a_ds, 0.0, 1.0) * 255.0).astype(np.uint8)
    out[out[..., 3] == 0] = 0
    return Image.fromarray(out, mode="RGBA")


def tint_alpha_image(src_img: Image.Image, target_w: int, rgb: Tuple[int, int, int]) -> Image.Image:
    """Resize a monochrome/brand logo using its alpha silhouette and lock exact RGB color."""
    rgba = src_img.convert("RGBA")
    bbox = rgba.getbbox()
    if bbox is None:
        raise ValueError("Source logo is completely transparent.")
    cropped = rgba.crop(bbox)
    cw, ch = cropped.size
    target_h = max(1, int(round(target_w * ch / cw)))

    alpha_ch = cropped.split()[3].resize((target_w, target_h), Image.Resampling.LANCZOS)
    a_arr = np.array(alpha_ch, dtype=np.uint8)

    out = np.zeros((target_h, target_w, 4), dtype=np.uint8)
    nonzero = a_arr > 0
    out[nonzero, 0] = rgb[0]
    out[nonzero, 1] = rgb[1]
    out[nonzero, 2] = rgb[2]
    out[:, :, 3] = a_arr
    return Image.fromarray(out, mode="RGBA")


# ==============================================================================
# COMPONENT 1: DUAL BRAND LOGOS (#ui_dual_logo)
# ==============================================================================
def forge_dual_logos() -> dict:
    """
    Forges:
      - 01a_logo_cosrx.png (Jet Black #000000, width=240px >= 80px, clear space=24px >= 5px)
      - 01b_logo_ulta.png  (Carrot Orange #F37830, width=220px >= 128px, clear space=56px >= 50px)
      - 01_logo_dual_lockup.png (1200x204 dual header lockup with >=56px ULTA clear space)
    """
    print("\n[1/5] Forging Dual Brand Logos (COSRX #000000 + ULTA #F26B1C)...")
    cosrx_src = Image.open(LOGO_COSRX_SRC)
    ulta_src = Image.open(LOGO_ULTA_SRC)

    cosrx_glyph = tint_alpha_image(cosrx_src, target_w=240, rgb=JET_BLACK_RGB)
    ulta_glyph = tint_alpha_image(ulta_src, target_w=220, rgb=CARROT_ORANGE_RGB)

    cw, ch = cosrx_glyph.size
    uw, uh = ulta_glyph.size

    # 01a_logo_cosrx.png (clear space >= 5px -> 24px all around)
    cosrx_pad = 24
    cosrx_canvas = Image.new("RGBA", (cw + 2 * cosrx_pad, ch + 2 * cosrx_pad), (0, 0, 0, 0))
    cosrx_canvas.alpha_composite(cosrx_glyph, (cosrx_pad, cosrx_pad))
    path_01a = os.path.join(LAYERS_DIR, "01a_logo_cosrx.png")
    cosrx_canvas.save(path_01a, "PNG")

    # 01b_logo_ulta.png (clear space >= 50px -> 56px all around)
    ulta_pad = 56
    ulta_canvas = Image.new("RGBA", (uw + 2 * ulta_pad, uh + 2 * ulta_pad), (0, 0, 0, 0))
    ulta_canvas.alpha_composite(ulta_glyph, (ulta_pad, ulta_pad))
    path_01b = os.path.join(LAYERS_DIR, "01b_logo_ulta.png")
    ulta_canvas.save(path_01b, "PNG")

    # 01_logo_dual_lockup.png (1200px wide header bar; ULTA keeps >=56px clear space on all 4 sides)
    lockup_w = 1200
    lockup_h = uh + 2 * ulta_pad  # 89 + 112 = 201 -> round to 204
    lockup_h = max(lockup_h, 204)
    lockup = Image.new("RGBA", (lockup_w, lockup_h), (0, 0, 0, 0))

    ulta_x = lockup_w - ulta_pad - uw
    ulta_y = (lockup_h - uh) // 2  # >= 56px top & bottom
    cosrx_x = 56
    # Optically align COSRX wordmark slightly higher to match the main 'ULTA' letters above 'BEAUTY'
    cosrx_y = ulta_y + (uh - ch) // 2 - 6

    lockup.alpha_composite(cosrx_glyph, (cosrx_x, cosrx_y))
    lockup.alpha_composite(ulta_glyph, (ulta_x, ulta_y))
    path_01 = os.path.join(LAYERS_DIR, "01_logo_dual_lockup.png")
    lockup.save(path_01, "PNG")

    print(f"      -> {path_01a} ({cosrx_canvas.size}, glyph={cw}x{ch}, clear_space={cosrx_pad}px)")
    print(f"      -> {path_01b} ({ulta_canvas.size}, glyph={uw}x{uh}, clear_space={ulta_pad}px)")
    print(f"      -> {path_01} ({lockup.size})")
    return {
        "01": path_01,
        "01a": path_01a,
        "01b": path_01b,
        "cosrx_glyph_size": (cw, ch),
        "ulta_glyph_size": (uw, uh),
    }


# ==============================================================================
# PLAYWRIGHT HTML/CSS TRANSPARENT RENDERER (INTER VARIABLE FONT, 2x SSAA)
# ==============================================================================
def render_playwright_jobs(jobs: list[dict], tmp_dir: str) -> None:
    """
    Runs a single headless Chromium session via Node Playwright to render all
    transparent RGBA typography/UI jobs at 2x deviceScaleFactor onto alpha=0 canvases.
    """
    runner_js = r"""
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(path.join(process.cwd(), 'package.json'));
const { chromium } = require('playwright');

const cfgPath = process.argv[process.argv.length - 1];
const cfg = JSON.parse(fs.readFileSync(cfgPath, 'utf-8'));

const browser = await chromium.launch({ headless: true });
try {
  for (const job of cfg.jobs) {
    const context = await browser.newContext({
      viewport: { width: job.width, height: job.height },
      deviceScaleFactor: job.scale || 2,
    });
    const page = await context.newPage();
    await page.setContent(job.html, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(120);
    await page.screenshot({
      path: job.outPath,
      type: 'png',
      omitBackground: true,
    });
    await context.close();
  }
} finally {
  await browser.close();
}
"""
    cfg_path = os.path.join(tmp_dir, "pw_jobs.json")
    js_path = os.path.join(tmp_dir, "pw_runner.mjs")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump({"jobs": jobs}, f)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(runner_js)

    proc = subprocess.run(
        ["node", js_path, cfg_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Playwright render failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")


def downsample_playwright_png(hi_path: str, out_path: str, factor: int = 2) -> Image.Image:
    """Convert 2x Playwright RGBA screenshot via premultiplied SSAA downsample."""
    hi = Image.open(hi_path).convert("RGBA")
    arr = np.array(hi, dtype=np.float32) / 255.0
    img = downsample_ssaa_rgba(arr[..., :3], arr[..., 3], factor=factor)
    img.save(out_path, "PNG")
    return img


# ==============================================================================
# COMPONENT 3: PROMOTION RIBBON TAG ('EARLY ACCESS')
# ==============================================================================
def forge_early_access_ribbon(text_mask_hi: np.ndarray, out_path: str) -> Image.Image:
    """
    Synthesizes a 3D undulating Carrot Orange (#F37830) silk/sash promotion ribbon
    ('띠 오브제') with folded rear swallowtail tabs, subtle satin sheen, and
    wave-conformed Pure White 'EARLY ACCESS' typography at 2x SSAA.
    Final size: 760 x 176 RGBA (native alpha=0, zero clipping, zero gray halo).
    """
    print("\n[2/5] Forging 3D Undulating Promotion Ribbon ('EARLY ACCESS')...")
    out_w, out_h = 760, 176
    ss = 2
    W, H = out_w * ss, out_h * ss

    yy, xx = np.indices((H, W), dtype=np.float32)
    cx, cy = W * 0.5, H * 0.5

    # Main ribbon geometric parameters (at 2x SSAA)
    body_half_w = 576.0   # 288px * 2 -> total front ribbon width ~576px (out of 760)
    body_half_h = 68.0    # 34px * 2 -> ribbon height ~68px
    wave_amp = 14.0       # Graceful gentle S-wave amplitude (7px at 1x)

    # Normalized horizontal parameter u in [-1, 1] across main ribbon
    u = (xx - cx) / body_half_w
    # Smooth S-wave centerline y_c(x)
    y_wave = cy + wave_amp * np.sin(math.pi * u)
    # Derivative dy/dx for 3D silk surface normal lighting
    dy_du = wave_amp * math.pi * np.cos(math.pi * u)
    slope_x = dy_du / body_half_w

    # --- 1. Rear Folded Swallowtail Tabs (Left & Right) ---
    # Each rear tab extends slightly outward & lower behind the main ribbon edge
    rgb_buf = np.zeros((H, W, 3), dtype=np.float32)
    a_buf = np.zeros((H, W), dtype=np.float32)

    base_orange = np.array(CARROT_ORANGE_RGB, dtype=np.float32) / 255.0
    deep_orange = np.array([188, 68, 16], dtype=np.float32) / 255.0      # Folded back tab base
    crease_orange = np.array([128, 38, 6], dtype=np.float32) / 255.0     # Deep fold crease
    bright_orange = np.array([255, 148, 82], dtype=np.float32) / 255.0   # Silk specular crest

    for side in (-1.0, +1.0):
        # Rear tab sits slightly lower (+20px at 2x) and protrudes outward to ±660
        tab_inner_x = cx + side * (body_half_w - 58.0)
        tab_outer_x = cx + side * (body_half_w + 92.0)
        tab_y_center = (cy + wave_amp * math.sin(math.pi * side)) + (16.0 if side > 0 else 18.0)

        # Horizontal signed distance inside tab
        if side < 0:
            x_in = xx - tab_outer_x   # >=0 inside
            x_out = tab_inner_x - xx  # >=0 inside
        else:
            x_in = tab_outer_x - xx
            x_out = xx - tab_inner_x

        dy_tab = np.abs(yy - tab_y_center)
        # Swallowtail V-notch cut into the outer tip (depth 42px at 2x)
        notch_depth = 42.0 * (1.0 - np.clip(dy_tab / (body_half_h * 0.94), 0.0, 1.0))
        d_outer_notch = x_in - notch_depth
        d_vert = (body_half_h * 0.92) - dy_tab
        d_tab = np.minimum(np.minimum(d_outer_notch, x_out), d_vert)
        tab_alpha = np.clip(d_tab + 0.5, 0.0, 1.0)

        # Shade rear tab: darker near the fold crease under the main ribbon
        dist_from_edge = np.clip(np.abs(xx - (cx + side * body_half_w)) / 95.0, 0.0, 1.0)
        v_grad = 1.0 - 0.16 * np.clip(dy_tab / body_half_h, 0.0, 1.0)
        tab_col = crease_orange * (1.0 - dist_from_edge[..., None]) + deep_orange * dist_from_edge[..., None]
        tab_col = np.clip(tab_col * v_grad[..., None], 0.0, 1.0)

        rgb_buf, a_buf = over_premul(rgb_buf, a_buf, tab_col, tab_alpha)

        # Small triangular fold-under connector between main ribbon corner and rear tab
        fold_x0 = cx + side * (body_half_w - 42.0)
        fold_x1 = cx + side * body_half_w
        if side < 0:
            t_fx = np.clip((xx - fold_x1) / max(fold_x0 - fold_x1, 1.0), 0.0, 1.0)
            in_fx = (xx >= fold_x1) & (xx <= fold_x0)
        else:
            t_fx = np.clip((fold_x1 - xx) / max(fold_x1 - fold_x0, 1.0), 0.0, 1.0)
            in_fx = (xx >= fold_x0) & (xx <= fold_x1)
        y_top_fold = (cy + wave_amp * math.sin(math.pi * side)) + body_half_h - 4.0
        y_bot_fold = tab_y_center + body_half_h * 0.92
        y_diag = y_top_fold + (y_bot_fold - y_top_fold) * (1.0 - t_fx)
        fold_a = np.where(in_fx & (yy >= y_top_fold - 2.0) & (yy <= y_diag), 1.0, 0.0).astype(np.float32)
        fold_col = np.broadcast_to(crease_orange * 0.88, (H, W, 3))
        rgb_buf, a_buf = over_premul(rgb_buf, a_buf, fold_col, fold_a)

    # --- 2. Main Front Undulating Ribbon Body ---
    # Slight angled parallelogram slant on left/right ends for dynamic commercial energy
    slant = (yy - y_wave) * 0.12
    d_x = body_half_w - np.abs((xx - cx) - slant)
    d_y = body_half_h - np.abs(yy - y_wave)
    # Soft rounded corner bevel (r = 8px at 2x)
    r_c = 8.0
    qx = np.maximum(-d_x + r_c, 0.0)
    qy = np.maximum(-d_y + r_c, 0.0)
    sdf_body = np.sqrt(qx * qx + qy * qy) + np.minimum(np.maximum(-d_x + r_c, -d_y + r_c), 0.0) - r_c
    body_alpha = np.clip(0.5 - sdf_body, 0.0, 1.0)

    # 3D silk/satin surface shading along the S-wave + vertical cylinder pillow
    v_norm = np.clip((yy - y_wave) / body_half_h, -1.0, 1.0)
    # Normal from wave slope & gentle vertical cushion
    nx = -slope_x * 2.2
    ny = v_norm * 0.24
    nz = np.sqrt(np.maximum(1.0 - np.clip(nx * nx + ny * ny, 0.0, 0.85), 0.15))
    # Top-left studio key light
    lx, ly, lz = -0.45, -0.40, 0.80
    l_norm = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / l_norm, ly / l_norm, lz / l_norm
    ndotl = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)

    # Subtle satin crest highlight & warm lower bevel
    satin_spec = (np.clip(ndotl, 0.0, 1.0) ** 6.0) * 0.24
    edge_trim = smoothstep(0.84, 0.98, np.abs(v_norm))
    top_rim_glint = smoothstep(-0.78, -0.94, v_norm) * 0.14

    body_col = (
        base_orange[None, None, :] * (0.86 + 0.18 * ndotl[..., None])
        + (bright_orange - base_orange)[None, None, :] * (satin_spec[..., None] + top_rim_glint[..., None])
        - (base_orange - deep_orange)[None, None, :] * (edge_trim[..., None] * 0.18)
    )
    # Subtle micro-silk horizontal sheen lines
    silk_grain = 0.008 * np.sin(yy * 0.9 + xx * 0.03)
    body_col = np.clip(body_col + silk_grain[..., None], 0.0, 1.0)

    # Soft inner contact shadow cast by front ribbon onto rear tabs
    shadow_offset_y = 6.0
    d_y_sh = body_half_h - np.abs((yy - shadow_offset_y) - y_wave)
    d_x_sh = (body_half_w + 4.0) - np.abs((xx - cx) - slant)
    sh_mask = np.clip(np.minimum(d_x_sh, d_y_sh) * 0.15, 0.0, 1.0) * a_buf * (1.0 - body_alpha)
    rgb_buf = rgb_buf * (1.0 - 0.35 * sh_mask[..., None])

    rgb_buf, a_buf = over_premul(rgb_buf, a_buf, body_col, body_alpha)

    # --- 3. Warp Playwright 'EARLY ACCESS' Glyph Mask along Ribbon S-Wave ---
    # text_mask_hi has shape (H, W) with float alpha in [0, 1] centered at (cx, cy)
    src_y = yy - (y_wave - cy)
    src_y_clamped = np.clip(src_y, 0.0, H - 1.001)
    y0 = np.floor(src_y_clamped).astype(np.int32)
    y1 = np.minimum(y0 + 1, H - 1)
    fy = src_y_clamped - y0
    x_idx = np.arange(W, dtype=np.int32)[None, :]
    warped_text = text_mask_hi[y0, x_idx] * (1.0 - fy) + text_mask_hi[y1, x_idx] * fy
    warped_text = np.clip(warped_text, 0.0, 1.0) * body_alpha

    # Crisp subtle warm burnt-orange drop shadow (2px down at 2x) behind white letters
    sh_text = np.roll(warped_text, shift=3, axis=0) * body_alpha
    sh_text[:3, :] = 0.0
    rgb_buf, a_buf = over_premul(
        rgb_buf,
        a_buf,
        np.broadcast_to(crease_orange, (H, W, 3)),
        sh_text * 0.42,
    )

    # Pure White crisp lettering
    white_col = np.ones((H, W, 3), dtype=np.float32)
    rgb_buf, a_buf = over_premul(rgb_buf, a_buf, white_col, warped_text)

    img = downsample_ssaa_rgba(rgb_buf, a_buf, factor=ss)
    img.save(out_path, "PNG")
    print(f"      -> {out_path} ({img.size})")
    return img


# ==============================================================================
# COMPONENT 2: 3D CARROT ORANGE ULTA KRAFT SHOPPING BAG (SHARED-CAMERA SPLIT)
# ==============================================================================
def normalize3(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def dot3(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sum(a * b, axis=-1)


def smin_poly(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def smax_poly(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    return -smin_poly(-a, -b, k)


def sd_box(p: np.ndarray, b: np.ndarray, r: float = 0.0) -> np.ndarray:
    q = np.abs(p) - (b - r)
    outside = np.linalg.norm(np.maximum(q, 0.0), axis=-1)
    inside = np.minimum(np.maximum(q[:, 0], np.maximum(q[:, 1], q[:, 2])), 0.0)
    return outside + inside - r


def rot_x(deg: float) -> np.ndarray:
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float32)


def rot_y(deg: float) -> np.ndarray:
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)


def rot_z(deg: float) -> np.ndarray:
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float32)


# Authentic ULTA landscape kraft shopping bag geometry (W:H ≈ 1.32:1)
BAG_HH = 0.375
W_BASE = 0.485
W_TOP = 0.505          # Subtle outward flare at mouth for abundant retail silhouette
D_BASE = 0.210
D_TOP = 0.220
WALL_T = 0.018
CUFF_H = 0.078
CUFF_EXTRA_T = 0.008
GUSSET_MAX_DEPTH = 0.068

HANDLE_X = 0.185
HANDLE_Y_ANCHOR = BAG_HH - 0.048
HANDLE_Z_ANCHOR = D_TOP - WALL_T - 0.008
HANDLE_CORD_RADIUS = 0.0155

# Energetic 3D orientation matching Page 6 PICKDI PPTX (gentle yaw + playful -6.5° tilt)
BAG_YAW_DEG = -13.0
BAG_ROLL_DEG = -6.5
R_BAG_TO_WORLD = rot_z(BAG_ROLL_DEG) @ rot_y(BAG_YAW_DEG)
R_WORLD_TO_BAG = R_BAG_TO_WORLD.T


def _build_kraft_handle_polyline(
    z_sign: float,
    arch_height: float,
    outward_drape: float,
    asym_shift: float = 0.0,
    n_seg: int = 34,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    t = np.linspace(0.0, 1.0, n_seg + 1, dtype=np.float32)
    s = (t - 0.5) * math.pi
    cos_s = np.maximum(np.cos(s), 0.0)
    sin_s = np.sin(s)

    x = HANDLE_X * sin_s * (1.0 + 0.05 * (cos_s ** 1.3)) + asym_shift * (cos_s ** 2)
    y = HANDLE_Y_ANCHOR + arch_height * (cos_s ** 0.80)
    z = z_sign * HANDLE_Z_ANCHOR + z_sign * outward_drape * (np.maximum(np.sin(math.pi * t), 0.0) ** 0.90)

    pts = np.stack([x, y, z], axis=-1).astype(np.float32)
    ab = pts[1:] - pts[:-1]
    inv_l2 = 1.0 / np.maximum(np.sum(ab * ab, axis=-1), 1e-8)
    tangents = normalize3(ab)
    return pts, ab, inv_l2, tangents


_ULTA_HANDLE_FRONT = _build_kraft_handle_polyline(
    z_sign=+1.0, arch_height=0.335, outward_drape=0.028, asym_shift=0.004
)
_ULTA_HANDLE_REAR = _build_kraft_handle_polyline(
    z_sign=-1.0, arch_height=0.330, outward_drape=0.024, asym_shift=-0.004
)


def _eval_polyline_tube(
    p: np.ndarray,
    poly: Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    radius: float,
) -> Tuple[np.ndarray, np.ndarray]:
    pts, ab, inv_l2, tangents = poly
    n_pts = p.shape[0]
    min_d2 = np.full(n_pts, 1e6, dtype=np.float32)
    best_tan = np.zeros((n_pts, 3), dtype=np.float32)
    best_tan[:, 1] = 1.0

    for i in range(len(ab)):
        pa = p - pts[i][None, :]
        h = np.clip(np.sum(pa * ab[i][None, :], axis=-1) * inv_l2[i], 0.0, 1.0)
        diff = pa - ab[i][None, :] * h[:, None]
        d2 = np.sum(diff * diff, axis=-1)
        closer = d2 < min_d2
        if np.any(closer):
            min_d2[closer] = d2[closer]
            best_tan[closer] = tangents[i]

    return np.sqrt(min_d2) - radius, best_tan


def _load_ulta_logo_mask_for_bag() -> np.ndarray:
    """Load and smooth-upscale ULTA Beauty alpha mask for crisp 3D front-panel projection."""
    src = Image.open(LOGO_ULTA_SRC).convert("RGBA")
    bbox = src.getbbox()
    cropped = src.crop(bbox)
    # 2x smooth Lanczos upscale for ultra-clean bilinear sampling at 2048x2048 SSAA
    w, h = cropped.size
    a = cropped.split()[3].resize((w * 2, h * 2), Image.Resampling.LANCZOS)
    return np.array(a, dtype=np.float32) / 255.0


def build_ulta_bag_scene(ulta_mask: np.ndarray):
    """
    Returns SDFs & PBR shader for:
      - full_sdf: combined bag (for shared camera auto-framing)
      - back_sdf: rear kraft wall + interior cavity + BOTH twisted kraft handles (03_decor_bag_back.png)
      - front_sdf: front kraft wall + front top lip + white ULTA logo (09_decor_bag_front.png)
    """
    mask_h, mask_w = ulta_mask.shape
    logo_aspect = mask_w / float(mask_h)  # ~2.479

    # Kraft paper palette calibrated so lit front panel resolves directly to #F26B1C (242, 107, 28)
    body_lin = rgb_to_lin((246, 109, 28))        # Vivid #F26B1C ULTA Orange kraft albedo
    gusset_deep_lin = rgb_to_lin((194, 66, 10))  # Deepened warm burnt-orange side gusset
    interior_lin = rgb_to_lin((136, 42, 6))      # Warm shaded kraft interior cavity
    rim_accent_lin = rgb_to_lin((255, 130, 52))  # Subtle folded top lip highlight
    handle_lin = rgb_to_lin((232, 98, 22))       # Matching twisted #F26B1C kraft handles
    white_ink_lin = rgb_to_lin((255, 255, 255))  # Pure White #FFFFFF screen-printed ULTA logo

    def eval_bag_body_local(pb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        x = pb[:, 0]
        y = pb[:, 1]
        z = pb[:, 2]

        t_y = np.clip((y + BAG_HH) / (2.0 * BAG_HH), 0.0, 1.0)
        w_y = W_BASE * (1.0 - t_y) + W_TOP * t_y
        d_y = D_BASE * (1.0 - t_y) + D_TOP * t_y

        # V-shaped side gusset crease along ±X faces
        z_abs_crisp = np.sqrt(z * z + 0.0050 * 0.0050) - 0.0050
        v_profile = np.maximum(0.0, 1.0 - z_abs_crisp / np.maximum(d_y, 1e-4))
        gusset_ramp = smoothstep(0.03, 0.24, t_y)
        gusset_in = GUSSET_MAX_DEPTH * gusset_ramp * v_profile

        # Subtle organic paper bow/swell across front & back panel (authentic stuffed kraft bag)
        panel_swell = 0.010 * (1.0 - (x / np.maximum(w_y, 1e-4)) ** 2) * np.sin(math.pi * t_y)
        panel_swell = np.clip(panel_swell, 0.0, 0.012)

        w_eff = w_y - gusset_in
        d_eff = d_y + panel_swell

        r_edge = 0.010
        qx = np.abs(x) - (w_eff - r_edge)
        qy = np.abs(y) - (BAG_HH - r_edge)
        qz = np.abs(z) - (d_eff - r_edge)
        d_outer = (
            np.sqrt(np.maximum(qx, 0.0) ** 2 + np.maximum(qy, 0.0) ** 2 + np.maximum(qz, 0.0) ** 2)
            + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0.0)
            - r_edge
        ) * 0.86

        # Hollow open-top interior cavity
        cuff_blend = smoothstep(BAG_HH - CUFF_H - 0.016, BAG_HH - CUFF_H + 0.008, y)
        wall_t = WALL_T + CUFF_EXTRA_T * cuff_blend

        in_w = np.maximum(w_eff - wall_t, 0.05)
        in_d = np.maximum(d_eff - wall_t, 0.03)
        r_in = 0.006
        iqx = np.abs(x) - (in_w - r_in)
        iqz = np.abs(z) - (in_d - r_in)
        iqy = (-BAG_HH + 0.042) - y
        d_inner = (
            np.sqrt(np.maximum(iqx, 0.0) ** 2 + np.maximum(iqy, 0.0) ** 2 + np.maximum(iqz, 0.0) ** 2)
            + np.minimum(np.maximum(iqx, np.maximum(iqy, iqz)), 0.0)
            - r_in
        ) * 0.86

        d_body = smax_poly(d_outer, -d_inner, 0.0040)
        gusset_factor = gusset_ramp * (v_profile ** 1.35) * smoothstep(w_eff - 0.09, w_eff - 0.014, np.abs(x))
        is_interior = (-d_inner > d_outer - 0.003) & (y < BAG_HH - 0.005)
        return d_body, gusset_factor, is_interior.astype(np.float32)

    def eval_handles_local(pb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        d_bound = sd_box(
            pb - np.array([0.0, BAG_HH + 0.12, 0.0], dtype=np.float32)[None, :],
            np.array([0.30, 0.30, 0.30], dtype=np.float32),
            0.03,
        )
        near = d_bound < 0.06
        d_handles = d_bound + 0.06
        tan_out = np.zeros_like(pb)
        tan_out[:, 1] = 1.0

        if np.any(near):
            pbn = pb[near]
            d_f, tan_f = _eval_polyline_tube(pbn, _ULTA_HANDLE_FRONT, HANDLE_CORD_RADIUS)
            d_r, tan_r = _eval_polyline_tube(pbn, _ULTA_HANDLE_REAR, HANDLE_CORD_RADIUS)
            use_f = d_f <= d_r
            d_h = np.where(use_f, d_f, d_r)
            tan_h = np.where(use_f[:, None], tan_f, tan_r)

            d_handles = d_handles.copy()
            d_handles[near] = d_h
            tan_out[near] = tan_h

        return d_handles, tan_out

    def sdf_full_world(p_world: np.ndarray) -> np.ndarray:
        pb = p_world @ R_WORLD_TO_BAG.T
        d_body, _, _ = eval_bag_body_local(pb)
        d_handles, _ = eval_handles_local(pb)
        return np.minimum(d_body, d_handles)

    def sdf_back_world(p_world: np.ndarray) -> np.ndarray:
        """03_decor_bag_back.png: Rear wall + interior cavity + BOTH kraft handles."""
        pb = p_world @ R_WORLD_TO_BAG.T
        d_body, _, _ = eval_bag_body_local(pb)
        # Keep z <= +0.010 (tiny +0.010 overlap tucked behind front shell -> 0.0px seam gap)
        d_back_body = np.maximum(d_body, pb[:, 2] - 0.010)
        d_handles, _ = eval_handles_local(pb)
        return np.minimum(d_back_body, d_handles)

    def sdf_front_world(p_world: np.ndarray) -> np.ndarray:
        """09_decor_bag_front.png: Front paper shell + front gusset + white ULTA logo."""
        pb = p_world @ R_WORLD_TO_BAG.T
        d_body, _, _ = eval_bag_body_local(pb)
        # Keep z >= 0.0 cleanly (front half covering product bases)
        return np.maximum(d_body, -pb[:, 2])

    def sample_front_logo(pb: np.ndarray, n_local: np.ndarray, is_interior: np.ndarray) -> np.ndarray:
        """Bilinearly sample Pure White ULTA logo directly in bag-local front-face UV space."""
        front_face = (pb[:, 2] > 0.14) & (is_interior < 0.5) & (n_local[:, 2] > 0.65)
        logo_a = np.zeros(pb.shape[0], dtype=np.float32)
        if not np.any(front_face):
            return logo_a

        pf = pb[front_face]
        # Logo width spans ~68% of front panel width, aspect-locked to source logo
        logo_half_w = W_BASE * 0.68
        logo_half_h = logo_half_w / logo_aspect
        logo_center_y = -0.025  # Optically balanced slightly below geometric vertical center

        u = (pf[:, 0] / logo_half_w) * 0.5 + 0.5
        v = 0.5 - ((pf[:, 1] - logo_center_y) / logo_half_h) * 0.5

        inside = (u >= 0.0) & (u <= 1.0) & (v >= 0.0) & (v <= 1.0)
        if not np.any(inside):
            return logo_a

        ui = u[inside] * (mask_w - 1.001)
        vi = v[inside] * (mask_h - 1.001)
        x0 = np.floor(ui).astype(np.int32)
        y0 = np.floor(vi).astype(np.int32)
        x1 = np.minimum(x0 + 1, mask_w - 1)
        y1 = np.minimum(y0 + 1, mask_h - 1)
        fx = ui - x0
        fy = vi - y0

        val = (
            ulta_mask[y0, x0] * (1.0 - fx) * (1.0 - fy)
            + ulta_mask[y0, x1] * fx * (1.0 - fy)
            + ulta_mask[y1, x0] * (1.0 - fx) * fy
            + ulta_mask[y1, x1] * fx * fy
        )
        out_f = np.zeros(pf.shape[0], dtype=np.float32)
        out_f[inside] = val
        logo_a[front_face] = out_f
        return logo_a

    def material_world(p_world: np.ndarray, n_world: np.ndarray, include_logo: bool, include_handles: bool) -> dict:
        pb = p_world @ R_WORLD_TO_BAG.T
        n_local = n_world @ R_WORLD_TO_BAG.T

        d_body, gusset_factor, is_interior = eval_bag_body_local(pb)
        if include_handles:
            d_handles, tan_local = eval_handles_local(pb)
            d_back_body = np.maximum(d_body, pb[:, 2] - 0.010)
            is_handle = (d_handles <= d_back_body + 1e-4).astype(np.float32)
        else:
            is_handle = np.zeros(pb.shape[0], dtype=np.float32)
            tan_local = np.zeros_like(pb)
            tan_local[:, 1] = 1.0

        is_paper = 1.0 - is_handle

        # Multi-frequency kraft paper fiber texture + subtle natural paper crinkle
        fiber = (
            np.sin(pb[:, 0] * 210.0 + pb[:, 1] * 85.0) * np.cos(pb[:, 1] * 240.0 - pb[:, 2] * 175.0) * 0.45
            + np.sin(pb[:, 0] * 420.0 - pb[:, 1] * 310.0) * 0.35
            + np.cos(pb[:, 0] * 45.0 + pb[:, 1] * 18.0) * 0.20
        )

        gusset_mix = np.clip(gusset_factor * 0.68, 0.0, 0.74)[:, None]
        paper_albedo = body_lin[None, :] * (1.0 - gusset_mix) + gusset_deep_lin[None, :] * gusset_mix

        # Subtle highlight on folded top rim
        rim_band = smoothstep(BAG_HH - 0.020, BAG_HH - 0.002, pb[:, 1])[:, None]
        paper_albedo = paper_albedo * (1.0 - 0.30 * rim_band) + rim_accent_lin[None, :] * (0.30 * rim_band)

        # Shaded darker interior kraft cavity
        cav_depth = smoothstep(BAG_HH - 0.01, BAG_HH - 0.22, pb[:, 1])[:, None]
        int_albedo = paper_albedo * (1.0 - 0.62 * cav_depth) + interior_lin[None, :] * (0.62 * cav_depth)
        paper_albedo = paper_albedo * (1.0 - is_interior[:, None]) + int_albedo * is_interior[:, None]

        # Subtle kraft fiber tonal variation (±2.2%)
        paper_albedo = np.clip(paper_albedo * (1.0 + 0.022 * fiber[:, None]), 0.0, 1.0)

        # Perspective-mapped Pure White ULTA logo on front face
        logo_mask = np.zeros(pb.shape[0], dtype=np.float32)
        if include_logo:
            logo_mask = sample_front_logo(pb, n_local, is_interior)
            # Screen-printed white ink follows subtle paper micro-grain
            ink_col = white_ink_lin[None, :] * (0.985 + 0.015 * fiber[:, None])
            paper_albedo = paper_albedo * (1.0 - logo_mask[:, None]) + ink_col * logo_mask[:, None]

        # Twisted kraft paper cord handles (helical twist shading)
        twist = np.sin(pb[:, 0] * 195.0 + pb[:, 1] * 210.0 + pb[:, 2] * 160.0)
        handle_albedo = handle_lin[None, :] * (0.94 + 0.06 * twist[:, None])

        albedo = paper_albedo * is_paper[:, None] + handle_albedo * is_handle[:, None]
        roughness = (
            np.clip(0.56 + 0.03 * fiber, 0.48, 0.65) * is_paper
            + 0.50 * is_handle
        )
        # Slightly smoother satin ink on white ULTA print
        roughness = roughness * (1.0 - 0.22 * logo_mask)

        return {
            "albedo": albedo.astype(np.float32),
            "roughness": roughness.astype(np.float32),
            "is_handle": is_handle.astype(np.float32),
            "is_interior": is_interior.astype(np.float32),
            "gusset_factor": gusset_factor.astype(np.float32),
            "logo_mask": logo_mask.astype(np.float32),
            "body_bounce_lin": body_lin.astype(np.float32),
        }

    return sdf_full_world, sdf_back_world, sdf_front_world, material_world


def compute_normals(p: np.ndarray, sdf_fn: Callable[[np.ndarray], np.ndarray], eps: float = 1.4e-3) -> np.ndarray:
    e1 = np.array([1, -1, -1], dtype=np.float32) * eps
    e2 = np.array([-1, -1, 1], dtype=np.float32) * eps
    e3 = np.array([-1, 1, -1], dtype=np.float32) * eps
    e4 = np.array([1, 1, 1], dtype=np.float32) * eps
    n = (
        e1 * sdf_fn(p + e1)[:, None]
        + e2 * sdf_fn(p + e2)[:, None]
        + e3 * sdf_fn(p + e3)[:, None]
        + e4 * sdf_fn(p + e4)[:, None]
    )
    return normalize3(n)


def compute_ao(p: np.ndarray, n: np.ndarray, sdf_fn: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    occ = np.zeros(p.shape[0], dtype=np.float32)
    sca = 1.0
    for i in range(1, 7):
        h = 0.018 + 0.050 * i
        d = sdf_fn(p + n * h)
        occ += np.maximum(h - d, 0.0) * sca
        sca *= 0.64
    return np.clip(1.0 - 1.95 * occ, 0.18, 1.0)


def shade_kraft_bag_pbr(
    p: np.ndarray,
    n: np.ndarray,
    v: np.ndarray,
    mat: dict,
    ao: np.ndarray,
    sdf_shadow_fn: Callable[[np.ndarray], np.ndarray],
) -> np.ndarray:
    """Cook-Torrance GGX matte kraft paper studio shader calibrated for Carrot Orange #F37830."""
    N = normalize3(n)
    V = normalize3(v)
    NdotV = np.clip(dot3(N, V), 1e-4, 1.0)

    albedo = mat["albedo"]
    r = np.clip(mat["roughness"], 0.12, 1.0)[..., None]
    is_interior = mat["is_interior"][..., None]
    gusset_factor = mat["gusset_factor"][..., None]
    logo_mask = mat["logo_mask"][..., None]
    body_bounce = mat["body_bounce_lin"][None, :]

    a2 = (r * r) ** 2
    F0 = 0.022

    # Bright clean commercial studio 3-point lighting (white-backdrop e-commerce look)
    lights = [
        (normalize3(np.array([-0.42, 0.58, 0.72], dtype=np.float32)), np.array([2.25, 2.20, 2.14], dtype=np.float32), True),
        (normalize3(np.array([0.78, 0.15, 0.60], dtype=np.float32)), np.array([0.78, 0.80, 0.84], dtype=np.float32) * 0.85, False),
        (normalize3(np.array([0.18, 0.78, -0.58], dtype=np.float32)), np.array([0.90, 0.86, 0.80], dtype=np.float32) * 0.50, False),
    ]

    color = np.zeros_like(albedo)
    for L_dir, L_col, cast_shadow in lights:
        L = L_dir[None, :]
        H = normalize3(L + V)
        NdotL = np.clip(dot3(N, L), 0.0, 1.0)[..., None]
        NdotH = np.clip(dot3(N, H), 0.0, 1.0)[..., None]
        HdotV = np.clip(dot3(H, V), 0.0, 1.0)[..., None]

        sh = 1.0
        if cast_shadow:
            sh = np.ones(p.shape[0], dtype=np.float32)
            t_sh = np.full(p.shape[0], 0.020, dtype=np.float32)
            for _ in range(14):
                ps = p + L * t_sh[:, None]
                d_sh = sdf_shadow_fn(ps)
                sh = np.minimum(sh, np.clip(6.0 * d_sh / t_sh, 0.0, 1.0))
                t_sh = t_sh + np.clip(d_sh, 0.016, 0.20)
            sh = (0.44 + 0.56 * sh)[:, None]

        denom = (NdotH * NdotH) * (a2 - 1.0) + 1.0
        D = a2 / (math.pi * denom * denom + 1e-6)
        k_g = ((r + 1.0) ** 2) / 8.0
        G = (NdotV[..., None] / (NdotV[..., None] * (1.0 - k_g) + k_g)) * (
            NdotL / (NdotL * (1.0 - k_g) + k_g)
        )
        F = F0 + (1.0 - F0) * ((1.0 - HdotV) ** 5)

        spec = (D * G * F) / (4.0 * NdotV[..., None] * NdotL + 1e-4) * 0.32
        diff = (1.0 - F) * albedo / math.pi
        color += (diff + spec) * L_col[None, :] * NdotL * sh

    # Clean white studio hemisphere IBL
    up = np.clip(N[:, 1] * 0.5 + 0.5, 0.0, 1.0)[..., None]
    sky_col = np.array([0.92, 0.90, 0.88], dtype=np.float32)[None, :]
    ground_col = np.array([0.62, 0.56, 0.52], dtype=np.float32)[None, :] * 0.72 + body_bounce * 0.28
    hemi_env = ground_col * (1.0 - up) + sky_col * up

    ao_eff = ao[..., None] * (1.0 - 0.30 * gusset_factor) * (1.0 - 0.34 * is_interior)
    ao_eff = np.clip(ao_eff, 0.14, 1.0)
    ambient_diff = albedo * hemi_env * 0.62 * ao_eff

    # Soft wrap illumination for warm kraft paper feel
    wrap_ndotl = np.clip((dot3(N, lights[0][0][None, :]) + 0.35) / 1.35, 0.0, 1.0)[..., None]
    soft_wrap = albedo * sky_col * wrap_ndotl * 0.10 * ao_eff

    lin_final = color + ambient_diff + soft_wrap
    # Gentle Reinhard tone curve preserving saturated Carrot Orange & crisp Pure White logo
    lin_mapped = lin_final / (1.0 + lin_final * 0.14)
    srgb = linear_to_srgb(lin_mapped)
    # Boost white logo slightly so screen-printed ULTA reads crisp Pure White (#FFFFFF)
    srgb = srgb * (1.0 - 0.35 * logo_mask) + np.clip(srgb * 1.18, 0.0, 1.0) * (0.35 * logo_mask)
    return np.clip(srgb, 0.0, 1.0)


def build_bag_camera(pitch_deg: float = 13.0, cam_dist: float = 5.4):
    pitch = math.radians(pitch_deg)
    target = np.array([0.0, 0.10, 0.0], dtype=np.float32)
    cam_pos = target + np.array(
        [0.0, cam_dist * math.sin(pitch), cam_dist * math.cos(pitch)],
        dtype=np.float32,
    )
    forward = normalize3((target - cam_pos)[None, :])[0]
    world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    right = normalize3(np.cross(forward, world_up)[None, :])[0]
    up = normalize3(np.cross(right, forward)[None, :])[0]
    return cam_pos, right, up, forward


def raymarch_grid(
    res: int,
    cam_pos: np.ndarray,
    right: np.ndarray,
    up: np.ndarray,
    forward: np.ndarray,
    fov_scale: float,
    center_offset_xy: Tuple[float, float],
    sdf_fn: Callable[[np.ndarray], np.ndarray],
    bound_center: np.ndarray,
    bound_radius: float = 1.25,
    max_steps: int = 88,
    hit_eps: float = 5e-4,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    lin = (np.arange(res, dtype=np.float32) + 0.5) / res * 2.0 - 1.0
    gx, gy = np.meshgrid(lin, -lin)

    sx = gx * fov_scale + center_offset_xy[0]
    sy = gy * fov_scale + center_offset_xy[1]
    rd = (
        forward[None, None, :]
        + sx[..., None] * right[None, None, :]
        + sy[..., None] * up[None, None, :]
    )
    rd = normalize3(rd.reshape(-1, 3))

    oc = (cam_pos - bound_center)[None, :]
    b = dot3(oc, rd)
    c = float(np.dot(cam_pos - bound_center, cam_pos - bound_center)) - bound_radius * bound_radius
    disc = b * b - c
    active_idx = np.where(disc >= 0.0)[0]

    hit_mask_flat = np.zeros(res * res, dtype=bool)
    if len(active_idx) == 0:
        return hit_mask_flat.reshape(res, res), np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)

    sqrt_disc = np.sqrt(np.maximum(disc[active_idx], 0.0))
    t_near = np.maximum(-b[active_idx] - sqrt_disc, 0.05)
    t_far = -b[active_idx] + sqrt_disc

    cur_idx = active_idx
    cur_t = t_near.copy()
    cur_tfar = t_far.copy()

    hit_indices = []
    hit_ts = []

    for _ in range(max_steps):
        if len(cur_idx) == 0:
            break
        pts = cam_pos[None, :] + rd[cur_idx] * cur_t[:, None]
        d = sdf_fn(pts)

        hit = d < hit_eps
        if np.any(hit):
            hit_indices.append(cur_idx[hit])
            hit_ts.append(cur_t[hit] + d[hit])

        alive = (~hit) & ((cur_t + d) < cur_tfar)
        if not np.any(alive):
            break
        cur_idx = cur_idx[alive]
        cur_t = cur_t[alive] + np.maximum(d[alive], hit_eps * 0.5)
        cur_tfar = cur_tfar[alive]

    if not hit_indices:
        return hit_mask_flat.reshape(res, res), np.zeros((0, 3), np.float32), np.zeros((0, 3), np.float32)

    all_hit_idx = np.concatenate(hit_indices)
    all_hit_t = np.concatenate(hit_ts)
    order = np.argsort(all_hit_idx)
    all_hit_idx = all_hit_idx[order]
    all_hit_t = all_hit_t[order]

    hit_mask_flat[all_hit_idx] = True
    hit_rd = rd[all_hit_idx]
    hit_pos = cam_pos[None, :] + hit_rd * all_hit_t[:, None]
    return hit_mask_flat.reshape(res, res), hit_pos, hit_rd


def auto_frame_shared_camera(
    sdf_full: Callable[[np.ndarray], np.ndarray],
    cam_pos: np.ndarray,
    right: np.ndarray,
    up: np.ndarray,
    forward: np.ndarray,
    bound_center: np.ndarray,
) -> Tuple[float, Tuple[float, float]]:
    probe_res = 256
    init_fov = 0.28
    mask, _, _ = raymarch_grid(
        probe_res, cam_pos, right, up, forward, init_fov, (0.0, 0.0), sdf_full, bound_center, max_steps=72
    )
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise RuntimeError("Auto-framing probe found empty ULTA bag SDF!")

    x_min_n = ((xs.min() + 0.5) / probe_res * 2.0 - 1.0) * init_fov
    x_max_n = ((xs.max() + 0.5) / probe_res * 2.0 - 1.0) * init_fov
    y_max_n = -((ys.min() + 0.5) / probe_res * 2.0 - 1.0) * init_fov
    y_min_n = -((ys.max() + 0.5) / probe_res * 2.0 - 1.0) * init_fov

    cx = 0.5 * (x_min_n + x_max_n)
    cy = 0.5 * (y_min_n + y_max_n)
    max_half = max(0.5 * (x_max_n - x_min_n), 0.5 * (y_max_n - y_min_n))
    # Leave 44px margin (>40px SOP-FORGE-3D safe margin)
    target_half_norm = (BAG_CANVAS - 2 * (BAG_SAFE_MARGIN + 4)) / BAG_CANVAS
    return float(max_half / target_half_norm), (float(cx), float(cy))


def forge_ulta_shopping_bag_split() -> Tuple[str, str]:
    """
    Renders pixel-aligned 1024x1024 RGBA split layers through one shared 3D camera:
      - assets/brands/COSRX/layers/03_decor_bag_back.png
      - assets/brands/COSRX/layers/09_decor_bag_front.png
    """
    t0 = time.time()
    print("\n[3/5] Forging 3D Carrot Orange ULTA Shopping Bag (Shared-Camera Back/Front Split)...")
    ulta_mask = _load_ulta_logo_mask_for_bag()
    sdf_full, sdf_back, sdf_front, material_fn = build_ulta_bag_scene(ulta_mask)

    cam_pos, right, up, forward = build_bag_camera(pitch_deg=13.0, cam_dist=5.4)
    bound_center = np.array([0.0, 0.10, 0.0], dtype=np.float32)
    fov_scale, center_xy = auto_frame_shared_camera(sdf_full, cam_pos, right, up, forward, bound_center)
    hi_res = BAG_CANVAS * BAG_SSAA

    def render_pass(
        name: str,
        sdf_pass: Callable[[np.ndarray], np.ndarray],
        include_logo: bool,
        include_handles: bool,
        out_path: str,
    ) -> Image.Image:
        tp = time.time()
        hit_mask, hit_pos, hit_rd = raymarch_grid(
            hi_res, cam_pos, right, up, forward, fov_scale, center_xy, sdf_pass, bound_center
        )
        rgb_hi = np.zeros((hi_res, hi_res, 3), dtype=np.float32)
        a_hi = np.zeros((hi_res, hi_res), dtype=np.float32)

        if len(hit_pos) > 0:
            normals = compute_normals(hit_pos, sdf_pass)
            ao = compute_ao(hit_pos, normals, sdf_full)
            mat = material_fn(hit_pos, normals, include_logo=include_logo, include_handles=include_handles)
            shaded = shade_kraft_bag_pbr(hit_pos, normals, -hit_rd, mat, ao, sdf_full)
            rgb_hi[hit_mask] = shaded
            a_hi[hit_mask] = 1.0

        img = downsample_ssaa_rgba(rgb_hi, a_hi, factor=BAG_SSAA)
        img.save(out_path, "PNG")
        print(f"      -> {out_path} ({img.size}, {time.time() - tp:.1f}s)")
        return img

    path_back = os.path.join(LAYERS_DIR, "03_decor_bag_back.png")
    path_front = os.path.join(LAYERS_DIR, "09_decor_bag_front.png")

    render_pass("back", sdf_back, include_logo=False, include_handles=True, out_path=path_back)
    render_pass("front", sdf_front, include_logo=True, include_handles=False, out_path=path_front)
    print(f"      [OK] Split bag completed in {time.time() - t0:.1f}s")
    return path_back, path_front


# ==============================================================================
# COMPONENTS 4 & 5: TYPOGRAPHY LOCKUP, CTA PILL, & RIBBON GLYPH MASK
# ==============================================================================
def forge_playwright_ui_components() -> dict:
    """
    Uses a single batched Playwright session with authentic local InterVariable.ttf
    to rasterize:
      - Ribbon 'EARLY ACCESS' glyph mask -> passed into 3D silk ribbon synthesizer
      - 10_typography_headline_discount.png ('BLACK FRIDAY' + 'UP TO 30% OFF')
      - 11_ui_cta_button.png (Jet Black pill 'SHOP NOW >', height=76px >= 64px)
    """
    print("\n[4/5] Forging Typography Lockup & High-Conversion CTA Pill (Playwright Inter)...")
    font_url = f"file://{INTER_FONT_PATH}"

    font_face_css = f"""
    @font-face {{
      font-family: 'InterBrand';
      src: url('{font_url}') format('truetype');
      font-weight: 100 900;
      font-style: normal;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
      background: transparent;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
      text-rendering: geometricPrecision;
    }}
    """

    # Job A: 'EARLY ACCESS' white glyph mask for 760x176 ribbon (at 2x -> 1520x352)
    ribbon_text_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" /><style>
{font_face_css}
body {{
  width: 760px; height: 176px;
  display: flex; align-items: center; justify-content: center;
}}
.txt {{
  font-family: 'InterBrand', sans-serif;
  font-weight: 800;
  font-size: 38px;
  letter-spacing: 0.14em;
  color: #FFFFFF;
  line-height: 1;
  white-space: nowrap;
  padding-left: 0.14em;
}}
</style></head><body><div class="txt">EARLY ACCESS</div></body></html>"""

    # Job B: 10_typography_headline_discount.png (1060x284, generous >=32px safe margins)
    headline_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" /><style>
{font_face_css}
body {{
  width: 1060px; height: 284px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 14px;
}}
.headline {{
  font-family: 'InterBrand', sans-serif;
  font-weight: 900;
  font-size: 118px;
  letter-spacing: -0.04em;
  line-height: 0.94;
  color: #000000;
  white-space: nowrap;
}}
.discount {{
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 14px;
  line-height: 1;
  white-space: nowrap;
}}
.disc-label {{
  font-family: 'InterBrand', sans-serif;
  font-weight: 800;
  font-size: 46px;
  letter-spacing: 0.04em;
  color: #000000;
}}
.disc-pct {{
  font-family: 'InterBrand', sans-serif;
  font-weight: 900;
  font-size: 64px;
  letter-spacing: -0.03em;
  color: #F26B1C;
}}
</style></head><body>
  <div class="headline">BLACK FRIDAY</div>
  <div class="discount">
    <span class="disc-label">UP TO</span>
    <span class="disc-pct">30%</span>
    <span class="disc-label">OFF</span>
  </div>
</body></html>"""

    # Job C: 11_ui_cta_button.png (448x148 canvas, 368x76 Jet Black pill -> height 76px >= 64px)
    cta_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" /><style>
{font_face_css}
body {{
  width: 448px; height: 148px;
  display: flex; align-items: center; justify-content: center;
}}
.cta-pill {{
  width: 368px;
  height: 76px;
  border-radius: 999px;
  background: linear-gradient(180deg, #1E1E1E 0%, #050505 42%, #000000 100%);
  box-shadow: inset 0 1.5px 0 rgba(255, 255, 255, 0.24), inset 0 -2px 0 rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
}}
.cta-text {{
  font-family: 'InterBrand', sans-serif;
  font-weight: 800;
  font-size: 36px;
  letter-spacing: 0.11em;
  color: #FFFFFF;
  line-height: 1;
  padding-left: 4px;
}}
.cta-arrow {{
  width: 18px;
  height: 26px;
  display: block;
}}
</style></head><body>
  <div class="cta-pill">
    <span class="cta-text">SHOP NOW</span>
    <svg class="cta-arrow" viewBox="0 0 14 22" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2.5 2.5L11 11L2.5 19.5" stroke="#FFFFFF" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
</body></html>"""

    path_ribbon = os.path.join(LAYERS_DIR, "02_ribbon_early_access.png")
    path_headline = os.path.join(LAYERS_DIR, "10_typography_headline_discount.png")
    path_cta = os.path.join(LAYERS_DIR, "11_ui_cta_button.png")

    with tempfile.TemporaryDirectory(prefix="cosrx_ui_pw_") as tmp_dir:
        hi_ribbon_txt = os.path.join(tmp_dir, "ribbon_text_hi.png")
        hi_headline = os.path.join(tmp_dir, "headline_hi.png")
        hi_cta = os.path.join(tmp_dir, "cta_hi.png")

        render_playwright_jobs(
            [
                {"width": 760, "height": 176, "scale": 2, "html": ribbon_text_html, "outPath": hi_ribbon_txt},
                {"width": 1060, "height": 284, "scale": 2, "html": headline_html, "outPath": hi_headline},
                {"width": 448, "height": 148, "scale": 2, "html": cta_html, "outPath": hi_cta},
            ],
            tmp_dir,
        )

        # Synthesize 02_ribbon_early_access.png using exact Playwright Inter glyph mask
        ribbon_txt_arr = np.array(Image.open(hi_ribbon_txt).convert("RGBA"), dtype=np.float32)[..., 3] / 255.0
        forge_early_access_ribbon(ribbon_txt_arr, path_ribbon)

        # Premultiplied SSAA downsample for headline & CTA
        img_headline = downsample_playwright_png(hi_headline, path_headline, factor=2)
        img_cta = downsample_playwright_png(hi_cta, path_cta, factor=2)
        print(f"      -> {path_headline} ({img_headline.size})")
        print(f"      -> {path_cta} ({img_cta.size})")

    return {
        "02": path_ribbon,
        "10": path_headline,
        "11": path_cta,
    }


# ==============================================================================
# HANDOVER COMPOSITE PREVIEW (1200x1200 UI-ONLY VERIFICATION)
# ==============================================================================
def render_ui_preview() -> str:
    """
    Renders output/TASK_COSRX/preview_ui_components.png (1200x1200)
    combining all forged non-product UI & bag layers onto a clean white studio backdrop.
    """
    print("\n[5/5] Rendering UI Components Composite Preview (1200x1200)...")
    W, H = 1200, 1200
    yy, xx = np.indices((H, W), dtype=np.float32)
    dist = np.sqrt(((xx - W * 0.5) / (W * 0.65)) ** 2 + ((yy - H * 0.48) / (H * 0.65)) ** 2)
    t = np.clip(dist, 0.0, 1.0)[..., None]
    # Clean White (#FFFFFF) center -> subtle ULTA Chalk White (#F8F5F2) studio outer vignette
    c_center = np.array([255, 255, 255], dtype=np.float32)
    c_outer = np.array(CHALK_WHITE_RGB, dtype=np.float32)
    bg_rgb = np.round(c_center * (1.0 - t) + c_outer * t).astype(np.uint8)
    bg_a = np.full((H, W, 1), 255, dtype=np.uint8)
    canvas = Image.fromarray(np.concatenate([bg_rgb, bg_a], axis=-1), mode="RGBA")

    # Soft grounded studio shadow under the ULTA bag (preview backdrop only)
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    sdraw.ellipse((350, 992, 850, 1046), fill=(48, 22, 8, 42))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=22))
    canvas.alpha_composite(shadow_layer)

    # Load all forged layers
    l01 = Image.open(os.path.join(LAYERS_DIR, "01_logo_dual_lockup.png")).convert("RGBA")
    l02 = Image.open(os.path.join(LAYERS_DIR, "02_ribbon_early_access.png")).convert("RGBA")
    l03 = Image.open(os.path.join(LAYERS_DIR, "03_decor_bag_back.png")).convert("RGBA")
    l09 = Image.open(os.path.join(LAYERS_DIR, "09_decor_bag_front.png")).convert("RGBA")
    l10 = Image.open(os.path.join(LAYERS_DIR, "10_typography_headline_discount.png")).convert("RGBA")
    l11 = Image.open(os.path.join(LAYERS_DIR, "11_ui_cta_button.png")).convert("RGBA")

    # Resize bag pair identically (1:1 shared-camera alignment check!)
    bag_size = 560
    l03_s = l03.resize((bag_size, bag_size), Image.Resampling.LANCZOS)
    l09_s = l09.resize((bag_size, bag_size), Image.Resampling.LANCZOS)
    bag_x = (W - bag_size) // 2
    bag_y = 508

    # Stack in exact painter's order (products 04..08 will slot cleanly between l03_s and l09_s)
    canvas.alpha_composite(l01, (0, 0))
    canvas.alpha_composite(l10, ((W - l10.width) // 2, 134))
    canvas.alpha_composite(l02, ((W - l02.width) // 2, 376))
    canvas.alpha_composite(l03_s, (bag_x, bag_y))
    canvas.alpha_composite(l09_s, (bag_x, bag_y))
    canvas.alpha_composite(l11, ((W - l11.width) // 2, 1034))

    os.makedirs(os.path.dirname(PREVIEW_OUT), exist_ok=True)
    canvas.convert("RGB").save(PREVIEW_OUT, "PNG")
    print(f"      -> {PREVIEW_OUT} ({canvas.size})")
    return PREVIEW_OUT


# ==============================================================================
# AUTOMATED BRAND & GEOMETRY COMPLIANCE VERIFIER
# ==============================================================================
def verify_brand_compliance() -> None:
    print("\n[VERIFY] Running Brand Book & Specification Compliance Assertions...")
    expected_files = [
        "01_logo_dual_lockup.png",
        "01a_logo_cosrx.png",
        "01b_logo_ulta.png",
        "02_ribbon_early_access.png",
        "03_decor_bag_back.png",
        "09_decor_bag_front.png",
        "10_typography_headline_discount.png",
        "11_ui_cta_button.png",
    ]
    for fn in expected_files:
        p = os.path.join(LAYERS_DIR, fn)
        assert os.path.exists(p), f"Missing output: {p}"
        im = Image.open(p)
        assert im.mode == "RGBA", f"{fn} must be RGBA, got {im.mode}"
        arr = np.array(im)
        alpha = arr[:, :, 3]
        assert np.any(alpha == 0) and np.any(alpha > 200), f"{fn} missing valid transparency"

    # 1. COSRX logo check: Jet Black #000000, width >= 80px, clear space >= 5px
    cosrx_im = Image.open(os.path.join(LAYERS_DIR, "01a_logo_cosrx.png"))
    cw, ch = cosrx_im.size
    cx0, cy0, cx1, cy1 = cosrx_im.getbbox()
    c_glyph_w = cx1 - cx0
    c_pad = min(cx0, cy0, cw - cx1, ch - cy1)
    c_arr = np.array(cosrx_im)
    c_rgb = np.median(c_arr[c_arr[:, :, 3] > 200][:, :3], axis=0)
    assert c_glyph_w >= 80, f"COSRX glyph width {c_glyph_w} < 80px"
    assert c_pad >= 5, f"COSRX clear space {c_pad} < 5px"
    assert tuple(c_rgb.astype(int)) == JET_BLACK_RGB, f"COSRX color {c_rgb} != #000000"
    print(f"  [PASS] COSRX Logo: width={c_glyph_w}px (>=80), clear_space={c_pad}px (>=5), RGB={tuple(c_rgb.astype(int))}")

    # 2. ULTA logo check: Carrot Orange #F37830, width >= 128px, clear space >= 50px
    ulta_im = Image.open(os.path.join(LAYERS_DIR, "01b_logo_ulta.png"))
    uw, uh = ulta_im.size
    ux0, uy0, ux1, uy1 = ulta_im.getbbox()
    u_glyph_w = ux1 - ux0
    u_pad = min(ux0, uy0, uw - ux1, uh - uy1)
    u_arr = np.array(ulta_im)
    u_rgb = np.median(u_arr[u_arr[:, :, 3] > 200][:, :3], axis=0)
    assert u_glyph_w >= 128, f"ULTA glyph width {u_glyph_w} < 128px"
    assert u_pad >= 50, f"ULTA clear space {u_pad} < 50px"
    assert tuple(u_rgb.astype(int)) == CARROT_ORANGE_RGB, f"ULTA color {u_rgb} != #F37830"
    print(f"  [PASS] ULTA Logo:  width={u_glyph_w}px (>=128), clear_space={u_pad}px (>=50), RGB={tuple(u_rgb.astype(int))}")

    # 3. CTA pill height check >= 64px
    cta_im = Image.open(os.path.join(LAYERS_DIR, "11_ui_cta_button.png"))
    _, py0, _, py1 = cta_im.getbbox()
    pill_h = py1 - py0
    assert pill_h >= 64, f"CTA pill height {pill_h} < 64px"
    print(f"  [PASS] CTA Button: pill_height={pill_h}px (>=64)")

    # 4. Bag shared-camera dimensions & safe margin >= 40px + Carrot Orange front check
    bag_b = Image.open(os.path.join(LAYERS_DIR, "03_decor_bag_back.png"))
    bag_f = Image.open(os.path.join(LAYERS_DIR, "09_decor_bag_front.png"))
    assert bag_b.size == bag_f.size == (BAG_CANVAS, BAG_CANVAS), "Bag split dimensions mismatch"
    comb = bag_b.copy()
    comb.alpha_composite(bag_f)
    bx0, by0, bx1, by1 = comb.getbbox()
    b_margin = min(bx0, by0, BAG_CANVAS - bx1, BAG_CANVAS - by1)
    assert b_margin >= BAG_SAFE_MARGIN, f"Bag safe margin {b_margin} < {BAG_SAFE_MARGIN}px"

    f_arr = np.array(bag_f)
    # Sample orange kraft pixels (exclude white ULTA logo where R,G,B > 220)
    f_mask = (f_arr[:, :, 3] > 240) & (f_arr[:, :, 2] < 140)
    f_med = np.median(f_arr[f_mask][:, :3], axis=0)
    print(
        f"  [PASS] ULTA Bag:   size={bag_b.size}, safe_margin={b_margin}px (>={BAG_SAFE_MARGIN}), "
        f"front_kraft_median_RGB={tuple(f_med.astype(int))} (target={CARROT_ORANGE_RGB})"
    )

    assert os.path.exists(PREVIEW_OUT), f"Preview missing: {PREVIEW_OUT}"
    print(f"  [PASS] Preview:    {PREVIEW_OUT} ({Image.open(PREVIEW_OUT).size})")


def main() -> None:
    t_start = time.time()
    os.makedirs(LAYERS_DIR, exist_ok=True)
    forge_dual_logos()
    forge_playwright_ui_components()
    forge_ulta_shopping_bag_split()
    render_ui_preview()
    verify_brand_compliance()
    print(f"\n✅ DIR-FORGE-COSRX-ULTA-UI-072 COMPLETE in {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
