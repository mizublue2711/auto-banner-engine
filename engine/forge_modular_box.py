#!/usr/bin/env python3
"""
DIR-FORGE-MODULAR-GIFTBOX-020: Procedural 3D Modular Winter Gift Box Forge
Synthesizes 4 pixel-aligned 1024x1024 native RGBA (alpha=0) sandwich layers
from a single shared 3D isometric/dimetric camera (~35 deg downward tilt)
for 1:1 CSS absolute stacking:

  z=1: assets/brands/gsshop/decors/decor_box_contact_shadow.png
  z=2: assets/brands/gsshop/decors/decor_box_back_interior.png
  z=4: assets/brands/gsshop/decors/decor_box_front_rim.png
  z=5: assets/brands/gsshop/decors/decor_box_lid_flying.png

Plus an optional z-index 3 compositing verification mockup.
"""

from __future__ import annotations

import argparse
import math
import os
import time
from typing import Callable, Tuple

import numpy as np
from PIL import Image, ImageDraw

# ==============================================================================
# LOCKED PBR PALETTE & GLOBAL SCENE PARAMETERS (DIR-FORGE-MODULAR-GIFTBOX-020)
# ==============================================================================
CANVAS_SIZE = 1024
SAFE_MARGIN_PX = 40
SSAA = 2

OUT_DIR = os.path.join("assets", "brands", "gsshop", "decors")

# Palette RGB (0..255)
BOX_EXTERIOR_HEX = (237, 242, 247)      # #EDF2F7 Snow-white porcelain (max clamp)
CAVITY_LIGHT_HEX = (203, 213, 225)      # #CBD5E1 Interior cavity upper
CAVITY_DARK_HEX = (148, 163, 184)       # #94A3B8 Interior cavity deep floor/corner
RIBBON_AZURE_HEX = (15, 120, 255)       # #0F78FF GS SHOP Azure Blue satin
RIBBON_FOLD_HEX = (3, 70, 148)          # #034694 Deepened Azure fabric fold shadow
GOLD_ACCENT_HEX = (245, 158, 11)        # #F59E0B Subtle edge stitching/accent
ICE_FILL_HEX = (208, 232, 255)          # Cool ice-blue ambient bounce
CAVITY_AO_RGB = (15, 23, 42)            # rgba(15, 23, 42, 0.35)


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1.0 / 2.4)) - 0.055)


def hex_to_lin(rgb_u8: Tuple[int, int, int]) -> np.ndarray:
    return srgb_to_linear(np.array(rgb_u8, dtype=np.float32) / 255.0)


# Strictly clamped <= 85% albedo on snow-white porcelain to prevent specular blowout
PORCELAIN_LIN = hex_to_lin(BOX_EXTERIOR_HEX) * 0.85
CAVITY_LIGHT_LIN = hex_to_lin(CAVITY_LIGHT_HEX)
CAVITY_DARK_LIN = hex_to_lin(CAVITY_DARK_HEX)
AZURE_LIN = hex_to_lin(RIBBON_AZURE_HEX)
AZURE_FOLD_LIN = hex_to_lin(RIBBON_FOLD_HEX)
GOLD_LIN = hex_to_lin(GOLD_ACCENT_HEX)
ICE_LIN = hex_to_lin(ICE_FILL_HEX)
CAVITY_AO_LIN = hex_to_lin(CAVITY_AO_RGB)
SNOW_SRGB_CLAMP = np.array(BOX_EXTERIOR_HEX, dtype=np.float32) / 255.0


# ==============================================================================
# VECTORIZED 3D MATH & SDF PRIMITIVES
# ==============================================================================
def normalize3(v: np.ndarray) -> np.ndarray:
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-8)


def dot3(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sum(a * b, axis=-1)


def smin_poly(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def sd_box(p: np.ndarray, b: np.ndarray, r: float = 0.0) -> np.ndarray:
    """Rounded 3D box centered at origin with half-extents b and corner radius r."""
    q = np.abs(p) - (b - r)
    outside = np.linalg.norm(np.maximum(q, 0.0), axis=-1)
    inside = np.minimum(np.maximum(q[:, 0], np.maximum(q[:, 1], q[:, 2])), 0.0)
    return outside + inside - r


def sd_ellipsoid(p: np.ndarray, r: np.ndarray) -> np.ndarray:
    k0 = np.linalg.norm(p / r[None, :], axis=-1)
    k1 = np.linalg.norm(p / (r * r)[None, :], axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def sd_capsule(p: np.ndarray, a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    pa = p - a[None, :]
    ba = b - a
    h = np.clip(np.sum(pa * ba[None, :], axis=-1) / float(np.dot(ba, ba)), 0.0, 1.0)
    return np.linalg.norm(pa - ba[None, :] * h[:, None], axis=-1) - r


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


# ==============================================================================
# SHARED PARAMETRIC SCENE & CAMERA (IDENTICAL ORIGIN ACROSS ALL 4 LAYERS)
# ==============================================================================
# Box local dimensions: centered at x=0, z=0, resting on ground plane y=0
BOX_W = 0.56          # half-width X
BOX_D = 0.56          # half-depth Z
BOX_H = 0.70          # total height Y
WALL_T = 0.064        # sturdy porcelain wall thickness
BEVEL_R = 0.024       # soft porcelain edge bevel
RIBBON_HALF_W = 0.115 # Azure satin ribbon half-width
RIBBON_THICK = 0.012  # raised satin ribbon relief

# Box orientation in world space: yaw +30 deg so opening faces gently top-right
# Front exterior faces visible to camera: local +Z (front-right) and local -X (front-left)
# Back interior walls visible behind tucked products: local -Z (back-left) and local +X (back-right)
BOX_YAW_DEG = 30.0
R_BOX_TO_WORLD = rot_y(BOX_YAW_DEG)
R_WORLD_TO_BOX = R_BOX_TO_WORLD.T
BOX_WORLD_OFFSET = np.array([0.04, -0.60, 0.0], dtype=np.float32)

# Floating Lid (z=5): detached above box, tilted 25 deg towards upper-left
LID_W = BOX_W + 0.048
LID_D = BOX_D + 0.048
LID_H = 0.175
LID_WORLD_OFFSET = np.array([-0.26, 0.64, 0.02], dtype=np.float32)
# Dynamic 25 deg tilt towards upper-left + matching yaw
R_LID_TO_WORLD = rot_z(25.0) @ rot_x(-8.0) @ rot_y(BOX_YAW_DEG - 4.0)
R_WORLD_TO_LID = R_LID_TO_WORLD.T


def build_shared_camera():
    """
    Isometric / Dimetric perspective (~35 deg downward tilt).
    Fixed camera origin & look-at shared identically across all 4 layers.
    """
    tilt_rad = math.radians(35.0)
    cam_dist = 6.2
    target = np.array([-0.04, -0.05, 0.0], dtype=np.float32)
    cam_pos = target + np.array(
        [0.0, cam_dist * math.sin(tilt_rad), cam_dist * math.cos(tilt_rad)],
        dtype=np.float32,
    )
    forward = normalize3((target - cam_pos)[None, :])[0]
    world_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    right = normalize3(np.cross(forward, world_up)[None, :])[0]
    up = normalize3(np.cross(right, forward)[None, :])[0]
    # Calibrated fov_scale so the union of all 4 layers sits boldly inside 40px safe margins
    fov_scale = 0.208
    return cam_pos, right, up, forward, fov_scale


def generate_camera_rays(res: int, cam_pos, right, up, forward, fov_scale):
    lin = (np.arange(res, dtype=np.float32) + 0.5) / res * 2.0 - 1.0
    gx, gy = np.meshgrid(lin, -lin)  # +Y is up
    rd = (
        forward[None, None, :]
        + gx[..., None] * fov_scale * right[None, None, :]
        + gy[..., None] * fov_scale * up[None, None, :]
    )
    rd = normalize3(rd.reshape(-1, 3))
    return rd


# ==============================================================================
# MODULAR 3D GEOMETRY SDFS (SHARED ANCHOR COORDINATES)
# ==============================================================================
def world_to_box(p_world: np.ndarray) -> np.ndarray:
    return (p_world - BOX_WORLD_OFFSET[None, :]) @ R_WORLD_TO_BOX.T


def world_to_lid(p_world: np.ndarray) -> np.ndarray:
    return (p_world - LID_WORLD_OFFSET[None, :]) @ R_WORLD_TO_LID.T


def sdf_back_interior_local(pb: np.ndarray) -> np.ndarray:
    """
    Layer 2 (z=2): Cavity floor + rear interior walls (-Z and +X).
    Overlaps cleanly at the miter corners with the front walls so stacking is seamless.
    """
    # Cavity floor (y in [0, WALL_T])
    c_floor = np.array([0.0, WALL_T * 0.5, 0.0], dtype=np.float32)
    b_floor = np.array([BOX_W - 0.004, WALL_T * 0.5, BOX_D - 0.004], dtype=np.float32)
    d_floor = sd_box(pb - c_floor[None, :], b_floor, BEVEL_R * 0.7)

    # Back-left wall (local -Z face: z in [-BOX_D, -BOX_D + WALL_T])
    c_bz = np.array([0.0, BOX_H * 0.5, -BOX_D + WALL_T * 0.5], dtype=np.float32)
    b_bz = np.array([BOX_W, BOX_H * 0.5, WALL_T * 0.5], dtype=np.float32)
    d_bz = sd_box(pb - c_bz[None, :], b_bz, BEVEL_R)

    # Back-right wall (local +X face: x in [BOX_W - WALL_T, BOX_W])
    c_bx = np.array([BOX_W - WALL_T * 0.5, BOX_H * 0.5, 0.0], dtype=np.float32)
    b_bx = np.array([WALL_T * 0.5, BOX_H * 0.5, BOX_D], dtype=np.float32)
    d_bx = sd_box(pb - c_bx[None, :], b_bx, BEVEL_R)

    d = smin_poly(d_bz, d_bx, 0.014)
    d = smin_poly(d, d_floor, 0.016)
    return d


def sdf_front_walls_local(pb: np.ndarray) -> np.ndarray:
    """
    Layer 3 (z=4) porcelain body: Front exterior walls (+Z and -X), front corner edge, and top rim.
    """
    # Front-right wall (local +Z face: z in [BOX_D - WALL_T, BOX_D])
    c_fz = np.array([0.0, BOX_H * 0.5, BOX_D - WALL_T * 0.5], dtype=np.float32)
    b_fz = np.array([BOX_W, BOX_H * 0.5, WALL_T * 0.5], dtype=np.float32)
    d_fz = sd_box(pb - c_fz[None, :], b_fz, BEVEL_R)

    # Front-left wall (local -X face: x in [-BOX_W, -BOX_W + WALL_T])
    c_fx = np.array([-BOX_W + WALL_T * 0.5, BOX_H * 0.5, 0.0], dtype=np.float32)
    b_fx = np.array([WALL_T * 0.5, BOX_H * 0.5, BOX_D], dtype=np.float32)
    d_fx = sd_box(pb - c_fx[None, :], b_fx, BEVEL_R)

    return smin_poly(d_fz, d_fx, 0.014)


def sdf_front_ribbons_local(pb: np.ndarray) -> np.ndarray:
    """
    Raised Azure Blue satin ribbons wrapping around both front exterior walls and over the top rim.
    """
    # Ribbon on +Z front wall (centered at x=0, wraps over top rim)
    c_rz = np.array([0.0, BOX_H * 0.5 + 0.002, BOX_D - WALL_T * 0.5 + RIBBON_THICK * 0.5], dtype=np.float32)
    b_rz = np.array([RIBBON_HALF_W, BOX_H * 0.5 + RIBBON_THICK, WALL_T * 0.5 + RIBBON_THICK], dtype=np.float32)
    d_rz = sd_box(pb - c_rz[None, :], b_rz, 0.012)

    # Ribbon on -X front wall (centered at z=0, wraps over top rim)
    c_rx = np.array([-BOX_W + WALL_T * 0.5 - RIBBON_THICK * 0.5, BOX_H * 0.5 + 0.002, 0.0], dtype=np.float32)
    b_rx = np.array([WALL_T * 0.5 + RIBBON_THICK, BOX_H * 0.5 + RIBBON_THICK, RIBBON_HALF_W], dtype=np.float32)
    d_rx = sd_box(pb - c_rx[None, :], b_rx, 0.012)

    return np.minimum(d_rz, d_rx)


def sdf_full_box_world(p: np.ndarray) -> np.ndarray:
    """Full open box (used for continuous cross-layer AO so seams match seamlessly)."""
    pb = world_to_box(p)
    d_back = sdf_back_interior_local(pb)
    d_front = np.minimum(sdf_front_walls_local(pb), sdf_front_ribbons_local(pb))
    return np.minimum(d_back, d_front)


def sdf_back_interior_world(p: np.ndarray) -> np.ndarray:
    return sdf_back_interior_local(world_to_box(p))


def sdf_front_rim_world(p: np.ndarray) -> np.ndarray:
    pb = world_to_box(p)
    return np.minimum(sdf_front_walls_local(pb), sdf_front_ribbons_local(pb))


# ==============================================================================
# FLAT-BAND SATIN SILK RIBBON BOW PRIMITIVES (DIR-REFINE-LID-BOW-021)
# ==============================================================================
def _build_loop_polyline(length: float, height: float, n_seg: int = 24) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Precompute closed teardrop ribbon-loop centerline in local (x, y) plane:
    Starts pinched at knot (0, 0.02), rises in a graceful silk arch to (length, height),
    and sweeps smoothly back underneath to the knot.
    Returns (pts [n_seg+1, 2], seg_ab [n_seg, 2], seg_inv_len2 [n_seg]).
    """
    ts = np.linspace(0.0, 2.0 * math.pi, n_seg + 1, dtype=np.float32)
    # Teardrop ribbon curve: pinched at t=0 and t=2*pi, full rounded belly near t=pi
    s_u = 0.5 * (1.0 - np.cos(ts))  # 0 at knot -> 1 at outer tip -> 0 at knot
    x = length * (s_u ** 0.85)
    # Upper arch (sin > 0) rises cleanly higher than lower return curve (sin < 0)
    arch = np.sin(ts)
    y = (
        0.028
        + height * (0.48 * s_u + 0.44 * arch * (0.38 + 0.62 * s_u))
        + 0.025 * np.sin(2.0 * ts) * s_u
    )
    # Keep lower belly gently above lid surface
    y = np.maximum(y, 0.016)
    pts = np.stack([x, y], axis=-1)
    ab = pts[1:] - pts[:-1]
    inv_l2 = 1.0 / np.maximum(np.sum(ab * ab, axis=-1), 1e-8)
    return pts, ab, inv_l2


def _build_tail_polyline(length: float, wave_y: float, wave_z: float, n_seg: int = 16):
    """
    Precompute graceful S-curved trailing satin ribbon tail lying across the lid top.
    """
    u = np.linspace(0.0, 1.0, n_seg + 1, dtype=np.float32)
    x = 0.06 + length * u
    # Gentle silk undulation rising slightly from knot then draping onto lid surface
    y = 0.036 * np.exp(-3.2 * u) + 0.014 + wave_y * np.sin(math.pi * u) * (1.0 - 0.35 * u)
    z = wave_z * np.sin(1.15 * math.pi * u) * (u ** 0.9)
    pts = np.stack([x, y, z], axis=-1)
    ab = pts[1:] - pts[:-1]
    inv_l2 = 1.0 / np.maximum(np.sum(ab * ab, axis=-1), 1e-8)
    return pts, ab, inv_l2


# Precompute loop and tail curves once at module load for fast vectorized SDF eval
_LOOP_PRIMARY = _build_loop_polyline(length=0.47, height=0.22, n_seg=24)
_LOOP_UPPER = _build_loop_polyline(length=0.37, height=0.26, n_seg=22)
_TAIL_CURVE_A = _build_tail_polyline(length=0.44, wave_y=0.024, wave_z=0.065, n_seg=14)
_TAIL_CURVE_B = _build_tail_polyline(length=0.41, wave_y=0.020, wave_z=-0.055, n_seg=14)


def sd_flat_satin_loop(
    p_local: np.ndarray,
    ang_deg: float,
    curve_data,
    half_width_outer: float = 0.105,
    half_width_knot: float = 0.036,
    ribbon_thick: float = 0.011,
    roll_deg: float = 0.0,
) -> np.ndarray:
    """
    Exact 3D SDF of a thin flat-band satin ribbon loop with pinched fabric gathers/creases
    near the center knot and crisp flat ribbon edges (NO tubular balloon inflation).
    """
    pts, ab, inv_l2 = curve_data
    q = p_local @ rot_y(ang_deg)
    if abs(roll_deg) > 1e-3:
        q = q @ rot_x(roll_deg)

    qx, qy, qz = q[:, 0], q[:, 1], q[:, 2]

    # Quick bounding-sphere cull for distant points so raymarch stays blazing fast
    # (returns safe conservative lower bound when far away)
    n_pts = q.shape[0]
    p2 = q[:, :2]  # [N, 2]

    # Vectorized closest distance to 2D polyline segments
    min_d2 = np.full(n_pts, 1e9, dtype=np.float32)
    best_x = np.zeros(n_pts, dtype=np.float32)
    for i in range(ab.shape[0]):
        pa = p2 - pts[i][None, :]
        h = np.clip((pa[:, 0] * ab[i, 0] + pa[:, 1] * ab[i, 1]) * inv_l2[i], 0.0, 1.0)
        dx = pa[:, 0] - ab[i, 0] * h
        dy = pa[:, 1] - ab[i, 1] * h
        d2 = dx * dx + dy * dy
        closer = d2 < min_d2
        min_d2 = np.where(closer, d2, min_d2)
        best_x = np.where(closer, pts[i, 0] + ab[i, 0] * h, best_x)

    d_curve = np.sqrt(min_d2)

    # Ribbon width pinches tightly into center knot and flares gracefully along loop belly
    length_max = float(pts[:, 0].max())
    u_out = np.clip(best_x / max(length_max, 1e-4), 0.0, 1.0)
    # Smooth pinch profile: narrow at knot, wide silky belly
    w_half = half_width_knot + (half_width_outer - half_width_knot) * (u_out ** 0.58)

    # Delicate folding creases radiating from the center knot (3-pleat silk gather)
    z_norm = np.clip(qz / np.maximum(w_half, 0.02), -1.2, 1.2)
    knot_gather = np.exp(-u_out * 3.4)
    crease_disp = 0.0085 * np.cos(3.0 * math.pi * z_norm) * knot_gather
    # Subtle soft crown across ribbon width so light catches a sleek satin sheen
    satin_camber = 0.004 * (1.0 - z_norm * z_norm) * (1.0 - knot_gather)

    d_sheet = d_curve - (ribbon_thick + crease_disp + satin_camber)
    d_width = np.abs(qz) - w_half

    # Exact extruded flat-band ribbon box distance (bevel r=0.006 for crisp silk edge)
    bevel = 0.006
    d_ext = (
        np.minimum(np.maximum(d_sheet + bevel, d_width + bevel), 0.0)
        + np.hypot(np.maximum(d_sheet + bevel, 0.0), np.maximum(d_width + bevel, 0.0))
        - bevel
    )
    return d_ext * 0.85


def sd_satin_tail(
    p_local: np.ndarray,
    ang_deg: float,
    curve_data,
    half_width: float = 0.074,
    ribbon_thick: float = 0.009,
    cut_angle_deg: float = 34.0,
) -> np.ndarray:
    """
    Graceful trailing flat-band satin ribbon tail with an angled diagonal cut end.
    """
    pts, ab, inv_l2 = curve_data
    q = p_local @ rot_y(ang_deg)
    n_pts = q.shape[0]

    # Closest point on 3D centerline curve (using X-Y profile & Z drift)
    min_d2 = np.full(n_pts, 1e9, dtype=np.float32)
    best_u = np.zeros(n_pts, dtype=np.float32)
    best_z = np.zeros(n_pts, dtype=np.float32)
    n_seg = ab.shape[0]

    for i in range(n_seg):
        pa = q - pts[i][None, :]
        # Project onto segment in XY for sheet distance, track Z offset for ribbon width
        seg_xy_l2 = float(ab[i, 0] ** 2 + ab[i, 1] ** 2) + 1e-8
        h = np.clip((pa[:, 0] * ab[i, 0] + pa[:, 1] * ab[i, 1]) / seg_xy_l2, 0.0, 1.0)
        dx = pa[:, 0] - ab[i, 0] * h
        dy = pa[:, 1] - ab[i, 1] * h
        d2 = dx * dx + dy * dy
        closer = d2 < min_d2
        min_d2 = np.where(closer, d2, min_d2)
        best_u = np.where(closer, (i + h) / n_seg, best_u)
        best_z = np.where(closer, pts[i, 2] + ab[i, 2] * h, best_z)

    d_curve = np.sqrt(min_d2)
    z_off = q[:, 2] - best_z

    # Narrow near knot, flares gently to full flat-band width
    w_half = 0.042 + (half_width - 0.042) * (best_u ** 0.45)
    d_sheet = d_curve - ribbon_thick
    d_width = np.abs(z_off) - w_half

    bevel = 0.005
    d_band = (
        np.minimum(np.maximum(d_sheet + bevel, d_width + bevel), 0.0)
        + np.hypot(np.maximum(d_sheet + bevel, 0.0), np.maximum(d_width + bevel, 0.0))
        - bevel
    )

    # Crisp diagonal angled cut at the end of the ribbon tail!
    end_pt = pts[-1]
    cut_rad = math.radians(cut_angle_deg)
    # Plane normal tilted in XZ so the tail tip has a stylish diagonal shear cut
    nx, nz = math.cos(cut_rad), math.sin(cut_rad)
    d_cut = (q[:, 0] - (end_pt[0] - 0.025)) * nx + (q[:, 2] - end_pt[2]) * nz
    return np.maximum(d_band, d_cut) * 0.85


def sdf_lid_parts_local(pl: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Layer 4 (z=5): Preserved detached floating lid + gold-trim crossed ribbons
    + reconstructed luxury flat-band satin silk bow with knot creases & angled tails.
    Returns (d_porcelain_lid, d_ribbon_and_bow).
    """
    # 1. Porcelain lid shell (PRESERVED exactly)
    d_outer = sd_box(
        pl - np.array([0.0, 0.0, 0.0], dtype=np.float32)[None, :],
        np.array([LID_W, LID_H * 0.5, LID_D], dtype=np.float32),
        0.026,
    )
    d_inner_cut = sd_box(
        pl - np.array([0.0, -0.055, 0.0], dtype=np.float32)[None, :],
        np.array([LID_W - 0.06, LID_H * 0.5, LID_D - 0.06], dtype=np.float32),
        0.012,
    )
    d_lid = np.maximum(d_outer, -d_inner_cut)

    # 2. Crossed Azure Blue satin ribbons wrapping around the lid (PRESERVED exactly)
    d_rib_x = sd_box(
        pl - np.array([0.0, 0.004, 0.0], dtype=np.float32)[None, :],
        np.array([LID_W + RIBBON_THICK, LID_H * 0.5 + RIBBON_THICK, RIBBON_HALF_W], dtype=np.float32),
        0.014,
    )
    d_rib_z = sd_box(
        pl - np.array([0.0, 0.004, 0.0], dtype=np.float32)[None, :],
        np.array([RIBBON_HALF_W, LID_H * 0.5 + RIBBON_THICK, LID_D + RIBBON_THICK], dtype=np.float32),
        0.014,
    )
    d_rib_wrap = np.maximum(np.minimum(d_rib_x, d_rib_z), -d_inner_cut)

    # 3. Luxury Flat-Band Satin Silk Bow on top of the lid
    y_top = LID_H * 0.5 + RIBBON_THICK
    pb = pl - np.array([0.0, y_top, 0.0], dtype=np.float32)[None, :]

    # Fast spatial cull: only evaluate detailed bow loops near the bow bounding box
    d_bow_bound = sd_box(
        pb - np.array([0.0, 0.14, 0.0], dtype=np.float32)[None, :],
        np.array([0.56, 0.24, 0.56], dtype=np.float32),
        0.05,
    )
    near_bow = d_bow_bound < 0.08

    d_bow = d_bow_bound + 0.08
    if np.any(near_bow):
        pbn = pb[near_bow]

        # Cinched flat-band fabric center knot (with 2 delicate silk tension creases)
        pk = pbn @ rot_y(16.0)
        knot_crease = 0.005 * np.cos(pk[:, 2] * 55.0) * np.exp(-(pk[:, 0] ** 2) * 80.0)
        d_knot = sd_box(
            pk - np.array([0.0, 0.048, 0.0], dtype=np.float32)[None, :],
            np.array([0.068, 0.054, 0.082], dtype=np.float32),
            0.026,
        ) + knot_crease

        # 4 sculpted flat-band satin loops (2 wide primary + 2 perkier upper cross loops)
        l1 = sd_flat_satin_loop(pbn, 16.0, _LOOP_PRIMARY, half_width_outer=0.112, half_width_knot=0.036, ribbon_thick=0.011, roll_deg=7.0)
        l2 = sd_flat_satin_loop(pbn, 196.0, _LOOP_PRIMARY, half_width_outer=0.112, half_width_knot=0.036, ribbon_thick=0.011, roll_deg=-7.0)
        l3 = sd_flat_satin_loop(pbn, 74.0, _LOOP_UPPER, half_width_outer=0.095, half_width_knot=0.032, ribbon_thick=0.010, roll_deg=-9.0)
        l4 = sd_flat_satin_loop(pbn, 254.0, _LOOP_UPPER, half_width_outer=0.095, half_width_knot=0.032, ribbon_thick=0.010, roll_deg=9.0)

        # 2 graceful trailing flat-band satin tails with crisp angled diagonal cut ends
        t1 = sd_satin_tail(pbn, -48.0, _TAIL_CURVE_A, half_width=0.078, ribbon_thick=0.009, cut_angle_deg=36.0)
        t2 = sd_satin_tail(pbn, 134.0, _TAIL_CURVE_B, half_width=0.074, ribbon_thick=0.009, cut_angle_deg=-34.0)

        db_near = smin_poly(d_knot, l1, 0.012)
        db_near = smin_poly(db_near, l2, 0.012)
        db_near = smin_poly(db_near, l3, 0.012)
        db_near = smin_poly(db_near, l4, 0.012)
        db_near = smin_poly(db_near, t1, 0.008)
        db_near = smin_poly(db_near, t2, 0.008)
        d_bow = d_bow.copy()
        d_bow[near_bow] = db_near

    d_ribbon_total = smin_poly(d_rib_wrap, d_bow, 0.009)
    return d_lid, d_ribbon_total


def sdf_lid_world(p: np.ndarray) -> np.ndarray:
    d_lid, d_rib = sdf_lid_parts_local(world_to_lid(p))
    return np.minimum(d_lid, d_rib)


# ==============================================================================
# PBR SHADER (KEY LIGHT TOP-LEFT 45 DEG, COOL ICE FILL, DEEP CAVITY AO)
# ==============================================================================
def compute_normals(p: np.ndarray, sdf_fn: Callable[[np.ndarray], np.ndarray], eps: float = 1.6e-3) -> np.ndarray:
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


def compute_ao(p: np.ndarray, n: np.ndarray, sdf_fn: Callable[[np.ndarray], np.ndarray], strength: float = 1.85) -> np.ndarray:
    occ = np.zeros(p.shape[0], dtype=np.float32)
    sca = 1.0
    for i in range(1, 6):
        h = 0.028 + 0.070 * i
        d = sdf_fn(p + n * h)
        occ += (h - d) * sca
        sca *= 0.62
    return np.clip(1.0 - strength * occ, 0.18, 1.0)


def shade_modular_pbr(
    p: np.ndarray,
    n: np.ndarray,
    v: np.ndarray,
    albedo: np.ndarray,
    roughness: np.ndarray,
    metallic: np.ndarray,
    ao: np.ndarray,
    shadow_sdf: Callable[[np.ndarray], np.ndarray],
    clearcoat: np.ndarray | None = None,
    clamp_snow_mask: np.ndarray | None = None,
    cavity_ao_weight: np.ndarray | None = None,
    satin_aniso_mask: np.ndarray | None = None,
    satin_tangent: np.ndarray | None = None,
) -> np.ndarray:
    N = normalize3(n)
    V = normalize3(v)
    NdotV = np.clip(dot3(N, V), 1e-4, 1.0)

    r = np.clip(roughness, 0.05, 1.0)[..., None]
    m = np.clip(metallic, 0.0, 1.0)[..., None]
    a2 = (r * r) ** 2
    F0 = 0.04 * (1.0 - m) + albedo * m

    # Build orthonormal tangent frame for elongated anisotropic satin silk sheen
    if satin_aniso_mask is not None and satin_tangent is not None:
        T_raw = satin_tangent - N * dot3(satin_tangent, N)[:, None]
        T_len = np.linalg.norm(T_raw, axis=-1, keepdims=True)
        fallback = np.cross(N, np.array([[0.0, 1.0, 0.0]], dtype=np.float32))
        T = normalize3(np.where(T_len > 1e-4, T_raw, fallback))
        B = normalize3(np.cross(N, T))
    else:
        T = None
        B = None

    # Key light: Top-Left 45 deg elevation, clean cool-white
    # Fill light: Ambient cool ice-blue bounce rgba(15, 120, 255, 0.18)
    lights = [
        (normalize3(np.array([-0.58, 0.71, 0.56], dtype=np.float32)), np.array([2.05, 2.15, 2.28], dtype=np.float32), True),
        (normalize3(np.array([0.75, 0.12, 0.65], dtype=np.float32)), ICE_LIN * 0.95, False),
        (normalize3(np.array([0.25, 0.68, -0.68], dtype=np.float32)), np.array([0.42, 0.72, 1.15], dtype=np.float32) * 0.48, False),
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
            t_sh = np.full(p.shape[0], 0.03, dtype=np.float32)
            for _ in range(14):
                ps = p + L * t_sh[:, None]
                d_sh = shadow_sdf(ps)
                sh = np.minimum(sh, np.clip(5.5 * d_sh / t_sh, 0.0, 1.0))
                t_sh = t_sh + np.clip(d_sh, 0.02, 0.25)
            sh = (0.42 + 0.58 * sh)[:, None]

        # Standard isotropic GGX
        denom = (NdotH * NdotH) * (a2 - 1.0) + 1.0
        D_iso = a2 / (math.pi * denom * denom + 1e-6)

        # Anisotropic GGX silk lobe (broad elongated sheen across ribbon width, soft along curve)
        if satin_aniso_mask is not None and T is not None:
            TdotH = dot3(T, H)[..., None]
            BdotH = dot3(B, H)[..., None]
            at = 0.52  # broad soft elongation along ribbon tangent
            ab_r = 0.24  # tighter cross-ribbon sheen band (no pinpoint plastic dot!)
            a_denom = (TdotH * TdotH) / (at * at) + (BdotH * BdotH) / (ab_r * ab_r) + (NdotH * NdotH)
            D_aniso = 1.0 / (math.pi * at * ab_r * a_denom * a_denom + 1e-6)
            sm = satin_aniso_mask[..., None]
            D = D_iso * (1.0 - sm) + D_aniso * sm
        else:
            D = D_iso

        k_g = ((r + 1.0) ** 2) / 8.0
        G = (NdotV[..., None] / (NdotV[..., None] * (1.0 - k_g) + k_g)) * (
            NdotL / (NdotL * (1.0 - k_g) + k_g)
        )
        F = F0 + (1.0 - F0) * ((1.0 - HdotV) ** 5)

        spec = (D * G * F) / (4.0 * NdotV[..., None] * NdotL + 1e-4)
        # Silk tinted sheen: satin reflects slightly colored silk highlights instead of stark white plastic
        if satin_aniso_mask is not None:
            sm = satin_aniso_mask[..., None]
            silk_tint = 0.55 * np.ones((1, 3), dtype=np.float32) + 0.45 * np.clip(albedo * 1.45, 0.0, 1.0)
            spec = spec * ((1.0 - sm) + sm * silk_tint * 0.85)
        kD = (1.0 - F) * (1.0 - m)
        diff = kD * albedo / math.pi
        color += (diff + spec) * L_col[None, :] * NdotL * sh

        # Soft grazing fabric sheen (Charlie-style silk rim luminosity on curved folds)
        if satin_aniso_mask is not None and cast_shadow:
            sm = satin_aniso_mask[..., None]
            sheen_fresnel = ((1.0 - NdotV[..., None]) ** 2.6) * (0.35 + 0.65 * NdotL)
            sheen_col = np.clip(albedo * 1.35 + ICE_LIN[None, :] * 0.18, 0.0, 1.0)
            color += sm * sheen_fresnel * sheen_col * 0.28 * sh

        if clearcoat is not None and cast_shadow:
            cc = clearcoat[..., None]
            a2_cc = 0.14 ** 4
            denom_cc = (NdotH * NdotH) * (a2_cc - 1.0) + 1.0
            D_cc = a2_cc / (math.pi * denom_cc * denom_cc + 1e-6)
            F_cc = 0.04 + 0.96 * ((1.0 - HdotV) ** 5)
            spec_cc = (D_cc * F_cc * 0.45) / (4.0 * NdotV[..., None] * NdotL + 0.08)
            color += cc * spec_cc * L_col[None, :] * NdotL * sh

    # Hemisphere IBL: cool ice-blue sky + azure-tinted bounce
    up = np.clip(N[:, 1] * 0.5 + 0.5, 0.0, 1.0)[..., None]
    ground_col = ICE_LIN * 0.82 + AZURE_LIN * 0.18
    hemi_env = ground_col[None, :] * (1.0 - up) + ICE_LIN[None, :] * up

    # Apply deepened cavity occlusion (rgba(15, 23, 42, 0.35)) where cavity_ao_weight is active
    ao_col = ao[..., None]
    if cavity_ao_weight is not None:
        cw = cavity_ao_weight[..., None]
        ao_col = ao_col * (1.0 - 0.35 * cw * (1.0 - ao_col))
        cavity_tint = CAVITY_AO_LIN[None, :] * 0.35 * cw
        ambient_diff = (1.0 - m) * albedo * hemi_env * 0.62 * ao_col * (1.0 - 0.30 * cw) + cavity_tint * (1.0 - ao_col)
    else:
        ambient_diff = (1.0 - m) * albedo * hemi_env * 0.62 * ao_col

    # Subtle environment specular reflection (satin sheen)
    R = normalize3(2.0 * NdotV[..., None] * N - V)
    env_grad = np.clip(R[:, 1] * 0.5 + 0.5, 0.0, 1.0)[..., None]
    env_spec = (np.array([0.22, 0.36, 0.55], dtype=np.float32)[None, :] * (1.0 - env_grad) + ICE_LIN[None, :] * 0.90 * env_grad)
    F_env = F0 + (np.maximum(1.0 - r, F0) - F0) * ((1.0 - NdotV[..., None]) ** 5)
    ambient_spec = F_env * env_spec * np.where(m > 0.5, 0.85, 0.22) * ao_col

    lin_final = color + ambient_diff + ambient_spec
    lin_mapped = lin_final / (1.0 + lin_final * 0.18)
    srgb = linear_to_srgb(lin_mapped)

    if clamp_snow_mask is not None:
        cm = clamp_snow_mask[..., None]
        # Clamp highlights strictly <= #EDF2F7 (237, 242, 247) and preserve cool porcelain hue
        clamped = np.minimum(srgb, SNOW_SRGB_CLAMP[None, :])
        srgb = srgb * (1.0 - cm) + clamped * cm

    return np.clip(srgb, 0.0, 1.0)


# ==============================================================================
# RAYMARCHER & LAYER RENDERERS (DIRECT NATIVE RGBA, NO POST-CROP)
# ==============================================================================
def raymarch_layer(
    res: int,
    cam_pos: np.ndarray,
    rd: np.ndarray,
    sdf_fn: Callable[[np.ndarray], np.ndarray],
    bound_center: np.ndarray,
    bound_radius: float,
    max_steps: int = 86,
    hit_eps: float = 5e-4,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    oc = cam_pos[None, :] - bound_center[None, :]
    b = dot3(oc, rd)
    c = float(np.dot(cam_pos - bound_center, cam_pos - bound_center)) - bound_radius * bound_radius
    disc = b * b - c
    active_idx = np.where(disc >= 0.0)[0]

    hit_mask_flat = np.zeros(res * res, dtype=bool)
    if len(active_idx) == 0:
        return hit_mask_flat.reshape(res, res), np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.float32)

    t_near = np.maximum(-b[active_idx] - np.sqrt(np.maximum(disc[active_idx], 0.0)), 0.1)
    t_far = -b[active_idx] + np.sqrt(np.maximum(disc[active_idx], 0.0))

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
        return hit_mask_flat.reshape(res, res), np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.float32)

    all_hit_idx = np.concatenate(hit_indices)
    all_hit_t = np.concatenate(hit_ts)
    order = np.argsort(all_hit_idx)
    all_hit_idx = all_hit_idx[order]
    all_hit_t = all_hit_t[order]

    hit_mask_flat[all_hit_idx] = True
    hit_rd = rd[all_hit_idx]
    hit_pos = cam_pos[None, :] + hit_rd * all_hit_t[:, None]
    return hit_mask_flat.reshape(res, res), hit_pos, hit_rd


def downsample_ssaa_rgba(hi_rgb: np.ndarray, hi_alpha: np.ndarray) -> np.ndarray:
    """Premultiplied 2x2 SSAA box downsample -> straight RGBA uint8 (zero halo)."""
    hi_rgb = hi_rgb.reshape(CANVAS_SIZE, SSAA, CANVAS_SIZE, SSAA, 3)
    hi_alpha = hi_alpha.reshape(CANVAS_SIZE, SSAA, CANVAS_SIZE, SSAA)

    premul = hi_rgb * hi_alpha[..., None]
    out_alpha = hi_alpha.mean(axis=(1, 3))
    out_premul = premul.mean(axis=(1, 3))

    out_rgb = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.float32)
    nz = out_alpha > 1e-6
    out_rgb[nz] = np.clip(out_premul[nz] / out_alpha[nz, None], 0.0, 1.0)

    rgba = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 4), dtype=np.uint8)
    rgba[..., :3] = np.round(out_rgb * 255.0).astype(np.uint8)
    rgba[..., 3] = np.round(np.clip(out_alpha, 0.0, 1.0) * 255.0).astype(np.uint8)
    return rgba


def save_layer(rgba: np.ndarray, name: str, out_path: str, t0: float) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(out_path, optimize=True)
    ys, xs = np.where(rgba[..., 3] > 0)
    if len(xs) > 0:
        print(
            f"[MODULAR-BOX] {name} -> {out_path} ({time.time() - t0:.2f}s) | "
            f"bbox=({xs.min()},{ys.min()})..({xs.max()},{ys.max()}) | "
            f"margins T={ys.min()} B={CANVAS_SIZE-1-ys.max()} L={xs.min()} R={CANVAS_SIZE-1-xs.max()}"
        )
    else:
        print(f"[MODULAR-BOX] WARNING: {name} is empty!")


# ==============================================================================
# LAYER 1 (z=1): CONTACT SHADOW
# ==============================================================================
def render_contact_shadow(cam_pos, rd, out_path: str) -> np.ndarray:
    t0 = time.time()
    hi_res = CANVAS_SIZE * SSAA
    # Intersect camera rays with ground plane y = BOX_WORLD_OFFSET[1]
    ground_y = float(BOX_WORLD_OFFSET[1])
    denom = rd[:, 1]
    valid = denom < -1e-5
    t = np.where(valid, (ground_y - cam_pos[1]) / np.where(valid, denom, -1.0), -1.0)
    valid = valid & (t > 0.1) & (t < 20.0)

    hi_rgb = np.zeros((hi_res * hi_res, 3), dtype=np.float32)
    hi_alpha = np.zeros((hi_res * hi_res,), dtype=np.float32)

    v_idx = np.where(valid)[0]
    p_gnd = cam_pos[None, :] + rd[v_idx] * t[v_idx, None]
    pb = world_to_box(p_gnd)

    # Slight directional offset opposite top-left key light (+x, +z in world -> shift in box local)
    key_shift_world = np.array([0.08, 0.0, 0.04], dtype=np.float32)
    key_shift_box = key_shift_world @ R_WORLD_TO_BOX.T
    px = pb[:, 0] - key_shift_box[0]
    pz = pb[:, 2] - key_shift_box[2]

    # Exact 2D rounded-box footprint distance on ground plane
    qx = np.abs(px) - (BOX_W - 0.06)
    qz = np.abs(pz) - (BOX_D - 0.06)
    d_out = np.hypot(np.maximum(qx, 0.0), np.maximum(qz, 0.0))
    d_in = np.minimum(np.maximum(qx, qz), 0.0)
    d_foot = d_out + d_in - 0.06  # <= 0 directly under the box base

    # Dual-lobe physically-motivated contact shadow (kept cleanly inside 40px safe margin):
    # 1. Tight dark contact AO under base (rgba(15, 23, 42, 0.42))
    # 2. Soft cool-azure ambient spread (rgba(15, 120, 255, 0.18))
    tight_a = np.exp(-((np.maximum(d_foot + 0.04, 0.0) / 0.10) ** 2)) * 0.42
    broad_a = np.exp(-((np.maximum(d_foot, 0.0) / 0.19) ** 2)) * 0.19
    alpha = np.clip(tight_a + broad_a, 0.0, 0.56)

    # Smooth cutoff to 0 well inside the 40px safe margin
    fade_cut = np.clip((0.34 - d_foot) / 0.12, 0.0, 1.0)
    alpha *= fade_cut * fade_cut * (3.0 - 2.0 * fade_cut)
    alpha = np.where(alpha < 0.004, 0.0, alpha)

    # Blend deep navy-slate core into cool azure outer halo
    core_w = np.clip(tight_a / np.maximum(alpha, 1e-5), 0.0, 1.0)[:, None]
    col_core = np.array([15, 28, 56], dtype=np.float32) / 255.0
    col_outer = np.array([15, 105, 235], dtype=np.float32) / 255.0
    rgb = col_outer[None, :] * (1.0 - core_w) + col_core[None, :] * core_w

    hi_rgb[v_idx] = rgb
    hi_alpha[v_idx] = alpha

    rgba = downsample_ssaa_rgba(hi_rgb, hi_alpha)
    save_layer(rgba, "Step 1 Contact Shadow (z=1)", out_path, t0)
    return rgba


# ==============================================================================
# LAYER 2 (z=2): BACK INTERIOR CAVITY & FLOOR
# ==============================================================================
def render_back_interior(cam_pos, rd, out_path: str) -> np.ndarray:
    t0 = time.time()
    hi_res = CANVAS_SIZE * SSAA
    bound_center = BOX_WORLD_OFFSET + np.array([0.0, BOX_H * 0.5, 0.0], dtype=np.float32)
    hit_mask, hit_pos, hit_rd = raymarch_layer(
        hi_res, cam_pos, rd, sdf_back_interior_world, bound_center, bound_radius=1.25
    )

    n = compute_normals(hit_pos, sdf_back_interior_world)
    # Use full-box SDF for AO so the cavity corners and floor-wall junctions have deep realism
    ao = compute_ao(hit_pos, n, sdf_full_box_world, strength=2.2)

    pb = world_to_box(hit_pos)
    nb = n @ R_WORLD_TO_BOX.T

    # Distinguish interior cavity faces vs top rim / exterior edges
    # Interior cavity: facing +Z (back-left inner wall), -X (back-right inner wall), or +Y on floor
    is_floor = (pb[:, 1] < WALL_T + 0.025) & (nb[:, 1] > 0.35)
    is_inner_wall = (
        ((pb[:, 2] > -BOX_D + WALL_T * 0.5) & (nb[:, 2] > 0.35))
        | ((pb[:, 0] < BOX_W - WALL_T * 0.5) & (nb[:, 0] < -0.35))
    )
    is_cavity = (is_floor | is_inner_wall).astype(np.float32)

    # Recessed depth shadow gradient inside cavity: #CBD5E1 near top rim -> #94A3B8 deep at floor/corner
    depth_t = np.clip(1.0 - (pb[:, 1] / BOX_H), 0.0, 1.0)
    corner_dist = np.hypot(pb[:, 0] - (BOX_W - WALL_T), pb[:, 2] - (-BOX_D + WALL_T))
    corner_t = np.clip(1.0 - corner_dist / 0.75, 0.0, 1.0)
    recess = np.clip(depth_t * 0.72 + corner_t * 0.38, 0.0, 1.0)[:, None]
    cavity_albedo = CAVITY_LIGHT_LIN[None, :] * (1.0 - recess) + CAVITY_DARK_LIN[None, :] * recess

    # Exterior rim / outer edge of back walls: cool snow-white porcelain (#EDF2F7 clamped)
    # Add subtle cool ice tint on porcelain rim so it stays crisp and luminous
    porcelain_cool = PORCELAIN_LIN * np.array([0.94, 0.97, 1.02], dtype=np.float32)
    albedo = porcelain_cool[None, :] * (1.0 - is_cavity[:, None]) + cavity_albedo * is_cavity[:, None]
    roughness = 0.42 * (1.0 - is_cavity) + 0.62 * is_cavity
    metallic = np.zeros(hit_pos.shape[0], dtype=np.float32)

    srgb_hits = shade_modular_pbr(
        p=hit_pos,
        n=n,
        v=-hit_rd,
        albedo=albedo,
        roughness=roughness,
        metallic=metallic,
        ao=ao,
        shadow_sdf=sdf_full_box_world,
        clearcoat=None,
        clamp_snow_mask=np.ones(hit_pos.shape[0], dtype=np.float32),
        cavity_ao_weight=is_cavity,
    )

    hi_rgb = np.zeros((hi_res * hi_res, 3), dtype=np.float32)
    hi_alpha = np.zeros((hi_res * hi_res,), dtype=np.float32)
    flat_idx = np.where(hit_mask.ravel())[0]
    hi_rgb[flat_idx] = srgb_hits
    hi_alpha[flat_idx] = 1.0

    rgba = downsample_ssaa_rgba(hi_rgb, hi_alpha)
    save_layer(rgba, "Step 2 Back Interior (z=2)", out_path, t0)
    return rgba


# ==============================================================================
# LAYER 3 (z=4): FRONT EXTERIOR WALLS, RIM & AZURE BLUE SATIN RIBBONS
# ==============================================================================
def render_front_rim(cam_pos, rd, out_path: str) -> np.ndarray:
    t0 = time.time()
    hi_res = CANVAS_SIZE * SSAA
    bound_center = BOX_WORLD_OFFSET + np.array([0.0, BOX_H * 0.5, 0.0], dtype=np.float32)
    hit_mask, hit_pos, hit_rd = raymarch_layer(
        hi_res, cam_pos, rd, sdf_front_rim_world, bound_center, bound_radius=1.25
    )

    n = compute_normals(hit_pos, sdf_front_rim_world)
    ao = compute_ao(hit_pos, n, sdf_full_box_world, strength=1.8)

    pb = world_to_box(hit_pos)
    d_wall = sdf_front_walls_local(pb)
    d_rib = sdf_front_ribbons_local(pb)
    is_ribbon = (d_rib <= d_wall + 1e-4).astype(np.float32)

    # Subtle gold edge stitching/accent (#F59E0B) along both vertical borders of the Azure ribbon
    dist_from_rib_edge_z = np.abs(np.abs(pb[:, 0]) - (RIBBON_HALF_W - 0.014))
    dist_from_rib_edge_x = np.abs(np.abs(pb[:, 2]) - (RIBBON_HALF_W - 0.014))
    on_z_rib = (pb[:, 2] > BOX_D - WALL_T - 0.02) & (np.abs(pb[:, 0]) < RIBBON_HALF_W + 0.01)
    on_x_rib = (pb[:, 0] < -BOX_W + WALL_T + 0.02) & (np.abs(pb[:, 2]) < RIBBON_HALF_W + 0.01)
    is_gold = (
        (is_ribbon > 0.5)
        & (
            (on_z_rib & (dist_from_rib_edge_z < 0.0075))
            | (on_x_rib & (dist_from_rib_edge_x < 0.0075))
        )
    ).astype(np.float32)

    porcelain_cool = PORCELAIN_LIN * np.array([0.94, 0.97, 1.02], dtype=np.float32)
    albedo = porcelain_cool[None, :] * (1.0 - is_ribbon[:, None]) + AZURE_LIN[None, :] * is_ribbon[:, None]
    albedo = albedo * (1.0 - is_gold[:, None]) + GOLD_LIN[None, :] * is_gold[:, None]

    roughness = 0.34 * (1.0 - is_ribbon) + 0.22 * is_ribbon
    roughness = roughness * (1.0 - is_gold) + 0.25 * is_gold
    metallic = 0.0 * (1.0 - is_gold) + 0.75 * is_gold
    clearcoat = 0.14 * (1.0 - is_ribbon) + 0.58 * is_ribbon
    clamp_snow = 1.0 - is_ribbon

    srgb_hits = shade_modular_pbr(
        p=hit_pos,
        n=n,
        v=-hit_rd,
        albedo=albedo,
        roughness=roughness,
        metallic=metallic,
        ao=ao,
        shadow_sdf=sdf_full_box_world,
        clearcoat=clearcoat,
        clamp_snow_mask=clamp_snow,
    )

    hi_rgb = np.zeros((hi_res * hi_res, 3), dtype=np.float32)
    hi_alpha = np.zeros((hi_res * hi_res,), dtype=np.float32)
    flat_idx = np.where(hit_mask.ravel())[0]
    hi_rgb[flat_idx] = srgb_hits
    hi_alpha[flat_idx] = 1.0

    rgba = downsample_ssaa_rgba(hi_rgb, hi_alpha)
    save_layer(rgba, "Step 3 Front Rim (z=4)", out_path, t0)
    return rgba


# ==============================================================================
# LAYER 4 (z=5): FLOATING DETACHED LID + 3D AZURE BLUE RIBBON BOW
# ==============================================================================
def render_lid_flying(cam_pos, rd, out_path: str) -> np.ndarray:
    t0 = time.time()
    hi_res = CANVAS_SIZE * SSAA
    bound_center = LID_WORLD_OFFSET + np.array([0.0, 0.12, 0.0], dtype=np.float32)
    hit_mask, hit_pos, hit_rd = raymarch_layer(
        hi_res, cam_pos, rd, sdf_lid_world, bound_center, bound_radius=1.25
    )

    n = compute_normals(hit_pos, sdf_lid_world)
    ao = compute_ao(hit_pos, n, sdf_lid_world, strength=1.75)

    pl = world_to_lid(hit_pos)
    d_lid, d_rib = sdf_lid_parts_local(pl)
    is_ribbon = (d_rib <= d_lid + 1e-4).astype(np.float32)

    # Gold edge trim (#F59E0B) along the crossed lid ribbon bands (below the bow)
    on_band = (is_ribbon > 0.5) & (pl[:, 1] < LID_H * 0.5 + RIBBON_THICK + 0.01)
    edge_x = np.abs(np.abs(pl[:, 0]) - (RIBBON_HALF_W - 0.014)) < 0.007
    edge_z = np.abs(np.abs(pl[:, 2]) - (RIBBON_HALF_W - 0.014)) < 0.007
    # Exclude center intersection where bow sits
    outside_knot = np.hypot(pl[:, 0], pl[:, 2]) > 0.16
    is_gold = (on_band & outside_knot & (edge_x | edge_z)).astype(np.float32)

    # Deepen GS SHOP Azure Blue (#0F78FF) into darker folds (#034694) using AO + knot/cavity depth
    # Enhances satin fabric fold realism without losing brand azure vibrancy
    y_top = LID_H * 0.5 + RIBBON_THICK
    on_bow = (is_ribbon > 0.5) & (pl[:, 1] >= y_top - 0.005)
    nl = n @ R_WORLD_TO_LID.T
    # Fold darkness driven by occlusion (1 - ao) and inner downward-facing loop surfaces
    fold_depth = np.clip((1.0 - ao) * 1.45 + np.clip(-nl[:, 1], 0.0, 1.0) * 0.45, 0.0, 1.0)
    # Extra subtle fold deepening inside knot gathers
    r_knot = np.hypot(pl[:, 0], pl[:, 2])
    fold_depth = np.clip(fold_depth + 0.25 * np.exp(-r_knot * 6.5) * on_bow.astype(np.float32), 0.0, 0.92)[:, None]
    azure_fabric = AZURE_LIN[None, :] * (1.0 - fold_depth) + AZURE_FOLD_LIN[None, :] * fold_depth

    porcelain_cool = PORCELAIN_LIN * np.array([0.94, 0.97, 1.02], dtype=np.float32)
    albedo = porcelain_cool[None, :] * (1.0 - is_ribbon[:, None]) + azure_fabric * is_ribbon[:, None]
    albedo = albedo * (1.0 - is_gold[:, None]) + GOLD_LIN[None, :] * is_gold[:, None]

    # Satin Silk PBR: roughness 0.37 (within 0.35-0.40), ZERO plastic clearcoat dots!
    roughness = 0.34 * (1.0 - is_ribbon) + 0.37 * is_ribbon
    roughness = roughness * (1.0 - is_gold) + 0.24 * is_gold
    metallic = 0.0 * (1.0 - is_gold) + 0.78 * is_gold
    clearcoat = 0.12 * (1.0 - is_ribbon)  # zero clearcoat on satin silk bow/ribbons
    clamp_snow = 1.0 - is_ribbon

    # Radial/longitudinal tangent field for anisotropic silk sheen sweeping across bow loops
    rad_local = normalize3(np.stack([pl[:, 0] + 1e-4, np.zeros_like(pl[:, 1]), pl[:, 2] + 1e-4], axis=-1))
    satin_tangent = normalize3(rad_local @ R_LID_TO_WORLD.T)
    satin_aniso_mask = is_ribbon * (1.0 - is_gold)

    srgb_hits = shade_modular_pbr(
        p=hit_pos,
        n=n,
        v=-hit_rd,
        albedo=albedo,
        roughness=roughness,
        metallic=metallic,
        ao=ao,
        shadow_sdf=sdf_lid_world,
        clearcoat=clearcoat,
        clamp_snow_mask=clamp_snow,
        satin_aniso_mask=satin_aniso_mask,
        satin_tangent=satin_tangent,
    )

    hi_rgb = np.zeros((hi_res * hi_res, 3), dtype=np.float32)
    hi_alpha = np.zeros((hi_res * hi_res,), dtype=np.float32)
    flat_idx = np.where(hit_mask.ravel())[0]
    hi_rgb[flat_idx] = srgb_hits
    hi_alpha[flat_idx] = 1.0

    rgba = downsample_ssaa_rgba(hi_rgb, hi_alpha)
    save_layer(rgba, "Step 4 Floating Lid (z=5)", out_path, t0)
    return rgba


# ==============================================================================
# STEP 5: COMPOSITING VERIFICATION MOCKUP (z=1 -> z=2 -> z=3 product -> z=4 -> z=5)
# ==============================================================================
def build_compositing_verification(
    shadow_rgba: np.ndarray,
    back_rgba: np.ndarray,
    front_rgba: np.ndarray,
    lid_rgba: np.ndarray,
    out_path: str,
) -> None:
    """
    Stack all 4 layers at 1:1 origin with a 3D-shaded placeholder tangerine/gift
    product tucked at z-index 3 to verify physical cavity tucking & rim occlusion.
    """
    # Light cool-winter studio background for visual verification
    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (235, 244, 255, 255))

    # z=1: Contact shadow
    canvas = Image.alpha_composite(canvas, Image.fromarray(shadow_rgba, "RGBA"))
    # z=2: Back interior cavity
    canvas = Image.alpha_composite(canvas, Image.fromarray(back_rgba, "RGBA"))

    # z=3: Placeholder hero products (Jeju tangerine sphere + product pack tucked inside cavity)
    prod = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(prod)
    # Soft product pack box on left-center inside cavity
    draw.rounded_rectangle([395, 360, 575, 650], radius=24, fill=(37, 99, 235, 255), outline=(255, 255, 255, 230), width=5)
    # Bright Jeju tangerine placeholder sphere on right-center inside cavity
    cx, cy, r = 610, 485, 118
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(249, 115, 22, 255), outline=(255, 237, 213, 255), width=4)
    # Specular dot on tangerine
    draw.ellipse([cx - 65, cy - 72, cx - 22, cy - 35], fill=(255, 237, 213, 210))
    # Label text
    draw.text((425, 455), "Z-INDEX 3\nPRODUCT", fill=(255, 255, 255, 255))
    canvas = Image.alpha_composite(canvas, prod)

    # z=4: Front rim & Azure ribbons (occludes bottom 15-25% of z=3 products!)
    canvas = Image.alpha_composite(canvas, Image.fromarray(front_rgba, "RGBA"))
    # z=5: Floating lid with 3D bow
    canvas = Image.alpha_composite(canvas, Image.fromarray(lid_rgba, "RGBA"))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.convert("RGB").save(out_path, optimize=True)
    print(f"[MODULAR-BOX] Compositing verification mockup saved -> {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="DIR-FORGE-MODULAR-GIFTBOX-020")
    parser.add_argument(
        "--only",
        choices=["all", "shadow", "back", "front", "lid", "verify"],
        default="all",
    )
    parser.add_argument(
        "--verify-out",
        default=os.path.join("out", "modular_giftbox_compositing_verify.png"),
    )
    args = parser.parse_args()

    cam_pos, right, up, forward, fov_scale = build_shared_camera()
    rd = generate_camera_rays(CANVAS_SIZE * SSAA, cam_pos, right, up, forward, fov_scale)

    p_shadow = os.path.join(OUT_DIR, "decor_box_contact_shadow.png")
    p_back = os.path.join(OUT_DIR, "decor_box_back_interior.png")
    p_front = os.path.join(OUT_DIR, "decor_box_front_rim.png")
    p_lid = os.path.join(OUT_DIR, "decor_box_lid_flying.png")

    shadow_rgba = render_contact_shadow(cam_pos, rd, p_shadow) if args.only in ("all", "shadow") else np.array(Image.open(p_shadow).convert("RGBA"))
    back_rgba = render_back_interior(cam_pos, rd, p_back) if args.only in ("all", "back") else np.array(Image.open(p_back).convert("RGBA"))
    front_rgba = render_front_rim(cam_pos, rd, p_front) if args.only in ("all", "front") else np.array(Image.open(p_front).convert("RGBA"))
    lid_rgba = render_lid_flying(cam_pos, rd, p_lid) if args.only in ("all", "lid") else np.array(Image.open(p_lid).convert("RGBA"))

    if args.only in ("all", "verify"):
        build_compositing_verification(shadow_rgba, back_rgba, front_rgba, lid_rgba, args.verify_out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
