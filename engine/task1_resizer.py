"""
Deterministic Task 1 Production Resizer (`engine/task1_resizer.py`).

Consumes:
  - `config/task1_size_guide_matrix.json` (11 artboard zone specs from Size Guide PSD)
  - `assets/brands/xexymix/cutouts/` (clean RGBA layers from 1440x1800 Master PSD)
  - `assets/brands/xexymix/badges/` (11 native per-artboard promo badges from Size Guide PSD)

Renders all 11 verified PNG ad placements using high-quality `Image.Resampling.BICUBIC`
into `output/task1_production/TASK1_XEXYMIX_11_SIZES/`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = ROOT / "config" / "task1_size_guide_matrix.json"
DEFAULT_MANIFEST = ROOT / "assets" / "brands" / "xexymix" / "cutouts" / "master_assets_manifest.json"
DEFAULT_OUT_DIR = ROOT / "output" / "task1_production" / "TASK1_XEXYMIX_11_SIZES"

# Model bounding box inside 1440x1800 base_model_scene.png (x, y, w, h)
MASTER_MODEL_BBOX = (700.0, 0.0, 740.0, 1800.0)

# Normalized outer silhouette tangent anchors relative to MASTER_MODEL_BBOX (mx, my, mw, mh):
# - Pocket target: outer silhouette contour tangent at hip/pocket seam (x=869, y=382 on 1440x1800)
# - Fleece target: outer silhouette contour tangent at outer thigh (x=755, y=792 on 1440x1800)
POCKET_TARGET_NORM = (0.228, 0.212)
FLEECE_TARGET_NORM = (0.074, 0.440)


def fit_contain(
    img: Image.Image,
    max_w: int,
    max_h: int,
) -> Image.Image:
    """Resize `img` with BICUBIC to fit inside (max_w, max_h) preserving aspect ratio."""
    if max_w <= 0 or max_h <= 0:
        return img
    scale = min(max_w / img.width, max_h / img.height)
    new_w = max(1, int(round(img.width * scale)))
    new_h = max(1, int(round(img.height * scale)))
    return img.resize((new_w, new_h), Image.Resampling.BICUBIC)


def build_seamless_backdrop(
    base_scene: Image.Image,
    target_w: int,
    target_h: int,
    layout_type: str,
    flip_x: bool = False,
) -> Tuple[Image.Image, Tuple[float, float, float, float]]:
    """
    Frame `base_model_scene.png` (1440x1800) cleanly onto (target_w, target_h)
    without stretching or cropping the model's head/body/sneakers.

    Returns:
        (canvas_rgba, (model_x, model_y, model_w, model_h)) in target canvas coordinates.
    """
    src = base_scene.convert("RGBA")
    if flip_x:
        src = src.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

    sw, sh = src.size
    target_ratio = target_w / target_h
    src_ratio = sw / sh  # 0.80
    mmx, mmy, mmw, mmh = MASTER_MODEL_BBOX

    # Exact 4:5 match (1440x1800, 960x1200, 800x1000)
    if abs(target_ratio - src_ratio) < 0.02:
        sx = target_w / sw
        sy = target_h / sh
        model_box = (mmx * sx, mmy * sy, mmw * sx, mmh * sy)
        return src.resize((target_w, target_h), Image.Resampling.BICUBIC), model_box

    # Tall 9:16 (1440x2560): cover-scale to height, crop right-weighted so full model is visible
    if target_ratio < src_ratio:
        scale = target_h / sh
        scaled_w = int(round(sw * scale))
        scaled = src.resize((scaled_w, target_h), Image.Resampling.BICUBIC)
        if flip_x:
            crop_x = 0
        else:
            # Right-aligned crop keeps 100% of model + clean left barricade
            crop_x = max(0, scaled_w - target_w)
        model_box = (mmx * scale - crop_x, mmy * scale, mmw * scale, mmh * scale)
        return scaled.crop((crop_x, 0, crop_x + target_w, target_h)), model_box

    # Square, Wide, or Landscape Micro (target_ratio > 0.80):
    # Scale full model height to target_h so head-to-sneakers are 100% preserved,
    # and seamlessly blend into a clean ambient studio backdrop (#E2E4E7 -> #D8DADB)
    # using a wide cosine-tapered horizontal alpha feather (150px-220px on standard/wide).
    scale = target_h / sh
    scaled_w = max(1, int(round(sw * scale)))
    scaled = src.resize((scaled_w, target_h), Image.Resampling.BICUBIC)

    # Synthesize clean vertical ambient studio gradient (#E2E4E7 top -> #D8DADB bottom)
    top_rgb = np.array([226.0, 228.0, 231.0], dtype=np.float32)  # #E2E4E7
    bot_rgb = np.array([216.0, 218.0, 219.0], dtype=np.float32)  # #D8DADB
    grad_t = np.linspace(0.0, 1.0, target_h, dtype=np.float32)[:, None, None]
    bg_rgb = (top_rgb * (1.0 - grad_t) + bot_rgb * grad_t).astype(np.uint8)
    bg_arr = np.broadcast_to(bg_rgb, (target_h, target_w, 3)).copy()
    bg_rgba = np.concatenate(
        [bg_arr, np.full((target_h, target_w, 1), 255, dtype=np.uint8)], axis=2
    )
    canvas = Image.fromarray(bg_rgba, mode="RGBA")

    # Wide cosine-tapered horizontal alpha feather across transition boundary (150px-220px for wide/square)
    if target_w >= 800:
        feather_w = min(220, max(150, int(round(scaled_w * 0.36))))
    else:
        feather_w = min(int(scaled_w * 0.32), max(28, int(round(target_w * 0.18))))
    feather_w = min(feather_w, max(1, scaled_w - 1))

    t = np.linspace(0.0, 1.0, feather_w, dtype=np.float32)
    cosine_decay = 0.5 * (1.0 - np.cos(np.pi * t))
    ramp_u8 = np.clip(np.round(cosine_decay * 255.0), 0, 255).astype(np.uint8)

    if not flip_x:
        # Model is on the right -> feather left transition edge of `scaled`
        paste_x = target_w - scaled_w
        mask_arr = np.full((target_h, scaled_w), 255, dtype=np.uint8)
        mask_arr[:, :feather_w] = ramp_u8[None, :]
        mask = Image.fromarray(mask_arr, mode="L")
        canvas.paste(scaled, (paste_x, 0), mask)
        model_box = (paste_x + mmx * scale, mmy * scale, mmw * scale, mmh * scale)
    else:
        # Flipped (kakao_bizboard): model is on the left -> feather right transition edge
        mask_arr = np.full((target_h, scaled_w), 255, dtype=np.uint8)
        mask_arr[:, scaled_w - feather_w :] = ramp_u8[::-1][None, :]
        mask = Image.fromarray(mask_arr, mode="L")
        canvas.paste(scaled, (0, 0), mask)
        flipped_mx = (sw - (mmx + mmw)) * scale
        model_box = (flipped_mx, mmy * scale, mmw * scale, mmh * scale)

    return canvas, model_box


def apply_legibility_scrim(
    canvas: Image.Image,
    zone_px: Dict[str, int],
    opacity: float = 0.42,
) -> None:
    """Apply a soft feathered dark scrim behind white headline text on bright backdrops."""
    w, h = canvas.size
    zx, zy, zw, zh = zone_px["x"], zone_px["y"], zone_px["width"], zone_px["height"]
    if zw <= 0 or zh <= 0:
        return

    pad_x = max(16, int(zw * 0.12))
    pad_y = max(12, int(zh * 0.18))
    x1 = max(0, zx - pad_x)
    y1 = max(0, zy - pad_y)
    x2 = min(w, zx + zw + pad_x)
    y2 = min(h, zy + zh + pad_y)
    rw, rh = x2 - x1, y2 - y1
    if rw <= 0 or rh <= 0:
        return

    # Smooth cosine-tapered elliptical vignette (fades strictly to 0.0 at boundary -> zero hard edges)
    yy, xx = np.mgrid[0:rh, 0:rw]
    nx = (xx - rw / 2.0) / max(1.0, rw / 2.0)
    ny = (yy - rh / 2.0) / max(1.0, rh / 2.0)
    r = np.sqrt(nx * nx + ny * ny)
    falloff = np.clip(1.0 - r, 0.0, 1.0)
    alpha_f = (falloff * falloff * (3.0 - 2.0 * falloff)) * opacity
    alpha_u8 = (alpha_f * 255).astype(np.uint8)

    scrim = np.zeros((rh, rw, 4), dtype=np.uint8)
    scrim[..., 0] = 16
    scrim[..., 1] = 20
    scrim[..., 2] = 26
    scrim[..., 3] = alpha_u8

    scrim_img = Image.fromarray(scrim, mode="RGBA")
    canvas.alpha_composite(scrim_img, (x1, y1))


def draw_callout_leader_lines(
    canvas: Image.Image,
    card1_rect: Tuple[int, int, int, int],
    card2_rect: Tuple[int, int, int, int],
    model_box: Tuple[float, float, float, float],
) -> None:
    """
    Draw 4x supersampled anti-aliased white orthogonal (Manhattan 90-degree)
    callout leader lines connecting the right border of each feature card to the
    outer silhouette contour edge of the leggings, terminated with tangent white dots.
    """
    w, h = canvas.size
    mx, my, mw, mh = model_box

    # Card right-edge attachment anchors (aligned flush to white card border & photo center)
    c1x, c1y, c1w, c1h = card1_rect
    c2x, c2y, c2w, c2h = card2_rect
    origin1 = (c1x + c1w * 0.905, c1y + c1h * 0.44)
    origin2 = (c2x + c2w * 0.905, c2y + c2h * 0.44)

    # Outer silhouette edge tangent targets (do not penetrate interior fabric)
    target1 = (mx + mw * POCKET_TARGET_NORM[0], my + mh * POCKET_TARGET_NORM[1])
    target2 = (mx + mw * FLEECE_TARGET_NORM[0], my + mh * FLEECE_TARGET_NORM[1])

    # Crisp 2.0px stroke and 2.5px terminal dot radius (4x supersampled for AA)
    stroke_w = 2.0
    dot_r = 2.5
    ss = 4
    overlay = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for (x1, y1), (x2, y2) in ((origin1, target1), (origin2, target2)):
        # Strictly orthogonal Manhattan routing (zero diagonal slopes)
        if abs(y1 - y2) < 10.0:
            # Direct horizontal route
            pts = [(x1, y1), (x2, y1)]
            end_x, end_y = x2, y1
        else:
            # 90-degree elbow route: Horizontal -> Vertical -> Horizontal
            x_mid = x1 + (x2 - x1) * 0.4
            pts = [(x1, y1), (x_mid, y1), (x_mid, y2), (x2, y2)]
            end_x, end_y = x2, y2

        pts_ss = [(px * ss, py * ss) for (px, py) in pts]
        shadow_pts_ss = [(px * ss, py * ss + ss) for (px, py) in pts]

        # Subtle contrast shadow pass
        draw.line(
            shadow_pts_ss,
            fill=(0, 0, 0, 50),
            width=int(round((stroke_w + 0.8) * ss)),
            joint="curve",
        )
        # Main crisp white orthogonal stroke RGBA(255, 255, 255, 240)
        draw.line(
            pts_ss,
            fill=(255, 255, 255, 240),
            width=int(round(stroke_w * ss)),
            joint="curve",
        )
        # Terminal tangent dot (radius = 2.5px) at outer silhouette contour
        r_ss = dot_r * ss
        draw.ellipse(
            [
                end_x * ss - r_ss - ss * 0.75,
                end_y * ss - r_ss - ss * 0.75,
                end_x * ss + r_ss + ss * 0.75,
                end_y * ss + r_ss + ss * 0.75,
            ],
            fill=(0, 0, 0, 60),
        )
        draw.ellipse(
            [
                end_x * ss - r_ss,
                end_y * ss - r_ss,
                end_x * ss + r_ss,
                end_y * ss + r_ss,
            ],
            fill=(255, 255, 255, 255),
        )

    aa_overlay = overlay.resize((w, h), Image.Resampling.LANCZOS)
    canvas.alpha_composite(aa_overlay, (0, 0))


def composite_feature_cards(
    canvas: Image.Image,
    artboard_spec: Dict[str, Any],
    assets: Dict[str, Image.Image],
    manifest: Dict[str, Any],
    model_box: Tuple[float, float, float, float],
) -> None:
    fc_zone = artboard_spec["zones"]["feature_card_zone"]
    if not fc_zone.get("visible", False):
        return

    w, h = artboard_spec["width"], artboard_spec["height"]
    layout_type = artboard_spec["layout_type"]
    px = fc_zone["px"]
    hl_px = artboard_spec["zones"]["headline_zone"]["px"]

    card1 = assets["card_pocket_clean"]
    card2 = assets["card_fleece_clean"]
    stagger_px = max(16, int(round(32 * (w / 1200.0))))

    card1_rect: Tuple[int, int, int, int]
    card2_rect: Tuple[int, int, int, int]

    if layout_type == "vertical_4_5" and fc_zone.get("use_leader_lines", False):
        # Exact proportional mapping from master 1440x1800 canvas
        mw_c = manifest["master_canvas"]["width"]
        mh_c = manifest["master_canvas"]["height"]
        sx = w / mw_c
        sy = h / mh_c

        master_fleece_bottom = (
            manifest["assets"]["card_fleece_clean"]["master_bbox"]["y"]
            + manifest["assets"]["card_fleece_clean"]["master_bbox"]["height"]
        ) * sy
        max_allowed_bottom = hl_px["y"] - int(h * 0.025)

        if master_fleece_bottom <= max_allowed_bottom:
            rects = []
            for key, img in (("card_pocket_clean", card1), ("card_fleece_clean", card2)):
                mb = manifest["assets"][key]["master_bbox"]
                tw = max(1, int(round(img.width * sx)))
                th = max(1, int(round(img.height * sy)))
                tx = int(round(mb["x"] * sx))
                ty = int(round(mb["y"] * sy))
                resized = img.resize((tw, th), Image.Resampling.BICUBIC)
                canvas.alpha_composite(resized, (tx, ty))
                rects.append((tx, ty, tw, th))
            draw_callout_leader_lines(canvas, rects[0], rects[1], model_box)
            return

    if layout_type == "wide":
        # Dedicated staggered vertical feature-card column between flush-left typography & right model
        x_cards = int(round(w * 0.525))
        y_top = int(round(h * 0.095))
        y_bot = int(round(h * 0.89))
        avail_h = max(120, y_bot - y_top)
        gap = max(14, int(round(avail_h * 0.055)))
        slot_h = max(60, (avail_h - gap) // 2)
        c1 = fit_contain(card1, slot_h, slot_h)
        c2 = fit_contain(card2, slot_h, slot_h)
        card1_rect = (x_cards, y_top, c1.width, c1.height)
        card2_rect = (x_cards + stagger_px, y_top + c1.height + gap, c2.width, c2.height)
        canvas.alpha_composite(c1, (card1_rect[0], card1_rect[1]))
        canvas.alpha_composite(c2, (card2_rect[0], card2_rect[1]))
        draw_callout_leader_lines(canvas, card1_rect, card2_rect, model_box)
        return

    # Vertical 9:16, kakao_feed_4_5, and Square (1:1): staggered vertical stack
    # ensures unobstructed horizontal callout leader lines to both anatomical zones
    zx, zy, zw, zh = px["x"], px["y"], px["width"], px["height"]
    gap = max(10, int(zh * 0.035))
    slot_h = max(40, (zh - gap) // 2)
    c1 = fit_contain(card1, max(40, zw - stagger_px), slot_h)
    c2 = fit_contain(card2, max(40, zw - stagger_px), slot_h)
    card1_rect = (zx, zy, c1.width, c1.height)
    card2_rect = (zx + stagger_px, zy + c1.height + gap, c2.width, c2.height)
    canvas.alpha_composite(c1, (card1_rect[0], card1_rect[1]))
    canvas.alpha_composite(c2, (card2_rect[0], card2_rect[1]))
    draw_callout_leader_lines(canvas, card1_rect, card2_rect, model_box)


def render_artboard(
    spec: Dict[str, Any],
    assets: Dict[str, Image.Image],
    manifest: Dict[str, Any],
    out_dir: Path,
) -> Path:
    slug = spec["slug"]
    w, h = spec["width"], spec["height"]
    layout_type = spec["layout_type"]
    is_micro = spec["is_micro"]
    zones = spec["zones"]

    flip_x = bool(zones["model_zone"].get("flip_x", False))
    canvas, model_box = build_seamless_backdrop(
        assets["base_model_scene"],
        target_w=w,
        target_h=h,
        layout_type=layout_type,
        flip_x=flip_x,
    )

    # Flush-left typography anchor for horizontal wide layouts
    x_base = int(round(w * 0.065))

    if layout_type == "wide":
        # Lock logo, headline, and promo ribbon strictly flush-left to x_base
        logo_box = {
            "x": x_base,
            "y": int(round(h * 0.08)),
            "width": int(round(w * 0.175)),
            "height": int(round(h * 0.05)),
        }
        hl_box = {
            "x": x_base,
            "y": int(round(h * 0.235)),
            "width": int(round(w * 0.415)),
            "height": int(round(h * 0.34)),
        }
        promo_px = zones["promo_sticker_zone"]["px"]
        promo_box = {
            "x": x_base,
            "y": int(round(h * 0.68)),
            "width": min(int(round(w * 0.43)), promo_px["width"]),
            "height": min(int(round(h * 0.21)), promo_px["height"]),
        }
    else:
        logo_box = zones["logo_zone"]["px"]
        hl_box = zones["headline_zone"]["px"]
        promo_box = zones["promo_sticker_zone"]["px"]

    # 1. Soft legibility scrim behind headline on square, wide, and micro layouts
    if layout_type in ("square", "wide", "micro"):
        scrim_opacity = 0.52 if is_micro else 0.34
        apply_legibility_scrim(canvas, hl_box, opacity=scrim_opacity)

    # 2. Brand Logo
    logo_z = zones["logo_zone"]
    if logo_z.get("visible", True):
        logo_resized = fit_contain(assets["logo_xexymix"], logo_box["width"], logo_box["height"])
        canvas.alpha_composite(logo_resized, (logo_box["x"], logo_box["y"]))

    # 3. AI Generated Watermark permanently suppressed across all 11 placements

    # 4. Feature Cards + Parametric Callout Leader Lines (omitted on micro viewports)
    composite_feature_cards(canvas, spec, assets, manifest, model_box)

    # 5. Headline Group
    hl_z = zones["headline_zone"]
    if hl_z.get("visible", True):
        hl_resized = fit_contain(assets["headline_group"], hl_box["width"], hl_box["height"])
        if hl_z.get("anchor") == "middle_right":
            hx = hl_box["x"] + max(0, hl_box["width"] - hl_resized.width)
        else:
            hx = hl_box["x"]
        hy = hl_box["y"] + max(0, (hl_box["height"] - hl_resized.height) // 2)
        canvas.alpha_composite(hl_resized, (hx, hy))

    # 6. Native Promo Ribbon / Starburst Badge (exact pixel match from Size Guide PSD)
    promo_z = zones["promo_sticker_zone"]
    if promo_z.get("visible", True):
        native_path = promo_z.get("native_badge_path")
        promo_img: Image.Image
        if native_path and (ROOT / native_path).exists():
            promo_img = Image.open(ROOT / native_path).convert("RGBA")
        else:
            promo_img = assets["promo_master"]
        if layout_type == "wide":
            promo_img = fit_contain(promo_img, promo_box["width"], promo_box["height"])
            canvas.alpha_composite(promo_img, (promo_box["x"], promo_box["y"]))
        else:
            if promo_img.size != (promo_box["width"], promo_box["height"]):
                promo_img = promo_img.resize((promo_box["width"], promo_box["height"]), Image.Resampling.BICUBIC)
            canvas.alpha_composite(promo_img, (promo_box["x"], promo_box["y"]))

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.png"
    canvas.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render all 11 Task 1 XEXYMIX banners.")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), help="Path to task1_size_guide_matrix.json")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to master_assets_manifest.json")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Output directory")
    args = parser.parse_args()

    matrix = json.loads(Path(args.matrix).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    out_dir = Path(args.out)

    assets: Dict[str, Image.Image] = {}
    for key, info in manifest["assets"].items():
        assets[key] = Image.open(ROOT / info["path"]).convert("RGBA")

    print(f"[task1_resizer] Rendering {len(matrix['artboards'])} placements -> {out_dir}")
    for spec in matrix["artboards"]:
        out_path = render_artboard(spec, assets, manifest, out_dir)
        print(f"  [ok] {spec['slug']:22s} ({spec['width']}x{spec['height']}) -> {out_path.relative_to(ROOT)}")

    print("[task1_resizer] Complete.")


if __name__ == "__main__":
    main()
