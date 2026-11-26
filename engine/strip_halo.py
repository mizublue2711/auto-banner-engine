#!/usr/bin/env python3
"""
RADICAL HALO & GROUND-PLANE SHADOW STRIPPER - auto-banner-engine
Directive: DIR-RADICAL-HALO-AND-SHADOW-STRIP-016

Dedicated post-processor for assets/brands/gsshop/decors/*.png:
1. Identify the solid object mask where Alpha > 20.
2. Erode the alpha mask inward by 3 pixels (cv2.erode) to shave off the outer
   jagged white/gray sticker rim.
3. Peel variable-thickness border-connected studio-gray sticker halos while
   preserving genuine white 3D object surfaces (geometric circle trim on bauble,
   clean cube walls on gift_box, smooth tubular contour on candy_cane, open
   trapped flat studio wedges on snowflake).
4. Clip horizontal flat ground-plane floor shadows in the bottom 15-18% via
   cool-gray shadow peeling and geometric base-envelope truncation.
5. Apply subtle 1px Gaussian anti-aliasing strictly on the outer alpha
   transition edge with nearest-interior RGB decontamination.
6. Overwrite all 9 PNG files in assets/brands/gsshop/decors/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt, label

PURE_COLORED_ITEMS = (
    "decor_tree",
    "decor_gingerbread",
    "decor_santa_hat",
    "decor_stocking",
)

MIXED_WHITE_ITEMS = (
    "decor_bauble",
    "decor_candy_cane",
    "decor_gift_box",
    "decor_snowman",
)

PURE_WHITE_ITEMS = ("decor_snowflake",)


def _classify_item(filename: str) -> str:
    stem = Path(filename).stem.lower()
    if any(k in stem for k in PURE_WHITE_ITEMS):
        return "pure_white"
    if any(k in stem for k in MIXED_WHITE_ITEMS):
        return "mixed"
    return "pure_colored"


def _keep_largest_component(mask: np.ndarray) -> np.ndarray:
    labeled, num = label(mask)
    if num <= 1:
        return mask
    areas = np.bincount(labeled.ravel())
    areas[0] = 0
    best = int(np.argmax(areas))
    return labeled == best


def _peel_border_connected(
    mask: np.ndarray,
    removable: np.ndarray,
    max_iters: int = 16,
) -> np.ndarray:
    """Iteratively peel removable pixels connected (4-neighbor) to exterior ~mask."""
    out = mask.copy()
    struct = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    for _ in range(max_iters):
        exterior = ~out
        border = out & binary_dilation(exterior, structure=struct)
        to_remove = border & removable
        if not np.any(to_remove):
            break
        out[to_remove] = False
    return out


def _fit_circle_to_band(mask: np.ndarray, y_top: int, y_bot: int) -> tuple[float, float, float] | None:
    """Algebraic least-squares circle fit to left/right silhouette points in [y_top, y_bot]."""
    pts_x: list[float] = []
    pts_y: list[float] = []
    for y in range(y_top, y_bot + 1, 2):
        rxs = np.where(mask[y])[0]
        if len(rxs) > 40:
            pts_x.extend([float(rxs.min()), float(rxs.max())])
            pts_y.extend([float(y), float(y)])
    if len(pts_x) < 12:
        return None
    px = np.array(pts_x)
    py = np.array(pts_y)
    A = np.column_stack([px, py, np.ones_like(px)])
    rhs = -(px * px + py * py)
    sol, _, _, _ = np.linalg.lstsq(A, rhs, rcond=None)
    cx = float(-sol[0] / 2.0)
    cy = float(-sol[1] / 2.0)
    rad = float(np.sqrt(max(1.0, cx * cx + cy * cy - sol[2])))
    return cx, cy, rad


def _compute_color_features(rgb: np.ndarray) -> dict[str, np.ndarray]:
    rgb_f = rgb.astype(np.float32)
    r, g, b = rgb_f[:, :, 0], rgb_f[:, :, 1], rgb_f[:, :, 2]
    brightness = (r + g + b) / 3.0
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    chroma = cmax - cmin

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hsv_s = hsv[:, :, 1].astype(np.float32)
    hsv_v = hsv[:, :, 2].astype(np.float32)

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad = np.hypot(gx, gy)

    mean_local = cv2.blur(gray, (5, 5))
    mean_sq = cv2.blur(gray * gray, (5, 5))
    local_std = np.sqrt(np.maximum(mean_sq - mean_local * mean_local, 0.0))

    return {
        "r": r,
        "g": g,
        "b": b,
        "brightness": brightness,
        "chroma": chroma,
        "hsv_s": hsv_s,
        "hsv_v": hsv_v,
        "gray": gray,
        "grad": grad,
        "local_std": local_std,
    }


def _strip_studio_halo(
    mask: np.ndarray,
    feats: dict[str, np.ndarray],
    item_name: str,
    category: str,
) -> np.ndarray:
    """Strip variable-thickness studio white/gray sticker halo while protecting white 3D faces."""
    r, g, b = feats["r"], feats["g"], feats["b"]
    brightness = feats["brightness"]
    chroma = feats["chroma"]
    hsv_s = feats["hsv_s"]
    hsv_v = feats["hsv_v"]
    grad = feats["grad"]
    local_std = feats["local_std"]

    studio_neutral = (
        (r > 188) & (g > 188) & (b > 188)
        & (np.abs(r - g) < 16) & (np.abs(g - b) < 18)
    )
    studio_broad = (brightness > 172) & (chroma < 30)

    if category == "pure_colored":
        pale_studio = (hsv_s < 62) & (hsv_v > 160)
        if "santa_hat" in item_name or "stocking" in item_name:
            pale_blue_halo = (brightness > 188) & (r > 155) & (hsv_s < 95)
            removable = studio_neutral | studio_broad | pale_studio | pale_blue_halo
        elif "gingerbread" in item_name:
            # Strip studio halo while protecting warm pinkish-white wrist/ankle icing
            is_pink_icing = (r > g + 10) & (r > 175) & (b > g - 8)
            removable = (studio_neutral | studio_broad | pale_studio) & (~is_pink_icing)
        else:
            removable = studio_neutral | studio_broad | pale_studio
        mask = _peel_border_connected(mask, removable, max_iters=14)

    elif "gift_box" in item_name:
        # Top 25% is the blue bow (peel studio halo cleanly); below is the white 3D cube
        # whose crisp rounded shoulders and vertical walls stay 100% intact.
        ys = np.where(mask)[0]
        if len(ys):
            ymin, ymax = int(ys.min()), int(ys.max())
            bow_cut = ymin + int((ymax - ymin) * 0.25)
            bow_zone = np.zeros_like(mask)
            bow_zone[:bow_cut, :] = True
            pale_bow_halo = bow_zone & (
                studio_neutral
                | ((brightness > 175) & (chroma < 32))
                | ((hsv_s < 65) & (hsv_v > 170))
            )
            mask = _peel_border_connected(mask, pale_bow_halo, max_iters=12)

    elif "bauble" in item_name:
        # Geometric precision: the bauble body is a smooth circular sphere topped by a silver cap.
        ys = np.where(mask)[0]
        if len(ys):
            ymin, ymax = int(ys.min()), int(ys.max())
            h_obj = ymax - ymin
            circle = _fit_circle_to_band(
                mask, ymin + int(h_obj * 0.38), ymin + int(h_obj * 0.76)
            )
            if circle is not None:
                cx, cy, rad = circle
                yy, xx = np.ogrid[: mask.shape[0], : mask.shape[1]]
                dist_c = np.hypot(xx - cx, yy - cy)
                # Tightly scope cap_zone to the silver cap & ring at upper-right so it never
                # cuts into the smooth white stripe on the upper-left shoulder of the sphere
                # and clips any thin whisker sticking up to the left of the cap base
                cap_zone = (yy < cy - rad * 0.56) & (xx > cx + rad * 0.05)
                sphere_trim = (~cap_zone) & (dist_c > (rad - 2.4))
                mask[sphere_trim] = False

                # Around the metallic silver cap & hanging ring, strip bright studio gray
                # (shaded metallic silver has brightness < 178) and remove thin detached whiskers
                cap_halo = cap_zone & (
                    ((r > 175) & (g > 175) & (b > 175) & (chroma < 20))
                    | ((brightness > 178) & (chroma < 20))
                )
                mask = _peel_border_connected(mask, cap_halo, max_iters=16)

                # Morphological opening on cap_zone eliminates thin 2px left whiskers cleanly
                k3_cap = np.ones((3, 3), dtype=np.uint8)
                cap_opened = cv2.morphologyEx(
                    (mask & cap_zone).astype(np.uint8), cv2.MORPH_OPEN, k3_cap
                ) > 0
                mask[cap_zone] = cap_opened[cap_zone]

                # Punch out the studio-gray hole inside the silver hanging loop
                top_band = np.zeros_like(mask)
                top_band[ymin : ymin + int(h_obj * 0.22), :] = True
                ring_hole = (
                    top_band & mask & (r > 185) & (g > 185) & (b > 185)
                    & (chroma < 18) & (grad < 32.0)
                )
                mask[ring_hole] = False

    elif "candy_cane" in item_name:
        # Preserve smooth tubular white stripes! Erode 1 extra px (4px total) to cleanly
        # clear the uniform sticker border around white stripes, then peel pure studio
        # white/gray fringe strictly bordering blue stripes or neutral studio rim.
        k3 = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.erode(mask.astype(np.uint8), k3, iterations=1) > 0

        blue_stripes = ((b - r) > 32) & (hsv_s > 60) & mask
        near_blue = binary_dilation(blue_stripes, structure=np.ones((9, 9), dtype=bool))
        halo_on_blue = near_blue & (
            (r > 192) & (g > 192) & (b > 192) & (chroma < 18)
        )
        mask = _peel_border_connected(mask, halo_on_blue, max_iters=5)

        # Peel residual pure neutral studio-gray rim (R,G,B > 196, low chroma < 12)
        pure_studio_nibs = (r > 196) & (g > 196) & (b > 196) & (chroma < 12)
        mask = _peel_border_connected(mask, pure_studio_nibs, max_iters=2)

        k_ell = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, k_ell) > 0
        mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, k3) > 0

    elif "snowman" in item_name:
        # Peel studio halo near dark hat, brown arms, blue mittens, blue scarf —
        # explicitly EXCLUDING the orange carrot nose (R > G + 25 & R > 150) so the white
        # right cheek is never nibbled!
        is_orange_carrot = (r > g + 25) & (r > 140)
        is_hat_arm_mitten_scarf = (
            ((hsv_s > 65) & (~is_orange_carrot))
            | (brightness < 110)
        ) & mask
        near_colored_part = binary_dilation(
            is_hat_arm_mitten_scarf, structure=np.ones((11, 11), dtype=bool)
        )
        snowman_halo = near_colored_part & (
            studio_neutral
            | ((brightness > 188) & (chroma < 24))
            | ((hsv_s < 58) & (hsv_v > 184))
        )
        mask = _peel_border_connected(mask, snowman_halo, max_iters=10)
        # Also peel studio-gray outer rim clinging to shaded snowball & hat edges
        flat_studio_rim = (
            (r > 194.0) & (g > 194.0) & (b > 194.0) & (chroma < 16.0)
        )
        mask = _peel_border_connected(mask, flat_studio_rim, max_iters=3)

    elif category == "pure_white":
        # Snowflake:
        # 1) Peel flat outer rim studio pixels
        flat_outer = (
            (brightness > 212) & (chroma < 12) & (grad < 14.0) & (local_std < 4.5)
        )
        mask = _peel_border_connected(mask, flat_outer, max_iters=14)

        # 2) Open the 6 trapped ultra-flat studio background wedges between snowflake arms!
        #    Real 3D frosted arms have grad > 14 and local_std > 2.5, while trapped studio
        #    background wedges are uniform bright gray (grad < 9, std < 2.2, brightness > 220).
        ys, xs = np.where(mask)
        if len(ys):
            cy_s = float(ys.mean())
            cx_s = float(xs.mean())
            yy, xx = np.ogrid[: mask.shape[0], : mask.shape[1]]
            dist_center = np.hypot(xx - cx_s, yy - cy_s)

            # Never punch the solid central hub (radius < 22px)
            flat_wedge = (
                mask
                & (dist_center > 22.0)
                & (brightness > 220.0)
                & (chroma < 10.0)
                & (grad < 10.0)
                & (local_std < 2.4)
            )
            labeled_w, num_w = label(flat_wedge)
            if num_w > 0:
                areas_w = np.bincount(labeled_w.ravel())
                areas_w[0] = 0
                pockets = np.zeros_like(mask)
                for cid in range(1, num_w + 1):
                    if areas_w[cid] >= 45:
                        pockets |= labeled_w == cid
                if np.any(pockets):
                    # Dilate pockets 1px into soft flat fringe so wedge edges are clean
                    pockets_exp = binary_dilation(
                        pockets, structure=np.ones((3, 3), dtype=bool)
                    ) & (brightness > 214.0) & (chroma < 12.0) & (grad < 22.0)
                    mask[pockets | pockets_exp] = False

    return mask


def _clip_ground_plane_shadows(
    mask: np.ndarray,
    feats: dict[str, np.ndarray],
    item_name: str,
    category: str,
) -> np.ndarray:
    """Clip horizontal flat ground shadows in the bottom 15-18%."""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return mask

    ymin, ymax = int(ys.min()), int(ys.max())
    h_obj = ymax - ymin
    if h_obj < 20:
        return mask

    r, g, b = feats["r"], feats["g"], feats["b"]
    brightness = feats["brightness"]
    chroma = feats["chroma"]
    hsv_s = feats["hsv_s"]

    # --- 1. Colored-base items ---
    if category == "pure_colored" or "candy_cane" in item_name:
        bcut_18 = ymax - int(h_obj * 0.18)
        bottom_zone = np.zeros_like(mask)
        bottom_zone[bcut_18 : ymax + 1, :] = True

        if "gingerbread" in item_name:
            bcut_gb = ymax - int(h_obj * 0.22)
            bottom_zone[bcut_gb : ymax + 1, :] = True
            shadow_cand = bottom_zone & ((r - b) < 16) & (brightness > 95) & (chroma < 48)
        elif "tree" in item_name:
            shadow_cand = bottom_zone & (b >= r - 6) & (brightness > 90) & (hsv_s < 75)
        elif "santa_hat" in item_name or "stocking" in item_name:
            bcut_blue = ymax - int(h_obj * 0.20)
            bottom_zone[bcut_blue : ymax + 1, :] = True
            shadow_cand = bottom_zone & (hsv_s < 88) & (brightness > 92)
        elif "candy_cane" in item_name:
            shadow_cand = bottom_zone & (hsv_s < 65) & (chroma < 38)
        else:
            shadow_cand = bottom_zone & (chroma < 44) & (hsv_s < 70) & (brightness > 95)

        mask = _peel_border_connected(mask, shadow_cand, max_iters=60)
        return _keep_largest_component(mask)

    # --- 2. Gift box: straight vertical walls + dark contact crease floor cutoff ---
    if "gift_box" in item_name:
        y_wall_top = ymin + int(h_obj * 0.52)
        y_wall_bot = ymin + int(h_obj * 0.78)
        wall_xs_right, wall_xs_left = [], []
        for y in range(y_wall_top, y_wall_bot + 1):
            rxs = np.where(mask[y])[0]
            if len(rxs) > 20:
                wall_xs_left.append(int(rxs.min()))
                wall_xs_right.append(int(rxs.max()))
        if wall_xs_right:
            ref_left = int(np.percentile(wall_xs_left, 25))
            ref_right = int(np.percentile(wall_xs_right, 50)) - 2
            bcut_22 = ymax - int(h_obj * 0.22)
            mask[bcut_22 : ymax + 1, : max(0, ref_left)] = False
            mask[bcut_22 : ymax + 1, min(mask.shape[1], ref_right) :] = False

        # Cut below the dark floor contact crease under the cube (and clip any right-edge
        # vertical shadow pillar hanging below the bottom-right cube corner).
        bcut_16 = ymax - int(h_obj * 0.16)
        cut_ys_by_x: dict[int, int] = {}
        for x in range(int(xs.min()), int(xs.max()) + 1):
            col_ys = np.where(mask[bcut_16 : ymax + 1, x])[0] + bcut_16
            if len(col_ys) < 3:
                continue
            col_b = brightness[col_ys, x]
            col_s = hsv_s[col_ys, x]
            dark_idx = np.where((col_b < 118) & (col_s < 115))[0]
            if len(dark_idx) > 0:
                cut_y = int(col_ys[dark_idx[0]])
                cut_ys_by_x[x] = cut_y
                mask[cut_y : ymax + 1, x] = False

        # For rightmost/leftmost columns that missed the dark contact crease, extrapolate
        # the clean bottom floor slope so zero vertical shadow pillar hangs at the corner.
        if cut_ys_by_x:
            known_xs = sorted(cut_ys_by_x.keys())
            right_cut_y = cut_ys_by_x[known_xs[-1]]
            left_cut_y = cut_ys_by_x[known_xs[0]]
            for x in range(known_xs[-1] + 1, int(xs.max()) + 1):
                mask[right_cut_y : ymax + 1, x] = False
            for x in range(int(xs.min()), known_xs[0]):
                mask[left_cut_y : ymax + 1, x] = False

        # Remove any tiny trailing gray shadow nub at very bottom corners
        ys_now = np.where(mask)[0]
        if len(ys_now):
            bcut_10 = ymax - int(h_obj * 0.10)
            bot_z = np.zeros_like(mask)
            bot_z[bcut_10 : ymax + 1, :] = True
            dark_or_gray_nub = bot_z & (brightness < 145) & (hsv_s < 90)
            mask = _peel_border_connected(mask, dark_or_gray_nub, max_iters=10)
        return _keep_largest_component(mask)

    # --- 3. Snowflake: clip horizontal flare below the narrow vertical bottom stem ---
    if "snowflake" in item_name:
        y_scan_start = ymax - int(h_obj * 0.22)
        y_scan_end = ymax - int(h_obj * 0.04)
        widths = []
        for y in range(y_scan_start, y_scan_end + 1):
            rxs = np.where(mask[y])[0]
            if len(rxs):
                widths.append((y, int(rxs.max() - rxs.min()), int(rxs.min()), int(rxs.max())))
        if widths:
            neck_y, _, neck_l, neck_r = min(widths, key=lambda t: t[1])
            pad = 2
            mask[neck_y + 1 : ymax + 1, : max(0, neck_l - pad)] = False
            mask[neck_y + 1 : ymax + 1, min(mask.shape[1], neck_r + pad + 1) :] = False
            stem_bot_zone = np.zeros_like(mask)
            stem_bot_zone[neck_y + 6 : ymax + 1, :] = True
            dark_contact = stem_bot_zone & (brightness < 185) & (chroma < 22)
            mask = _peel_border_connected(mask, dark_contact, max_iters=15)
        return _keep_largest_component(mask)

    # --- 4. Bauble: already trimmed to exact sphere circle in _strip_studio_halo ---
    if "bauble" in item_name:
        return _keep_largest_component(mask)

    # --- 5. Snowman: monotonic convex inward taper + fitted lower snowball arc ---
    if "snowman" in item_name:
        y_belly_top = ymin + int(h_obj * 0.72)
        y_belly_bot = ymin + int(h_obj * 0.85)
        best_l = None
        best_r = None
        for y in range(y_belly_top, ymax + 1):
            rxs = np.where(mask[y])[0]
            if len(rxs) == 0:
                continue
            cur_l, cur_r = int(rxs.min()), int(rxs.max())
            if y <= y_belly_bot:
                best_l, best_r = cur_l, cur_r
            else:
                if best_l is not None and cur_l < best_l:
                    mask[y, :best_l] = False
                    cur_l = best_l
                if best_r is not None and cur_r > best_r:
                    mask[y, best_r + 1 :] = False
                    cur_r = best_r
                best_l = cur_l if best_l is None else max(best_l, cur_l)
                best_r = cur_r if best_r is None else min(best_r, cur_r)

        circle = _fit_circle_to_band(mask, ymin + int(h_obj * 0.72), ymin + int(h_obj * 0.92))
        if circle is not None:
            cx, cy, rad = circle
            yy, xx = np.ogrid[: mask.shape[0], : mask.shape[1]]
            outside_ball = np.hypot(xx - cx, yy - cy) > (rad + 1.5)
            mask[(yy >= ymin + int(h_obj * 0.86)) & outside_ball] = False
        return _keep_largest_component(mask)

    return _keep_largest_component(mask)


def strip_halo_and_shadow(
    img: Image.Image,
    item_name: str,
    clear_outer_margin: int = 10,
) -> tuple[Image.Image, dict]:
    arr = np.array(img.convert("RGBA"), dtype=np.uint8)
    rgb = arr[:, :, :3].copy()
    alpha = arr[:, :, 3].copy()

    # Step 1: Identify solid object mask where Alpha > 20
    solid_mask = alpha > 20
    initial_area = int(solid_mask.sum())
    if initial_area == 0:
        return img, {"category": "empty", "initial_px": 0, "final_px": 0, "stripped_px": 0, "retained_pct": 0.0}

    category = _classify_item(item_name)
    feats = _compute_color_features(rgb)

    # Step 2: Mandatory morphological inward erosion (cv2.erode, 3x3 kernel)
    kernel_3x3 = np.ones((3, 3), dtype=np.uint8)
    erode_iters = 2 if category == "pure_white" else 3
    eroded = cv2.erode(solid_mask.astype(np.uint8), kernel_3x3, iterations=erode_iters) > 0

    # Step 2b: Strip remaining variable-thickness studio white/gray sticker halo
    halo_stripped = _strip_studio_halo(eroded, feats, item_name, category)

    # Step 3: Clip horizontal flat ground shadows in the bottom 15-18%
    clean_mask = _clip_ground_plane_shadows(halo_stripped, feats, item_name, category)
    clean_mask = _keep_largest_component(clean_mask)

    # Step 4: Subtle 1px Gaussian smoothing strictly on outer alpha transition edge
    # + nearest-interior RGB decontamination to eliminate harsh staircasing & color bleed
    clean_u8 = clean_mask.astype(np.uint8)
    inner_core = cv2.erode(clean_u8, kernel_3x3, iterations=1) > 0
    outer_limit = cv2.dilate(clean_u8, kernel_3x3, iterations=1) > 0

    blurred = cv2.GaussianBlur(clean_u8.astype(np.float32) * 255.0, (3, 3), sigmaX=0.8)
    new_alpha = np.zeros_like(alpha, dtype=np.uint8)
    transition_band = outer_limit & (~inner_core)
    new_alpha[transition_band] = np.clip(np.round(blurred[transition_band]), 0, 255).astype(np.uint8)
    new_alpha[inner_core] = 255
    new_alpha[new_alpha < 15] = 0

    # Optionally clear outer image margins (disabled when caller guarantees safe padding)
    if clear_outer_margin > 0:
        m = clear_outer_margin
        new_alpha[:m, :] = 0
        new_alpha[-m:, :] = 0
        new_alpha[:, :m] = 0
        new_alpha[:, -m:] = 0

    # Decontaminate RGB on the 1px antialiased transition ring from nearest deep interior pixel
    source_core = cv2.erode(clean_u8, kernel_3x3, iterations=2) > 0
    if not np.any(source_core):
        source_core = inner_core if np.any(inner_core) else clean_mask

    new_rgb = rgb.copy()
    if np.any(source_core):
        _, nearest_idx = distance_transform_edt(~source_core, return_indices=True)
        semi_ring = (new_alpha > 0) & (~inner_core)
        sy, sx = np.where(semi_ring)
        new_rgb[sy, sx] = rgb[nearest_idx[0, sy, sx], nearest_idx[1, sy, sx]]

    new_rgb[new_alpha == 0] = 0

    final_area = int((new_alpha > 20).sum())
    result_img = Image.fromarray(np.dstack((new_rgb, new_alpha)), "RGBA")
    stats = {
        "category": category,
        "initial_px": initial_area,
        "final_px": final_area,
        "stripped_px": max(0, initial_area - final_area),
        "retained_pct": round(100.0 * final_area / max(1, initial_area), 1),
    }
    return result_img, stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Strip white/gray sticker halos and flat ground-plane floor shadows from decor PNGs."
    )
    parser.add_argument(
        "target_dir",
        nargs="?",
        type=Path,
        default=Path("assets/brands/gsshop/decors"),
        help="Directory containing decor PNG files to process in-place.",
    )
    args = parser.parse_args()

    png_files = sorted(args.target_dir.glob("*.png"))
    if not png_files:
        print(f"No PNG files found in {args.target_dir}")
        return 1

    print("\n=========== STRIP HALO & GROUND-PLANE SHADOW ENGINE ===========")
    print(f"Target directory: {args.target_dir} ({len(png_files)} PNG files)\n")

    for path in png_files:
        with Image.open(path) as im:
            cleaned, stats = strip_halo_and_shadow(im, path.name)
        cleaned.save(path, "PNG", optimize=True)
        print(
            f"[DONE] {path.name:24s} ({stats['category']:12s}) | "
            f"stripped={stats['stripped_px']:5d} px | retained={stats['retained_pct']:5.1f}%"
        )

    print("\n===============================================================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
