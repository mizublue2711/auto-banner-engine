#!/usr/bin/env python3
"""
Step 1: Sync, rename, clean, and assert the Ground Truth Manifest for
`assets/brands/COSRX/layers/`.

Preserves all 8 Cụm 5 UI/Typography assets (verified against
`output/TASK_COSRX/sub_ui_typography_dock.json` and `templates/sub_cosrx_ui_dock.html`)
alongside all 15 canonical Stage/Background/Product/Texture assets (23 PNGs total),
and removes redundant intermediate/metadata files.
"""

from __future__ import annotations

import os
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
LAYERS_DIR = REPO_ROOT / "assets" / "brands" / "COSRX" / "layers"

RENAMES: list[tuple[str, str]] = [
    ("08_product_snail_cream_jar.png", "07_product_snail_cream.png"),
    ("07_product_pdrn_serum.png", "08_product_pdrn_pack.png"),
    ("07b_accessory_brush_applicator.png", "08b_accessory_brush_applicator.png"),
    ("00c_back_cosrx_molecular_crystals.png", "00c_molecular_crystals_back.png"),
    ("00c_front_cosrx_molecular_crystals.png", "00c_molecular_crystals_front.png"),
]

GROUND_TRUTH_CLUSTERS: dict[str, list[str]] = {
    "CUM_1_BACKGROUND_AND_SHELF": [
        "00_bg_vanity_morning_light.png",
        "00b_pedestal_wood_shelf.png",
    ],
    "CUM_2_BAG_3D_FRAME": [
        "03_decor_bag_back.png",
        "09_decor_bag_front.png",
    ],
    "CUM_3_HERO_PRODUCTS_AND_ACCESSORY": [
        "04_product_holiday_kit.png",
        "05_product_snail_essence.png",
        "06_product_peptide_serum.png",
        "07_product_snail_cream.png",
        "08_product_pdrn_pack.png",
        "08b_accessory_brush_applicator.png",
    ],
    "CUM_4_TEXTURES_AND_EFFECTS": [
        "01_swatch_snail_cream.png",
        "02_droplets_aqueous_serum.png",
        "07b_swatch_pdrn_serum.png",
        "00c_molecular_crystals_back.png",
        "00c_molecular_crystals_front.png",
    ],
    "CUM_5_TYPOGRAPHY_AND_UI": [
        "01a_logo_cosrx.png",
        "01b_logo_ulta.png",
        "01_logo_dual_lockup.png",
        "02_ribbon_early_access.png",
        "10a_headline_black_friday.png",
        "10b_discount_up_to_30_off.png",
        "10_typography_headline_discount.png",
        "11_ui_cta_button.png",
    ],
}

ALL_GROUND_TRUTH_FILES: list[str] = [
    fname for files in GROUND_TRUTH_CLUSTERS.values() for fname in files
]


def sync_and_verify() -> None:
    assert LAYERS_DIR.is_dir(), f"Layers directory missing: {LAYERS_DIR}"

    # 1. Perform canonical renames (idempotent)
    renamed_log: list[str] = []
    for old_name, new_name in RENAMES:
        src = LAYERS_DIR / old_name
        dst = LAYERS_DIR / new_name
        if src.exists() and not dst.exists():
            src.rename(dst)
            renamed_log.append(f"{old_name} -> {new_name}")
        elif src.exists() and dst.exists():
            raise RuntimeError(
                f"Conflict: both {old_name} and {new_name} exist in {LAYERS_DIR}"
            )

    if renamed_log:
        print("[SYNC] Renamed canonical files:")
        for line in renamed_log:
            print(f"  - {line}")
    else:
        print("[SYNC] All canonical filenames already in place.")

    # 2. Remove any files not in the Ground Truth Manifest (intermediate / junk)
    allowed = set(ALL_GROUND_TRUTH_FILES)
    removed_log: list[str] = []
    for entry in sorted(LAYERS_DIR.iterdir()):
        if entry.name not in allowed:
            if entry.is_file():
                entry.unlink()
                removed_log.append(entry.name)

    if removed_log:
        print("[CLEAN] Removed unapproved/intermediate files:")
        for name in removed_log:
            print(f"  - {name}")
    else:
        print("[CLEAN] No extra/junk files found.")

    # 3. Strict Ground Truth Assertions
    for cluster, files in GROUND_TRUTH_CLUSTERS.items():
        print(f"\n[{cluster}] ({len(files)} files)")
        for fname in files:
            fpath = LAYERS_DIR / fname
            assert os.path.exists(fpath), f"MISSING Ground Truth layer: {fpath}"
            with Image.open(fpath) as im:
                assert im.mode == "RGBA", f"Expected RGBA for {fname}, got {im.mode}"
                w, h = im.size
                print(f"  OK  {fname:38s} {w:4d}x{h:4d} {im.mode}")

    actual_files = sorted(p.name for p in LAYERS_DIR.iterdir())
    expected_files = sorted(ALL_GROUND_TRUTH_FILES)
    assert actual_files == expected_files, (
        f"Directory mismatch!\nExtra: {set(actual_files) - set(expected_files)}\n"
        f"Missing: {set(expected_files) - set(actual_files)}"
    )

    print(
        f"\n[PASS] Ground Truth Manifest verified: {len(actual_files)} clean RGBA layers "
        f"(15 Stage/BG + 8 UI/Typography), 0 junk files."
    )


if __name__ == "__main__":
    sync_and_verify()
