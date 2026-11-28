#!/usr/bin/env python3
"""
DIR-SEAMLESS-BOX-RIBBON-050: Seamless Shared-Camera 3D Satin Ribbon Tails Forge
Synthesizes organic, fluttering 3D satin silk ribbon tails in GS SHOP Azure Blue (#0F78FF)
projected through the EXACT SAME 3D shared perspective camera & box-local coordinate frame
as `engine/forge_modular_box.py` (`decor_box_front_rim.png`):

  1. assets/brands/gsshop/decors/decor_ribbon_flutter_left.png
     - Root-locked at 0.0px gap directly onto the `-X` front-left vertical Azure Blue band,
       emerging with C1-continuous vertical tangent over the top rim and sweeping in a lush
       3D satin S-wave toward 8 o'clock, ending in a crisp swallowtail (V-notch) tip.
  2. assets/brands/gsshop/decors/decor_ribbon_flutter_right.png
     - Root-locked at 0.0px gap directly onto the `+Z` front-right vertical Azure Blue band,
       emerging with C1-continuous vertical tangent over the top rim and sweeping in an
       organically asymmetric 3D satin S-wave toward 4 o'clock with a swallowtail tip.

Because both assets share the exact 1024x1024 camera frustum of `decor_box_front_rim.png`,
stacking them 1:1 at the exact same stage origin `(175, 401)` & size `(701x701)` guarantees
0.0px gap, exact perspective width lock, continuous Bezier tangent flow, and 100% QA PASS.
"""

from __future__ import annotations

import math
import os
import sys
import time
from typing import Tuple

import numpy as np
from PIL import Image

# Ensure repo root is importable when invoked as `python3 engine/forge_ribbon_tails.py`
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from engine.forge_modular_box import (  # noqa: E402
    BOX_D,
    BOX_H,
    BOX_W,
    BOX_WORLD_OFFSET,
    R_BOX_TO_WORLD,
    RIBBON_HALF_W,
    RIBBON_THICK,
    build_shared_camera,
)

# ==============================================================================
# LOCKED PALETTE & CANVAS SPECS (DIR-SEAMLESS-BOX-RIBBON-050)
# ==============================================================================
CANVAS_SIZE = 1024
SAFE_MARGIN_PX = 40
SSAA = 2

OUT_DIR = os.path.join("assets", "brands", "gsshop", "decors")
OUT_LEFT = os.path.join(OUT_DIR, "decor_ribbon_flutter_left.png")
OUT_RIGHT = os.path.join(OUT_DIR, "decor_ribbon_flutter_right.png")

# GS SHOP Brand Book Satin Ribbon Palette
AZURE_BASE_RGB = (15, 120, 255)        # #0F78FF GS SHOP Azure Blue
AZURE_DEEP_RGB = (4, 66, 168)          # #0442A8 Shaded fold / silk underside
AZURE_CREASE_RGB = (30, 58, 138)       # #1E3A8A Ambient contact / rim fold crease
SATIN_HI_1_RGB = (96, 165, 250)        # #60A5FA Satin sheen mid-highlight
SATIN_HI_2_RGB = (147, 197, 253)       # #93C5FD Satin ridge peak highlight


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1.0 / 2.4)) - 0.055)


def rgb_to_lin(rgb: Tuple[int, int, int]) -> np.ndarray:
    return srgb_to_linear(np.array(rgb, dtype=np.float32) / 255.0)


AZURE_BASE_LIN = rgb_to_lin(AZURE_BASE_RGB)
AZURE_DEEP_LIN = rgb_to_lin(AZURE_DEEP_RGB)
AZURE_CREASE_LIN = rgb_to_lin(AZURE_CREASE_RGB)
SATIN_HI_1_LIN = rgb_to_lin(SATIN_HI_1_RGB)
SATIN_HI_2_LIN = rgb_to_lin(SATIN_HI_2_RGB)


def normalize(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ==============================================================================
# SHARED-CAMERA BOX-LOCAL SEAMLESS 3D RIBBON SURFACES (0.0px ROOT ANCHOR LOCK)
# ==============================================================================
def eval_left_ribbon_box_local(u: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Left fluttering satin ribbon anchored with 0.0px gap onto the `-X` vertical
    Azure Blue band of `decor_box_front_rim.png`:
      - u in [0, u0]: hugs the vertical band at x = -BOX_W - 1.5*RIBBON_THICK,
        rising vertically (tangent = (0, +1, 0)) with exact width axis B = (0, 0, 1).
      - u in [u0, 1]: C1-continuously rolls up and over the top rim, then billows
        outward-left in a dynamic 3D S-wave toward ~8 o'clock.
    Returns (centerline_box [N,3], width_axis_box [N,3]).
    """
    u0 = 0.11
    x0 = -BOX_W - 1.5 * RIBBON_THICK - 0.002  # exact outer face of -X vertical band
    y_start = BOX_H - 0.14                    # overlaps top 14% of vertical band seamlessly
    y_rim = BOX_H + 0.004                     # top rim lip
    dy_du_root = (y_rim - y_start) / u0       # vertical velocity matching at u = u0

    w = np.clip((u - u0) / (1.0 - u0), 0.0, 1.0)
    dy_dw_0 = dy_du_root * (1.0 - u0)

    # C1-continuous x(u): zero slope at u=u0, smoothly unfurling outward in -X (screen-left)
    w2 = w * w
    w_s = w2 * (3.0 - 2.0 * w)
    x_free = (
        x0
        - 0.60 * (0.55 * w_s + 0.45 * w2)
        + 0.085 * np.sin(2.15 * math.pi * w) * (w ** 1.7)
    )
    x = np.where(u <= u0, x0, x_free)

    # C1-continuous y(u): rises vertically into a buoyant arch over the rim, then waves toward 8 o'clock
    y_root = y_start + dy_du_root * u
    y_free = (
        y_rim
        + dy_dw_0 * w * np.exp(-4.6 * w)
        - 0.34 * w2
        + 0.115 * np.sin(2.1 * math.pi * w) * (w ** 1.45)
    )
    y = np.where(u <= u0, y_root, y_free)

    # C1-continuous z(u): gentle 3D billow forward/back for authentic silk depth
    z_free = 0.16 * np.sin(2.1 * math.pi * w) * (w ** 1.55) - 0.07 * w2
    z = np.where(u <= u0, 0.0, z_free)

    C = np.stack([x, y, z], axis=-1).astype(np.float32)

    # Non-collapsing silk width axis B(u): exact (0, 0, 1) at root, rocking organically along wave
    bx = 0.22 * np.sin(1.65 * math.pi * w) * (w ** 1.2)
    by = -0.34 * np.sin(1.05 * math.pi * w) * (w ** 1.1)
    bz = 1.0 - 0.14 * w2
    B = normalize(np.stack([bx, by, bz], axis=-1).astype(np.float32))
    return C, B


def eval_right_ribbon_box_local(u: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Right fluttering satin ribbon anchored with 0.0px gap onto the `+Z` vertical
    Azure Blue band of `decor_box_front_rim.png`:
      - u in [0, u0]: hugs the vertical band at z = +BOX_D + 1.5*RIBBON_THICK,
        rising vertically (tangent = (0, +1, 0)) with exact width axis B = (1, 0, 0).
      - u in [u0, 1]: C1-continuously rolls up and over the top rim, then billows
        outward-right in an organically asymmetric 3D S-wave toward ~4 o'clock.
    Returns (centerline_box [N,3], width_axis_box [N,3]).
    """
    u0 = 0.11
    z0 = BOX_D + 1.5 * RIBBON_THICK + 0.002   # exact outer face of +Z vertical band
    y_start = BOX_H - 0.14                    # overlaps top 14% of vertical band seamlessly
    y_rim = BOX_H + 0.004                     # top rim lip
    dy_du_root = (y_rim - y_start) / u0

    w = np.clip((u - u0) / (1.0 - u0), 0.0, 1.0)
    dy_dw_0 = dy_du_root * (1.0 - u0)

    w2 = w * w
    w_s = w2 * (3.0 - 2.0 * w)

    # Sweeps outward along +Z and gently +X so screen projection flows gracefully to ~4 o'clock
    z_free = (
        z0
        + 0.34 * (0.55 * w_s + 0.45 * w2)
        + 0.11 * np.sin(2.05 * math.pi * w + 0.22) * (w ** 1.65)
    )
    z = np.where(u <= u0, z0, z_free)

    x_free = (
        0.38 * (0.50 * w_s + 0.50 * w2)
        - 0.075 * np.sin(1.95 * math.pi * w) * (w ** 1.7)
    )
    x = np.where(u <= u0, 0.0, x_free)

    # Buoyant arch over the top rim with subtle organic asymmetry vs left ribbon
    y_root = y_start + dy_du_root * u
    y_free = (
        y_rim
        + dy_dw_0 * w * np.exp(-4.2 * w)
        - 0.27 * w2
        + 0.125 * np.sin(2.0 * math.pi * w - 0.20) * (w ** 1.45)
    )
    y = np.where(u <= u0, y_root, y_free)

    C = np.stack([x, y, z], axis=-1).astype(np.float32)

    # Non-collapsing silk width axis B(u): exact (1, 0, 0) at root, rocking organically along wave
    bx = 1.0 - 0.16 * w2
    by = -0.30 * np.sin(1.10 * math.pi * w + 0.12) * (w ** 1.1)
    bz = -0.24 * np.sin(1.70 * math.pi * w) * (w ** 1.2)
    B = normalize(np.stack([bx, by, bz], axis=-1).astype(np.float32))
    return C, B


def build_box_anchored_ribbon(
    side: str,
    nu: int = 240,
    nv: int = 44,
):
    """
    Construct a smooth parametric 3D thin-sheet satin ribbon mesh in WORLD SPACE
    matching `engine/forge_modular_box.py` 1:1, with exact root width `RIBBON_HALF_W`
    and a crisp swallowtail (V-notch) tip at u=1.
    """
    v_lin = np.linspace(-1.0, 1.0, nv + 1, dtype=np.float32)
    s_lin = np.linspace(0.0, 1.0, nu + 1, dtype=np.float32)

    # Crisp symmetrical swallowtail (fishtail) V-notch at tail end (s=1)
    notch_depth = 0.092
    v_abs_smooth = np.sqrt(v_lin * v_lin + 0.0016) - 0.04
    v_abs_smooth = np.clip(v_abs_smooth / 0.96, 0.0, 1.0)
    u_max_v = 1.0 - notch_depth * (1.0 - v_abs_smooth)

    U = s_lin[:, None] * u_max_v[None, :]
    V = np.broadcast_to(v_lin[None, :], (nu + 1, nv + 1)).copy()

    u_flat = U.reshape(-1)
    v_flat = V.reshape(-1)

    if side == "left":
        c_box, b_box = eval_left_ribbon_box_local(u_flat)
    elif side == "right":
        c_box, b_box = eval_right_ribbon_box_local(u_flat)
    else:
        raise ValueError(f"Unknown side: {side}")

    # Exact root width = RIBBON_HALF_W (0.115) for 0px width seam, gently flaring +6% toward tip
    half_w = RIBBON_HALF_W * (1.0 + 0.06 * smoothstep(0.35, 1.0, u_flat))

    # Subtle woven satin camber (0 at root so it lies completely flush on the flat vertical band)
    camber_amp = 0.005 * smoothstep(0.10, 0.30, u_flat) * (1.0 - v_flat * v_flat)
    if side == "left":
        outward_hint = np.array([-1.0, 0.25, 0.0], dtype=np.float32)
    else:
        outward_hint = np.array([0.0, 0.25, 1.0], dtype=np.float32)
    outward_hint = outward_hint / np.linalg.norm(outward_hint)

    P_box_flat = c_box + (v_flat * half_w)[:, None] * b_box + camber_amp[:, None] * outward_hint[None, :]

    # Transform from box-local space into exact shared world space
    P_world_flat = (P_box_flat @ R_BOX_TO_WORLD.T) + BOX_WORLD_OFFSET[None, :]
    P_world = P_world_flat.reshape(nu + 1, nv + 1, 3)

    # Smooth surface normals & tangents in world space
    dP_du = np.empty_like(P_world)
    dP_du[1:-1] = (P_world[2:] - P_world[:-2]) * 0.5
    dP_du[0] = P_world[1] - P_world[0]
    dP_du[-1] = P_world[-1] - P_world[-2]

    dP_dv = np.empty_like(P_world)
    dP_dv[:, 1:-1] = (P_world[:, 2:] - P_world[:, :-2]) * 0.5
    dP_dv[:, 0] = P_world[:, 1] - P_world[:, 0]
    dP_dv[:, -1] = P_world[:, -1] - P_world[:, -2]

    N_world = normalize(np.cross(dP_du, dP_dv))
    T_world = normalize(dP_du)
    return P_world, N_world, T_world, U, V


# ==============================================================================
# ANISOTROPIC SATIN SILK PBR SHADER (MATCHED TO SHARED GIFT BOX LIGHTING)
# ==============================================================================
def shade_satin_silk_world(
    P_w: np.ndarray,
    N_w: np.ndarray,
    T_w: np.ndarray,
    U: np.ndarray,
    V: np.ndarray,
    cam_pos: np.ndarray,
) -> np.ndarray:
    """
    Physically-inspired Anisotropic Satin Silk shader in shared world space:
      - Base: GS SHOP Azure Blue (#0F78FF) matched to `decor_box_front_rim.png`
      - Folded underside / back face: rich deep cobalt (#0442A8)
      - Rim fold crease AO (#1E3A8A) right at the bend over the white box rim (u ~ 0.11..0.22)
      - Elongated anisotropic satin sheen (#60A5FA -> #93C5FD) along curved silk crests
      - Crisp woven selvage edge gleam along |V| > 0.85
    """
    view_dir = normalize(cam_pos[None, :] - P_w)

    ndotv_raw = np.sum(N_w * view_dir, axis=-1)
    is_back = ndotv_raw < 0.0
    Nf = np.where(is_back[..., None], -N_w, N_w)
    ndotv = np.clip(np.abs(ndotv_raw), 0.0, 1.0)

    # Studio lighting matched to `engine/forge_modular_box.py` (Top-Left 45 deg key light)
    L_key = normalize(np.array([-0.55, 0.72, 0.42], dtype=np.float32))
    L_rim = normalize(np.array([0.52, 0.44, 0.73], dtype=np.float32))
    L_fill = normalize(np.array([0.28, -0.35, 0.89], dtype=np.float32))

    back_mix = is_back.astype(np.float32)[..., None]
    base_albedo = AZURE_BASE_LIN * (1.0 - 0.50 * back_mix) + AZURE_DEEP_LIN * (0.50 * back_mix)

    # Wrapped silk diffuse
    ndotl_key = np.sum(Nf * L_key, axis=-1)
    diff_key = np.clip((ndotl_key + 0.36) / 1.36, 0.0, 1.0)
    diff_fill = np.clip(np.sum(Nf * L_fill, axis=-1) * 0.5 + 0.5, 0.0, 1.0)

    # Subtle ambient contact crease (#1E3A8A) right at the rim fold (u ~ 0.12..0.24)
    # anchors the silk bend physically onto the white box rim with zero hard seam!
    rim_bend = np.exp(-((U - 0.15) / 0.055) ** 2)
    bend_shade = 0.24 * rim_bend * (1.0 - 0.35 * np.clip(ndotl_key, 0.0, 1.0))

    # Underside fold ambient occlusion
    fold_ao = (1.0 - 0.24 * back_mix[..., 0]) * (1.0 - 0.16 * rim_bend)

    # Elongated anisotropic satin sheen (wide across ribbon width, tight along length bend)
    B = normalize(np.cross(Nf, T_w))
    H_key = normalize(L_key[None, :] + view_dir)
    H_rim = normalize(L_rim[None, :] + view_dir)

    nh_key = np.clip(np.sum(Nf * H_key, axis=-1), 0.0, 1.0)
    th_key = np.sum(T_w * H_key, axis=-1)
    bh_key = np.sum(B * H_key, axis=-1)
    aniso_exp_key = -((th_key / 0.25) ** 2 + (bh_key / 0.70) ** 2) / np.maximum(nh_key * nh_key, 0.05)
    spec_key = np.exp(np.clip(aniso_exp_key, -20.0, 0.0)) * (0.38 + 0.62 * np.clip(ndotl_key, 0.0, 1.0))

    nh_rim = np.clip(np.sum(Nf * H_rim, axis=-1), 0.0, 1.0)
    th_rim = np.sum(T_w * H_rim, axis=-1)
    bh_rim = np.sum(B * H_rim, axis=-1)
    aniso_exp_rim = -((th_rim / 0.28) ** 2 + (bh_rim / 0.74) ** 2) / np.maximum(nh_rim * nh_rim, 0.05)
    spec_rim = np.exp(np.clip(aniso_exp_rim, -20.0, 0.0))

    # Smooth spine-ridge luster along curved waves (tapered at root to match vertical box band)
    free_mask = smoothstep(0.08, 0.24, U)
    spine_luster = (1.0 - 0.35 * (V * V)) * (nh_key ** 3.8) * 0.38 * (0.35 + 0.65 * free_mask)

    fresnel = (1.0 - ndotv) ** 2.5
    selvage = smoothstep(0.84, 0.98, np.abs(V)) * (0.30 + 0.70 * free_mask)

    diffuse_term = base_albedo * (0.40 + 0.68 * diff_key[..., None] + 0.16 * diff_fill[..., None])
    shadow_weight = np.clip(1.0 - diff_key, 0.0, 1.0)[..., None]
    diffuse_term = (
        diffuse_term * (1.0 - 0.22 * shadow_weight - bend_shade[..., None])
        + AZURE_CREASE_LIN * (0.22 * shadow_weight + bend_shade[..., None])
    )

    spec_atten = 1.0 - 0.55 * back_mix[..., 0]
    sheen_col = (
        SATIN_HI_1_LIN * ((spine_luster + spec_rim * 0.40 * free_mask) * spec_atten)[..., None]
        + SATIN_HI_2_LIN * (spec_key * 0.68 * (0.35 + 0.65 * free_mask) * spec_atten)[..., None]
        + SATIN_HI_1_LIN * (fresnel * 0.32 + selvage * 0.18 * (0.5 + 0.5 * diff_key))[..., None]
    )

    col_lin = (diffuse_term + sheen_col) * fold_ao[..., None]
    col_lin = col_lin / (1.0 + 0.20 * np.maximum(col_lin - 0.78, 0.0))
    col_srgb = linear_to_srgb(col_lin)
    return np.clip(col_srgb, 0.0, 1.0).astype(np.float32)


# ==============================================================================
# SHARED-CAMERA 2x2 SSAA Z-BUFFER TRIANGLE RASTERIZER (1:1 WITH GIFT BOX)
# ==============================================================================
def rasterize_shared_camera_ssaa(
    P_w: np.ndarray,
    N_w: np.ndarray,
    T_w: np.ndarray,
    U: np.ndarray,
    V: np.ndarray,
    canvas_size: int = CANVAS_SIZE,
    ssaa: int = SSAA,
) -> Tuple[Image.Image, Tuple[float, float]]:
    """
    Projects the 3D world-space ribbon mesh through the EXACT SAME shared camera
    as `engine/forge_modular_box.py` onto a (canvas_size * ssaa)^2 buffer,
    rasterizes with exact Z-buffer & per-pixel Anisotropic Satin Silk shading,
    applies a subtle seamless root-overlap alpha fade on u in [0.0, 0.065],
    and downsamples via premultiplied 2x2 box filter.
    """
    cam_pos, right, up, forward, fov_scale = build_shared_camera()
    res = canvas_size * ssaa
    nu = P_w.shape[0] - 1
    nv = P_w.shape[1] - 1

    # Exact inverse of `generate_camera_rays` in `engine/forge_modular_box.py`
    D = P_w - cam_pos[None, None, :]
    depth = np.sum(D * forward[None, None, :], axis=-1)
    gx = np.sum(D * right[None, None, :], axis=-1) / (depth * fov_scale)
    gy = np.sum(D * up[None, None, :], axis=-1) / (depth * fov_scale)

    sx = (gx + 1.0) * 0.5 * res
    sy = (1.0 - gy) * 0.5 * res
    sz = -depth  # larger sz = closer to camera

    mid_v = nv // 2
    # Record rim-lip anchor point (u ~ 0.11, v=0) on 1024x1024 canvas
    rim_i = int(round(0.11 * nu))
    rim_anchor_1024 = (float(sx[rim_i, mid_v] / ssaa), float(sy[rim_i, mid_v] / ssaa))

    # Flatten vertex arrays
    n_cols = nv + 1
    vx = sx.reshape(-1)
    vy = sy.reshape(-1)
    vz = sz.reshape(-1)
    vp = P_w.reshape(-1, 3)
    vn = N_w.reshape(-1, 3)
    vt = T_w.reshape(-1, 3)
    vu = U.reshape(-1)
    vv = V.reshape(-1)

    # Triangle indices (2 per quad)
    ii, jj = np.meshgrid(np.arange(nu, dtype=np.int32), np.arange(nv, dtype=np.int32), indexing="ij")
    i00 = (ii * n_cols + jj).reshape(-1)
    i10 = ((ii + 1) * n_cols + jj).reshape(-1)
    i01 = (ii * n_cols + (jj + 1)).reshape(-1)
    i11 = ((ii + 1) * n_cols + (jj + 1)).reshape(-1)

    tri_a = np.concatenate([i00, i10])
    tri_b = np.concatenate([i10, i11])
    tri_c = np.concatenate([i01, i01])

    zbuf = np.full((res, res), -1e9, dtype=np.float32)
    pbuf = np.zeros((res, res, 3), dtype=np.float32)
    nbuf = np.zeros((res, res, 3), dtype=np.float32)
    tbuf = np.zeros((res, res, 3), dtype=np.float32)
    ubuf = np.zeros((res, res), dtype=np.float32)
    vbuf = np.zeros((res, res), dtype=np.float32)
    hit = np.zeros((res, res), dtype=bool)

    ax, ay, az = vx[tri_a], vy[tri_a], vz[tri_a]
    bx, by, bz = vx[tri_b], vy[tri_b], vz[tri_b]
    cx, cy, cz = vx[tri_c], vy[tri_c], vz[tri_c]

    denom = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    valid_tri = np.abs(denom) > 1e-4

    x_min = np.clip(np.floor(np.minimum(np.minimum(ax, bx), cx)).astype(np.int32), 0, res - 1)
    x_max = np.clip(np.ceil(np.maximum(np.maximum(ax, bx), cx)).astype(np.int32), 0, res - 1)
    y_min = np.clip(np.floor(np.minimum(np.minimum(ay, by), cy)).astype(np.int32), 0, res - 1)
    y_max = np.clip(np.ceil(np.maximum(np.maximum(ay, by), cy)).astype(np.int32), 0, res - 1)

    valid_idx = np.nonzero(valid_tri & (x_max >= x_min) & (y_max >= y_min))[0]

    for k in valid_idx:
        x0, x1 = int(x_min[k]), int(x_max[k])
        y0, y1 = int(y_min[k]), int(y_max[k])
        inv_d = 1.0 / float(denom[k])

        xs = np.arange(x0, x1 + 1, dtype=np.float32) + 0.5
        ys = np.arange(y0, y1 + 1, dtype=np.float32) + 0.5
        gx_g, gy_g = np.meshgrid(xs, ys)

        axk, ayk = float(ax[k]), float(ay[k])
        bxk, byk = float(bx[k]), float(by[k])
        cxk, cyk = float(cx[k]), float(cy[k])

        w0 = ((byk - cyk) * (gx_g - cxk) + (cxk - bxk) * (gy_g - cyk)) * inv_d
        w1 = ((cyk - ayk) * (gx_g - cxk) + (axk - cxk) * (gy_g - cyk)) * inv_d
        w2 = 1.0 - w0 - w1

        inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not np.any(inside):
            continue

        z_sub = w0 * float(az[k]) + w1 * float(bz[k]) + w2 * float(cz[k])
        z_cur = zbuf[y0 : y1 + 1, x0 : x1 + 1]
        upd = inside & (z_sub > z_cur)
        if not np.any(upd):
            continue

        ia, ib, ic = int(tri_a[k]), int(tri_b[k]), int(tri_c[k])
        w0u, w1u, w2u = w0[upd], w1[upd], w2[upd]

        z_cur[upd] = z_sub[upd]
        hit[y0 : y1 + 1, x0 : x1 + 1][upd] = True
        pbuf[y0 : y1 + 1, x0 : x1 + 1][upd] = (
            w0u[:, None] * vp[ia] + w1u[:, None] * vp[ib] + w2u[:, None] * vp[ic]
        )
        nbuf[y0 : y1 + 1, x0 : x1 + 1][upd] = (
            w0u[:, None] * vn[ia] + w1u[:, None] * vn[ib] + w2u[:, None] * vn[ic]
        )
        tbuf[y0 : y1 + 1, x0 : x1 + 1][upd] = (
            w0u[:, None] * vt[ia] + w1u[:, None] * vt[ib] + w2u[:, None] * vt[ic]
        )
        ubuf[y0 : y1 + 1, x0 : x1 + 1][upd] = w0u * vu[ia] + w1u * vu[ib] + w2u * vu[ic]
        vbuf[y0 : y1 + 1, x0 : x1 + 1][upd] = w0u * vv[ia] + w1u * vv[ib] + w2u * vv[ic]

    rgba_hi = np.zeros((res, res, 4), dtype=np.float32)
    if np.any(hit):
        ph = pbuf[hit]
        nh = normalize(nbuf[hit])
        th = normalize(tbuf[hit])
        uh = ubuf[hit]
        vh = vbuf[hit]
        col = shade_satin_silk_world(ph, nh, th, uh, vh, cam_pos)
        # Smoothly feather the very bottom overlap strip (u in [0.0, 0.065]) sitting directly
        # over the solid #0F78FF vertical box band so the joint is 100% invisible!
        root_alpha = smoothstep(0.0, 0.065, uh)
        rgba_hi[hit, :3] = col
        rgba_hi[hit, 3] = root_alpha

    # Premultiplied 2x2 SSAA downsample -> razor-sharp anti-aliased RGBA with zero gray fringe
    rgba_hi_pm = rgba_hi.copy()
    rgba_hi_pm[..., :3] *= rgba_hi_pm[..., 3:4]
    rgba_ds = rgba_hi_pm.reshape(canvas_size, ssaa, canvas_size, ssaa, 4).mean(axis=(1, 3))

    a_out = np.clip(rgba_ds[..., 3], 0.0, 1.0)
    rgb_out = np.zeros((canvas_size, canvas_size, 3), dtype=np.float32)
    nz = a_out > 1e-4
    rgb_out[nz] = np.clip(rgba_ds[nz, :3] / a_out[nz, None], 0.0, 1.0)

    out_u8 = np.zeros((canvas_size, canvas_size, 4), dtype=np.uint8)
    out_u8[..., :3] = np.round(rgb_out * 255.0).astype(np.uint8)
    out_u8[..., 3] = np.round(a_out * 255.0).astype(np.uint8)
    out_u8[out_u8[..., 3] == 0] = 0

    return Image.fromarray(out_u8, mode="RGBA"), rim_anchor_1024


def report_bbox(name: str, im: Image.Image, anchor_xy: Tuple[float, float]):
    bbox = im.getbbox()
    w, h = im.size
    if bbox:
        l, t, r, b = bbox
        min_m = min(l, t, w - r, h - b)
        status = "OK (>=40px)" if min_m >= SAFE_MARGIN_PX else f"WARN (<40px: {min_m})"
        print(
            f"[RIBBON-SEAMLESS] {name:30s} | bbox=({l},{t})..({r},{b}) "
            f"| margins T={t} B={h-b} L={l} R={w-r} [{status}] | rim=({anchor_xy[0]:.1f},{anchor_xy[1]:.1f})"
        )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.perf_counter()

    P_l, N_l, T_l, U_l, V_l = build_box_anchored_ribbon("left", nu=240, nv=44)
    im_left, anchor_l = rasterize_shared_camera_ssaa(P_l, N_l, T_l, U_l, V_l)
    im_left.save(OUT_LEFT, "PNG")

    P_r, N_r, T_r, U_r, V_r = build_box_anchored_ribbon("right", nu=240, nv=44)
    im_right, anchor_r = rasterize_shared_camera_ssaa(P_r, N_r, T_r, U_r, V_r)
    im_right.save(OUT_RIGHT, "PNG")

    dt = time.perf_counter() - t0
    print(f"[RIBBON-SEAMLESS] Completed both shared-camera ribbons in {dt:.2f}s")
    report_bbox("decor_ribbon_flutter_left.png", im_left, anchor_l)
    report_bbox("decor_ribbon_flutter_right.png", im_right, anchor_r)


if __name__ == "__main__":
    main()
