#!/usr/bin/env python3
"""
DIR-ASSEMBLE-COSRX-MASTER-1200x1200-077: COSRX x ULTA Layered Master PSD Builder
(engine/cosrx_psd_builder.py)

Compiles the COSRX x ULTA Beauty 1200x1200 Master Banner into a fully editable,
multi-layer RGBA Adobe Photoshop PSD with strict sandwich-depth hierarchy.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageCms
from psd_tools import PSDImage
from psd_tools.constants import Resource, Tag
from psd_tools.psd.image_resources import ImageResource

ROOT = Path(__file__).resolve().parent.parent
COSRX_DIR = ROOT / "assets" / "brands" / "COSRX"
LAYERS_DIR = COSRX_DIR / "layers"
TEXTURES_DIR = COSRX_DIR / "textures"

OUT_DIR = ROOT / "output" / "TASK_COSRX"
DEFAULT_OUT_PSD = OUT_DIR / "cosrx_master_1200x1200.psd"

CANVAS_W = 1200
CANVAS_H = 1200

SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def load_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Missing asset: {path}")
    with Image.open(path) as im:
        return im.convert("RGBA").copy()


def apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 0.999:
        return img
    arr = np.array(img.convert("RGBA"), dtype=np.float32)
    arr[..., 3] = np.clip(arr[..., 3] * opacity, 0.0, 255.0)
    return Image.fromarray(np.round(arr).astype(np.uint8), mode="RGBA")


def rotate_css(
    img: Image.Image,
    deg: float,
    origin_x_frac: float = 0.5,
    origin_y_frac: float = 0.5,
) -> Tuple[Image.Image, float, float]:
    """Rotate image like CSS transform: rotate(deg) deg around origin."""
    if abs(deg) < 1e-4:
        return img, 0.0, 0.0
    w, h = img.size
    ox = w * origin_x_frac
    oy = h * origin_y_frac

    rad = math.radians(deg)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    corners = [
        (-ox, -oy),
        (w - ox, -oy),
        (w - ox, h - oy),
        (-ox, h - oy),
    ]
    rot_corners = [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in corners]
    min_x = min(x for x, y in rot_corners)
    max_x = max(x for x, y in rot_corners)
    min_y = min(y for x, y in rot_corners)
    max_y = max(y for x, y in rot_corners)

    center_rot_x = (min_x + max_x) / 2.0
    center_rot_y = (min_y + max_y) / 2.0
    dx = center_rot_x
    dy = center_rot_y

    rotated = img.rotate(-deg, resample=Image.Resampling.BICUBIC, expand=True)
    return rotated, dx, dy


def tight_crop_with_offset(img: Image.Image, left: float, top: float) -> Tuple[Image.Image, int, int]:
    bbox = img.getbbox()
    if bbox is None:
        return img, int(round(left)), int(round(top))
    cropped = img.crop(bbox)
    return cropped, int(round(left + bbox[0])), int(round(top + bbox[1]))


def add_pixel_layer(
    group,
    img: Image.Image,
    name: str,
    left: int,
    top: int,
    unicode_name: str | None = None,
) -> None:
    rgba = img.convert("RGBA")
    pl = group.create_pixel_layer(rgba, name=name, top=int(round(top)), left=int(round(left)))
    if unicode_name:
        pl.tagged_blocks.set_data(Tag.UNICODE_LAYER_NAME, unicode_name)


def build_cosrx_master_psd(out_psd: Path = DEFAULT_OUT_PSD) -> Path:
    print("[PSD] Compiling COSRX x ULTA 1200x1200 Layered Master PSD...")
    out_psd.parent.mkdir(parents=True, exist_ok=True)

    # 1. Background studio laboratory gradient (#FFFFFF to #FBFBFB)
    yy, xx = np.indices((CANVAS_H, CANVAS_W), dtype=np.float32)
    dist = np.sqrt(((xx - CANVAS_W * 0.5) / (CANVAS_W * 0.7)) ** 2 + ((yy - CANVAS_H * 0.45) / (CANVAS_H * 0.7)) ** 2)
    t = np.clip(dist, 0.0, 1.0)[..., None]
    c_center = np.array([255, 255, 255], dtype=np.float32)
    c_outer = np.array([251, 251, 251], dtype=np.float32)
    bg_rgb = np.round(c_center * (1.0 - t) + c_outer * t).astype(np.uint8)
    bg_a = np.full((CANVAS_H, CANVAS_W, 1), 255, dtype=np.uint8)
    im_bg_gradient = Image.fromarray(np.concatenate([bg_rgb, bg_a], axis=-1), mode="RGBA")

    # Load all 11 source RGBA layers and textures
    im_smear_src = load_rgba(TEXTURES_DIR / "03_smear_hydrating_wave.png")
    im_header_src = load_rgba(LAYERS_DIR / "01_logo_dual_lockup.png")
    im_bag_back_src = load_rgba(LAYERS_DIR / "03_decor_bag_back.png")
    im_kit_src = load_rgba(LAYERS_DIR / "04_product_holiday_kit.png")
    im_pdrn_src = load_rgba(LAYERS_DIR / "07_product_pdrn_serum.png")
    im_snail_src = load_rgba(LAYERS_DIR / "05_product_snail_essence.png")
    im_peptide_src = load_rgba(LAYERS_DIR / "06_product_peptide_serum.png")
    im_swatch_src = load_rgba(TEXTURES_DIR / "01_swatch_snail_cream.png")
    im_cream_src = load_rgba(LAYERS_DIR / "08_product_snail_cream_jar.png")
    im_bag_front_src = load_rgba(LAYERS_DIR / "09_decor_bag_front.png")
    im_droplets_src = load_rgba(TEXTURES_DIR / "02_droplets_aqueous_serum.png")
    im_ribbon_src = load_rgba(LAYERS_DIR / "02_ribbon_early_access.png")
    im_cta_src = load_rgba(LAYERS_DIR / "11_ui_cta_button.png")

    # Optional independent UI layers or combined fallback
    path_10a = LAYERS_DIR / "10a_headline_black_friday.png"
    path_10b = LAYERS_DIR / "10b_discount_up_to_30_off.png"
    path_10_combined = LAYERS_DIR / "10_typography_headline_discount.png"
    has_independent_typo = path_10a.exists() and path_10b.exists()

    # Initialize 1200x1200 RGBA 8-bit PSD
    psd = PSDImage.new("RGBA", (CANVAS_W, CANVAS_H))

    # ==========================================================================
    # GROUP 1: 01_Backdrop_and_Bag_Rear (Bottom-most)
    # ==========================================================================
    grp_01 = psd.create_group(name="01_Backdrop_and_Bag_Rear", open_folder=True)
    add_pixel_layer(grp_01, im_bg_gradient, "Studio_Laboratory_Background", left=0, top=0,
                    unicode_name="Studio Laboratory Background (#FFFFFF / #FBFBFB)")

    smear_scaled = im_smear_src.resize((1520, 1440), Image.Resampling.LANCZOS)
    smear_op = apply_opacity(smear_scaled, 0.12)
    smear_c, sm_x, sm_y = tight_crop_with_offset(smear_op, -160, -120)
    add_pixel_layer(grp_01, smear_c, "Hydrating_Smear_Texture", left=sm_x, top=sm_y,
                    unicode_name="Hydrating Smear Texture (03_smear_hydrating_wave.png)")

    bag_back_scaled = im_bag_back_src.resize((840, 840), Image.Resampling.LANCZOS)
    bb_c, bb_x, bb_y = tight_crop_with_offset(bag_back_scaled, 180, 240)
    add_pixel_layer(grp_01, bb_c, "Bag_Rear_and_Cavity", left=bb_x, top=bb_y,
                    unicode_name="Kraft Bag Rear Cavity & Handles (03_decor_bag_back.png)")

    # ==========================================================================
    # GROUP 2: 02_Midground_Products_and_Anchor
    # ==========================================================================
    grp_02 = psd.create_group(name="02_Midground_Products_and_Anchor", open_folder=True)
    kit_scaled = im_kit_src.resize((335, 468), Image.Resampling.LANCZOS)
    kit_c, kit_x, kit_y = tight_crop_with_offset(kit_scaled, 432.5, 335)
    add_pixel_layer(grp_02, kit_c, "Product_Anchor_Holiday_Kit", left=kit_x, top=kit_y,
                    unicode_name="Product Anchor Holiday Kit (04_product_holiday_kit.png)")

    pdrn_scaled = im_pdrn_src.resize((106, 410), Image.Resampling.LANCZOS)
    pdrn_rot, pdrn_dx, pdrn_dy = rotate_css(pdrn_scaled, -10.0, 0.5, 0.85)
    pdrn_c, pdrn_x, pdrn_y = tight_crop_with_offset(pdrn_rot, 336 + pdrn_dx, 360 + pdrn_dy)
    add_pixel_layer(grp_02, pdrn_c, "Product_PDRN_Serum", left=pdrn_x, top=pdrn_y,
                    unicode_name="Product PDRN Serum (07_product_pdrn_serum.png)")

    snail_scaled = im_snail_src.resize((175, 425), Image.Resampling.LANCZOS)
    snail_c, snail_x, snail_y = tight_crop_with_offset(snail_scaled, 442, 310)
    add_pixel_layer(grp_02, snail_c, "Product_Snail_Essence", left=snail_x, top=snail_y,
                    unicode_name="Product Snail Essence (05_product_snail_essence.png)")

    pep_scaled = im_peptide_src.resize((196, 410), Image.Resampling.LANCZOS)
    pep_c, pep_x, pep_y = tight_crop_with_offset(pep_scaled, 624, 326)
    add_pixel_layer(grp_02, pep_c, "Product_Peptide_Serum", left=pep_x, top=pep_y,
                    unicode_name="Product Peptide Serum (06_product_peptide_serum.png)")
    # ==========================================================================
    # GROUP 3: 03_Foreground_Products
    # ==========================================================================
    grp_03 = psd.create_group(name="03_Foreground_Products", open_folder=True)
    swatch_scaled = apply_opacity(im_swatch_src.resize((260, 390), Image.Resampling.LANCZOS), 0.95)
    sw_c, sw_x, sw_y = tight_crop_with_offset(swatch_scaled, 660, 485)
    add_pixel_layer(grp_03, sw_c, "Swatch_Snail_Cream", left=sw_x, top=sw_y,
                    unicode_name="Swatch Snail Cream (01_swatch_snail_cream.png)")

    cream_scaled = im_cream_src.resize((224, 275), Image.Resampling.LANCZOS)
    cream_rot, cr_dx, cr_dy = rotate_css(cream_scaled, 15.0, 0.5, 0.6)
    cr_c, cr_x, cr_y = tight_crop_with_offset(cream_rot, 712 + cr_dx, 472 + cr_dy)
    add_pixel_layer(grp_03, cr_c, "Product_Snail_Cream_Jar", left=cr_x, top=cr_y,
                    unicode_name="Product Snail Cream Jar (08_product_snail_cream_jar.png)")

    # ==========================================================================
    # GROUP 4: 04_Kraft_Bag_Front_Panel
    # ==========================================================================
    grp_04 = psd.create_group(name="04_Kraft_Bag_Front_Panel", open_folder=True)
    bag_front_scaled = im_bag_front_src.resize((840, 840), Image.Resampling.LANCZOS)
    bf_c, bf_x, bf_y = tight_crop_with_offset(bag_front_scaled, 180, 240)
    add_pixel_layer(grp_04, bf_c, "Bag_Front_Panel", left=bf_x, top=bf_y,
                    unicode_name="Kraft Bag Front Panel (09_decor_bag_front.png - 0.0px Seam)")

    # ==========================================================================
    # GROUP 5: 05_Atmosphere_Droplets
    # ==========================================================================
    grp_05 = psd.create_group(name="05_Atmosphere_Droplets", open_folder=True)
    dr_scaled = apply_opacity(im_droplets_src.resize((210, 135), Image.Resampling.LANCZOS), 0.85)
    dr_c, dr_x, dr_y = tight_crop_with_offset(dr_scaled, 410, 295)
    add_pixel_layer(grp_05, dr_c, "Cosmetic_Gel_Droplets", left=dr_x, top=dr_y,
                    unicode_name="Cosmetic Gel Droplets (02_droplets_aqueous_serum.png)")

    # ==========================================================================
    # GROUP 6: 06_UI_and_Typography (Top-most)
    # ==========================================================================
    grp_06 = psd.create_group(name="06_UI_and_Typography", open_folder=True)
    hdr_c, hdr_x, hdr_y = tight_crop_with_offset(im_header_src, 0, 36)
    add_pixel_layer(grp_06, hdr_c, "Header_Dual_Brand_Slot", left=hdr_x, top=hdr_y,
                    unicode_name="Header Dual Brand Slot (01_logo_dual_lockup.png)")

    if has_independent_typo:
        # Tier 2: Main Headline 'BLACK FRIDAY' @ top: 110px
        im_headline = load_rgba(path_10a)
        head_c, head_x, head_y = tight_crop_with_offset(im_headline, (CANVAS_W - 580) / 2.0, 110)
        add_pixel_layer(grp_06, head_c, "Main_Headline_Black_Friday", left=head_x, top=head_y,
                        unicode_name="Main Headline 'BLACK FRIDAY' (10a_headline_black_friday.png)")

        # Tier 3: Ribbon scaled to 500x88px @ top: 200px (ends at Y=288px)
        ribbon_scaled = im_ribbon_src.resize((500, 88), Image.Resampling.LANCZOS)
        rib_c, rib_x, rib_y = tight_crop_with_offset(ribbon_scaled, (CANVAS_W - 500) / 2.0, 200)
        add_pixel_layer(grp_06, rib_c, "Promo_Ribbon_Early_Access", left=rib_x, top=rib_y,
                        unicode_name="Promo Ribbon Early Access (02_ribbon_early_access.png)")

        # Tier 4: Discount message @ top: 305px (ends at Y=355px, buffer >=65px to Y=430px)
        im_discount = load_rgba(path_10b)
        disc_c, disc_x, disc_y = tight_crop_with_offset(im_discount, (CANVAS_W - 600) / 2.0, 305)
        add_pixel_layer(grp_06, disc_c, "Discount_Up_To_30_Off", left=disc_x, top=disc_y,
                        unicode_name="Discount Message 'UP TO 30% OFF' (10b_discount_up_to_30_off.png)")
    else:
        # Fallback to combined layer if standalone layers are absent
        rib_c, rib_x, rib_y = tight_crop_with_offset(im_ribbon_src, (CANVAS_W - 760) / 2.0, 218)
        add_pixel_layer(grp_06, rib_c, "Promo_Ribbon_Early_Access", left=rib_x, top=rib_y,
                        unicode_name="Promo Ribbon Early Access (02_ribbon_early_access.png)")

        im_typo_src = load_rgba(path_10_combined)
        typo_c, typo_x, typo_y = tight_crop_with_offset(im_typo_src, (CANVAS_W - 1060) / 2.0, 318)
        add_pixel_layer(grp_06, typo_c, "Typography_Headline_and_Discount", left=typo_x, top=typo_y,
                        unicode_name="Typography Headline & Discount (10_typography_headline_discount.png)")

    # Call To Action Dock (Active Pill bottom clearance = 45px, canvas top = 1043px)
    cta_c, cta_x, cta_y = tight_crop_with_offset(im_cta_src, (CANVAS_W - 448) / 2.0, 1043)
    add_pixel_layer(grp_06, cta_c, "UI_CTA_Dock", left=cta_x, top=cta_y,
                    unicode_name="UI CTA Dock (11_ui_cta_button.png - 45px Bottom Clearance)")

    # Embed sRGB ICC profile
    try:
        psd.image_resources[Resource.ICC_PROFILE] = ImageResource(
            resource_id=Resource.ICC_PROFILE,
            name="",
            data=SRGB_ICC,
        )
    except Exception as exc:
        print(f"[WARN] ICC profile injection skipped: {exc}")

    # Save PSD
    psd.save(out_psd)
    size_mb = out_psd.stat().st_size / (1024 * 1024)
    print(f"\n[OK] Exported Layered PSD: {out_psd} (1200x1200, RGB 8-bit, {size_mb:.2f} MB)")

    # Re-open and verify layer tree
    reloaded = PSDImage.open(out_psd)
    total_groups = sum(1 for layer in reloaded if layer.is_group())
    total_layers = len(list(reloaded.descendants()))
    print(f"[PSD] Verified: {total_groups} Groups | {total_layers} Descendants")
    for layer in reloaded:
        print(f"  ├── [FOLDER] {layer.name}")
        for sub in layer:
            print(f"  │    ├── {sub.name} ({sub.width}x{sub.height} @ left={sub.left}, top={sub.top})")

    return out_psd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="COSRX Layered Master PSD Builder")
    parser.add_argument("--output", default=str(DEFAULT_OUT_PSD), help="Output PSD path")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    build_cosrx_master_psd(Path(args.output))
