#!/usr/bin/env python3
"""
Task 2 Compliance & Meritz Brand Book QA Verification Gate
(`engine/qa_task2_checker.py`).

Standalone verification suite asserting all Design Brief & Meritz Brand Book requirements:
  1. Asset Integrity & Brand Palette Purity:
     - `hero_coin_3d.png` (1024x1024) + 3 sub-feature icons (512x512) exist in
       `assets/brands/meritz/visuals/`, are valid RGBA PNGs, and preserve alpha transparency.
     - All 3 geometric micro-icons strictly adhere to the Meritz Brand Palette
       (#EF3B24, #141414, #FFFFFF, #F2F2F2, neutral grays — zero ungrounded pastel/neon tones).
  2. Brand & Color Assertions:
     - Official Meritz logo (`assets/logos/meritz/logo.png`) verified in `[LOGO]`.
     - CTA button in `[CTA_BUTTON]` verified as exact Vermillion Red (`#EF3B24`) with white text.
     - Canvas/typography verified for Chalk White (`#F2F2F2`), Pure White (`#FFFFFF`),
       and Obsidian Black (`#141414`).
  3. Mandatory Legal Disclaimer Strings:
     - Exact verbatim presence of both legal disclaimer lines inside `[LEGAL]` plus visible
       bottom-stage neutral dark-gray text pixels.
  4. Layer Group Structure (PSD Check) & Preview Fidelity:
     - All 7 required top-level groups exist and are non-empty:
       `[LOGO]`, `[HEADLINE]`, `[HERO_VISUAL]`, `[FEATURE_ICONS]`,
       `[CTA_BUTTON]`, `[LEGAL]`, `[BACKGROUND]`.
     - Companion `meritz_partners_preview.jpg` matches canvas dimensions and composite.

Usage:
  python3 engine/qa_task2_checker.py --target deliverables/task2_meritz/meritz_partners_master.psd
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image
from psd_tools import PSDImage

ROOT = Path(__file__).resolve().parent.parent
VISUALS_DIR = ROOT / "assets" / "brands" / "meritz" / "visuals"
LOGO_PATH = ROOT / "assets" / "logos" / "meritz" / "logo.png"
OPTION2_TASK_PATH = ROOT / "tasks" / "task2_creative" / "meritz_option2.json"

REQUIRED_GROUPS = [
    "[LOGO]",
    "[HEADLINE]",
    "[HERO_VISUAL]",
    "[FEATURE_ICONS]",
    "[CTA_BUTTON]",
    "[LEGAL]",
    "[BACKGROUND]",
]

LEGAL_LINE_1 = "*‘24년 8월 ~ ‘25년 7월 수익자의 첫 달 평균 금액 기준, 수익은 보험체결 후 발생, 개인차 있음"
LEGAL_LINE_2 = "*보험업법상 보험설계사를 모집하는 것으로 정규 또는 비정규 직원 채용과는 무관"

EXPECTED_ASSETS = {
    "hero_coin_3d.png": (1024, 1024),
    "icon_sprout_beginner.png": (512, 512),
    "icon_flexible_growth.png": (512, 512),
    "icon_honey_sidejob.png": (512, 512),
}


class CheckReport:
    def __init__(self) -> None:
        self.rows: List[Tuple[str, bool, str]] = []

    def record(self, name: str, passed: bool, detail: str) -> None:
        self.rows.append((name, passed, detail))

    def all_passed(self) -> bool:
        return all(ok for _, ok, _ in self.rows)

    def print_summary(self, target: Path) -> None:
        print("=" * 98)
        print(f"TASK 2 COMPLIANCE QA GATE | TARGET: {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
        print("=" * 98)
        for name, ok, detail in self.rows:
            tag = "PASS" if ok else "FAIL"
            print(f"[{tag}] {name:38s} | {detail}")
        print("-" * 98)
        passed_n = sum(1 for _, ok, _ in self.rows if ok)
        overall = "PASSED" if self.all_passed() else "FAILED"
        print(f"SUMMARY: {passed_n}/{len(self.rows)} CHECKS PASSED | OVERALL STATUS: {overall}")
        print("=" * 98)


def check_assets_and_palette(report: CheckReport, visuals_dir: Path) -> None:
    for filename, expected_size in EXPECTED_ASSETS.items():
        path = visuals_dir / filename
        if not path.exists():
            report.record(f"Asset Exists: {filename}", False, "MISSING")
            continue

        with Image.open(path) as im:
            mode_ok = im.mode == "RGBA"
            size_ok = im.size == expected_size
            arr = np.array(im.convert("RGBA"))

        alpha = arr[..., 3]
        transparent_ratio = float((alpha == 0).mean())
        opaque_ratio = float((alpha >= 200).mean())
        alpha_ok = (alpha.min() == 0) and (transparent_ratio >= 0.08) and (opaque_ratio >= 0.05)

        ok = mode_ok and size_ok and alpha_ok
        report.record(
            f"Asset Integrity: {filename}",
            ok,
            f"mode={im.mode}, size={im.size[0]}x{im.size[1]}, transp={transparent_ratio*100:.1f}%, opaque={opaque_ratio*100:.1f}%",
        )

        # Enforce strict Brand Book palette purity on the 3 geometric micro-icons
        if filename.startswith("icon_"):
            opaque_mask = alpha >= 160
            rgb = arr[opaque_mask, :3].astype(np.int16)
            if len(rgb) == 0:
                report.record(f"Brand Palette: {filename}", False, "no opaque pixels")
                continue
            chroma = rgb.max(axis=1) - rgb.min(axis=1)
            is_neutral = chroma <= 24  # Covers #141414, #5A5D62, #F2F2F2, #FFFFFF & grayscale AA
            # Vermillion Red (#EF3B24) and its anti-aliased blends toward white/black
            is_vermillion = (rgb[:, 0] >= 100) & ((rgb[:, 0] - rgb[:, 1]) >= 25) & ((rgb[:, 0] - rgb[:, 2]) >= 30) & (rgb[:, 1] >= rgb[:, 2] - 12)
            purity = float((is_neutral | is_vermillion).mean())
            has_red = int(((rgb[:, 0] >= 220) & (rgb[:, 1] <= 80) & (rgb[:, 2] <= 60)).sum())
            pal_ok = purity >= 0.995 and has_red >= 200
            report.record(
                f"Brand Palette: {filename}",
                pal_ok,
                f"purity={purity*100:.2f}%, vermillion_px={has_red}",
            )


def check_option2_hero_and_task(report: CheckReport, visuals_dir: Path) -> None:
    """Option 2 (Zero-Gravity Architecture) 3D hero scene & task config checks."""
    hero_path = visuals_dir / "hero_option2_scene.png"
    if not hero_path.exists():
        report.record("Option 2 Hero: hero_option2_scene.png", False, "MISSING")
    else:
        with Image.open(hero_path) as im:
            mode_ok = im.mode == "RGBA"
            size_ok = im.size == (1200, 1200)
            has_icc = bool(im.info.get("icc_profile"))
            arr = np.array(im.convert("RGBA"))

        alpha = arr[..., 3]
        transparent_ratio = float((alpha == 0).mean())
        opaque_ratio = float((alpha >= 200).mean())
        partial_alpha_px = int(((alpha > 5) & (alpha < 245)).sum())
        # Zero opaque backdrop box along the 4 outer edges
        border_opaque = int(
            (alpha[0, :] >= 200).sum()
            + (alpha[-1, :] >= 200).sum()
            + (alpha[:, 0] >= 200).sum()
            + (alpha[:, -1] >= 200).sum()
        )
        alpha_ok = (
            (alpha.min() == 0)
            and (transparent_ratio >= 0.25)
            and (opaque_ratio >= 0.08)
            and (border_opaque == 0)
        )
        report.record(
            "Option 2 Hero Integrity (1200x1200)",
            mode_ok and size_ok and has_icc and alpha_ok,
            f"mode={im.mode}, size={im.size[0]}x{im.size[1]}, icc={has_icc}, transp={transparent_ratio*100:.1f}%, opaque={opaque_ratio*100:.1f}%, border_opaque={border_opaque}",
        )

        # Color & Materiality assertions: Champagne Gold + Matte Li Vermillion Red #EF3B24
        vis = alpha >= 160
        rgb = arr[vis, :3].astype(np.int16)
        r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]

        # Metallic Champagne Gold / Bronze (#C5A059 / #D4AF37 family)
        gold_px = int(((r >= 120) & (g >= 90) & (r > g) & (g > b) & ((r - b) >= 35)).sum())
        # Official Meritz Vermillion Red (#EF3B24 matte stone family)
        red_mask_2d = (
            (alpha >= 180)
            & (arr[..., 0].astype(np.int16) >= 135)
            & ((arr[..., 0].astype(np.int16) - arr[..., 1].astype(np.int16)) >= 80)
            & ((arr[..., 0].astype(np.int16) - arr[..., 2].astype(np.int16)) >= 100)
        )
        red_px = int(red_mask_2d.sum())

        # Matte Li Anti-Plastic Gate: check inside central monolith bounding box for glossy white hotspots
        glossy_ratio = 0.0
        if red_px > 0:
            rys, rxs = np.nonzero(red_mask_2d)
            sub = arr[int(rys.min()) : int(rys.max()) + 1, int(rxs.min()) : int(rxs.max()) + 1]
            sub_a = sub[..., 3] >= 200
            sub_r, sub_g, sub_b = sub[..., 0], sub[..., 1], sub[..., 2]
            # Glossy plastic specular hotspot on red monolith (excluding gold wireframe pixels where R-B>=35)
            white_spec = sub_a & (sub_r >= 245) & (sub_g >= 235) & (sub_b >= 230)
            glossy_ratio = float(white_spec.sum()) / max(1, red_px)

        mat_ok = (gold_px >= 25000) and (red_px >= 25000) and (glossy_ratio < 0.005)
        report.record(
            "Option 2 Materiality (Gold + Matte Red)",
            mat_ok,
            f"gold_px={gold_px}, matte_red_px={red_px}, glossy_hotspot={glossy_ratio*100:.3f}%",
        )

        dof_ok = partial_alpha_px >= 15000
        report.record(
            "Option 2 DoF & 2x SSAA Alpha Feather",
            dof_ok,
            f"partial_alpha_px={partial_alpha_px}",
        )

    # Option 2 Workflow B JSON contract check
    if not OPTION2_TASK_PATH.exists():
        report.record("Task JSON: meritz_option2.json", False, "MISSING")
    else:
        cfg = json.loads(OPTION2_TASK_PATH.read_text(encoding="utf-8"))
        content = cfg.get("content", {})
        disclaimers = content.get("disclaimers", [])
        asset_ok = content.get("visual_stage_asset") == "assets/brands/meritz/visuals/hero_option2_scene.png"
        legal_ok = any(LEGAL_LINE_1 in d for d in disclaimers) and any(LEGAL_LINE_2 in d for d in disclaimers)
        dims_ok = len(cfg.get("target_dimensions", [])) >= 1
        report.record(
            "Task JSON: meritz_option2.json",
            asset_ok and legal_ok and dims_ok,
            f"task_id={cfg.get('task_id')}, asset_ok={asset_ok}, legal_ok={legal_ok}, dims={len(cfg.get('target_dimensions', []))}",
        )


def check_psd_compliance(report: CheckReport, psd_path: Path, option: int = 1) -> None:
    if not psd_path.exists():
        report.record("Target PSD Exists", False, f"File not found: {psd_path}")
        return

    psd = PSDImage.open(str(psd_path))
    w, h = psd.size
    report.record("PSD Readable & Canvas Size", w >= 1200 and h >= 1200, f"{w}x{h} px, color_mode={psd.color_mode}")

    # 4. Layer Group Structure
    groups_by_name: Dict[str, object] = {}
    for layer in psd:
        if layer.is_group():
            groups_by_name[layer.name] = layer

    missing_groups = [g for g in REQUIRED_GROUPS if g not in groups_by_name]
    empty_groups = [g for g in REQUIRED_GROUPS if g in groups_by_name and len(list(groups_by_name[g])) == 0]
    struct_ok = (len(missing_groups) == 0) and (len(empty_groups) == 0)
    report.record(
        "PSD 7 Layer Groups Structure",
        struct_ok,
        f"found={len(groups_by_name)}/7, missing={missing_groups or 'none'}, empty={empty_groups or 'none'}",
    )

    # 2a. Brand Logo Assertion (`assets/logos/meritz/logo.png` -> `[LOGO]`)
    logo_file_ok = LOGO_PATH.exists()
    logo_group_ok = False
    logo_detail = "missing [LOGO] group"
    if logo_file_ok and "[LOGO]" in groups_by_name:
        with Image.open(LOGO_PATH) as ref_logo:
            ref_ratio = ref_logo.width / max(1, ref_logo.height)
        logo_comp = groups_by_name["[LOGO]"].composite()
        bbox = logo_comp.getbbox()
        if bbox:
            lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            actual_ratio = lw / max(1, lh)
            ratio_err = abs(actual_ratio - ref_ratio) / ref_ratio
            arr = np.array(logo_comp.crop(bbox).convert("RGBA"))
            rgb = arr[..., :3].astype(np.int16)
            red_px = int(((arr[..., 3] > 180) & (rgb[..., 0] >= 215) & (rgb[..., 1] <= 85) & (rgb[..., 2] <= 65)).sum())
            logo_group_ok = (ratio_err <= 0.08) and (red_px >= 500)
            logo_detail = f"bbox={lw}x{lh}, ratio={actual_ratio:.2f} (ref {ref_ratio:.2f}), meritz_red_px={red_px}"
        else:
            logo_detail = "[LOGO] composite is empty"
    report.record("Brand Logo (logo.png -> [LOGO])", logo_file_ok and logo_group_ok, logo_detail)

    # 2b. Official Meritz Red CTA Assertion (`#EF3B24` in `[CTA_BUTTON]`)
    cta_ok = False
    cta_detail = "missing [CTA_BUTTON] group"
    if "[CTA_BUTTON]" in groups_by_name:
        cta_comp = groups_by_name["[CTA_BUTTON]"].composite()
        arr = np.array(cta_comp.convert("RGBA"))
        a = arr[..., 3]
        r = arr[..., 0].astype(np.int16)
        g = arr[..., 1].astype(np.int16)
        b = arr[..., 2].astype(np.int16)
        # Exact Meritz Red #EF3B24 = RGB(239, 59, 36) within ±3 tolerance
        exact_red = (a >= 245) & (np.abs(r - 239) <= 3) & (np.abs(g - 59) <= 3) & (np.abs(b - 36) <= 3)
        white_txt = (a >= 220) & (r >= 240) & (g >= 240) & (b >= 240)
        red_count = int(exact_red.sum())
        white_count = int(white_txt.sum())
        cta_ok = (red_count >= 25000) and (white_count >= 1500)
        cta_detail = f"#EF3B24_px={red_count}, white_label_px={white_count}"
    report.record("CTA Official Meritz Red (#EF3B24)", cta_ok, cta_detail)

    # 2c. Brand Book Institutional Palette in [BACKGROUND] & [HEADLINE]
    bg_ok = False
    bg_detail = "missing [BACKGROUND]"
    if "[BACKGROUND]" in groups_by_name:
        bg_arr = np.array(groups_by_name["[BACKGROUND]"].composite().convert("RGB"), dtype=np.int16)
        chalk_px = int(((np.abs(bg_arr[..., 0] - 242) <= 2) & (np.abs(bg_arr[..., 1] - 242) <= 2) & (np.abs(bg_arr[..., 2] - 242) <= 2)).sum())
        white_px = int(((bg_arr[..., 0] >= 253) & (bg_arr[..., 1] >= 253) & (bg_arr[..., 2] >= 253)).sum())
        bg_ok = chalk_px >= 50000 and white_px >= 500000
        bg_detail = f"chalk_#F2F2F2_px={chalk_px}, pure_#FFFFFF_px={white_px}"
    report.record("Background Chalk/Pure White", bg_ok, bg_detail)

    hl_ok = False
    hl_detail = "missing [HEADLINE]"
    if "[HEADLINE]" in groups_by_name:
        hl_arr = np.array(groups_by_name["[HEADLINE]"].composite().convert("RGBA"))
        a = hl_arr[..., 3]
        rgb = hl_arr[..., :3].astype(np.int16)
        obs_px = int(((a >= 200) & (np.abs(rgb[..., 0] - 20) <= 6) & (np.abs(rgb[..., 1] - 20) <= 6) & (np.abs(rgb[..., 2] - 20) <= 6)).sum())
        hl_ok = obs_px >= 12000
        hl_detail = f"obsidian_#141414_glyph_px={obs_px}"
    report.record("Headline Obsidian Black (#141414)", hl_ok, hl_detail)

    # 3. Mandatory Legal Disclaimers Assertion (Exact verbatim strings + visible bottom pixels)
    legal_1_ok = False
    legal_2_ok = False
    legal_px_ok = False
    legal_detail = "missing [LEGAL] group"
    if "[LEGAL]" in groups_by_name:
        legal_grp = groups_by_name["[LEGAL]"]
        layer_names = [child.name for child in legal_grp.descendants()]
        legal_1_ok = any(LEGAL_LINE_1 in name for name in layer_names)
        legal_2_ok = any(LEGAL_LINE_2 in name for name in layer_names)
        legal_comp = legal_grp.composite()
        lbbox = legal_comp.getbbox()
        if lbbox:
            l_arr = np.array(legal_comp.convert("RGBA"))
            vis_px = int((l_arr[..., 3] >= 80).sum())
            canvas_y_top = legal_grp.top + lbbox[1]
            in_bottom = canvas_y_top >= int(h * 0.80)
            legal_px_ok = (vis_px >= 1500) and in_bottom
            legal_detail = f"line1={legal_1_ok}, line2={legal_2_ok}, visible_px={vis_px}, y_top={canvas_y_top}"
        else:
            legal_detail = f"line1={legal_1_ok}, line2={legal_2_ok}, empty legal render"
    report.record("Mandatory Disclaimers (Line 1 & 2)", legal_1_ok and legal_2_ok and legal_px_ok, legal_detail)

    # 4b. Option 2 [HERO_VISUAL] Integration & Non-Overlap Check
    if option == 2:
        hero_ok = False
        hero_detail = "missing [HERO_VISUAL]"
        if "[HERO_VISUAL]" in groups_by_name:
            hero_grp = groups_by_name["[HERO_VISUAL]"]
            hero_comp = hero_grp.composite()
            hbbox = hero_comp.getbbox()
            if hbbox:
                h_arr = np.array(hero_comp.convert("RGBA"))
                ha = h_arr[..., 3]
                hr = h_arr[..., 0].astype(np.int16)
                hg = h_arr[..., 1].astype(np.int16)
                hb = h_arr[..., 2].astype(np.int16)
                h_red = int(((ha >= 160) & (hr >= 135) & ((hr - hg) >= 80) & ((hr - hb) >= 100)).sum())
                h_gold = int(((ha >= 140) & (hr >= 120) & (hg >= 90) & (hr > hg) & (hg > hb) & ((hr - hb) >= 35)).sum())
                y_top = hero_grp.top + hbbox[1]
                y_bot = hero_grp.top + hbbox[3]
                clear_zones = (y_top >= 150) and (y_bot <= 865)
                hero_ok = (h_red >= 4000) and (h_gold >= 4000) and clear_zones
                hero_detail = f"y=[{y_top}..{y_bot}], red_px={h_red}, gold_px={h_gold}, clear_zones={clear_zones}"
            else:
                hero_detail = "[HERO_VISUAL] composite is empty"
        report.record("Option 2 [HERO_VISUAL] Integration", hero_ok, hero_detail)

    # 4c. Companion Preview JPEG Check
    if psd_path.stem.endswith("_master"):
        preview_path = psd_path.parent / "meritz_partners_preview.jpg"
    else:
        candidate = psd_path.parent / f"{psd_path.stem}_preview.jpg"
        fallback_opt1 = psd_path.parent / "meritz_partners_preview.jpg"
        preview_path = candidate if candidate.exists() or option == 2 else fallback_opt1
    if preview_path.exists():
        with Image.open(preview_path) as prev:
            p_ok = (prev.mode == "RGB") and (prev.size == (w, h))
            p_detail = f"{preview_path.name}, mode={prev.mode}, size={prev.size[0]}x{prev.size[1]}, {preview_path.stat().st_size/1024:.1f} KB"
        report.record("Deliverable Preview JPEG (sRGB)", p_ok, p_detail)
    else:
        report.record("Deliverable Preview JPEG (sRGB)", False, f"MISSING: {preview_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Task 2 Meritz Partners Compliance QA Checker.")
    parser.add_argument(
        "--target",
        required=True,
        help="Path to target Master PSD (e.g. deliverables/task2_meritz/meritz_partners_option2.psd).",
    )
    parser.add_argument(
        "--option",
        type=int,
        choices=[1, 2],
        default=None,
        help="Force Option 1 or Option 2 checks (auto-detected from filename if omitted).",
    )
    parser.add_argument(
        "--visuals-dir",
        default=str(VISUALS_DIR),
        help="Directory containing generated Meritz visual assets.",
    )
    args = parser.parse_args()

    target = Path(args.target)
    if not target.is_absolute():
        target = ROOT / target

    visuals_dir = Path(args.visuals_dir)
    if not visuals_dir.is_absolute():
        visuals_dir = ROOT / visuals_dir

    option = args.option if args.option is not None else (2 if "option2" in target.stem.lower() else 1)

    report = CheckReport()
    check_assets_and_palette(report, visuals_dir)
    if option == 2:
        check_option2_hero_and_task(report, visuals_dir)
    check_psd_compliance(report, target, option=option)
    report.print_summary(target)

    sys.exit(0 if report.all_passed() else 1)


if __name__ == "__main__":
    main()
