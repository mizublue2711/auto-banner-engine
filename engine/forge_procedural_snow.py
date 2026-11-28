#!/usr/bin/env python3
"""
DIR-PHASE1-SNOW-AND-DIR-026: 3-Tier Procedural Snow System Forge
Project: auto-banner-engine (GS SHOP Master Banner Upgrade — Phase 1)

Synthesizes 3 luxurious 1080x1080 native RGBA (Alpha=0) procedural snow layers
using multi-octave 2D Perlin gradient noise (fBm), domain warping, heightfield
normal shading, subsurface cool-ambient light absorption (#D9E6F2 / #E2E8F0 to
#F0F9FF / #FFFFFF), and micro-granular crystalline sparkle scattering:

  1. assets/brands/gsshop/layers/snow_tier_1_back_blur.png
     - Behind gift box (lower-mid zone), soft rolling snow dunes,
       cool ambient blue-tinted white (#D9E6F2), optical Gaussian blur (~12px).
  2. assets/brands/gsshop/layers/snow_tier_2_box_bed.png
     - Directly beneath and cradling the gift box base, crisp powdery foreground-
       middle snow ground with physical box depression (snow pocket), displaced
       snow berm, micro-texture noise, and soft ambient contact shadow.
  3. assets/brands/gsshop/layers/snow_tier_3_front_blur.png
     - In front of box base / right behind CTA button, gentle wavy snow drift
       crowning bottom ~140px, brighter luminous snow (#FFFFFF + #F0F9FF),
       subtle optical Gaussian blur (~5px).

Dual-Delivery Sync:
  Copies all 3 generated PNGs into showcase_site/assets/cutouts/gsshop/.

Visual Verification Preview:
  Saves a dark-background 2x2 inspection sheet strictly inside
  output/TASK_GSSHOP/snow_3tier_preview_dark.png.
"""

from __future__ import annotations

import math
import os
import shutil
import time
from typing import Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

# ==============================================================================
# LOCKED PATHS & CANVAS CONSTANTS
# ==============================================================================
CANVAS_W = 1080
CANVAS_H = 1080

LAYERS_OUT_DIR = os.path.join("assets", "brands", "gsshop", "layers")
SHOWCASE_SYNC_DIR = os.path.join("showcase_site", "assets", "cutouts", "gsshop")
TASK_OUTPUT_DIR = os.path.join("output", "TASK_GSSHOP")

TIER_FILES = (
    "snow_tier_1_back_blur.png",
    "snow_tier_2_box_bed.png",
    "snow_tier_3_front_blur.png",
)

# Color Palette (sRGB 0..1)
HEX = lambda r, g, b: np.array([r, g, b], dtype=np.float32) / 255.0

COL_SSS_ICE_EDGE = HEX(224, 242, 254)    # #E0F2FE (SSS translucent ice-snow edge, zero muddy gray)

COL_TIER1_SHADOW = HEX(198, 221, 242)    # Clean cool atmospheric dune valley
COL_TIER1_MID = HEX(217, 230, 242)       # #D9E6F2 (Spec target)
COL_TIER1_CREST = HEX(238, 246, 253)     # Soft cool rim highlight

COL_TIER2_DEEP_SHADOW = HEX(175, 206, 236)  # Clean ice-blue contact AO (zero muddy gray)
COL_TIER2_SHADOW = HEX(187, 214, 242)       # #BBD6F2 pastel blue trough shadow
COL_TIER2_MID = HEX(220, 235, 250)          # #DCEBFA pastel slope transition
COL_TIER2_CREST = HEX(255, 255, 255)        # #FFFFFF sunlit powder
COL_TIER2_ICE = HEX(240, 249, 255)          # #F0F9FF ice tint

COL_TIER3_SHADOW = HEX(187, 214, 242)       # #BBD6F2 pastel blue trough & slope shadow
COL_TIER3_ICE = HEX(220, 235, 250)          # #DCEBFA soft pastel snow mid-tone
COL_TIER3_CREST = HEX(255, 255, 255)        # #FFFFFF luminous sunlit crest


# ==============================================================================
# VECTORIZED 2D PERLIN NOISE & fBm ENGINE (PURE NUMPY)
# ==============================================================================
def _fade(t: np.ndarray) -> np.ndarray:
    """Quintic Perlin smoothstep 6t^5 - 15t^4 + 10t^3."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin2d(
    h: int,
    w: int,
    res_y: int,
    res_x: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Fast vectorized 2D Perlin gradient noise over an (h, w) grid with
    (res_y, res_x) lattice cells. Returns float32 array roughly in [-1, 1].
    """
    angles = rng.uniform(0.0, 2.0 * math.pi, size=(res_y + 2, res_x + 2))
    grad_x = np.cos(angles).astype(np.float32)
    grad_y = np.sin(angles).astype(np.float32)

    gy = np.linspace(0.0, float(res_y), h, endpoint=False, dtype=np.float32)
    gx = np.linspace(0.0, float(res_x), w, endpoint=False, dtype=np.float32)

    iy = np.floor(gy).astype(np.int32)
    ix = np.floor(gx).astype(np.int32)
    fy = (gy - iy)[:, None]
    fx = (gx - ix)[None, :]

    u = _fade(fx)
    v = _fade(fy)

    iy0 = iy[:, None]
    iy1 = iy0 + 1
    ix0 = ix[None, :]
    ix1 = ix0 + 1

    n00 = grad_x[iy0, ix0] * fx + grad_y[iy0, ix0] * fy
    n10 = grad_x[iy0, ix1] * (fx - 1.0) + grad_y[iy0, ix1] * fy
    n01 = grad_x[iy1, ix0] * fx + grad_y[iy1, ix0] * (fy - 1.0)
    n11 = grad_x[iy1, ix1] * (fx - 1.0) + grad_y[iy1, ix1] * (fy - 1.0)

    nx0 = n00 * (1.0 - u) + n10 * u
    nx1 = n01 * (1.0 - u) + n11 * u
    out = nx0 * (1.0 - v) + nx1 * v
    return (out * 1.4142135).astype(np.float32)


def fbm2d(
    h: int,
    w: int,
    octaves: Sequence[Tuple[int, int, float]],
    rng: np.random.Generator,
) -> np.ndarray:
    """Multi-octave Perlin fractional Brownian motion normalized to [0, 1]."""
    acc = np.zeros((h, w), dtype=np.float32)
    total_w = 0.0
    for ry, rx, weight in octaves:
        acc += weight * perlin2d(h, w, ry, rx, rng)
        total_w += weight
    acc /= max(total_w, 1e-6)
    return np.clip(0.5 + 0.5 * acc, 0.0, 1.0)


def smoothstep(edge0, edge1, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / np.maximum(edge1 - edge0, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def premul_gaussian_blur(
    rgb: np.ndarray,
    alpha: np.ndarray,
    sigma: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """Optical Gaussian blur in premultiplied RGBA space (zero dark halo)."""
    a = np.clip(alpha, 0.0, 1.0).astype(np.float32)
    premul = np.clip(rgb, 0.0, 1.0).astype(np.float32) * a[..., None]

    a_b = gaussian_filter(a, sigma=sigma, mode="constant", cval=0.0)
    out_premul = np.empty_like(premul)
    for c in range(3):
        out_premul[..., c] = gaussian_filter(
            premul[..., c], sigma=sigma, mode="constant", cval=0.0
        )

    out_rgb = np.where(
        a_b[..., None] > 1e-5,
        out_premul / np.maximum(a_b[..., None], 1e-5),
        0.0,
    )
    return np.clip(out_rgb, 0.0, 1.0), np.clip(a_b, 0.0, 1.0)


def apply_safe_border_feather(
    alpha: np.ndarray,
    margin_zero: int = 14,
    feather_px: int = 52,
    bottom_feather_px: int = 34,
) -> np.ndarray:
    """
    Smoothly tapers alpha to 0.0 before reaching the outermost canvas margin.
    Uses a generous organic side/bottom feather so snow banks never look boxy,
    while strictly guaranteeing:
      - 0 clipped pixels on the 1px outer canvas border (alpha == 0)
      - 0 corner artifacts in all four 10x10 corners (alpha == 0).
    """
    h, w = alpha.shape
    y = np.arange(h, dtype=np.float32)[:, None]
    x = np.arange(w, dtype=np.float32)[None, :]

    left_f = smoothstep(float(margin_zero), float(margin_zero + feather_px), x)
    right_f = smoothstep(
        float(margin_zero), float(margin_zero + feather_px), (w - 1.0) - x
    )
    top_f = smoothstep(float(margin_zero), float(margin_zero + 24), y)
    bot_f = smoothstep(
        float(margin_zero), float(margin_zero + bottom_feather_px), (h - 1.0) - y
    )

    env = left_f * right_f * top_f * bot_f
    out = alpha * env
    # Hard guarantee: zero inside margin_zero (covers 1px border + 10x10 corners)
    out[:margin_zero, :] = 0.0
    out[h - margin_zero :, :] = 0.0
    out[:, :margin_zero] = 0.0
    out[:, w - margin_zero :] = 0.0
    return np.clip(out, 0.0, 1.0)


def shade_snow_heightfield(
    height: np.ndarray,
    col_shadow: np.ndarray,
    col_mid: np.ndarray,
    col_crest: np.ndarray,
    rng: np.random.Generator,
    normal_strength: float = 18.0,
    sparkle_strength: float = 0.28,
    micro_grain_strength: float = 0.045,
) -> np.ndarray:
    """
    Physically-inspired powdery snow shader:
      - Surface normals from heightfield gradient
      - Upper-left winter key light with subsurface scattering (wrap diffuse)
      - Cool ambient shadow absorption -> sunlit luminous crests
      - Multi-scale micro-granular powder scattering + crystalline sparkles
    """
    h, w = height.shape
    gy, gx = np.gradient(height)
    nx = -gx * normal_strength
    ny = -gy * normal_strength
    nz = np.ones_like(height, dtype=np.float32)
    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    nx *= inv_len
    ny *= inv_len
    nz *= inv_len

    # Key light from upper-left-front (matching GS SHOP gift box & hero lighting)
    lx, ly, lz = -0.42, -0.58, 0.70
    l_norm = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / l_norm, ly / l_norm, lz / l_norm

    ndotl = nx * lx + ny * ly + nz * lz
    # Subsurface scattering wrap diffuse (snow scatters light softly into shadows)
    diff_wrap = np.clip((ndotl + 0.52) / 1.52, 0.0, 1.0)
    # Softly bias with height so elevated crests catch more sky dome light
    sky_lift = np.clip(0.55 * diff_wrap + 0.45 * height, 0.0, 1.0)

    # 3-stop snow color ramp (shadow -> mid -> crest)
    t_low = np.clip(sky_lift * 2.0, 0.0, 1.0)[..., None]
    t_high = np.clip((sky_lift - 0.5) * 2.0, 0.0, 1.0)[..., None]
    rgb_low = col_shadow * (1.0 - t_low) + col_mid * t_low
    rgb = np.where(
        sky_lift[..., None] < 0.5,
        rgb_low,
        col_mid * (1.0 - t_high) + col_crest * t_high,
    )

    # Micro-granular powdery scattering (high-frequency tactile grain)
    if micro_grain_strength > 0.0:
        grain_fine = rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)
        grain_soft = gaussian_filter(grain_fine, sigma=0.75)
        # Cool-tinted micro shadow vs bright micro facet
        grain_delta = grain_soft * micro_grain_strength
        rgb[..., 0] = np.clip(rgb[..., 0] + grain_delta * 1.05, 0.0, 1.0)
        rgb[..., 1] = np.clip(rgb[..., 1] + grain_delta * 0.95, 0.0, 1.0)
        rgb[..., 2] = np.clip(rgb[..., 2] + grain_delta * 0.70, 0.0, 1.0)

    # Crystalline ice-sparkle glints (sparse bright facets on sunlit slopes)
    if sparkle_strength > 0.0:
        crystal_seed = rng.random((h, w), dtype=np.float32)
        glint_raw = np.where(crystal_seed > 0.9925, (crystal_seed - 0.9925) / 0.0075, 0.0)
        # Soften slightly into tiny physical crystal highlights
        glint = gaussian_filter(glint_raw.astype(np.float32), sigma=0.65)
        glint = np.clip(glint * 4.5, 0.0, 1.0) * smoothstep(0.38, 0.85, diff_wrap)
        rgb = rgb + (glint * sparkle_strength)[..., None] * (
            np.array([1.0, 1.0, 1.0], dtype=np.float32) - rgb
        )

    return np.clip(rgb, 0.0, 1.0)


def apply_sss_ice_edge(
    rgb: np.ndarray,
    alpha: np.ndarray,
    strength: float = 0.88,
) -> np.ndarray:
    """
    Subsurface Scattering (SSS) edge color transition:
    In the semi-transparent snow feathering band (0 < alpha < 0.94), smoothly
    transitions edge RGB toward pure ice-snow #E0F2FE as alpha -> 0 so edges
    glow like translucent backlit snow and NEVER turn muddy gray.
    """
    edge_t = (1.0 - smoothstep(0.04, 0.94, alpha)) * strength
    out = rgb * (1.0 - edge_t[..., None]) + COL_SSS_ICE_EDGE * edge_t[..., None]
    return np.clip(out, 0.0, 1.0)


def frayed_top_alpha_mask(
    yy: np.ndarray,
    ridge_y: np.ndarray,
    noise_meso: np.ndarray,
    noise_micro: np.ndarray,
    feather_px: float = 18.0,
    fray_amp_px: float = 8.0,
) -> np.ndarray:
    """
    Smooth 12-20px top-edge Alpha gradient combined with multi-octave Perlin
    noise fraying ('xơ hóa mép viền') so snow horizons dissolve organically
    with zero hard cut edges.
    """
    perlin_fray = (
        (noise_meso - 0.5) * (fray_amp_px * 1.4)
        + (noise_micro - 0.5) * (fray_amp_px * 0.9)
    )
    half_f = feather_px * 0.5
    yy_frayed = yy + perlin_fray
    return smoothstep(ridge_y[None, :] - half_f, ridge_y[None, :] + half_f, yy_frayed)


def save_rgba_png(rgb: np.ndarray, alpha: np.ndarray, path: str) -> None:
    """Save native straight-alpha RGBA PNG with guaranteed zeroed RGB where Alpha==0."""
    out = np.zeros((CANVAS_H, CANVAS_W, 4), dtype=np.uint8)
    a_u8 = np.round(np.clip(alpha, 0.0, 1.0) * 255.0).astype(np.uint8)
    rgb_u8 = np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)
    out[..., :3] = rgb_u8
    out[..., 3] = a_u8
    out[a_u8 == 0] = 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(out, mode="RGBA").save(path, format="PNG", optimize=True)


# ==============================================================================
# TIER 1: BACKGROUND ROLLING SNOW DUNES (OPTICAL BLUR ~12px)
# ==============================================================================
def build_tier_1_back_blur(rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """
    Behind the gift box (lower-mid zone):
    Soft rolling snow dune silhouettes in cool ambient blue-tinted white (#D9E6F2)
    with ~12px optical Gaussian blur for focal depth.
    """
    yy, xx = np.mgrid[0:CANVAS_H, 0:CANVAS_W].astype(np.float32)
    xn = np.arange(CANVAS_W, dtype=np.float32) / CANVAS_W  # 1D (0..1)

    # Multi-octave procedural snow texture
    noise_macro = fbm2d(CANVAS_H, CANVAS_W, [(3, 4, 0.55), (6, 8, 0.30), (14, 18, 0.15)], rng)
    noise_micro = fbm2d(CANVAS_H, CANVAS_W, [(32, 32, 0.6), (72, 72, 0.4)], rng)

    # Two overlapping rolling background dune profiles framing the gift box
    # Curve down softly near outer left/right edges so silhouettes feel organic
    edge_drop = 58.0 * np.exp(-((xn - 0.0) / 0.11) ** 2) + 58.0 * np.exp(-((xn - 1.0) / 0.11) ** 2)

    # Far-back rolling dune (left & right gentle peaks, dipping behind the box center)
    ridge_far = (
        642.0
        - 86.0 * np.exp(-((xn - 0.21) / 0.22) ** 2)
        - 102.0 * np.exp(-((xn - 0.79) / 0.23) ** 2)
        + 24.0 * np.sin(xn * math.pi * 2.4 + 0.5)
        + edge_drop
        + (noise_macro[640, :] - 0.5) * 34.0
    )

    # Secondary mid-back soft swell
    ridge_mid = (
        712.0
        - 58.0 * np.exp(-((xn - 0.32) / 0.24) ** 2)
        - 64.0 * np.exp(-((xn - 0.70) / 0.24) ** 2)
        + 18.0 * np.cos(xn * math.pi * 2.6 - 0.4)
        + edge_drop * 0.8
        + (noise_macro[710, :] - 0.5) * 26.0
    )

    # Organic lower silhouette termination (behind Tier 2 & Tier 3)
    bottom_bound = 970.0 - edge_drop * 0.65 + 16.0 * np.sin(xn * math.pi * 1.8)

    # Smooth 18px Perlin-frayed top-edge alpha gradients (zero hard edges)
    mask_far = frayed_top_alpha_mask(
        yy, ridge_far, noise_macro, noise_micro, feather_px=20.0, fray_amp_px=9.0
    )
    mask_mid = frayed_top_alpha_mask(
        yy, ridge_mid, noise_macro, noise_micro, feather_px=18.0, fray_amp_px=8.0
    )
    mask_bot = 1.0 - smoothstep(bottom_bound[None, :] - 65.0, bottom_bound[None, :], yy)

    # Combine dune heightfield for atmospheric shading
    crest_dist_far = np.clip((yy - ridge_far[None, :]) / 195.0, 0.0, 1.0)
    crest_dist_mid = np.clip((yy - ridge_mid[None, :]) / 180.0, 0.0, 1.0)

    # Sunlit ridge tops transitioning into cool ambient dune troughs
    h_far = (1.0 - crest_dist_far * 0.72) * 0.62 + noise_macro * 0.28 + noise_micro * 0.10
    h_mid = (1.0 - crest_dist_mid * 0.65) * 0.76 + noise_macro * 0.16 + noise_micro * 0.08

    # Composite mid dune over far dune heightfield
    height = np.clip(h_far * (1.0 - mask_mid * 0.72) + h_mid * (mask_mid * 0.72), 0.0, 1.0)
    alpha_raw = np.clip(np.maximum(mask_far * 0.88, mask_mid * 0.96) * mask_bot, 0.0, 1.0)

    # Inset slightly before 12px optical blur so blur spreads cleanly inside canvas
    pre_blur_env = apply_safe_border_feather(
        np.ones((CANVAS_H, CANVAS_W), dtype=np.float32),
        margin_zero=24,
        feather_px=56,
        bottom_feather_px=38,
    )
    alpha_pre = alpha_raw * pre_blur_env

    rgb_raw = shade_snow_heightfield(
        height=height,
        col_shadow=COL_TIER1_SHADOW,
        col_mid=COL_TIER1_MID,
        col_crest=COL_TIER1_CREST,
        rng=rng,
        normal_strength=18.0,
        sparkle_strength=0.06,
        micro_grain_strength=0.025,
    )

    # Subtle sunlit atmospheric rim along both dune crests
    rim_band = (
        np.exp(-((yy - ridge_far[None, :] - 10.0) / 22.0) ** 2) * mask_far
        + np.exp(-((yy - ridge_mid[None, :] - 10.0) / 20.0) ** 2) * mask_mid * 0.85
    )
    rgb_raw = np.clip(
        rgb_raw + (np.clip(rim_band, 0.0, 1.0) * 0.18)[..., None] * (COL_TIER1_CREST - rgb_raw),
        0.0,
        1.0,
    )

    # Optical Gaussian blur (~12px) in premultiplied space for focal depth
    rgb_blur, alpha_blur = premul_gaussian_blur(rgb_raw, alpha_pre, sigma=12.0)

    # Final clean border feathering + #E0F2FE SSS edge glow (zero muddy gray)
    alpha_final = apply_safe_border_feather(
        alpha_blur, margin_zero=14, feather_px=56, bottom_feather_px=36
    )
    rgb_final = apply_sss_ice_edge(rgb_blur, alpha_final, strength=0.88)
    return rgb_final, alpha_final


# ==============================================================================
# PARAMETRIC 7-WAVE PROFILE (DIR-FORGE-SNOW-WAVES-041)
# 4 crests & 3 troughs alternating across 1080px full-bleed width:
#   crest_1 : x  40..160 (center 100)  - gentle left swell
#   trough_1: x 180..280 (center 230)  - soft valley
#   crest_2 : x 320..440 (center 380)  - ridge cradling left box corner
#   trough_2: x 460..620 (center 540)  - center basin hugging box bottom (~15px)
#   crest_3 : x 640..780 (center 710)  - ridge cradling right box corner
#   trough_3: x 800..900 (center 850)  - soft transition valley
#   crest_4 : x 920..1040 (center 980) - gentle right swell
# ==============================================================================
def compute_7wave_profile(
    x: np.ndarray,
    base_y: float,
    crest_amps: Tuple[float, float, float, float],
    trough_depths: Tuple[float, float, float],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns `(ridge_y, crest_mask)` over 1D pixel coordinate array `x` (0..1079).
    `ridge_y` decreases at crests (higher on canvas) and increases at troughs (lower).
    `crest_mask` is in [0, 1] peaking at the 4 crests for rim highlight modulation.
    """
    c1 = np.exp(-((x - 100.0) / 56.0) ** 2)
    t1 = np.exp(-((x - 230.0) / 52.0) ** 2)
    c2 = np.exp(-((x - 380.0) / 62.0) ** 2)
    t2 = np.exp(-((x - 540.0) / 74.0) ** 2)
    c3 = np.exp(-((x - 710.0) / 66.0) ** 2)
    t3 = np.exp(-((x - 850.0) / 52.0) ** 2)
    c4 = np.exp(-((x - 980.0) / 58.0) ** 2)

    ridge_y = (
        base_y
        - crest_amps[0] * c1
        + trough_depths[0] * t1
        - crest_amps[1] * c2
        + trough_depths[1] * t2
        - crest_amps[2] * c3
        + trough_depths[2] * t3
        - crest_amps[3] * c4
    )
    crest_mask = np.clip(c1 + c2 + c3 + c4, 0.0, 1.0)
    return ridge_y.astype(np.float32), crest_mask.astype(np.float32)


# ==============================================================================
# TIER 2: CRISP BOX BED WITH 7-WAVE HORIZON, SNOW POCKET & CONTACT SHADOW
# ==============================================================================
def build_tier_2_box_bed(rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """
    DIR-FORGE-SNOW-WAVES-041:
    Full-bleed 1080x1080 mid-ground snow bed directly beneath and behind the gift box.
    Features a soft 7-wave rolling horizon, pastel blue (#DCEBFA / #BBD6F2) trough
    shading, powdery snow granulate, and a physical snow pocket cradling the box base.
    """
    yy, xx = np.mgrid[0:CANVAS_H, 0:CANVAS_W].astype(np.float32)
    x1d = np.arange(CANVAS_W, dtype=np.float32)

    # Multi-octave powdery snow noise (macro undulations + meso ripples + micro grains)
    noise_macro = fbm2d(CANVAS_H, CANVAS_W, [(4, 6, 0.50), (9, 12, 0.32), (20, 26, 0.18)], rng)
    noise_meso = fbm2d(CANVAS_H, CANVAS_W, [(38, 44, 0.55), (84, 96, 0.45)], rng)
    noise_micro = fbm2d(CANVAS_H, CANVAS_W, [(170, 170, 0.60), (280, 280, 0.40)], rng)

    # 7-wave mid-ground snow horizon (y ≈ 842..896, full-bleed across 0..1080px)
    bed_top, crest_mask = compute_7wave_profile(
        x1d,
        base_y=874.0,
        crest_amps=(22.0, 26.0, 26.0, 20.0),
        trough_depths=(14.0, 16.0, 14.0),
    )
    bed_top = bed_top + (noise_macro[870, :] - 0.5) * 10.0

    # Smooth Perlin-frayed top-edge alpha gradient (full-bleed left/right/bottom)
    mask_top = frayed_top_alpha_mask(
        yy, bed_top, noise_meso, noise_micro, feather_px=12.0, fray_amp_px=4.5
    )
    alpha_raw = np.clip(mask_top, 0.0, 1.0)

    # --- PHYSICAL SNOW POCKET ALIGNED TO GIFT BOX BASE ---
    box_cx, box_cy = 548.0, 918.0
    theta = math.radians(-4.0)
    dx = xx - box_cx
    dy = yy - box_cy
    rx = dx * math.cos(theta) - dy * math.sin(theta)
    ry = dx * math.sin(theta) + dy * math.cos(theta)

    a_rad, b_rad = 215.0, 72.0
    pocket_r = ((np.abs(rx) / a_rad) ** 1.65 + (np.abs(ry) / b_rad) ** 1.65) ** (1.0 / 1.65)
    pocket_r_noisy = pocket_r + (noise_meso - 0.5) * 0.07

    depression = 1.0 - smoothstep(0.58, 1.08, pocket_r_noisy)
    berm = np.exp(-((pocket_r_noisy - 1.12) / 0.24) ** 2)

    # Heightfield: 7-wave lateral undulation + depth gradient + powdery micro-texture
    depth_grad = np.clip((yy - bed_top[None, :]) / 180.0, 0.0, 1.0)
    wave_height_1d = np.clip((894.0 - bed_top) / 56.0, 0.0, 1.0)
    height = (
        0.48
        + 0.26 * wave_height_1d[None, :] * (1.0 - depth_grad * 0.35)
        - 0.14 * depth_grad
        + 0.15 * (noise_macro - 0.5)
        + 0.10 * (noise_meso - 0.5)
        + 0.06 * (noise_micro - 0.5)
        - 0.32 * depression
        + 0.20 * berm
    )
    height = np.clip(height, 0.0, 1.0)

    rgb = shade_snow_heightfield(
        height=height,
        col_shadow=COL_TIER2_SHADOW,
        col_mid=COL_TIER2_MID,
        col_crest=COL_TIER2_CREST,
        rng=rng,
        normal_strength=28.0,
        sparkle_strength=0.42,
        micro_grain_strength=0.052,
    )

    # Soft pastel-blue ambient contact shadow in the box pocket
    shadow_core = 1.0 - smoothstep(0.42, 1.04, pocket_r)
    shadow_penumbra = 1.0 - smoothstep(0.68, 1.35, pocket_r)
    ao_strength = np.clip(0.44 * shadow_core + 0.22 * shadow_penumbra, 0.0, 0.58)
    ao_smooth = gaussian_filter(ao_strength, sigma=10.0)
    rgb = rgb * (1.0 - ao_smooth[..., None]) + COL_TIER2_DEEP_SHADOW * ao_smooth[..., None]

    # Sunlit white rim highlight along the 4 crests
    crest_rim = np.exp(-((yy - bed_top[None, :] - 6.0) / 14.0) ** 2) * mask_top * (0.45 + 0.55 * crest_mask[None, :])
    rgb = np.clip(
        rgb + (crest_rim * 0.55)[..., None] * (COL_TIER2_CREST - rgb),
        0.0,
        1.0,
    )

    # Crisp subtle anti-aliasing (zero side feathering -> 100% full-bleed 1080px)
    rgb_aa, alpha_aa = premul_gaussian_blur(rgb, alpha_raw, sigma=0.7)
    rgb_final = apply_sss_ice_edge(rgb_aa, alpha_aa, strength=0.65)
    return rgb_final, alpha_aa


# ==============================================================================
# TIER 3: FOREGROUND 7-WAVE ORGANIC SNOWFIELD (FULL-BLEED 1080px)
# ==============================================================================
def build_tier_3_front_blur(rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    """
    DIR-FORGE-SNOW-WAVES-041:
    In front of the box base, right behind the CTA button:
    Organic rolling snowfield featuring exactly 7 rhythmic micro-ripples
    (4 crests & 3 troughs alternating across 1080px full-bleed width).
    - Pastel blue shading (#DCEBFA / #BBD6F2) in slopes and troughs
    - Powdery snow granulate texture + sparkling white rim highlights on all 4 crests
    - Center basin (trough_2) and flanking ridges (crest_2, crest_3) softly cradle
      the gift box bottom (~15px overlap at front vertex y≈958px).
    """
    yy, xx = np.mgrid[0:CANVAS_H, 0:CANVAS_W].astype(np.float32)
    x1d = np.arange(CANVAS_W, dtype=np.float32)

    noise_macro = fbm2d(CANVAS_H, CANVAS_W, [(5, 7, 0.55), (12, 16, 0.30), (26, 32, 0.15)], rng)
    noise_meso = fbm2d(CANVAS_H, CANVAS_W, [(42, 48, 0.55), (96, 108, 0.45)], rng)
    noise_micro = fbm2d(CANVAS_H, CANVAS_W, [(180, 180, 0.55), (300, 300, 0.45)], rng)

    # Primary 7-wave foreground silhouette (full-bleed 0..1080px):
    #   crest_1  (x=100): y ≈ 914  (gentle left swell)
    #   trough_1 (x=230): y ≈ 948  (soft valley)
    #   crest_2  (x=380): y ≈ 910  (cradles left base corner of gift box)
    #   trough_2 (x=540): y ≈ 944  (basin hugging ~15px over box front vertex y≈958)
    #   crest_3  (x=710): y ≈ 910  (cradles right base corner of gift box)
    #   trough_3 (x=850): y ≈ 948  (soft transition valley)
    #   crest_4  (x=980): y ≈ 916  (gentle right swell)
    wave_top, crest_mask = compute_7wave_profile(
        x1d,
        base_y=934.0,
        crest_amps=(20.0, 24.0, 24.0, 18.0),
        trough_depths=(14.0, 11.0, 14.0),
    )
    wave_top = wave_top + (noise_macro[935, :] - 0.5) * 6.5

    # Secondary foreground sub-ripple contour below wave_top for organic depth
    sub_wave_y = wave_top + 48.0 + 9.0 * np.sin(x1d * (2.0 * math.pi / 310.0) + 0.9)

    # Smooth Perlin-frayed top-edge alpha gradient (powdery snow edge, zero hard cut)
    mask_top = frayed_top_alpha_mask(
        yy, wave_top, noise_meso, noise_micro, feather_px=10.0, fray_amp_px=4.0
    )

    # 2D heightfield sculpted from the 7-wave profile + secondary foreground swell
    dist_from_crest = np.clip((yy - wave_top[None, :]) / 135.0, 0.0, 1.0)
    wave_elev_1d = np.clip((952.0 - wave_top) / 46.0, 0.0, 1.0)

    # Slope shading: troughs (wave_elev_1d -> 0) and lower slopes dip into cool pastel blue
    sub_ridge_lift = 0.16 * np.exp(-((yy - sub_wave_y[None, :]) / 24.0) ** 2)
    trough_basin = (1.0 - wave_elev_1d[None, :]) * np.exp(-((dist_from_crest - 0.22) / 0.34) ** 2)

    height = (
        0.58
        + 0.24 * wave_elev_1d[None, :] * (1.0 - dist_from_crest * 0.40)
        - 0.24 * trough_basin
        - 0.16 * dist_from_crest
        + sub_ridge_lift
        + 0.14 * (noise_macro - 0.5)
        + 0.09 * (noise_meso - 0.5)
        + 0.055 * (noise_micro - 0.5)
    )
    height = np.clip(height, 0.0, 1.0)

    rgb_raw = shade_snow_heightfield(
        height=height,
        col_shadow=COL_TIER3_SHADOW,
        col_mid=COL_TIER3_ICE,
        col_crest=COL_TIER3_CREST,
        rng=rng,
        normal_strength=26.0,
        sparkle_strength=0.48,
        micro_grain_strength=0.048,
    )

    # Soft pastel-blue shadow tint (#BBD6F2 / #DCEBFA) nested inside the 3 troughs & lower slopes
    trough_tint = np.clip(trough_basin * 0.55 + dist_from_crest * 0.18, 0.0, 0.52)
    rgb_raw = rgb_raw * (1.0 - trough_tint[..., None]) + COL_TIER3_SHADOW * trough_tint[..., None]

    # Sparkling sunlit white rim highlight along all 4 crests
    crest_rim = (
        np.exp(-((yy - wave_top[None, :] - 5.0) / 13.0) ** 2)
        * mask_top
        * (0.38 + 0.62 * crest_mask[None, :])
    )
    rgb_raw = np.clip(
        rgb_raw + (crest_rim * 0.72)[..., None] * (COL_TIER3_CREST - rgb_raw),
        0.0,
        1.0,
    )

    # Extra crisp crystalline sparkles concentrated on the 4 sunlit crest peaks
    sparkle_seed = rng.random((CANVAS_H, CANVAS_W), dtype=np.float32)
    sparkle_pts = np.where(sparkle_seed > 0.994, (sparkle_seed - 0.994) / 0.006, 0.0)
    sparkle_pts = gaussian_filter(sparkle_pts.astype(np.float32), sigma=0.7)
    sparkle_pts = np.clip(sparkle_pts * 5.0, 0.0, 1.0) * crest_rim
    rgb_raw = np.clip(rgb_raw + (sparkle_pts * 0.85)[..., None], 0.0, 1.0)

    # Gentle 1.5px optical softness to keep powdery granulate & 7 ripples crisp yet dreamy
    rgb_blur, alpha_blur = premul_gaussian_blur(rgb_raw, mask_top, sigma=1.5)
    rgb_final = apply_sss_ice_edge(rgb_blur, alpha_blur, strength=0.60)
    return rgb_final, alpha_blur


# ==============================================================================
# DARK-BACKGROUND VISUAL VERIFICATION SHEET (SAVED IN output/TASK_GSSHOP/)
# ==============================================================================
def render_dark_preview(
    tier_paths: Sequence[str],
    out_preview_path: str,
) -> None:
    """
    Renders a 2x2 inspection sheet on a deep midnight navy backdrop (#0B1220)
    showing Tier 1, Tier 2, Tier 3 individually plus the 3-tier combined stack.
    """
    panel_size = 540
    bg_color = (11, 18, 32, 255)  # #0B1220
    sheet = Image.new("RGBA", (panel_size * 2, panel_size * 2), bg_color)

    imgs = [Image.open(p).convert("RGBA") for p in tier_paths]

    # Combined 3-tier stack on dark backdrop
    combined = Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_color)
    for im in imgs:
        combined = Image.alpha_composite(combined, im)

    panels = [
        ("TIER 1: BACK BLUR (~12px, #D9E6F2)", Image.alpha_composite(Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_color), imgs[0])),
        ("TIER 2: CRISP BOX BED (POCKET + AO)", Image.alpha_composite(Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_color), imgs[1])),
        ("TIER 3: FRONT BLUR (~5px, #FFFFFF/#F0F9FF)", Image.alpha_composite(Image.new("RGBA", (CANVAS_W, CANVAS_H), bg_color), imgs[2])),
        ("COMBINED 3-TIER STACK (DARK BG AUDIT)", combined),
    ]

    draw = ImageDraw.Draw(sheet)
    positions = [(0, 0), (panel_size, 0), (0, panel_size), (panel_size, panel_size)]

    for (label, panel_img), (px, py) in zip(panels, positions):
        resized = panel_img.resize((panel_size, panel_size), Image.Resampling.LANCZOS)
        sheet.paste(resized, (px, py))
        # Subtle panel border + crisp top banner label
        draw.rectangle(
            [px, py, px + panel_size - 1, py + panel_size - 1],
            outline=(56, 82, 118, 255),
            width=2,
        )
        draw.rectangle([px + 10, py + 10, px + 390, py + 36], fill=(15, 23, 42, 220))
        draw.text((px + 18, py + 17), label, fill=(240, 249, 255, 255))

    os.makedirs(os.path.dirname(out_preview_path), exist_ok=True)
    sheet.convert("RGB").save(out_preview_path, format="PNG", optimize=True)


# ==============================================================================
# MAIN PIPELINE
# ==============================================================================
def main() -> int:
    t0 = time.perf_counter()
    os.makedirs(LAYERS_OUT_DIR, exist_ok=True)
    os.makedirs(SHOWCASE_SYNC_DIR, exist_ok=True)
    os.makedirs(TASK_OUTPUT_DIR, exist_ok=True)

    rng = np.random.default_rng(20261126)

    builders = [
        (TIER_FILES[0], build_tier_1_back_blur),
        (TIER_FILES[1], build_tier_2_box_bed),
        (TIER_FILES[2], build_tier_3_front_blur),
    ]

    rendered_paths = []
    print("[FORGE_SNOW] Synthesizing 3-tier procedural snow system (1080x1080 RGBA, Alpha=0)...")
    for fname, fn in builders:
        t_step = time.perf_counter()
        rgb, alpha = fn(rng)
        dst_layer = os.path.join(LAYERS_OUT_DIR, fname)
        save_rgba_png(rgb, alpha, dst_layer)

        # Dual-Delivery Sync
        dst_showcase = os.path.join(SHOWCASE_SYNC_DIR, fname)
        shutil.copy2(dst_layer, dst_showcase)
        rendered_paths.append(dst_layer)

        size_kb = os.path.getsize(dst_layer) / 1024.0
        alpha_zero_pct = float((alpha <= (0.5 / 255.0)).mean() * 100.0)
        elapsed = time.perf_counter() - t_step
        print(
            f"  ✓ {fname}: {size_kb:.1f} KB | Alpha=0 ratio: {alpha_zero_pct:.1f}% | "
            f"synced -> {dst_showcase} ({elapsed:.2f}s)"
        )

    preview_path = os.path.join(TASK_OUTPUT_DIR, "snow_3tier_preview_dark.png")
    render_dark_preview(rendered_paths, preview_path)
    print(f"[FORGE_SNOW] Dark-background visual preview -> {preview_path}")
    print(f"[FORGE_SNOW] Done in {time.perf_counter() - t0:.2f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())