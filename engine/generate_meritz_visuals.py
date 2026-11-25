#!/usr/bin/env python3
"""
Meritz Partners Visual Hook & Institutional Infographic Asset Generator
(`engine/generate_meritz_visuals.py`).

Generates 4 crisp, transparent RGBA sRGB PNG assets strictly aligned with the
Meritz Financial Group Brand Book (`assets/brands/meritz/Meritz_brand_book.pdf`):
  - Vermillion Red:       #EF3B24  RGB(239,  59,  36)
  - Obsidian Black:       #141414  RGB( 20,  20,  20)
  - Pure White:           #FFFFFF  RGB(255, 255, 255)
  - Chalk White:          #F2F2F2  RGB(242, 242, 242)
  - Institutional Gray:   #5A5D62  RGB( 90,  93,  98)

Outputs (saved to `assets/brands/meritz/visuals/`):
  1. `hero_coin_3d.png`           (1024x1024 RGBA, sRGB) — Chiseled 3D bullion coin tilted 38°
  2. `icon_sprout_beginner.png`   (512x512  RGBA, sRGB) — Architectural geometric sprout badge
  3. `icon_flexible_growth.png`   (512x512  RGBA, sRGB) — Institutional financial bar metric + red arrow
  4. `icon_honey_sidejob.png`     (512x512  RGBA, sRGB) — Precision geometric hexagonal emblem
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Sequence, Tuple

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "brands" / "meritz" / "visuals"

# Official Meritz Brand Book Palette
VERMILLION_RED = (239, 59, 36, 255)       # #EF3B24
OBSIDIAN_BLACK = (20, 20, 20, 255)        # #141414
PURE_WHITE = (255, 255, 255, 255)         # #FFFFFF
CHALK_WHITE = (242, 242, 242, 255)        # #F2F2F2
INSTITUTIONAL_GRAY = (90, 93, 98, 255)    # #5A5D62
HAIRLINE_GRAY = (214, 214, 214, 255)      # #D6D6D6

SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def save_srgb_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = img.convert("RGBA")
    rgba.save(path, "PNG", optimize=True, icc_profile=SRGB_ICC)


# ---------------------------------------------------------------------------
# 1. HERO VISUAL HOOK: Chiseled 3D Corporate Bullion Coin (1024x1024, 2x SSAA)
# ---------------------------------------------------------------------------

def _sd_segment_2d(
    px: np.ndarray,
    py: np.ndarray,
    ax: float,
    ay: float,
    bx: float,
    by: float,
) -> np.ndarray:
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    denom = bax * bax + bay * bay + 1e-12
    h = np.clip((pax * bax + pay * bay) / denom, 0.0, 1.0)
    dx = pax - bax * h
    dy = pay - bay * h
    return np.sqrt(dx * dx + dy * dy)


def _won_emblem_sdf(px: np.ndarray, py: np.ndarray) -> np.ndarray:
    """Chiseled geometric Korean Won (₩) emblem in coin face UV coordinates."""
    # Scale into emblem space (centered at 0,0, spans roughly [-0.42, 0.42])
    strokes = [
        # W left outer diagonal
        (-0.36, 0.28, -0.18, -0.28),
        # W left inner diagonal
        (-0.18, -0.28, 0.00, 0.14),
        # W right inner diagonal
        (0.00, 0.14, 0.18, -0.28),
        # W right outer diagonal
        (0.18, -0.28, 0.36, 0.28),
        # Upper horizontal Won bar
        (-0.41, 0.055, 0.41, 0.055),
        # Lower horizontal Won bar
        (-0.37, -0.075, 0.37, -0.075),
    ]
    d = np.full_like(px, 10.0)
    for i, (ax, ay, bx, by) in enumerate(strokes):
        thickness = 0.044 if i < 4 else 0.032
        seg = _sd_segment_2d(px, py, ax, ay, bx, by) - thickness
        d = np.minimum(d, seg)
    return d


def _coin_sdf(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    """
    Signed distance field of an institutional chiseled bullion coin:
      - Radius R = 1.0, half-thickness H = 0.132
      - Architectural chamfered bevel on outer rim
      - Milled radial rim fluting along outer cylindrical wall
      - Recessed brushed inner face with crisp double concentric hairline rings
      - Raised chiseled Korean Won (₩) relief emblem on front face (z > 0)
    """
    r = np.sqrt(x * x + y * y)
    az = np.abs(z)
    theta = np.arctan2(y, x)

    # Base cylinder with sharp architectural chamfer (bevel = 0.042)
    R = 1.0
    H = 0.132
    bevel = 0.042

    # Chamfered cylinder distance
    dr = r - (R - bevel)
    dz = az - (H - bevel)
    d_base = np.maximum(
        np.maximum(r - R, az - H),
        (dr + dz) * 0.70710678 - bevel * 0.70710678,
    )

    # Milled rim flutes on the outer vertical wall (64 crisp architectural ribs)
    edge_mask = np.clip((r - 0.935) / 0.045, 0.0, 1.0) * np.clip((0.105 - az) / 0.025, 0.0, 1.0)
    flute = 0.0085 * np.cos(64.0 * theta) * edge_mask
    d = d_base + flute

    # Front & back face reliefs (recessed dish + concentric precision ring + ₩ emblem on +z)
    face_zone = np.clip((az - 0.05) / 0.05, 0.0, 1.0)

    # Recessed inner dish for r < 0.79
    dish_t = np.clip((0.805 - r) / 0.030, 0.0, 1.0)
    dish_depth = 0.028 * dish_t * face_zone

    # Crisp raised hairline architectural ring at r = 0.735
    ring_band = np.exp(-((r - 0.735) / 0.014) ** 2) * 0.011 * face_zone

    # Raised chiseled Won emblem on front face (z > 0)
    front_mask = np.clip(z / 0.04, 0.0, 1.0)
    d_won = _won_emblem_sdf(x, y)
    won_height = np.clip(-d_won / 0.018, 0.0, 1.0) * 0.029 * front_mask * face_zone

    # Apply height relief along Z face
    d = d + dish_depth - ring_band - won_height
    return d


def _sample_studio_env(rx: np.ndarray, ry: np.ndarray, rz: np.ndarray) -> np.ndarray:
    """
    High-contrast architectural studio HDRI reflection map:
      - Deep Obsidian Black (#141414) studio dark panels for corporate contrast
      - Two crisp Pure White (#FFFFFF) rectangular architectural softboxes
      - Subtle warm champagne-platinum floor bounce
    """
    # Base dark obsidian studio backdrop
    env = np.zeros(rx.shape + (3,), dtype=np.float32)
    env[..., 0] = 0.14
    env[..., 1] = 0.12
    env[..., 2] = 0.10

    # Subtle vertical architectural gradient
    v = np.clip(ry * 0.5 + 0.5, 0.0, 1.0)
    env[..., 0] += 0.24 * v
    env[..., 1] += 0.21 * v
    env[..., 2] += 0.17 * v

    # Key architectural softbox (upper-left bright white strip)
    key = np.exp(-((rx + 0.42) ** 2 / 0.10 + (ry - 0.58) ** 2 / 0.06))
    env[..., 0] += 1.65 * key
    env[..., 1] += 1.58 * key
    env[..., 2] += 1.45 * key

    # Diagonal razor rim softbox (right edge catchlight)
    rim = np.exp(-((rx - 0.68) ** 2 / 0.05 + (ry - 0.15) ** 2 / 0.24))
    env[..., 0] += 1.10 * rim
    env[..., 1] += 1.02 * rim
    env[..., 2] += 0.88 * rim

    # Deep Obsidian contrast band across lower-mid reflection (gives bullion richness)
    dark_band = np.exp(-((ry + 0.18) ** 2 / 0.035))
    env *= (1.0 - 0.52 * dark_band)[..., None]

    # Subtle warm ground bounce
    bounce = np.clip(-ry - 0.25, 0.0, 1.0)
    env[..., 0] += 0.34 * bounce
    env[..., 1] += 0.26 * bounce
    env[..., 2] += 0.14 * bounce

    return env


def _rot_x(deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float32)


def _rot_y(deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float32)


def _rot_z(deg: float) -> np.ndarray:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float32)


def _draw_precision_glint(
    canvas: Image.Image,
    cx: float,
    cy: float,
    arm: float,
    core_r: float,
    opacity: float = 0.92,
) -> None:
    """Subtle razor-sharp 4-point optical specular glint (corporate jewelry/bullion style)."""
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Soft champagne-white glow behind glint
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gr = core_r * 2.8
    gd.ellipse((cx - gr, cy - gr, cx + gr, cy + gr), fill=(255, 248, 232, int(115 * opacity)))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(2.0, core_r * 0.9)))
    canvas.alpha_composite(glow)

    # Crisp 4-point tapered diamond star
    w = max(2.0, core_r * 0.34)
    pts_h = [(cx - arm, cy), (cx, cy - w), (cx + arm, cy), (cx, cy + w)]
    pts_v = [(cx, cy - arm), (cx + w, cy), (cx, cy + arm), (cx - w, cy)]
    draw.polygon(pts_h, fill=(255, 255, 255, int(250 * opacity)))
    draw.polygon(pts_v, fill=(255, 255, 255, int(250 * opacity)))
    draw.ellipse(
        (cx - core_r * 0.55, cy - core_r * 0.55, cx + core_r * 0.55, cy + core_r * 0.55),
        fill=(255, 255, 255, int(255 * opacity)),
    )
    canvas.alpha_composite(overlay)


def generate_hero_coin_3d(out_path: Path, final_size: int = 1024, ssaa: int = 2) -> None:
    t0 = time.perf_counter()
    res = final_size * ssaa  # 2048x2048

    # Normalized image plane [-1, 1] x [-1, 1], shifted slightly up to leave room for contact shadow
    lin = np.linspace(-1.0, 1.0, res, dtype=np.float32)
    uu, vv = np.meshgrid(lin, -lin)  # +v is up
    vv = vv - 0.08  # Raise coin slightly above bottom contact shadow

    # Perspective camera
    cam_z = 3.95
    fov_scale = 0.42
    rd_x = uu * fov_scale
    rd_y = vv * fov_scale
    rd_z = np.full_like(uu, -1.0)
    inv_len = 1.0 / np.sqrt(rd_x * rd_x + rd_y * rd_y + rd_z * rd_z)
    rd_x *= inv_len
    rd_y *= inv_len
    rd_z *= inv_len

    # Dynamic 38° tilt (35°–45° perspective angle) with corporate poise
    # Transform rays into coin local coordinates via R^T
    R_mat = _rot_z(-9.0) @ _rot_y(-24.0) @ _rot_x(36.0)
    RT = R_mat.T

    ro_l = RT @ np.array([0.0, 0.0, cam_z], dtype=np.float32)
    rd_lx = RT[0, 0] * rd_x + RT[0, 1] * rd_y + RT[0, 2] * rd_z
    rd_ly = RT[1, 0] * rd_x + RT[1, 1] * rd_y + RT[1, 2] * rd_z
    rd_lz = RT[2, 0] * rd_x + RT[2, 1] * rd_y + RT[2, 2] * rd_z

    # Bounding sphere pre-cull (radius = 1.12)
    b = ro_l[0] * rd_lx + ro_l[1] * rd_ly + ro_l[2] * rd_lz
    c = float(np.dot(ro_l, ro_l)) - 1.12 * 1.12
    disc = b * b - c
    active_mask = disc > 0.0
    idx = np.flatnonzero(active_mask)

    # Extract active rays
    r_dx = rd_lx.ravel()[idx]
    r_dy = rd_ly.ravel()[idx]
    r_dz = rd_lz.ravel()[idx]
    t = np.maximum(0.0, -b.ravel()[idx] - np.sqrt(np.maximum(0.0, disc.ravel()[idx])))
    t_max = -b.ravel()[idx] + np.sqrt(np.maximum(0.0, disc.ravel()[idx]))

    # Vectorized sphere tracing (44 iterations)
    hit = np.zeros_like(t, dtype=bool)
    alive = np.ones_like(t, dtype=bool)

    for _ in range(44):
        if not np.any(alive):
            break
        ai = np.flatnonzero(alive)
        px = ro_l[0] + r_dx[ai] * t[ai]
        py = ro_l[1] + r_dy[ai] * t[ai]
        pz = ro_l[2] + r_dz[ai] * t[ai]
        d = _coin_sdf(px, py, pz)
        # Conservative step factor 0.85 for crisp flutes & bevels
        t[ai] += d * 0.85
        just_hit = d < 1.2e-3
        hit[ai[just_hit]] = True
        alive[ai[just_hit | (t[ai] > t_max[ai])]] = False

    hit_sub = np.flatnonzero(hit)
    hit_global = idx[hit_sub]

    # Compute surface position & finite-difference normals on hit pixels
    hx = ro_l[0] + r_dx[hit_sub] * t[hit_sub]
    hy = ro_l[1] + r_dy[hit_sub] * t[hit_sub]
    hz = ro_l[2] + r_dz[hit_sub] * t[hit_sub]

    eps = 1.6e-3
    nx = _coin_sdf(hx + eps, hy, hz) - _coin_sdf(hx - eps, hy, hz)
    ny = _coin_sdf(hx, hy + eps, hz) - _coin_sdf(hx, hy - eps, hz)
    nz = _coin_sdf(hx, hy, hz + eps) - _coin_sdf(hx, hy, hz - eps)
    n_len = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
    nx /= n_len
    ny /= n_len
    nz /= n_len

    # Subtle radial brushed metallic micro-normal perturbation on inner face
    hr = np.sqrt(hx * hx + hy * hy)
    htheta = np.arctan2(hy, hx)
    dish_brush = np.clip((0.79 - hr) / 0.03, 0.0, 1.0) * np.clip((np.abs(hz) - 0.08) / 0.03, 0.0, 1.0)
    grain = np.sin(260.0 * hr + 3.0 * htheta) * 0.018 * dish_brush
    nx += (hx / (hr + 1e-6)) * grain
    ny += (hy / (hr + 1e-6)) * grain
    n_len2 = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-12
    nx /= n_len2
    ny /= n_len2
    nz /= n_len2

    # View vector (from surface toward camera)
    vx = -r_dx[hit_sub]
    vy = -r_dy[hit_sub]
    vz = -r_dz[hit_sub]

    # Reflection vector in local space, then rotate back to world space for studio HDRI
    ndotv = np.clip(nx * vx + ny * vy + nz * vz, 0.0, 1.0)
    ref_lx = 2.0 * ndotv * nx - vx
    ref_ly = 2.0 * ndotv * ny - vy
    ref_lz = 2.0 * ndotv * nz - vz

    ref_wx = R_mat[0, 0] * ref_lx + R_mat[0, 1] * ref_ly + R_mat[0, 2] * ref_lz
    ref_wy = R_mat[1, 0] * ref_lx + R_mat[1, 1] * ref_ly + R_mat[1, 2] * ref_lz
    ref_wz = R_mat[2, 0] * ref_lx + R_mat[2, 1] * ref_ly + R_mat[2, 2] * ref_lz

    # World-space normal for directional lighting
    n_wx = R_mat[0, 0] * nx + R_mat[0, 1] * ny + R_mat[0, 2] * nz
    n_wy = R_mat[1, 0] * nx + R_mat[1, 1] * ny + R_mat[1, 2] * nz
    n_wz = R_mat[2, 0] * nx + R_mat[2, 1] * ny + R_mat[2, 2] * nz

    # Refined Institutional Champagne-Gold Bullion Metal Albedo (restrained corporate prestige)
    # Slightly richer warm bullion on beveled rim & raised ₩ emblem, satin-brushed on recessed dish
    is_dish = dish_brush
    albedo_r = 0.90 - 0.06 * is_dish
    albedo_g = 0.74 - 0.07 * is_dish
    albedo_b = 0.43 - 0.06 * is_dish

    # Studio environment reflection
    env = _sample_studio_env(ref_wx, ref_wy, ref_wz)

    # Metallic Schlick Fresnel
    fresnel = 0.25 + 0.75 * ((1.0 - ndotv) ** 4.0)

    # Key directional studio light (upper-left-front)
    l1 = np.array([-0.48, 0.68, 0.55], dtype=np.float32)
    l1 /= np.linalg.norm(l1)
    ndotl1 = np.clip(n_wx * l1[0] + n_wy * l1[1] + n_wz * l1[2], 0.0, 1.0)

    # Halfway vector in world space for crisp GGX-like specular
    v_wx = -rd_x.ravel()[hit_global]
    v_wy = -rd_y.ravel()[hit_global]
    v_wz = -rd_z.ravel()[hit_global]
    h1x, h1y, h1z = l1[0] + v_wx, l1[1] + v_wy, l1[2] + v_wz
    h1_len = np.sqrt(h1x * h1x + h1y * h1y + h1z * h1z) + 1e-12
    ndoth1 = np.clip((n_wx * h1x + n_wy * h1y + n_wz * h1z) / h1_len, 0.0, 1.0)
    spec_sharp = (ndoth1 ** 88.0) * 1.15
    spec_broad = (ndoth1 ** 18.0) * 0.34

    # Rim light (right-back) to carve chiseled edge
    l2 = np.array([0.75, 0.20, 0.62], dtype=np.float32)
    l2 /= np.linalg.norm(l2)
    ndotl2 = np.clip(n_wx * l2[0] + n_wy * l2[1] + n_wz * l2[2], 0.0, 1.0)
    h2x, h2y, h2z = l2[0] + v_wx, l2[1] + v_wy, l2[2] + v_wz
    h2_len = np.sqrt(h2x * h2x + h2y * h2y + h2z * h2z) + 1e-12
    ndoth2 = np.clip((n_wx * h2x + n_wy * h2y + n_wz * h2z) / h2_len, 0.0, 1.0)
    spec_rim = (ndoth2 ** 42.0) * 0.55

    # Cavity AO: darken slightly right at the inner bevel step and Won relief base
    step_ao = 1.0 - 0.22 * np.exp(-((hr - 0.795) / 0.022) ** 2)
    d_won_h = _won_emblem_sdf(hx, hy)
    won_ao = 1.0 - 0.20 * np.exp(-((d_won_h - 0.012) / 0.024) ** 2) * np.clip(hz / 0.05, 0.0, 1.0)
    ao = step_ao * won_ao

    # Combine metallic reflection + diffuse + sharp specular
    col_r = (albedo_r * (0.28 + 0.62 * ndotl1 + 0.18 * ndotl2) + env[..., 0] * albedo_r * (0.68 + 0.32 * fresnel)) * ao + spec_sharp * 1.00 + spec_broad * albedo_r + spec_rim * 0.95
    col_g = (albedo_g * (0.26 + 0.60 * ndotl1 + 0.16 * ndotl2) + env[..., 1] * albedo_g * (0.68 + 0.32 * fresnel)) * ao + spec_sharp * 0.96 + spec_broad * albedo_g + spec_rim * 0.88
    col_b = (albedo_b * (0.22 + 0.54 * ndotl1 + 0.14 * ndotl2) + env[..., 2] * albedo_b * (0.68 + 0.32 * fresnel)) * ao + spec_sharp * 0.86 + spec_broad * albedo_b + spec_rim * 0.72

    # Filmic ACES-like tone mapping for crisp metallic highlights without harsh clipping
    def _tonemap(c: np.ndarray) -> np.ndarray:
        c = np.maximum(c, 0.0)
        return (c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14)

    out_rgba = np.zeros((res * res, 4), dtype=np.uint8)
    out_rgba[hit_global, 0] = np.clip(_tonemap(col_r) ** (1.0 / 1.08) * 255.0, 0, 255).astype(np.uint8)
    out_rgba[hit_global, 1] = np.clip(_tonemap(col_g) ** (1.0 / 1.08) * 255.0, 0, 255).astype(np.uint8)
    out_rgba[hit_global, 2] = np.clip(_tonemap(col_b) ** (1.0 / 1.08) * 255.0, 0, 255).astype(np.uint8)
    out_rgba[hit_global, 3] = 255

    coin_img = Image.fromarray(out_rgba.reshape((res, res, 4)), "RGBA")

    # Build grounded architectural soft contact shadow beneath coin
    canvas = Image.new("RGBA", (res, res), (0, 0, 0, 0))
    bbox = coin_img.getbbox()
    if bbox:
        bx0, by0, bx1, by1 = bbox
        cx = (bx0 + bx1) * 0.5
        bw = bx1 - bx0
        shadow_y = by1 + int(res * 0.018)

        # Dual-layer shadow: soft ambient penumbra + tighter contact core
        sh_ambient = Image.new("RGBA", (res, res), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh_ambient)
        aw = bw * 0.44
        ah = res * 0.042
        sd.ellipse((cx - aw, shadow_y - ah, cx + aw, shadow_y + ah), fill=(20, 20, 20, 56))
        sh_ambient = sh_ambient.filter(ImageFilter.GaussianBlur(radius=res * 0.028))

        sh_core = Image.new("RGBA", (res, res), (0, 0, 0, 0))
        cd = ImageDraw.Draw(sh_core)
        cw = bw * 0.28
        ch = res * 0.018
        cd.ellipse((cx - cw, shadow_y - ch, cx + cw, shadow_y + ch), fill=(20, 20, 20, 78))
        sh_core = sh_core.filter(ImageFilter.GaussianBlur(radius=res * 0.012))

        canvas.alpha_composite(sh_ambient)
        canvas.alpha_composite(sh_core)

    canvas.alpha_composite(coin_img)

    # Restrained architectural specular glints positioned on the coin's brightest bevel rim
    if bbox:
        bx0, by0, bx1, by1 = bbox
        bw, bh = bx1 - bx0, by1 - by0
        _draw_precision_glint(canvas, bx0 + bw * 0.25, by0 + bh * 0.16, arm=res * 0.055, core_r=res * 0.013, opacity=0.92)
        _draw_precision_glint(canvas, bx0 + bw * 0.84, by0 + bh * 0.34, arm=res * 0.036, core_r=res * 0.009, opacity=0.78)

    final_img = canvas.resize((final_size, final_size), Image.Resampling.LANCZOS)
    save_srgb_png(final_img, out_path)
    print(f"[OK] Generated {out_path.relative_to(ROOT)} ({final_size}x{final_size} RGBA, {(time.perf_counter()-t0):.2f}s)")


# ---------------------------------------------------------------------------
# 2. SUB-FEATURE ICON 1: Architectural Geometric Sprout Badge (`경력무관`)
# ---------------------------------------------------------------------------

def generate_icon_sprout_beginner(out_path: Path, final_size: int = 512, ssaa: int = 2) -> None:
    s = final_size * ssaa  # 1024x1024
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = s // 2
    r_outer = int(s * 0.435)
    r_inner = int(s * 0.375)

    # Crisp Pure White architectural badge disc with Obsidian Black precision ring
    draw.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), fill=PURE_WHITE, outline=OBSIDIAN_BLACK, width=int(s * 0.022))
    # Subtle Chalk White recessed inner technical ring
    draw.ellipse((cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner), fill=CHALK_WHITE, outline=HAIRLINE_GRAY, width=int(s * 0.006))

    # Architectural baseline
    base_y = int(s * 0.705)
    draw.line([(int(s * 0.28), base_y), (int(s * 0.72), base_y)], fill=OBSIDIAN_BLACK, width=int(s * 0.024))

    # Central crisp vertical stem (Obsidian Black)
    stem_top = int(s * 0.365)
    draw.line([(cx, base_y), (cx, stem_top)], fill=OBSIDIAN_BLACK, width=int(s * 0.024))

    # Left geometric angular leaf (pointed architectural kite in Obsidian Black + Pure White fill)
    left_leaf = [
        (cx - int(s * 0.010), int(s * 0.545)),
        (int(s * 0.345), int(s * 0.515)),
        (int(s * 0.275), int(s * 0.375)),
        (int(s * 0.415), int(s * 0.405)),
        (cx - int(s * 0.010), int(s * 0.495)),
    ]
    draw.polygon(left_leaf, fill=PURE_WHITE)
    _draw_closed_polyline(draw, left_leaf, OBSIDIAN_BLACK, width=int(s * 0.020))

    # Right ascending geometric apex leaf (clean 4-point convex architectural kite in Solid Vermillion Red #EF3B24)
    right_leaf = [
        (cx + int(s * 0.014), int(s * 0.485)),
        (int(s * 0.585), int(s * 0.345)),
        (int(s * 0.725), int(s * 0.295)),
        (int(s * 0.665), int(s * 0.445)),
    ]
    draw.polygon(right_leaf, fill=VERMILLION_RED)

    # Architectural top-center precision diamond node in Vermillion Red
    d_r = int(s * 0.032)
    d_cy = int(s * 0.275)
    draw.polygon(
        [(cx, d_cy - d_r), (cx + d_r, d_cy), (cx, d_cy + d_r), (cx - d_r, d_cy)],
        fill=VERMILLION_RED,
    )

    final_img = img.resize((final_size, final_size), Image.Resampling.LANCZOS)
    save_srgb_png(final_img, out_path)
    print(f"[OK] Generated {out_path.relative_to(ROOT)} ({final_size}x{final_size} RGBA)")


# ---------------------------------------------------------------------------
# 3. SUB-FEATURE ICON 2: Institutional Financial Bar Metric (`첫달부터 수익+`)
# ---------------------------------------------------------------------------

def generate_icon_flexible_growth(out_path: Path, final_size: int = 512, ssaa: int = 2) -> None:
    s = final_size * ssaa  # 1024x1024
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Architectural rounded-square container (Pure White + crisp Obsidian border)
    pad = int(s * 0.085)
    rad = int(s * 0.075)
    draw.rounded_rectangle(
        (pad, pad, s - pad, s - pad),
        radius=rad,
        fill=PURE_WHITE,
        outline=OBSIDIAN_BLACK,
        width=int(s * 0.022),
    )

    # Subtle institutional horizontal reference grid lines (Chalk White / Hairline)
    grid_x0, grid_x1 = int(s * 0.19), int(s * 0.81)
    for gy_ratio in (0.34, 0.50, 0.66):
        gy = int(s * gy_ratio)
        draw.line([(grid_x0, gy), (grid_x1, gy)], fill=CHALK_WHITE, width=int(s * 0.010))

    # Bold Obsidian coordinate baseline
    base_y = int(s * 0.775)
    draw.line([(int(s * 0.18), base_y), (int(s * 0.82), base_y)], fill=OBSIDIAN_BLACK, width=int(s * 0.022))

    # 3 Precision Ascending Financial Bars
    bar_w = int(s * 0.125)
    # Bar 1: Chalk White fill with crisp Obsidian Black frame
    b1_x0 = int(s * 0.23)
    b1_top = int(s * 0.58)
    draw.rectangle((b1_x0, b1_top, b1_x0 + bar_w, base_y), fill=CHALK_WHITE, outline=OBSIDIAN_BLACK, width=int(s * 0.018))

    # Bar 2: Solid Obsidian Black
    b2_x0 = int(s * 0.435)
    b2_top = int(s * 0.45)
    draw.rectangle((b2_x0, b2_top, b2_x0 + bar_w, base_y), fill=OBSIDIAN_BLACK)

    # Bar 3: Peak Bar in Solid Vermillion Red (#EF3B24)
    b3_x0 = int(s * 0.64)
    b3_top = int(s * 0.29)
    draw.rectangle((b3_x0, b3_top, b3_x0 + bar_w, base_y), fill=VERMILLION_RED)

    # Crisp diagonal linear growth vector arrow above bars
    ax0, ay0 = int(s * 0.23), int(s * 0.44)
    ax1, ay1 = int(s * 0.55), int(s * 0.23)
    draw.line([(ax0, ay0), (ax1, ay1)], fill=OBSIDIAN_BLACK, width=int(s * 0.022))
    # Vermillion Red sharp triangular arrowhead at (ax1, ay1)
    head = [
        (ax1 + int(s * 0.035), ay1 - int(s * 0.022)),
        (ax1 - int(s * 0.055), ay1 - int(s * 0.028)),
        (ax1 - int(s * 0.008), ay1 + int(s * 0.052)),
    ]
    draw.polygon(head, fill=VERMILLION_RED)

    # Precision architectural '+' sign in Vermillion Red (#EF3B24) at top-left quadrant
    px, py = int(s * 0.275), int(s * 0.265)
    p_arm = int(s * 0.052)
    p_w = int(s * 0.024)
    draw.rectangle((px - p_arm, py - p_w // 2, px + p_arm, py + p_w // 2), fill=VERMILLION_RED)
    draw.rectangle((px - p_w // 2, py - p_arm, px + p_w // 2, py + p_arm), fill=VERMILLION_RED)

    final_img = img.resize((final_size, final_size), Image.Resampling.LANCZOS)
    save_srgb_png(final_img, out_path)
    print(f"[OK] Generated {out_path.relative_to(ROOT)} ({final_size}x{final_size} RGBA)")


# ---------------------------------------------------------------------------
# 4. SUB-FEATURE ICON 3: Precision Geometric Hexagonal Symbol (`꿀부업`)
# ---------------------------------------------------------------------------

def _hex_points(cx: float, cy: float, r: float, angle_offset_deg: float = -30.0) -> list[Tuple[float, float]]:
    pts = []
    for k in range(6):
        ang = math.radians(angle_offset_deg + 60.0 * k)
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts


def _draw_closed_polyline(
    draw: ImageDraw.ImageDraw,
    pts: Sequence[Tuple[float, float]],
    color: Tuple[int, int, int, int],
    width: int,
) -> None:
    n = len(pts)
    for i in range(n):
        draw.line([pts[i], pts[(i + 1) % n]], fill=color, width=width)
    # Clean vertex caps so corners are crisp
    r = width * 0.48
    for x, y in pts:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def generate_icon_honey_sidejob(out_path: Path, final_size: int = 512, ssaa: int = 2) -> None:
    s = final_size * ssaa  # 1024x1024
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = s * 0.5
    r_outer = s * 0.42
    r_mid = s * 0.255
    r_core = s * 0.125

    outer_pts = _hex_points(cx, cy, r_outer, angle_offset_deg=-90.0)
    mid_pts = _hex_points(cx, cy, r_mid, angle_offset_deg=-90.0)
    core_pts = _hex_points(cx, cy, r_core, angle_offset_deg=-90.0)

    # Outer Hexagon Base (Pure White)
    draw.polygon(outer_pts, fill=PURE_WHITE)

    # Structured Isometric Architectural Facets (3-plane modular structure)
    # Top-left facet: Chalk White (#F2F2F2)
    draw.polygon([outer_pts[5], outer_pts[0], outer_pts[1], (cx, cy)], fill=CHALK_WHITE)
    # Bottom-right facet: Subtle Chalk White
    draw.polygon([outer_pts[2], outer_pts[3], (cx, cy)], fill=CHALK_WHITE)

    # Crisp Obsidian structural spokes connecting center to alternating vertices (isometric cube/honeycomb)
    stroke_w = int(s * 0.022)
    thin_w = int(s * 0.014)
    for idx_v in (0, 2, 4):
        draw.line([(cx, cy), outer_pts[idx_v]], fill=OBSIDIAN_BLACK, width=thin_w)

    # Secondary inner nested hexagon wireframe (Obsidian Black)
    draw.polygon(mid_pts, fill=PURE_WHITE)
    _draw_closed_polyline(draw, mid_pts, OBSIDIAN_BLACK, width=thin_w)

    # Bold Outer Hexagon Architectural Frame (Obsidian Black)
    _draw_closed_polyline(draw, outer_pts, OBSIDIAN_BLACK, width=stroke_w)

    # Central Decisive Vermillion Red (#EF3B24) Geometric Hex Core (Structured Side Revenue)
    draw.polygon(core_pts, fill=VERMILLION_RED)

    # Precision top-right vertex accent square in Vermillion Red
    vx, vy = outer_pts[1]
    dot_r = int(s * 0.032)
    draw.ellipse((vx - dot_r, vy - dot_r, vx + dot_r, vy + dot_r), fill=VERMILLION_RED, outline=PURE_WHITE, width=int(s * 0.008))

    final_img = img.resize((final_size, final_size), Image.Resampling.LANCZOS)
    save_srgb_png(final_img, out_path)
    print(f"[OK] Generated {out_path.relative_to(ROOT)} ({final_size}x{final_size} RGBA)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=== MERITZ BRAND BOOK VISUAL GENERATOR ===")
    print(f"Output directory: {OUT_DIR.relative_to(ROOT)}")
    generate_hero_coin_3d(OUT_DIR / "hero_coin_3d.png", final_size=1024, ssaa=2)
    generate_icon_sprout_beginner(OUT_DIR / "icon_sprout_beginner.png", final_size=512, ssaa=2)
    generate_icon_flexible_growth(OUT_DIR / "icon_flexible_growth.png", final_size=512, ssaa=2)
    generate_icon_honey_sidejob(OUT_DIR / "icon_honey_sidejob.png", final_size=512, ssaa=2)
    print("=== ALL 4 MERITZ VISUAL ASSETS GENERATED ===")


if __name__ == "__main__":
    main()
