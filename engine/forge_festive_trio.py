#!/usr/bin/env python3
"""
DIR-FORGE-FESTIVE-TRIO-019: Procedural 3D Festive Decors Generator
Generates 1024x1024 native RGBA (alpha=0) 3D PBR assets directly via
vectorized 3D Signed Distance Field (SDF) raymarching + Cook-Torrance GGX PBR.

Assets:
  - assets/brands/gsshop/decors/decor_snowflake.png
  - assets/brands/gsshop/decors/decor_candy_cane.png
  - assets/brands/gsshop/decors/decor_bauble.png
"""

from __future__ import annotations

import argparse
import math
import os
import time
from typing import Callable, Tuple

import numpy as np
from PIL import Image

# ==============================================================================
# LOCKED BRAND PALETTE (GS SHOP - DIR-FORGE-FESTIVE-TRIO-019)
# ==============================================================================
PRIMARY_AZURE_HEX = (15, 120, 255)      # #0F78FF
SNOW_WHITE_HEX = (237, 242, 247)        # #EDF2F7 (Clamped Base & Highlight Ceiling)
AMBIENT_ICE_HEX = (224, 242, 254)       # #E0F2FE (Ambient Cool Ice)
METALLIC_CAP_HEX = (226, 232, 240)      # #E2E8F0 (Metallic Hanger Cap)
SOFT_AZURE_SHADOW_ALPHA = 0.15          # rgba(15, 120, 255, 0.15)

CANVAS_SIZE = 1024
SAFE_MARGIN_PX = 40
SSAA = 2  # 2x2 supersampling (2048x2048 -> 1024x1024 premultiplied box downsample)

OUT_DIR = os.path.join("assets", "brands", "gsshop", "decors")


def srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * (c ** (1.0 / 2.4)) - 0.055)


def hex_to_lin(rgb_u8: Tuple[int, int, int]) -> np.ndarray:
    return srgb_to_linear(np.array(rgb_u8, dtype=np.float32) / 255.0)


AZURE_LIN = hex_to_lin(PRIMARY_AZURE_HEX)
SNOW_LIN = hex_to_lin(SNOW_WHITE_HEX)
ICE_LIN = hex_to_lin(AMBIENT_ICE_HEX)
METAL_LIN = hex_to_lin(METALLIC_CAP_HEX)
SNOW_SRGB_CLAMP = np.array(SNOW_WHITE_HEX, dtype=np.float32) / 255.0


# ==============================================================================
# VECTORIZED 3D MATH & SDF PRIMITIVES
# ==============================================================================
def normalize3(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(norm, 1e-8)


def dot3(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sum(a * b, axis=-1)


def smin_poly(a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """Polynomial smooth minimum for organic porcelain/clay fillets."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1.0 - h) + a * h - k * h * (1.0 - h)


def sd_capsule(p: np.ndarray, a: np.ndarray, b: np.ndarray, r: float) -> np.ndarray:
    pa = p - a
    ba = b - a
    h = np.clip(np.sum(pa * ba, axis=-1) / float(np.dot(ba, ba)), 0.0, 1.0)
    return np.linalg.norm(pa - ba * h[..., None], axis=-1) - r


def sd_hex_prism(p: np.ndarray, h_rad: float, h_z: float) -> np.ndarray:
    """Exact 3D hexagonal prism aligned along Z."""
    k = np.array([-0.8660254, 0.5, 0.57735027], dtype=np.float32)
    px = np.abs(p[..., 0])
    py = np.abs(p[..., 1])
    pz = np.abs(p[..., 2])
    dot_kp = 2.0 * np.minimum(k[0] * px + k[1] * py, 0.0)
    px = px - dot_kp * k[0]
    py = py - dot_kp * k[1]
    dx = px - np.clip(px, -k[2] * h_rad, k[2] * h_rad)
    dy = py - h_rad
    d_xy = np.hypot(dx, dy) * np.sign(dy)
    d_z = pz - h_z
    return np.minimum(np.maximum(d_xy, d_z), 0.0) + np.hypot(
        np.maximum(d_xy, 0.0), np.maximum(d_z, 0.0)
    )


def sd_rounded_cylinder(p: np.ndarray, ra: float, rb: float, h: float) -> np.ndarray:
    """Cylinder along Y axis with radius ra, corner bevel rb, half-height h."""
    dx = np.hypot(p[..., 0], p[..., 2]) - 2.0 * ra + rb
    dy = np.abs(p[..., 1]) - h
    return (
        np.minimum(np.maximum(dx, dy), 0.0)
        + np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
        - rb
    )


def sd_torus_xy(p: np.ndarray, R: float, r: float) -> np.ndarray:
    """Torus lying in the XY plane (ring hole along Z)."""
    qx = np.hypot(p[..., 0], p[..., 1]) - R
    qz = p[..., 2]
    return np.hypot(qx, qz) - r


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
# COOK-TORRANCE GGX PBR SHADER (CAVP-v2.0 ALBEDO CLAMPED)
# ==============================================================================
def shade_pbr(
    p: np.ndarray,
    n: np.ndarray,
    v: np.ndarray,
    albedo: np.ndarray,
    roughness: np.ndarray,
    metallic: np.ndarray,
    ao: np.ndarray,
    sdf_fn: Callable[[np.ndarray], np.ndarray],
    clearcoat: np.ndarray | None = None,
    clamp_snow_mask: np.ndarray | None = None,
    enable_self_shadow: bool = True,
) -> np.ndarray:
    """
    Physically-based GGX Cook-Torrance shader with studio 3-point + cool-ice IBL
    and azure-tinted soft ambient occlusion. Returns sRGB float in [0, 1].
    """
    N = normalize3(n)
    V = normalize3(v)
    NdotV = np.clip(dot3(N, V), 1e-4, 1.0)

    r = np.clip(roughness, 0.04, 1.0)[..., None]
    m = np.clip(metallic, 0.0, 1.0)[..., None]
    a2 = (r * r) ** 2

    # Dielectric F0 = 0.04, metallic uses albedo
    F0 = 0.04 * (1.0 - m) + albedo * m

    # Studio Lights (top-left key, cool-ice right fill, soft top-back rim)
    lights = [
        (normalize3(np.array([-0.55, 0.72, 0.80], dtype=np.float32)), np.array([2.25, 2.28, 2.32], dtype=np.float32), True),
        (normalize3(np.array([0.78, -0.18, 0.60], dtype=np.float32)), ICE_LIN * 0.92, False),
        (normalize3(np.array([0.35, 0.65, -0.55], dtype=np.float32)), np.array([0.45, 0.70, 1.05], dtype=np.float32) * 0.55, False),
    ]

    color = np.zeros_like(albedo)

    for L_dir, L_col, cast_shadow in lights:
        L = L_dir[None, :]
        H = normalize3(L + V)
        NdotL = np.clip(dot3(N, L), 0.0, 1.0)[..., None]
        NdotH = np.clip(dot3(N, H), 0.0, 1.0)[..., None]
        HdotV = np.clip(dot3(H, V), 0.0, 1.0)[..., None]

        # Soft shadow march for key light
        sh = 1.0
        if cast_shadow and enable_self_shadow:
            sh = np.ones(p.shape[0], dtype=np.float32)
            t_sh = np.full(p.shape[0], 0.025, dtype=np.float32)
            for _ in range(14):
                ps = p + L * t_sh[:, None]
                d_sh = sdf_fn(ps)
                sh = np.minimum(sh, np.clip(6.0 * d_sh / t_sh, 0.0, 1.0))
                t_sh = t_sh + np.clip(d_sh, 0.02, 0.25)
            # Soft studio shadow floor so shadows stay luminous & clean
            sh = (0.45 + 0.55 * sh)[:, None]

        # GGX Normal Distribution
        denom = (NdotH * NdotH) * (a2 - 1.0) + 1.0
        D = a2 / (math.pi * denom * denom + 1e-6)

        # Schlick-GGX Geometry
        k_g = ((r + 1.0) ** 2) / 8.0
        G_V = NdotV[..., None] / (NdotV[..., None] * (1.0 - k_g) + k_g)
        G_L = NdotL / (NdotL * (1.0 - k_g) + k_g)
        G = G_V * G_L

        # Fresnel-Schlick
        F = F0 + (1.0 - F0) * ((1.0 - HdotV) ** 5)

        spec = (D * G * F) / (4.0 * NdotV[..., None] * NdotL + 1e-4)
        kD = (1.0 - F) * (1.0 - m)
        diff = kD * albedo / math.pi

        color += (diff + spec) * L_col[None, :] * NdotL * sh

        # Optional glossy clearcoat layer (key light only for lush top-left studio highlight)
        if clearcoat is not None and cast_shadow:
            cc = clearcoat[..., None]
            a2_cc = 0.135 ** 4
            denom_cc = (NdotH * NdotH) * (a2_cc - 1.0) + 1.0
            D_cc = a2_cc / (math.pi * denom_cc * denom_cc + 1e-6)
            F_cc = 0.04 + 0.96 * ((1.0 - HdotV) ** 5)
            spec_cc = (D_cc * F_cc * 0.42) / (4.0 * NdotV[..., None] * NdotL + 0.08)
            color += cc * spec_cc * L_col[None, :] * NdotL * sh

    # Studio Environment / Hemisphere IBL
    # Sky = Ambient Cool Ice (#E0F2FE), Ground = Azure-tinted cool ambient bounce
    up = np.clip(N[:, 1] * 0.5 + 0.5, 0.0, 1.0)[..., None]
    ground_col = ICE_LIN * (1.0 - SOFT_AZURE_SHADOW_ALPHA) + AZURE_LIN * SOFT_AZURE_SHADOW_ALPHA
    hemi_env = ground_col[None, :] * (1.0 - up) + ICE_LIN[None, :] * up

    # Apply AO with subtle azure crevice tinting (rgba(15, 120, 255, 0.15))
    ao_col = ao[..., None] * np.ones((1, 3), dtype=np.float32)
    ao_tinted = ao_col + (1.0 - ao_col) * (AZURE_LIN[None, :] * 0.28)
    ambient_diff = (1.0 - m) * albedo * hemi_env * 0.62 * ao_tinted

    # Environment specular reflection (crucial for metallic cap & glossy highlights)
    R = normalize3(2.0 * NdotV[..., None] * N - V)
    # Procedural studio softbox environment map for crisp metallic reflections
    rx, ry, rz = R[:, 0], R[:, 1], R[:, 2]
    env_grad = np.clip(ry * 0.5 + 0.5, 0.0, 1.0)[..., None]
    env_col = (
        np.array([0.28, 0.36, 0.48], dtype=np.float32)[None, :] * (1.0 - env_grad)
        + ICE_LIN[None, :] * 0.95 * env_grad
    )
    # Top-left studio softbox reflection
    sb1 = np.exp(-6.5 * ((rx + 0.45) ** 2 + (ry - 0.58) ** 2 + (rz - 0.68) ** 2))[..., None]
    # Right-side studio strip reflection
    sb2 = np.exp(-9.0 * ((rx - 0.72) ** 2 + (ry - 0.12) ** 2 + (rz - 0.55) ** 2))[..., None]
    env_spec_col = env_col + sb1 * 1.45 + sb2 * 0.65 * ICE_LIN[None, :]

    # Keep dielectric grazing reflection subtle so blue edges never wash out to gray
    F_env = F0 + (np.maximum(1.0 - r, F0) - F0) * ((1.0 - NdotV[..., None]) ** 5)
    spec_env_weight = np.where(m > 0.5, 0.92, 0.24)
    ambient_spec = F_env * env_spec_col * spec_env_weight * ao[..., None]

    # Subtle subsurface/wrap bounce for soft porcelain/clay feel
    wrap_ndotl = np.clip((dot3(N, lights[0][0][None, :]) + 0.45) / 1.45, 0.0, 1.0)[..., None]
    soft_wrap = (1.0 - m) * albedo * ICE_LIN[None, :] * wrap_ndotl * 0.14 * ao_tinted

    lin_final = color + ambient_diff + ambient_spec + soft_wrap

    # Filmic-soft shoulder tone mapping (preserves saturation without gray washout)
    # Use gentle Reinhard-extended so #0F78FF stays vivid and #EDF2F7 stays crisp
    lin_mapped = lin_final / (1.0 + lin_final * 0.18)
    srgb = linear_to_srgb(lin_mapped)

    # Strict PBR Albedo Clamp on snow-white surfaces to #EDF2F7 (237, 242, 247)
    if clamp_snow_mask is not None:
        cm = clamp_snow_mask[..., None]
        clamped = np.minimum(srgb, SNOW_SRGB_CLAMP[None, :])
        srgb = srgb * (1.0 - cm) + clamped * cm

    return np.clip(srgb, 0.0, 1.0)


# ==============================================================================
# CORE 3D RAYMARCHER + AUTO-FRAMER (EXACT 40PX MARGIN, CENTERED, NATIVE ALPHA=0)
# ==============================================================================
def compute_normals(p: np.ndarray, sdf_fn: Callable[[np.ndarray], np.ndarray], eps: float = 1.5e-3) -> np.ndarray:
    """Tetrahedron finite-difference normals (4 SDF evals instead of 6)."""
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
    """5-tap SDF Ambient Occlusion."""
    occ = np.zeros(p.shape[0], dtype=np.float32)
    sca = 1.0
    for i in range(1, 6):
        h = 0.025 + 0.065 * i
        d = sdf_fn(p + n * h)
        occ += (h - d) * sca
        sca *= 0.62
    return np.clip(1.0 - 1.75 * occ, 0.22, 1.0)


def raymarch_grid(
    res: int,
    cam_pos: np.ndarray,
    fov_scale: float,
    center_offset_xy: Tuple[float, float],
    sdf_fn: Callable[[np.ndarray], np.ndarray],
    bound_radius: float = 1.65,
    max_steps: int = 72,
    hit_eps: float = 6e-4,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Raymarch a res x res grid onto native transparent canvas.
    Returns (hit_mask [res, res], hit_pos [N_hit, 3], ray_dir [N_hit, 3]).
    """
    lin = (np.arange(res, dtype=np.float32) + 0.5) / res * 2.0 - 1.0
    gx, gy = np.meshgrid(lin, -lin)  # +Y is up

    # Ray directions through image plane with centered offset
    rd_x = gx * fov_scale + center_offset_xy[0]
    rd_y = gy * fov_scale + center_offset_xy[1]
    rd_z = np.full_like(rd_x, -1.0)
    rd = np.stack([rd_x, rd_y, rd_z], axis=-1).reshape(-1, 3)
    rd = normalize3(rd)

    ro = np.broadcast_to(cam_pos[None, :], rd.shape).copy()

    # Analytic ray-bounding-sphere cull to skip empty background immediately
    oc = ro
    b = dot3(oc, rd)
    c = dot3(oc, oc) - bound_radius * bound_radius
    disc = b * b - c
    active_idx = np.where(disc >= 0.0)[0]

    hit_mask_flat = np.zeros(res * res, dtype=bool)
    if len(active_idx) == 0:
        return hit_mask_flat.reshape(res, res), np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.float32)

    t_near = np.maximum(-b[active_idx] - np.sqrt(np.maximum(disc[active_idx], 0.0)), 0.05)
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

    # Sort by flat pixel index for deterministic ordering
    order = np.argsort(all_hit_idx)
    all_hit_idx = all_hit_idx[order]
    all_hit_t = all_hit_t[order]

    hit_mask_flat[all_hit_idx] = True
    hit_rd = rd[all_hit_idx]
    hit_pos = cam_pos[None, :] + hit_rd * all_hit_t[:, None]

    return hit_mask_flat.reshape(res, res), hit_pos, hit_rd


def auto_frame_camera(
    sdf_fn: Callable[[np.ndarray], np.ndarray],
    cam_z: float = 4.2,
    bound_radius: float = 1.65,
) -> Tuple[np.ndarray, float, Tuple[float, float]]:
    """
    Fast 192x192 silhouette probe to compute exact fov_scale and center offset
    so the rendered object fits centered in 1024x1024 with exact 40px safe margin.
    """
    cam_pos = np.array([0.0, 0.0, cam_z], dtype=np.float32)
    probe_res = 256
    init_fov = 0.42
    mask, _, _ = raymarch_grid(
        probe_res, cam_pos, init_fov, (0.0, 0.0), sdf_fn, bound_radius=bound_radius, max_steps=64
    )
    ys, xs = np.where(mask)
    if len(xs) == 0:
        raise RuntimeError("Auto-framing probe found empty SDF!")

    # Convert pixel bounds to ray-plane coordinates (gx*init_fov, gy*init_fov)
    x_min_n = ((xs.min() + 0.5) / probe_res * 2.0 - 1.0) * init_fov
    x_max_n = ((xs.max() + 0.5) / probe_res * 2.0 - 1.0) * init_fov
    y_max_n = -((ys.min() + 0.5) / probe_res * 2.0 - 1.0) * init_fov
    y_min_n = -((ys.max() + 0.5) / probe_res * 2.0 - 1.0) * init_fov

    cx = 0.5 * (x_min_n + x_max_n)
    cy = 0.5 * (y_min_n + y_max_n)
    half_w = 0.5 * (x_max_n - x_min_n)
    half_h = 0.5 * (y_max_n - y_min_n)
    max_half = max(half_w, half_h)

    # Target normalized span inside 1024x1024 with exact 40px safe margin:
    # Inner span = 1024 - 2*40 = 944 px -> half-span = 944 / 1024 = 0.921875
    target_half_norm = (CANVAS_SIZE - 2 * SAFE_MARGIN_PX) / CANVAS_SIZE
    fov_scale = max_half / target_half_norm
    return cam_pos, float(fov_scale), (float(cx), float(cy))


def render_sdf_asset(
    name: str,
    sdf_fn: Callable[[np.ndarray], np.ndarray],
    material_fn: Callable[[np.ndarray, np.ndarray], dict],
    out_path: str,
    cam_z: float = 4.2,
    bound_radius: float = 1.65,
    enable_self_shadow: bool = True,
) -> None:
    t0 = time.time()
    print(f"\n[FORGE] Rendering {name} -> {out_path} ({CANVAS_SIZE}x{CANVAS_SIZE}, {SSAA}x SSAA)...")

    cam_pos, fov_scale, center_xy = auto_frame_camera(sdf_fn, cam_z=cam_z, bound_radius=bound_radius)
    hi_res = CANVAS_SIZE * SSAA

    hit_mask, hit_pos, hit_rd = raymarch_grid(
        hi_res,
        cam_pos,
        fov_scale,
        center_xy,
        sdf_fn,
        bound_radius=bound_radius,
        max_steps=84,
        hit_eps=5e-4,
    )

    n = compute_normals(hit_pos, sdf_fn, eps=1.4e-3)
    ao = compute_ao(hit_pos, n, sdf_fn)
    mat = material_fn(hit_pos, n)

    srgb_hits = shade_pbr(
        p=hit_pos,
        n=n,
        v=-hit_rd,
        albedo=mat["albedo"],
        roughness=mat["roughness"],
        metallic=mat["metallic"],
        ao=ao,
        sdf_fn=sdf_fn,
        clearcoat=mat.get("clearcoat"),
        clamp_snow_mask=mat.get("clamp_snow_mask"),
        enable_self_shadow=enable_self_shadow,
    )

    # Assemble high-res premultiplied RGBA on empty alpha=0 canvas
    hi_rgb = np.zeros((hi_res * hi_res, 3), dtype=np.float32)
    hi_alpha = np.zeros((hi_res * hi_res,), dtype=np.float32)
    flat_idx = np.where(hit_mask.ravel())[0]
    hi_rgb[flat_idx] = srgb_hits
    hi_alpha[flat_idx] = 1.0

    hi_rgb = hi_rgb.reshape(CANVAS_SIZE, SSAA, CANVAS_SIZE, SSAA, 3)
    hi_alpha = hi_alpha.reshape(CANVAS_SIZE, SSAA, CANVAS_SIZE, SSAA)

    # Premultiplied 2x2 box downsample -> pure unpremultiplied straight RGBA (ZERO halo!)
    premul = hi_rgb * hi_alpha[..., None]
    out_alpha = hi_alpha.mean(axis=(1, 3))
    out_premul = premul.mean(axis=(1, 3))

    out_rgb = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 3), dtype=np.float32)
    nz = out_alpha > 1e-6
    out_rgb[nz] = out_premul[nz] / out_alpha[nz, None]
    out_rgb = np.clip(out_rgb, 0.0, 1.0)

    rgba = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 4), dtype=np.uint8)
    rgba[..., :3] = np.round(out_rgb * 255.0).astype(np.uint8)
    rgba[..., 3] = np.round(out_alpha * 255.0).astype(np.uint8)

    # Exact centering & 40px safe margin verification (pixel-exact shift if off by 1-2px)
    ys, xs = np.where(rgba[..., 3] > 0)
    ymin, ymax, xmin, xmax = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    obj_w = xmax - xmin + 1
    obj_h = ymax - ymin + 1
    crop = rgba[ymin : ymax + 1, xmin : xmax + 1]

    # If the probe was off by > 2px from exact 944px max span, resize with premultiplied BILINEAR
    # (no Lanczos ringing halo outside the 1px AA contour!)
    target_span = CANVAS_SIZE - 2 * SAFE_MARGIN_PX
    max_dim = max(obj_w, obj_h)
    if abs(max_dim - target_span) > 2:
        scale = target_span / max_dim
        new_w = max(1, int(round(obj_w * scale)))
        new_h = max(1, int(round(obj_h * scale)))
        c_f = crop.astype(np.float32) / 255.0
        a_f = c_f[..., 3:4]
        p_rgb = Image.fromarray(np.round(c_f[..., :3] * a_f * 255.0).astype(np.uint8), "RGB").resize(
            (new_w, new_h), Image.Resampling.BILINEAR
        )
        p_a = Image.fromarray(crop[..., 3], "L").resize((new_w, new_h), Image.Resampling.BILINEAR)
        pr = np.array(p_rgb, dtype=np.float32) / 255.0
        pa = np.array(p_a, dtype=np.float32) / 255.0
        unp = np.zeros_like(pr)
        m_nz = pa > 1e-4
        unp[m_nz] = np.clip(pr[m_nz] / pa[m_nz, None], 0.0, 1.0)
        crop = np.zeros((new_h, new_w, 4), dtype=np.uint8)
        crop[..., :3] = np.round(unp * 255.0).astype(np.uint8)
        crop[..., 3] = np.array(p_a, dtype=np.uint8)
        obj_h, obj_w = new_h, new_w

    final_canvas = np.zeros((CANVAS_SIZE, CANVAS_SIZE, 4), dtype=np.uint8)
    x0 = (CANVAS_SIZE - obj_w) // 2
    y0 = (CANVAS_SIZE - obj_h) // 2
    final_canvas[y0 : y0 + obj_h, x0 : x0 + obj_w] = crop

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    Image.fromarray(final_canvas, "RGBA").save(out_path, optimize=True)

    f_ys, f_xs = np.where(final_canvas[..., 3] > 0)
    m_top = int(f_ys.min())
    m_bot = CANVAS_SIZE - 1 - int(f_ys.max())
    m_left = int(f_xs.min())
    m_right = CANVAS_SIZE - 1 - int(f_xs.max())
    print(
        f"[FORGE] Done {name} in {time.time() - t0:.2f}s | "
        f"bbox=({f_xs.min()},{f_ys.min()})..({f_xs.max()},{f_ys.max()}) | "
        f"margins T={m_top} B={m_bot} L={m_left} R={m_right} px"
    )


# ==============================================================================
# TICKET 2: 3D WINTER SNOWFLAKE (Porcelain/Clay 6-fold radial, beveled, soft AO)
# ==============================================================================
def build_snowflake():
    # Subtle 3D tilt so beveled porcelain depth & side thickness catch studio light
    R_pose = (rot_y(-11.0) @ rot_x(9.0)).T  # inverse rotation for SDF evaluation

    def sdf_snowflake(p: np.ndarray) -> np.ndarray:
        q = p @ R_pose

        # 6-fold rotational + mirror symmetry (D6 dihedral fold in XY)
        ang = np.arctan2(q[:, 1], q[:, 0])
        sector = math.pi / 3.0
        # Rotate by pi/2 so main arms point vertically up/down (classic iconic pose)
        ang_s = ((ang - math.pi / 2.0 + sector * 0.5) % sector) - sector * 0.5
        rad = np.hypot(q[:, 0], q[:, 1])

        # Folded local coordinates: +X along main arm, +Y mirrored side
        lx = rad * np.cos(ang_s)
        ly = np.abs(rad * np.sin(ang_s))
        # Slightly flatten Z (0.72) for plump porcelain ornament thickness (not spindly)
        lz = q[:, 2] * 1.18
        lp = np.stack([lx, ly, lz], axis=-1)

        # 1. Soft rounded center hexagon hub (beveled edges)
        d_hex = sd_hex_prism(
            np.stack([q[:, 0], q[:, 1], q[:, 2] * 1.15], axis=-1),
            h_rad=0.24,
            h_z=0.075,
        ) - 0.065

        # 2. Thick rounded main arm (capsule from center to tip)
        d_main = sd_capsule(
            lp,
            np.array([0.06, 0.0, 0.0], dtype=np.float32),
            np.array([0.96, 0.0, 0.0], dtype=np.float32),
            0.092,
        )

        # 3. Inner chevron branch (at 60 degrees, clean separation from neighboring arm)
        c60, s60 = math.cos(math.pi / 3.0), math.sin(math.pi / 3.0)
        b1_a = np.array([0.39, 0.0, 0.0], dtype=np.float32)
        b1_b = b1_a + np.array([c60, s60, 0.0], dtype=np.float32) * 0.24
        d_b1 = sd_capsule(lp, b1_a, b1_b, 0.070)

        # 4. Outer chevron branch (shorter, plump rounded tip, cleanly above bottom 15% band)
        b2_a = np.array([0.60, 0.0, 0.0], dtype=np.float32)
        b2_b = b2_a + np.array([c60, s60, 0.0], dtype=np.float32) * 0.17
        d_b2 = sd_capsule(lp, b2_a, b2_b, 0.060)

        # 5. Subtle central porcelain boss/button dome on hexagon face
        d_hub = np.linalg.norm(
            np.stack([q[:, 0], q[:, 1], q[:, 2] * 1.35], axis=-1), axis=-1
        ) - 0.18

        # Smooth porcelain/clay unions (plump beveled fillets)
        d = smin_poly(d_hex, d_main, 0.070)
        d = smin_poly(d, d_b1, 0.050)
        d = smin_poly(d, d_b2, 0.044)
        d = smin_poly(d, d_hub, 0.055)

        # Correct distance lipshitz factor for slight Z-squash
        return d * 0.82

    def mat_snowflake(p: np.ndarray, n: np.ndarray) -> dict:
        N = p.shape[0]
        # Smooth porcelain/clay snow-white base (#EDF2F7) with ultra-subtle cool-ice sheen
        albedo = np.broadcast_to(SNOW_LIN[None, :], (N, 3)).copy()
        roughness = np.full(N, 0.34, dtype=np.float32)
        metallic = np.zeros(N, dtype=np.float32)
        clearcoat = np.full(N, 0.18, dtype=np.float32)
        clamp_snow_mask = np.ones(N, dtype=np.float32)
        return {
            "albedo": albedo,
            "roughness": roughness,
            "metallic": metallic,
            "clearcoat": clearcoat,
            "clamp_snow_mask": clamp_snow_mask,
        }

    return sdf_snowflake, mat_snowflake


# ==============================================================================
# TICKET 3: 3D GLOSSY CANDY CANE (Classic J-hook, Azure + Clamped White spirals)
# ==============================================================================
def build_candy_cane():
    # Classic upright J-hook with subtle 3D studio turn for rich tubular volume
    R_pose = (rot_y(16.0) @ rot_x(6.0)).T

    # J-hook centerline geometry in local XY plane (Z=0):
    # - Straight shaft: from (x=+R_arc, y=-L_shaft) up to (x=+R_arc, y=Y_top)
    # - Top semicircle arc: center (0, Y_top), radius R_arc, angle from 0 to pi
    # - Short hook tip: from (x=-R_arc, y=Y_top) down to (x=-R_arc, y=Y_top - L_tip)
    R_ARC = 0.34
    Y_TOP = 0.42
    L_SHAFT = 1.24  # shaft runs from y = Y_TOP - L_SHAFT = -0.82 to y = +0.42
    L_TIP = 0.22    # short hook tip runs from y = +0.42 down to +0.20
    R_TUBE = 0.165

    def eval_cane_coords(q: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Exact analytical distance, arc-length `s`, and tube angle `theta`
        for the 3-segment J-hook centerline.
        """
        qx, qy, qz = q[:, 0], q[:, 1], q[:, 2]

        # Segment 1: straight vertical shaft at x = +R_ARC, y in [Y_TOP - L_SHAFT, Y_TOP]
        y1 = np.clip(qy, Y_TOP - L_SHAFT, Y_TOP)
        dx1 = qx - R_ARC
        dy1 = qy - y1
        d1 = np.sqrt(dx1 * dx1 + dy1 * dy1 + qz * qz)
        s1 = y1 - (Y_TOP - L_SHAFT)
        # Tube normal frame: radial_x = dx1 (outward +X), radial_z = qz
        th1 = np.arctan2(qz, dx1)

        # Segment 2: upper semicircle arc centered at (0, Y_TOP), angle in [0, pi]
        ax = qx
        ay = qy - Y_TOP
        ang = np.arctan2(ay, ax)
        # Clamp angle into [0, pi]: negative angles snap to 0 if ax>=0 else pi
        ang_c = np.where(ang >= 0.0, ang, np.where(ax >= 0.0, 0.0, math.pi))
        cx = R_ARC * np.cos(ang_c)
        cy = Y_TOP + R_ARC * np.sin(ang_c)
        dx2 = qx - cx
        dy2 = qy - cy
        d2 = np.sqrt(dx2 * dx2 + dy2 * dy2 + qz * qz)
        s2 = L_SHAFT + R_ARC * ang_c
        # Outward radial along arc normal (cos(ang_c), sin(ang_c))
        rad2 = dx2 * np.cos(ang_c) + dy2 * np.sin(ang_c)
        th2 = np.arctan2(qz, rad2)

        # Segment 3: short hook tip at x = -R_ARC, y in [Y_TOP - L_TIP, Y_TOP]
        y3 = np.clip(qy, Y_TOP - L_TIP, Y_TOP)
        dx3 = qx - (-R_ARC)
        dy3 = qy - y3
        d3 = np.sqrt(dx3 * dx3 + dy3 * dy3 + qz * qz)
        s3 = L_SHAFT + math.pi * R_ARC + (Y_TOP - y3)
        # Outward radial at x = -R_ARC is -dx3 (continuous with arc at ang=pi!)
        th3 = np.arctan2(qz, -dx3)

        # Pick nearest segment
        use2 = d2 < d1
        d_min = np.where(use2, d2, d1)
        s_min = np.where(use2, s2, s1)
        th_min = np.where(use2, th2, th1)

        use3 = d3 < d_min
        d_min = np.where(use3, d3, d_min)
        s_min = np.where(use3, s3, s_min)
        th_min = np.where(use3, th3, th_min)

        return d_min - R_TUBE, s_min, th_min

    def sdf_candy_cane(p: np.ndarray) -> np.ndarray:
        q = p @ R_pose
        # Shift slightly so center of mass sits near origin
        q = q + np.array([-0.03, 0.06, 0.0], dtype=np.float32)
        d, _, _ = eval_cane_coords(q)
        return d

    def mat_candy_cane(p: np.ndarray, n: np.ndarray) -> dict:
        q = p @ R_pose + np.array([-0.03, 0.06, 0.0], dtype=np.float32)
        _, s, theta = eval_cane_coords(q)

        # Bold alternating diagonal spiral stripes (Azure #0F78FF & Clamped White #EDF2F7)
        # 1 full stripe period (blue + white) every ~0.58 units along the cane
        spiral_phase = (s / 0.56) + (theta / (2.0 * math.pi))
        wave = np.sin(2.0 * math.pi * spiral_phase)
        # Smooth anti-aliased stripe transition (no aliasing jaggedness)
        t_white = np.clip((wave + 0.06) / 0.12, 0.0, 1.0)
        t_white = t_white * t_white * (3.0 - 2.0 * t_white)

        albedo = AZURE_LIN[None, :] * (1.0 - t_white[:, None]) + SNOW_LIN[None, :] * t_white[:, None]
        # Glossy candy glaze finish
        roughness = np.full(p.shape[0], 0.17, dtype=np.float32)
        metallic = np.zeros(p.shape[0], dtype=np.float32)
        clearcoat = np.full(p.shape[0], 0.85, dtype=np.float32)

        return {
            "albedo": albedo,
            "roughness": roughness,
            "metallic": metallic,
            "clearcoat": clearcoat,
            "clamp_snow_mask": t_white,
        }

    return sdf_candy_cane, mat_candy_cane


# ==============================================================================
# TICKET 4: 3D HOLIDAY BAUBLE (Sphere + Metallic Cap #E2E8F0 + Diagonal Stripes)
# ==============================================================================
def build_bauble():
    # Slight charming ornament tilt (~14 deg right) + tiny forward pitch
    R_pose = (rot_z(14.0) @ rot_x(7.0)).T

    SPHERE_R = 0.72
    SPHERE_Y = -0.14

    def eval_bauble_parts(p: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        q = p @ R_pose
        # 1. Perfect sphere body
        ps = q - np.array([0.0, SPHERE_Y, 0.0], dtype=np.float32)
        d_sphere = np.linalg.norm(ps, axis=-1) - SPHERE_R

        # 2. Metallic hanger cap sitting cleanly on top of sphere
        # Base collar seated into top of sphere (y = SPHERE_Y + SPHERE_R - 0.03)
        cap_y = SPHERE_Y + SPHERE_R + 0.055
        pc = q - np.array([0.0, cap_y, 0.0], dtype=np.float32)
        # Rounded satin metallic cylinder cap
        d_cap_body = sd_rounded_cylinder(pc, ra=0.115, rb=0.045, h=0.095)
        # Decorative metallic collar lip right where cap meets sphere
        p_lip = q - np.array([0.0, SPHERE_Y + SPHERE_R - 0.015, 0.0], dtype=np.float32)
        d_lip = sd_rounded_cylinder(p_lip, ra=0.125, rb=0.022, h=0.025)
        # Small top stem/neck holding the ring
        p_neck = q - np.array([0.0, cap_y + 0.115, 0.0], dtype=np.float32)
        d_neck = sd_rounded_cylinder(p_neck, ra=0.042, rb=0.015, h=0.035)
        # 3D metallic hanger ring (torus in XY plane)
        p_ring = q - np.array([0.0, cap_y + 0.235, 0.0], dtype=np.float32)
        d_ring = sd_torus_xy(p_ring, R=0.11, r=0.028)

        d_metal = smin_poly(d_cap_body, d_lip, 0.018)
        d_metal = smin_poly(d_metal, d_neck, 0.015)
        d_metal = smin_poly(d_metal, d_ring, 0.012)

        return d_sphere, d_metal

    def sdf_bauble(p: np.ndarray) -> np.ndarray:
        d_sphere, d_metal = eval_bauble_parts(p)
        return np.minimum(d_sphere, d_metal)

    def mat_bauble(p: np.ndarray, n: np.ndarray) -> dict:
        d_sphere, d_metal = eval_bauble_parts(p)
        is_metal = (d_metal <= d_sphere + 1e-4).astype(np.float32)

        q = p @ R_pose
        ps = q - np.array([0.0, SPHERE_Y, 0.0], dtype=np.float32)
        pn = normalize3(ps)

        # Bold alternating diagonal stripes wrapping smoothly around the 3D sphere
        # Combine latitude (pn_y) + gentle diagonal twist via x/z projection
        diag_coord = pn[:, 0] * 0.62 + pn[:, 1] * 0.78
        stripe_wave = np.sin(diag_coord * 3.5 * math.pi + 0.35)
        t_white = np.clip((stripe_wave + 0.05) / 0.10, 0.0, 1.0)
        t_white = t_white * t_white * (3.0 - 2.0 * t_white)

        sphere_albedo = AZURE_LIN[None, :] * (1.0 - t_white[:, None]) + SNOW_LIN[None, :] * t_white[:, None]

        # Blend sphere vs metallic cap (#E2E8F0)
        m_mask = is_metal[:, None]
        albedo = sphere_albedo * (1.0 - m_mask) + METAL_LIN[None, :] * m_mask
        roughness = 0.18 * (1.0 - is_metal) + 0.22 * is_metal
        metallic = 0.0 * (1.0 - is_metal) + 0.88 * is_metal
        clearcoat = 0.72 * (1.0 - is_metal) + 0.0 * is_metal
        clamp_snow_mask = t_white * (1.0 - is_metal)

        return {
            "albedo": albedo,
            "roughness": roughness,
            "metallic": metallic,
            "clearcoat": clearcoat,
            "clamp_snow_mask": clamp_snow_mask,
        }

    return sdf_bauble, mat_bauble


def main() -> int:
    parser = argparse.ArgumentParser(description="DIR-FORGE-FESTIVE-TRIO-019 Procedural 3D Asset Forge")
    parser.add_argument(
        "--only",
        choices=["all", "snowflake", "candy_cane", "bauble"],
        default="all",
        help="Which asset(s) to generate",
    )
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    if args.only in ("all", "snowflake"):
        sdf_fn, mat_fn = build_snowflake()
        render_sdf_asset(
            "Winter Snowflake",
            sdf_fn,
            mat_fn,
            os.path.join(OUT_DIR, "decor_snowflake.png"),
            cam_z=4.2,
            bound_radius=1.35,
            enable_self_shadow=True,
        )

    if args.only in ("all", "candy_cane"):
        sdf_fn, mat_fn = build_candy_cane()
        render_sdf_asset(
            "Glossy Candy Cane",
            sdf_fn,
            mat_fn,
            os.path.join(OUT_DIR, "decor_candy_cane.png"),
            cam_z=4.2,
            bound_radius=1.45,
            enable_self_shadow=True,
        )

    if args.only in ("all", "bauble"):
        sdf_fn, mat_fn = build_bauble()
        render_sdf_asset(
            "Holiday Bauble",
            sdf_fn,
            mat_fn,
            os.path.join(OUT_DIR, "decor_bauble.png"),
            cam_z=4.2,
            bound_radius=1.45,
            enable_self_shadow=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
