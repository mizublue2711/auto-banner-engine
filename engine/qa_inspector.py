#!/usr/bin/env python3
"""
Automated QA CLI Oracle (`engine/qa_inspector.py`)
==================================================
Standalone Automated QA Gatekeeper encapsulating PBR, optical, alpha-matting,
layout, safe-zone, and PSD-fidelity acceptance standards for `auto-banner-engine`.

Modules:
  1. ALPHA_AND_BORDER_GATEKEEPER
     - Defringe / White notch & Dark halo detection on transparent cutouts & PSD layers
     - Corner purity (4 canvas corners 100% pure gradient / zero stray or clipped shadow pixels)
  2. LAYOUT_AND_SAFE_ZONE_INSPECTOR
     - Safe-zone boundary compliance (40px standard margin, format-adaptive for MREC 300x250)
     - Alignment verification (800x1500, 1200x600, 300x250, 1080x1080, 1200x1200)
     - CTA text optical fill ratio (68.0% - 82.0%)
  3. FIDELITY_AND_PBR_INSPECTOR
     - SSIM / Pixel-diff between rendered PNG and PSD Master (SSIM >= 0.995)
     - PSD hierarchy & unmerged PBR layer verification (3D headline REV2, 3-tier PBR snow, etc.)
  4. CLI_INTERFACE
     - Supports `--target <dir> --brand <gsshop|cosrx|auto>`
     - Supports `--file <path>`
     - Preserves legacy `--workflow A --task <manifest.json>`
     - Exit code 0 (ALL_CHECKS_PASSED) or 1 (DEFECTS_DETECTED)
     - Markdown summary table: File Name | Check Item | Measured Value | Threshold | Status

Usage:
  python3 engine/qa_inspector.py --target output/TASK_GSSHOP/ --brand gsshop
  python3 engine/qa_inspector.py --target output/TASK_COSRX/ --brand cosrx
  python3 engine/qa_inspector.py --file output/TASK_GSSHOP/gsshop_800x1500.png
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image
from scipy.ndimage import (
    binary_dilation,
    binary_erosion,
    distance_transform_edt,
    gaussian_filter,
    maximum_filter,
    minimum_filter,
)

try:
    from psd_tools import PSDImage
except ImportError:
    PSDImage = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Brand & Format Specifications
# ---------------------------------------------------------------------------

SAFE_ZONE_UI_ROLES = {
    "logo",
    "header_dual_brand_slot",
    "glass_capsule",
    "badge",
    "sub_copy",
    "headline",
    "headline_black_friday",
    "promo_ribbon_early_access",
    "ribbon",
    "discount",
    "discount_up_to_30_off",
    "cta",
    "cta_button",
    "ui_cta_dock",
}

# Standard format alignment & safe-zone specifications
FORMAT_SPECS: Dict[str, Dict[str, Any]] = {
    "1080x1080": {
        "alignment_mode": "CENTER_SQUARE",
        "safe_margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
        "center_roles": ["glass_capsule", "headline", "cta"],
        "center_tol_px": 2.0,
    },
    "1200x1200": {
        "alignment_mode": "CENTER_SQUARE_DUAL_LOGO",
        "safe_margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
        "center_roles": ["headline", "ribbon", "discount", "cta"],
        "center_tol_px": 2.0,
    },
    "800x1500": {
        "alignment_mode": "CENTER_VERTICAL",
        "safe_margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
        "center_roles": ["logo", "glass_capsule", "headline", "cta"],
        "center_tol_px": 2.0,
    },
    "1200x600": {
        "alignment_mode": "SPLIT_LEFT",
        "safe_margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
        "flush_left_roles": ["logo", "glass_capsule", "headline", "cta"],
        "flush_left_anchor_x": 50.0,
        "flush_left_tol_px": 2.0,
        "left_col_max_right": 540.0,
    },
    "300x250": {
        "alignment_mode": "CENTER_MREC",
        "safe_margins": {"top": 10, "bottom": 10, "left": 12, "right": 12},
        "center_roles": ["glass_capsule", "headline", "cta"],
        "center_tol_px": 3.0,
    },
}

# Brand PSD hierarchy & unmerged PBR layer contracts
BRAND_PSD_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "gsshop": {
        "required_groups": [
            "01_Backdrop",
            "02_GiftBox_and_Tucked_Items",
            "03_Floating_Heroes_and_Decor",
            "04_Atmosphere_Particles",
            "05_UI_Lockup",
        ],
        "required_unmerged_patterns": [
            ("Snow Tier 1 Back (PBR)", r"snow_tier_1"),
            ("Snow Tier 2 Box Bed (PBR)", r"snow_tier_2"),
            ("Snow Tier 3 Front (PBR)", r"snow_tier_3"),
            ("3D Headline", r"headline_3d"),
            ("CTA Pill Background", r"cta_pill_background"),
            ("CTA Label Text", r"cta_label_text"),
        ],
        "cutout_layer_patterns": [
            r"burst_knit_sweater",
            r"burst_puffer_jacket",
            r"shopping_bag_pink",
            r"box_front_rim",
            r"decor_flying_lid",
            r"tucked_tangerine",
            r"decor_bauble(?!_sparkles)",
            r"decor_candy_cane",
        ],
    },
    "cosrx": {
        "required_groups": [
            "01_Backdrop_and_Pedestal",
            "02_Sub_Assembly_A_Stage_Burst",
            "03_Sub_Assembly_B_UI_Dock_and_Typography",
        ],
        "required_unmerged_patterns": [
            ("3D Headline REV2", r"10a_headline_3d_liquid_metal$"),
            ("3D Headline Shadow", r"10a_headline_3d_liquid_metal_shadow"),
            ("Backdrop Morning Light", r"00_bg_vanity_morning_light"),
            ("Pedestal Wood Shelf", r"00b_pedestal_wood_shelf"),
            ("UI CTA Button", r"11_ui_cta_button"),
        ],
        "cutout_layer_patterns": [
            r"10a_headline_3d_liquid_metal$",
            r"sub_stage_burst_bag",
            r"02_ribbon_early_access",
            r"11_ui_cta_button",
        ],
    },
}

CTA_FILL_MIN_PCT = 68.0
CTA_FILL_MAX_PCT = 82.0
SSIM_THRESHOLD = 0.995
CORNER_PURITY_THRESHOLD_PCT = 100.0
WHITE_NOTCH_MAX_PCT = 3.0


@dataclass
class CheckResult:
    file_name: str
    check_item: str
    measured_value: str
    threshold: str
    passed: bool
    detail: str = ""
    module: str = ""


# ---------------------------------------------------------------------------
# Helpers: Path, Brand & Companion Discovery
# ---------------------------------------------------------------------------

def _infer_brand(path: Path, explicit_brand: Optional[str]) -> str:
    if explicit_brand and explicit_brand.lower() != "auto":
        return explicit_brand.lower()
    s = str(path).lower()
    if "gsshop" in s:
        return "gsshop"
    if "cosrx" in s:
        return "cosrx"
    return "generic"


def _is_preview_or_debug_file(path: Path) -> bool:
    name = path.name.lower()
    return (
        name.startswith("preview_")
        or name.startswith("snow_3tier_preview")
        or name.startswith(".")
        or "_audit" in name
    )


def _find_companion_json(png_path: Path) -> Optional[Path]:
    stem = png_path.stem
    candidates = [
        png_path.with_suffix(".json"),
        png_path.parent / "variations" / f"{stem}.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _find_companion_psd(png_path: Path) -> Optional[Path]:
    stem = png_path.stem
    candidates = [
        png_path.with_suffix(".psd"),
        png_path.parent / "variations" / "psd" / f"{stem}.psd",
        png_path.parent / "psd" / f"{stem}.psd",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _is_transparent_cutout(img: Image.Image) -> bool:
    if img.mode not in ("RGBA", "LA", "PA"):
        return False
    alpha = np.array(img.convert("RGBA"))[:, :, 3]
    transparent_ratio = float(np.mean(alpha < 10))
    return transparent_ratio >= 0.05


def _bbox_from_any(raw: Any) -> Optional[Dict[str, float]]:
    if isinstance(raw, dict):
        if all(k in raw for k in ("x", "y", "width", "height")):
            return {
                "x": float(raw["x"]),
                "y": float(raw["y"]),
                "width": float(raw["width"]),
                "height": float(raw["height"]),
            }
    elif isinstance(raw, (list, tuple)) and len(raw) == 4:
        x1, y1, x2, y2 = [float(v) for v in raw]
        return {"x": x1, "y": y1, "width": max(0.0, x2 - x1), "height": max(0.0, y2 - y1)}
    return None


def _extract_ui_elements_from_manifest(
    manifest: Dict[str, Any],
    canvas_w: int,
    canvas_h: int,
    base_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Normalize UI element bboxes from either GSSHOP (`elements`) or COSRX (`layout_bboxes`) schema."""
    out: List[Dict[str, Any]] = []

    if isinstance(manifest.get("elements"), list):
        for elem in manifest["elements"]:
            if not isinstance(elem, dict):
                continue
            b = _bbox_from_any(elem.get("bbox"))
            if not b or b["width"] <= 0 or b["height"] <= 0:
                continue
            role = str(elem.get("role", elem.get("id", ""))).lower()
            has_text = bool(str(elem.get("text", "")).strip())
            if role in SAFE_ZONE_UI_ROLES or has_text:
                out.append({
                    "id": str(elem.get("id") or role),
                    "role": role,
                    "bbox": b,
                    "text": str(elem.get("text", "")),
                    "text_bbox": _bbox_from_any(elem.get("text_bbox") or elem.get("cta_text_bbox")),
                })
        return out

    if isinstance(manifest.get("layout_bboxes"), dict):
        lb = manifest["layout_bboxes"]
        dual = lb.get("dual_logos", {})
        if isinstance(dual, dict):
            for k in ("cosrx_bbox", "ulta_bbox"):
                b = _bbox_from_any(dual.get(k))
                if b:
                    out.append({"id": k.replace("_bbox", "_logo"), "role": "logo", "bbox": b})
        for key, role in (
            ("headline_3d_rev2", "headline"),
            ("ribbon", "ribbon"),
            ("discount", "discount"),
            ("cta_button", "cta"),
        ):
            entry = lb.get(key)
            if isinstance(entry, dict):
                b = _bbox_from_any(entry.get("bbox"))
                if b:
                    # For COSRX CTA button, prefer active opaque pill ink bounds over drop-shadow container
                    if role == "cta" and base_dir is not None:
                        dock_json = base_dir / "sub_ui_typography_dock.json"
                        if dock_json.exists():
                            try:
                                dock = json.loads(dock_json.read_text(encoding="utf-8"))
                                analysis = dock.get("cta_dock_analysis", {})
                                active_bot = analysis.get("active_pill_bottom_y_px")
                                active_h = analysis.get("active_pill_ink_height_px")
                                if active_bot and active_h:
                                    b = {
                                        "x": b["x"],
                                        "y": float(active_bot) - float(active_h),
                                        "width": b["width"],
                                        "height": float(active_h),
                                    }
                            except Exception:
                                pass
                    out.append({"id": key, "role": role, "bbox": b})
        return out

    return out


# ---------------------------------------------------------------------------
# MODULE 1: ALPHA_AND_BORDER_GATEKEEPER
# ---------------------------------------------------------------------------

def check_alpha_defringe(
    rgba_img: Image.Image,
    label: str,
    has_soft_shadows: bool = False,
    allow_white_surface: bool = False,
) -> Dict[str, Any]:
    """
    Vectorized Alpha Gatekeeper:
      - Zero-alpha RGB leak check (RGB > 0 where alpha == 0)
      - Premultiplication dark-halo check on anti-aliased transition edges
      - Studio white/light-gray notch check on outer 2px rim + semi-transparent edge
    """
    arr_u8 = np.array(rgba_img.convert("RGBA"))
    alpha_u8 = arr_u8[:, :, 3]
    rgb_u8 = arr_u8[:, :, :3]

    a = alpha_u8.astype(np.float32) / 255.0
    rgb = rgb_u8.astype(np.float32) / 255.0
    luma = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

    # 1. Zero-alpha dirty RGB
    zero_a_rgb = int(np.sum((alpha_u8 == 0) & (np.max(rgb_u8, axis=-1) > 1)))

    # 2. Dark halo (vectorized 3x3 neighborhood check)
    opaque = a >= 0.99
    if not np.any(opaque):
        return {
            "label": label,
            "zero_alpha_rgb": zero_a_rgb,
            "dark_halo_px": 0,
            "white_notch_pct": 0.0,
            "edge_px": 0,
            "passed": zero_a_rgb == 0,
        }

    near_op = binary_dilation(opaque, iterations=2)
    a_lo = 0.35 if has_soft_shadows else 0.05
    partial = (a > a_lo) & (a < 0.95) & near_op

    op_luma = np.where(opaque, luma, 1.0)
    nbr_min_luma = minimum_filter(op_luma, size=3, mode="nearest")
    has_op_nbr = maximum_filter(opaque.astype(np.uint8), size=3, mode="nearest") > 0
    dark_halo_mask = partial & has_op_nbr & (nbr_min_luma > 0.15) & (luma < 0.50 * nbr_min_luma)
    dark_halo_px = int(np.sum(dark_halo_mask))

    # 3. White / light-gray studio notch on outer 2px rim + semi-transparent border
    # Only flag edge pixels whose nearest deep-interior neighbor (5px inside core) is colored/dark,
    # avoiding false positives on legitimately white product surfaces (bottles, handles, sleeves).
    solid_mask = alpha_u8 > 20
    eroded_2px = binary_erosion(solid_mask, structure=np.ones((3, 3), dtype=bool), iterations=2)
    outer_rim = solid_mask & (~eroded_2px)
    semi_mask = (alpha_u8 > 10) & (alpha_u8 < 250)
    transition_edge = outer_rim | semi_mask
    edge_px = int(np.sum(transition_edge))

    white_notch_pct = 0.0
    if edge_px > 0 and not allow_white_surface:
        ty, tx = np.where(transition_edge)
        rgb_i = rgb_u8[ty, tx].astype(np.int16)
        r, g, b = rgb_i[:, 0], rgb_i[:, 1], rgb_i[:, 2]
        sat = np.max(rgb_i, axis=1) - np.min(rgb_i, axis=1)
        bright = (r + g + b) / 3.0
        studio_white = ((r > 210) & (g > 210) & (b > 210) & (sat < 14)) | ((bright > 205.0) & (sat < 12))

        deep_core = binary_erosion(solid_mask, structure=np.ones((3, 3), dtype=bool), iterations=5)
        if not np.any(deep_core):
            deep_core = eroded_2px
        if np.any(deep_core):
            _, (ny, nx) = distance_transform_edt(~deep_core, return_indices=True)
            core_rgb = rgb_u8[ny[ty, tx], nx[ty, tx]].astype(np.int16)
            core_sat = np.max(core_rgb, axis=1) - np.min(core_rgb, axis=1)
            core_bright = np.mean(core_rgb, axis=1)
            adj_colored = (core_bright < 185.0) | (core_sat >= 25)
            eval_px = int(np.sum(adj_colored))
            if eval_px > 0:
                white_notch_px = int(np.sum(studio_white & adj_colored))
                white_notch_pct = (white_notch_px / eval_px) * 100.0

    passed = (zero_a_rgb == 0) and (dark_halo_px == 0) and (white_notch_pct <= WHITE_NOTCH_MAX_PCT)
    return {
        "label": label,
        "zero_alpha_rgb": zero_a_rgb,
        "dark_halo_px": dark_halo_px,
        "white_notch_pct": round(white_notch_pct, 2),
        "edge_px": edge_px,
        "passed": passed,
    }


def check_corner_purity(img: Image.Image, patch_size: int = 16) -> Dict[str, Any]:
    """
    Verify 100% purity across all 4 canvas corners (TL, TR, BL, BR):
      - Transparent cutout (RGBA): 0 pixels with alpha > 5 in 4 corners (12x12).
      - Composite banner (RGB): fit linear gradient plane per corner patch (16x16) and
        verify 0 stray debris / clipped shadow pixels deviating > 14 RGB units from
        the local gradient plane.
    """
    w, h = img.size
    ps = min(patch_size, max(8, min(w, h) // 25))

    if _is_transparent_cutout(img):
        alpha = np.array(img.convert("RGBA"))[:, :, 3]
        corners = {
            "TL": alpha[:ps, :ps],
            "TR": alpha[:ps, -ps:],
            "BL": alpha[-ps:, :ps],
            "BR": alpha[-ps:, -ps:],
        }
        total_px = 4 * ps * ps
        bad_px = 0
        bad_corners = []
        for cname, patch in corners.items():
            cnt = int(np.sum(patch > 5))
            if cnt > 0:
                bad_px += cnt
                bad_corners.append(f"{cname}:{cnt}px")
        purity_pct = ((total_px - bad_px) / max(1, total_px)) * 100.0
        return {
            "mode": "rgba_alpha",
            "purity_pct": round(purity_pct, 2),
            "bad_px": bad_px,
            "bad_corners": bad_corners,
            "passed": bad_px == 0,
        }

    arr = np.array(img.convert("RGB"), dtype=np.float64)
    corners = {
        "TL": arr[:ps, :ps, :],
        "TR": arr[:ps, -ps:, :],
        "BL": arr[-ps:, :ps, :],
        "BR": arr[-ps:, -ps:, :],
    }

    yy, xx = np.mgrid[0:ps, 0:ps]
    design = np.column_stack([xx.ravel(), yy.ravel(), np.ones(ps * ps)])
    pinv = np.linalg.pinv(design)

    total_px = 4 * ps * ps
    bad_px = 0
    bad_corners = []
    max_residual = 0.0

    for cname, patch in corners.items():
        # Fit linear gradient plane independently for R, G, B
        residuals = np.zeros((ps, ps), dtype=np.float64)
        for ch in range(3):
            vals = patch[:, :, ch].ravel()
            coeff = pinv @ vals
            pred = (design @ coeff).reshape(ps, ps)
            residuals = np.maximum(residuals, np.abs(patch[:, :, ch] - pred))
        c_max = float(np.max(residuals))
        max_residual = max(max_residual, c_max)
        # Stray pixel / hard shadow clip threshold: > 14 RGB units from smooth linear gradient
        cnt = int(np.sum(residuals > 14.0))
        if cnt > 0:
            bad_px += cnt
            bad_corners.append(f"{cname}:{cnt}px(maxΔ={c_max:.1f})")

    purity_pct = ((total_px - bad_px) / max(1, total_px)) * 100.0
    return {
        "mode": "rgb_gradient",
        "purity_pct": round(purity_pct, 2),
        "bad_px": bad_px,
        "max_residual": round(max_residual, 2),
        "bad_corners": bad_corners,
        "passed": bad_px == 0,
    }


# ---------------------------------------------------------------------------
# MODULE 2: LAYOUT_AND_SAFE_ZONE_INSPECTOR
# ---------------------------------------------------------------------------

def check_safe_zones(
    elements: List[Dict[str, Any]],
    canvas_w: int,
    canvas_h: int,
    margins: Dict[str, int],
) -> Dict[str, Any]:
    min_x = float(margins["left"])
    min_y = float(margins["top"])
    max_x = float(canvas_w - margins["right"])
    max_y = float(canvas_h - margins["bottom"])

    violations: List[str] = []
    min_clearance = float("inf")
    checked = 0

    for elem in elements:
        b = elem["bbox"]
        x1, y1 = b["x"], b["y"]
        x2, y2 = x1 + b["width"], y1 + b["height"]
        checked += 1

        c_left = x1
        c_top = y1
        c_right = canvas_w - x2
        c_bot = canvas_h - y2
        min_clearance = min(min_clearance, c_left, c_top, c_right, c_bot)

        vios = []
        if x1 < min_x - 0.5:
            vios.append(f"L={x1:.1f}<{min_x:.0f}")
        if y1 < min_y - 0.5:
            vios.append(f"T={y1:.1f}<{min_y:.0f}")
        if x2 > max_x + 0.5:
            vios.append(f"R={c_right:.1f}<{margins['right']}")
        if y2 > max_y + 0.5:
            vios.append(f"B={c_bot:.1f}<{margins['bottom']}")
        if vios:
            violations.append(f"{elem['id']}({', '.join(vios)})")

    if checked == 0:
        return {
            "checked": 0,
            "min_clearance_px": 0.0,
            "violations": ["No UI elements found in manifest"],
            "passed": False,
        }

    return {
        "checked": checked,
        "min_clearance_px": round(min_clearance, 1),
        "violations": violations,
        "passed": len(violations) == 0,
    }


def _find_elem_by_role(elements: List[Dict[str, Any]], role: str) -> Optional[Dict[str, Any]]:
    role_l = role.lower()
    for e in elements:
        if e["role"] == role_l:
            return e
    # Fallback substring match
    for e in elements:
        if role_l in e["role"] or role_l in e["id"].lower():
            return e
    return None


def check_alignment(
    elements: List[Dict[str, Any]],
    canvas_w: int,
    canvas_h: int,
    spec: Dict[str, Any],
) -> Dict[str, Any]:
    mode = spec["alignment_mode"]
    issues: List[str] = []

    if mode == "SPLIT_LEFT":
        anchor_x = float(spec["flush_left_anchor_x"])
        tol = float(spec["flush_left_tol_px"])
        max_right = float(spec["left_col_max_right"])
        lefts: Dict[str, float] = {}
        max_dev = 0.0
        for role in spec["flush_left_roles"]:
            e = _find_elem_by_role(elements, role)
            if not e:
                continue
            x1 = e["bbox"]["x"]
            x2 = x1 + e["bbox"]["width"]
            lefts[role] = round(x1, 1)
            dev = abs(x1 - anchor_x)
            max_dev = max(max_dev, dev)
            if dev > tol:
                issues.append(f"{role}: left={x1:.1f}px (expect {anchor_x:.0f}±{tol:.0f})")
            if x2 > max_right + 0.5:
                issues.append(f"{role}: right={x2:.1f}px > {max_right:.0f}px")
        spread = (max(lefts.values()) - min(lefts.values())) if len(lefts) >= 2 else 0.0
        if spread > tol:
            issues.append(f"flush-left spread={spread:.1f}px > {tol:.0f}px")
        return {
            "mode": mode,
            "max_offset_px": round(max_dev, 2),
            "threshold": f"X={anchor_x:.0f}±{tol:.0f}px (SPLIT_LEFT)",
            "issues": issues,
            "passed": len(issues) == 0,
        }

    # CENTER modes (800x1500, 1080x1080, 1200x1200, 300x250)
    tol = float(spec["center_tol_px"])
    canvas_cx = canvas_w / 2.0
    max_dev = 0.0
    checked_roles = 0

    for role in spec["center_roles"]:
        e = _find_elem_by_role(elements, role)
        if not e:
            continue
        checked_roles += 1
        cx = e["bbox"]["x"] + e["bbox"]["width"] / 2.0
        dev = abs(cx - canvas_cx)
        max_dev = max(max_dev, dev)
        if dev > tol:
            issues.append(f"{role}: cx={cx:.1f} vs mid={canvas_cx:.1f} (Δ={dev:.1f}px)")

    # Dual-logo horizontal symmetry for 1200x1200 (COSRX left / ULTA right)
    if mode == "CENTER_SQUARE_DUAL_LOGO":
        logos = [e for e in elements if e["role"] == "logo"]
        if len(logos) == 2:
            logos_sorted = sorted(logos, key=lambda item: item["bbox"]["x"])
            left_m = logos_sorted[0]["bbox"]["x"]
            right_m = canvas_w - (logos_sorted[1]["bbox"]["x"] + logos_sorted[1]["bbox"]["width"])
            sym_dev = abs(left_m - right_m)
            max_dev = max(max_dev, sym_dev)
            if sym_dev > tol:
                issues.append(f"dual_logos: left={left_m:.1f}px vs right={right_m:.1f}px (Δ={sym_dev:.1f}px)")

    if checked_roles == 0:
        issues.append("No alignable UI elements found")

    return {
        "mode": mode,
        "max_offset_px": round(max_dev, 2),
        "threshold": f"|Δcx| <= {tol:.1f}px ({mode})",
        "issues": issues,
        "passed": len(issues) == 0,
    }


def check_cta_fill_ratio(
    img: Image.Image,
    elements: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Brand-agnostic CTA optical text fill ratio (target: 68.0% - 82.0%).
    Detects foreground glyph pixels contrasting against the CTA pill's interior fill.
    """
    cta = _find_elem_by_role(elements, "cta")
    if not cta:
        return None
    b = cta["bbox"]
    cta_w = b["width"]
    if cta_w <= 8:
        return None

    # Prefer explicit manifest text_bbox if present
    tb = cta.get("text_bbox")
    if tb and tb["width"] > 0:
        fill_pct = (tb["width"] / cta_w) * 100.0
        return {
            "fill_pct": round(fill_pct, 2),
            "text_w": round(tb["width"], 1),
            "cta_w": round(cta_w, 1),
            "passed": CTA_FILL_MIN_PCT <= fill_pct <= CTA_FILL_MAX_PCT,
        }

    arr = np.array(img.convert("RGB"))
    img_h, img_w, _ = arr.shape
    x1 = max(0, int(round(b["x"])))
    y1 = max(0, int(round(b["y"])))
    x2 = min(img_w, int(round(b["x"] + b["width"])))
    y2 = min(img_h, int(round(b["y"] + b["height"])))
    bw, bh = x2 - x1, y2 - y1
    if bw <= 10 or bh <= 10:
        return None

    inset_top = max(3, int(round(bh * 0.22)))
    inset_bot = max(2, int(round(bh * 0.16)))
    if y1 + inset_top >= y2 - inset_bot:
        return None

    crop = arr[y1 + inset_top : y2 - inset_bot, x1:x2].astype(np.float32)

    # Detect if manifest CTA bbox includes horizontal transparent shadow padding around a narrower pill:
    # Compare outer 2px columns against center-band dominant pill color.
    center_band = crop[:, int(bw * 0.20) : int(bw * 0.80), :]
    # Identify pill interior color by taking the median of darker/more-saturated half (excluding white text)
    c_flat = center_band.reshape(-1, 3)
    non_white = c_flat[(c_flat[:, 0] < 200) | (c_flat[:, 1] < 205) | (c_flat[:, 2] < 215)]
    pill_rgb = np.median(non_white if len(non_white) >= 20 else c_flat, axis=0)

    # Trim outer columns that don't belong to the pill (e.g., drop-shadow canvas margins)
    col_dist_to_pill = np.median(np.linalg.norm(crop - pill_rgb[None, None, :], axis=-1), axis=0)
    pill_cols = np.where(col_dist_to_pill < 45.0)[0]
    if len(pill_cols) >= max(20, int(bw * 0.50)):
        p_left, p_right = int(pill_cols.min()), int(pill_cols.max()) + 1
        crop = crop[:, p_left:p_right, :]
        bw = p_right - p_left
        cta_w = float(bw)

    cap_inset = max(4, int(round(min(bh * 0.48, bw * 0.12))))

    # Detect white/high-contrast glyphs against pill fill
    dist = np.linalg.norm(crop - pill_rgb[None, None, :], axis=-1)
    is_white = (crop[:, :, 0] > 205) & (crop[:, :, 1] > 210) & (crop[:, :, 2] > 220)
    glyph_mask = (dist > 85.0) | (is_white & (np.linalg.norm(pill_rgb - np.array([255, 255, 255])) > 60))

    if bw > 2 * cap_inset:
        glyph_mask[:, :cap_inset] = False
        glyph_mask[:, bw - cap_inset :] = False

    col_counts = glyph_mask.sum(axis=0)
    cols = np.where(col_counts >= 1)[0]
    if len(cols) == 0:
        return {
            "fill_pct": 0.0,
            "text_w": 0.0,
            "cta_w": round(cta_w, 1),
            "passed": False,
            "detail": "No CTA text glyph pixels detected",
        }

    text_w = float(cols.max() - cols.min() + 1)
    fill_pct = (text_w / cta_w) * 100.0
    return {
        "fill_pct": round(fill_pct, 2),
        "text_w": round(text_w, 1),
        "cta_w": round(cta_w, 1),
        "passed": CTA_FILL_MIN_PCT <= fill_pct <= CTA_FILL_MAX_PCT,
    }


# ---------------------------------------------------------------------------
# MODULE 3: FIDELITY_AND_PBR_INSPECTOR
# ---------------------------------------------------------------------------

def compute_ssim_and_mae(img_a: Image.Image, img_b: Image.Image) -> Tuple[float, float]:
    """Compute Wang et al. SSIM and RGB MAE between two equal-sized images."""
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size, Image.Resampling.LANCZOS)
    a = np.array(img_a.convert("RGB"), dtype=np.float64)
    b = np.array(img_b.convert("RGB"), dtype=np.float64)

    mae = float(np.mean(np.abs(a - b)))
    c1 = (0.01 * 255.0) ** 2
    c2 = (0.03 * 255.0) ** 2
    scores = []
    for ch in range(3):
        x, y = a[:, :, ch], b[:, :, ch]
        mu_x = gaussian_filter(x, sigma=1.5)
        mu_y = gaussian_filter(y, sigma=1.5)
        sig_x2 = gaussian_filter(x * x, sigma=1.5) - mu_x * mu_x
        sig_y2 = gaussian_filter(y * y, sigma=1.5) - mu_y * mu_y
        sig_xy = gaussian_filter(x * y, sigma=1.5) - mu_x * mu_y
        num = (2.0 * mu_x * mu_y + c1) * (2.0 * sig_xy + c2)
        den = (mu_x * mu_x + mu_y * mu_y + c1) * (sig_x2 + sig_y2 + c2)
        scores.append(float(np.mean(num / np.maximum(den, 1e-12))))
    return float(np.mean(scores)), mae


def inspect_psd_hierarchy_and_cutouts(
    psd_path: Path,
    brand: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Optional[Image.Image]]:
    """
    Open PSD, validate standard group hierarchy and unmerged PBR layers,
    run Alpha Gatekeeper on cutout layers inside the PSD, and return composite RGB.
    """
    if PSDImage is None:
        return (
            {"passed": False, "detail": "psd-tools not installed", "groups": [], "missing": ["psd-tools"]},
            [],
            None,
        )

    psd = PSDImage.open(str(psd_path))
    top_groups = [l.name for l in psd if l.is_group()]
    all_layers: List[Tuple[str, Any]] = []

    def _walk(container: Any) -> None:
        for lyr in container:
            all_layers.append((lyr.name, lyr))
            if lyr.is_group():
                _walk(lyr)

    _walk(psd)
    pixel_layer_names = [name for name, lyr in all_layers if not lyr.is_group()]

    contract = BRAND_PSD_CONTRACTS.get(brand)
    missing_groups: List[str] = []
    missing_layers: List[str] = []

    if contract:
        for req_g in contract["required_groups"]:
            if req_g not in top_groups:
                missing_groups.append(req_g)
        for label, pat in contract["required_unmerged_patterns"]:
            rx = re.compile(pat, re.IGNORECASE)
            if not any(rx.search(n) for n in pixel_layer_names):
                missing_layers.append(label)
    else:
        if len(top_groups) < 2:
            missing_groups.append(f"Expected >=2 top-level groups, found {len(top_groups)}")

    # Audit alpha edge quality on key cutout pixel layers inside PSD
    cutout_audits: List[Dict[str, Any]] = []
    cutout_patterns = contract["cutout_layer_patterns"] if contract else []
    if cutout_patterns:
        compiled = [re.compile(p, re.IGNORECASE) for p in cutout_patterns]
        for name, lyr in all_layers:
            if lyr.is_group() or not lyr.visible:
                continue
            if any(rx.search(name) for rx in compiled):
                try:
                    pil_lyr = lyr.topil()
                    if pil_lyr is not None and _is_transparent_cutout(pil_lyr):
                        is_soft = any(k in name.lower() for k in ("shadow", "stage_burst", "cta", "ribbon"))
                        is_white_ok = any(k in name.lower() for k in ("candy_cane", "bauble", "toilet_paper", "headline_3d_liquid_metal"))
                        res = check_alpha_defringe(
                            pil_lyr,
                            label=name,
                            has_soft_shadows=is_soft,
                            allow_white_surface=is_white_ok,
                        )
                        cutout_audits.append(res)
                except Exception:
                    pass

    comp_img = psd.composite()
    comp_rgb = comp_img.convert("RGB") if comp_img is not None else None

    passed = (len(missing_groups) == 0) and (len(missing_layers) == 0)
    hierarchy_report = {
        "groups_found": len(top_groups),
        "layers_found": len(pixel_layer_names),
        "missing_groups": missing_groups,
        "missing_layers": missing_layers,
        "passed": passed,
    }
    return hierarchy_report, cutout_audits, comp_rgb


# ---------------------------------------------------------------------------
# File & Directory Inspection Pipelines
# ---------------------------------------------------------------------------

def inspect_single_png(
    png_path: Path,
    brand: str,
    display_name: Optional[str] = None,
) -> List[CheckResult]:
    results: List[CheckResult] = []
    fname = display_name or png_path.name

    with Image.open(png_path) as raw_im:
        w, h = raw_im.size
        im = raw_im.copy()

    is_cutout = _is_transparent_cutout(im)
    size_key = f"{w}x{h}"

    # --- MODULE 1: ALPHA_AND_BORDER_GATEKEEPER ---
    if is_cutout:
        has_soft = any(k in fname.lower() for k in ("stage_burst", "ui_typography_dock", "shadow", "cta"))
        allow_white = any(k in fname.lower() for k in ("headline_3d", "snowflake", "ui_typography_dock"))
        alpha_res = check_alpha_defringe(im, label=fname, has_soft_shadows=has_soft, allow_white_surface=allow_white)
        measured = (
            f"zeroRGB={alpha_res['zero_alpha_rgb']}, "
            f"darkHalo={alpha_res['dark_halo_px']}px, "
            f"whiteNotch={alpha_res['white_notch_pct']:.2f}%"
        )
        detail = "" if alpha_res["passed"] else f"Alpha fringe/halo detected on {fname}: {measured}"
        results.append(CheckResult(
            file_name=fname,
            check_item="Alpha Gatekeeper (Defringe)",
            measured_value=measured,
            threshold=f"0px halo, <= {WHITE_NOTCH_MAX_PCT:.1f}% notch",
            passed=alpha_res["passed"],
            detail=detail,
            module="ALPHA_AND_BORDER_GATEKEEPER",
        ))

    corner_res = check_corner_purity(im)
    c_detail = ""
    if not corner_res["passed"]:
        c_detail = f"Corner contamination ({', '.join(corner_res['bad_corners'])})"
    results.append(CheckResult(
        file_name=fname,
        check_item="Corner Purity (4 Corners)",
        measured_value=f"{corner_res['purity_pct']:.2f}% ({corner_res['bad_px']} bad px)",
        threshold=f"{CORNER_PURITY_THRESHOLD_PCT:.1f}% (0 bad px)",
        passed=corner_res["passed"],
        detail=c_detail,
        module="ALPHA_AND_BORDER_GATEKEEPER",
    ))

    # --- MODULE 2: LAYOUT_AND_SAFE_ZONE_INSPECTOR ---
    manifest_path = _find_companion_json(png_path)
    if manifest_path and not is_cutout:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        elements = _extract_ui_elements_from_manifest(manifest, w, h, base_dir=png_path.parent)
        spec = FORMAT_SPECS.get(size_key, {
            "alignment_mode": "CENTER_SQUARE",
            "safe_margins": {"top": 40, "bottom": 40, "left": 40, "right": 40},
            "center_roles": ["headline", "cta"],
            "center_tol_px": 2.0,
        })
        margins = spec["safe_margins"]

        # Safe-zone check
        sz_res = check_safe_zones(elements, w, h, margins)
        m_str = f">={margins['top']}px" if margins["top"] == margins["left"] else f"T/B>={margins['top']}, L/R>={margins['left']}px"
        results.append(CheckResult(
            file_name=fname,
            check_item="Safe-Zone Boundary",
            measured_value=f"min_margin={sz_res['min_clearance_px']:.1f}px ({sz_res['checked']} UI elems)",
            threshold=m_str,
            passed=sz_res["passed"],
            detail="; ".join(sz_res["violations"]),
            module="LAYOUT_AND_SAFE_ZONE_INSPECTOR",
        ))

        # Alignment check
        al_res = check_alignment(elements, w, h, spec)
        results.append(CheckResult(
            file_name=fname,
            check_item=f"Alignment ({size_key})",
            measured_value=f"max_offset={al_res['max_offset_px']:.2f}px",
            threshold=al_res["threshold"],
            passed=al_res["passed"],
            detail="; ".join(al_res["issues"]),
            module="LAYOUT_AND_SAFE_ZONE_INSPECTOR",
        ))

        # CTA text fill ratio check
        cta_res = check_cta_fill_ratio(im, elements)
        if cta_res is not None:
            cta_detail = cta_res.get("detail", "")
            if not cta_res["passed"] and not cta_detail:
                cta_detail = (
                    f"CTA fill {cta_res['fill_pct']:.1f}% "
                    f"(text={cta_res['text_w']}px / pill={cta_res['cta_w']}px, target 68%-82%)"
                )
            results.append(CheckResult(
                file_name=fname,
                check_item="CTA Text Fill Ratio",
                measured_value=f"{cta_res['fill_pct']:.1f}% ({cta_res['text_w']:.0f}/{cta_res['cta_w']:.0f}px)",
                threshold=f"{CTA_FILL_MIN_PCT:.0f}% - {CTA_FILL_MAX_PCT:.0f}%",
                passed=cta_res["passed"],
                detail=cta_detail,
                module="LAYOUT_AND_SAFE_ZONE_INSPECTOR",
            ))

    # --- MODULE 3: FIDELITY_AND_PBR_INSPECTOR ---
    psd_path = _find_companion_psd(png_path)
    if psd_path and not is_cutout:
        hier, cutout_audits, psd_comp = inspect_psd_hierarchy_and_cutouts(psd_path, brand)

        if psd_comp is not None:
            ssim_val, mae_val = compute_ssim_and_mae(im, psd_comp)
            ssim_ok = ssim_val >= SSIM_THRESHOLD
            results.append(CheckResult(
                file_name=fname,
                check_item="SSIM / Pixel-Diff (PNG vs PSD)",
                measured_value=f"SSIM={ssim_val:.6f} (MAE={mae_val:.2f})",
                threshold=f"SSIM >= {SSIM_THRESHOLD:.3f}",
                passed=ssim_ok,
                detail="" if ssim_ok else f"Render mismatch vs {psd_path.name}: SSIM={ssim_val:.6f}, MAE={mae_val:.2f}",
                module="FIDELITY_AND_PBR_INSPECTOR",
            ))

        hier_detail_parts = []
        if hier["missing_groups"]:
            hier_detail_parts.append(f"Missing groups: {', '.join(hier['missing_groups'])}")
        if hier["missing_layers"]:
            hier_detail_parts.append(f"Missing unmerged layers: {', '.join(hier['missing_layers'])}")
        results.append(CheckResult(
            file_name=psd_path.name,
            check_item="PSD Hierarchy & PBR Layers",
            measured_value=f"{hier['groups_found']} groups, {hier['layers_found']} layers",
            threshold="All standard groups + unmerged PBR",
            passed=hier["passed"],
            detail="; ".join(hier_detail_parts),
            module="FIDELITY_AND_PBR_INSPECTOR",
        ))

        if cutout_audits:
            total_halo = sum(c["dark_halo_px"] for c in cutout_audits)
            total_zrgb = sum(c["zero_alpha_rgb"] for c in cutout_audits)
            max_notch = max(c["white_notch_pct"] for c in cutout_audits)
            failed_cutouts = [
                f"{c['label']}(halo={c['dark_halo_px']}px, notch={c['white_notch_pct']:.1f}%)"
                for c in cutout_audits if not c["passed"]
            ]
            all_cutouts_ok = len(failed_cutouts) == 0
            results.append(CheckResult(
                file_name=psd_path.name,
                check_item=f"PSD Cutout Alpha Gate ({len(cutout_audits)} layers)",
                measured_value=f"zeroRGB={total_zrgb}, darkHalo={total_halo}px, maxNotch={max_notch:.2f}%",
                threshold=f"0px halo, <= {WHITE_NOTCH_MAX_PCT:.1f}% notch",
                passed=all_cutouts_ok,
                detail="; ".join(failed_cutouts),
                module="ALPHA_AND_BORDER_GATEKEEPER",
            ))

    return results


def inspect_single_psd(psd_path: Path, brand: str) -> List[CheckResult]:
    """Direct inspection when `--file` points to a `.psd` file."""
    results: List[CheckResult] = []
    hier, cutout_audits, psd_comp = inspect_psd_hierarchy_and_cutouts(psd_path, brand)

    hier_detail_parts = []
    if hier["missing_groups"]:
        hier_detail_parts.append(f"Missing groups: {', '.join(hier['missing_groups'])}")
    if hier["missing_layers"]:
        hier_detail_parts.append(f"Missing unmerged layers: {', '.join(hier['missing_layers'])}")
    results.append(CheckResult(
        file_name=psd_path.name,
        check_item="PSD Hierarchy & PBR Layers",
        measured_value=f"{hier['groups_found']} groups, {hier['layers_found']} layers",
        threshold="All standard groups + unmerged PBR",
        passed=hier["passed"],
        detail="; ".join(hier_detail_parts),
        module="FIDELITY_AND_PBR_INSPECTOR",
    ))

    png_pair = psd_path.with_suffix(".png")
    if png_pair.exists() and psd_comp is not None:
        with Image.open(png_pair) as im:
            ssim_val, mae_val = compute_ssim_and_mae(im, psd_comp)
        ssim_ok = ssim_val >= SSIM_THRESHOLD
        results.append(CheckResult(
            file_name=psd_path.name,
            check_item="SSIM / Pixel-Diff (PNG vs PSD)",
            measured_value=f"SSIM={ssim_val:.6f} (MAE={mae_val:.2f})",
            threshold=f"SSIM >= {SSIM_THRESHOLD:.3f}",
            passed=ssim_ok,
            detail="" if ssim_ok else f"Mismatch vs {png_pair.name}",
            module="FIDELITY_AND_PBR_INSPECTOR",
        ))

    if cutout_audits:
        total_halo = sum(c["dark_halo_px"] for c in cutout_audits)
        total_zrgb = sum(c["zero_alpha_rgb"] for c in cutout_audits)
        max_notch = max(c["white_notch_pct"] for c in cutout_audits)
        failed_cutouts = [
            f"{c['label']}(halo={c['dark_halo_px']}px, notch={c['white_notch_pct']:.1f}%)"
            for c in cutout_audits if not c["passed"]
        ]
        results.append(CheckResult(
            file_name=psd_path.name,
            check_item=f"PSD Cutout Alpha Gate ({len(cutout_audits)} layers)",
            measured_value=f"zeroRGB={total_zrgb}, darkHalo={total_halo}px, maxNotch={max_notch:.2f}%",
            threshold=f"0px halo, <= {WHITE_NOTCH_MAX_PCT:.1f}% notch",
            passed=len(failed_cutouts) == 0,
            detail="; ".join(failed_cutouts),
            module="ALPHA_AND_BORDER_GATEKEEPER",
        ))

    return results


def inspect_target_directory(target_dir: Path, brand: str) -> List[CheckResult]:
    results: List[CheckResult] = []
    if not target_dir.exists() or not target_dir.is_dir():
        return [CheckResult(
            file_name=str(target_dir),
            check_item="Target Directory",
            measured_value="NOT FOUND",
            threshold="Existing directory",
            passed=False,
            detail=f"Directory does not exist: {target_dir}",
            module="CLI_INTERFACE",
        )]

    pngs = sorted(
        p for p in target_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".png" and not _is_preview_or_debug_file(p)
    )

    if not pngs:
        return [CheckResult(
            file_name=target_dir.name,
            check_item="Deliverable Discovery",
            measured_value="0 PNG files",
            threshold=">= 1 deliverable PNG",
            passed=False,
            detail=f"No deliverable PNGs found in {target_dir}",
            module="CLI_INTERFACE",
        )]

    for png in pngs:
        results.extend(inspect_single_png(png, brand))

    return results


# ---------------------------------------------------------------------------
# Report Formatter
# ---------------------------------------------------------------------------

def format_markdown_report(
    results: List[CheckResult],
    target_label: str,
    brand: str,
) -> str:
    lines: List[str] = []
    lines.append(f"# AUTOMATED QA ORACLE REPORT — `{brand.upper()}` (`{target_label}`)")
    lines.append("")
    lines.append("| File Name | Check Item | Measured Value | Threshold | Status |")
    lines.append("| :--- | :--- | :--- | :--- | :---: |")

    for r in results:
        status_str = "PASS" if r.passed else "FAIL"
        lines.append(
            f"| `{r.file_name}` | {r.check_item} | {r.measured_value} | {r.threshold} | **{status_str}** |"
        )

    passed_cnt = sum(1 for r in results if r.passed)
    failed_list = [r for r in results if not r.passed]
    overall = "ALL_CHECKS_PASSED" if not failed_list else "DEFECTS_DETECTED"
    exit_code = 0 if not failed_list else 1

    lines.append("")
    lines.append(
        f"**SUMMARY:** `{passed_cnt}/{len(results)} PASSED` | "
        f"`{len(failed_list)} FAILED` | **VERDICT:** `{overall}` (exit `{exit_code}`)"
    )

    if failed_list:
        lines.append("")
        lines.append("### Defect Details")
        for r in failed_list:
            detail_txt = r.detail or f"Measured `{r.measured_value}` vs `{r.threshold}`"
            lines.append(f"- **[{r.file_name}] {r.check_item}**: {detail_txt}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Legacy Workflow A Support (Backward Compatibility)
# ---------------------------------------------------------------------------

def _crop_zone_rgb(arr: np.ndarray, zone_px: Dict[str, int]) -> np.ndarray:
    h, w, _ = arr.shape
    x1 = max(0, min(w, int(zone_px["x"])))
    y1 = max(0, min(h, int(zone_px["y"])))
    x2 = max(x1, min(w, int(zone_px["x"] + zone_px["width"])))
    y2 = max(y1, min(h, int(zone_px["y"] + zone_px["height"])))
    return arr[y1:y2, x1:x2]


def inspect_workflow_a(task_path: Path) -> int:
    task = json.loads(task_path.read_text(encoding="utf-8"))
    matrix = json.loads((ROOT / task["size_guide_matrix"]).read_text(encoding="utf-8"))
    out_dir = ROOT / task["output_dir"]
    specs_by_slug = {ab["slug"]: ab for ab in matrix["artboards"]}
    all_passed = True

    print(f"=== QA INSPECTOR | WORKFLOW A | {task['task_id']} ===")
    for t in task["target_dimensions"]:
        slug, tw, th = t["name"], int(t["width"]), int(t["height"])
        png_path = out_dir / f"{slug}.png"
        spec = specs_by_slug.get(slug)
        if not png_path.exists() or not spec:
            all_passed = False
            print(f"{slug:22s} | MISSING / NO SPEC | FAILED")
            continue
        img = Image.open(png_path).convert("RGB")
        arr = np.array(img)
        dim_ok = img.size == (tw, th)
        model_ok = float(_crop_zone_rgb(arr, spec["zones"]["model_zone"]["px"]).std()) >= 22.0
        pr = _crop_zone_rgb(arr, spec["zones"]["promo_sticker_zone"]["px"]).astype(np.int16)
        ym = (pr[..., 0] >= 175) & (pr[..., 1] >= 195) & (pr[..., 2] <= 115) & ((pr[..., 1] - pr[..., 2]) >= 100)
        promo_ok = int(ym.sum()) >= 120 and float(ym.mean()) >= 0.015
        row_ok = dim_ok and model_ok and promo_ok
        if not row_ok:
            all_passed = False
        print(f"{slug:22s} | {img.size[0]}x{img.size[1]} | {'PASSED' if row_ok else 'FAILED'}")
    return 0 if all_passed else 1


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automated QA CLI Oracle for auto-banner-engine (PBR, Alpha, Layout, Safe-Zone, PSD Fidelity)"
    )
    parser.add_argument("--target", type=str, help="Target output directory to audit (e.g. output/TASK_GSSHOP/)")
    parser.add_argument("--file", type=str, help="Single file (.png or .psd) to audit")
    parser.add_argument(
        "--brand",
        type=str,
        default="auto",
        choices=["auto", "gsshop", "cosrx", "generic"],
        help="Brand rule profile (default: auto-detected from path)",
    )
    parser.add_argument("--json-out", type=str, help="Optional path to save structured JSON report")
    # Legacy Workflow A flags
    parser.add_argument("--workflow", choices=["A", "B"], help="Legacy workflow mode")
    parser.add_argument("--task", type=str, help="Legacy task JSON manifest path")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.workflow and args.task:
        task_path = Path(args.task)
        if not task_path.is_absolute():
            task_path = ROOT / task_path
        return inspect_workflow_a(task_path) if args.workflow == "A" else 0

    if not args.target and not args.file:
        parser.error("Provide either --target <dir> or --file <path>.")

    if args.file:
        fpath = Path(args.file)
        if not fpath.is_absolute():
            fpath = ROOT / fpath
        brand = _infer_brand(fpath, args.brand)
        if not fpath.exists():
            results = [CheckResult(
                file_name=str(args.file),
                check_item="File Existence",
                measured_value="MISSING",
                threshold="Existing file",
                passed=False,
                detail=f"File not found: {fpath}",
                module="CLI_INTERFACE",
            )]
        elif fpath.suffix.lower() == ".psd":
            results = inspect_single_psd(fpath, brand)
        else:
            results = inspect_single_png(fpath, brand)
        target_label = args.file
    else:
        tdir = Path(args.target)
        if not tdir.is_absolute():
            tdir = ROOT / tdir
        brand = _infer_brand(tdir, args.brand)
        results = inspect_target_directory(tdir, brand)
        target_label = args.target

    report_md = format_markdown_report(results, target_label, brand)
    print(report_md)

    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = ROOT / out_path
        payload = {
            "target": target_label,
            "brand": brand,
            "verdict": "ALL_CHECKS_PASSED" if all(r.passed for r in results) else "DEFECTS_DETECTED",
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "checks": [r.__dict__ for r in results],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
