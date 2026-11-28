#!/usr/bin/env python3
"""
INDEPENDENT MULTI-SIZE RESIZE QA INSPECTOR (`engine/qa_resize_inspector.py`)
Directives:
  - DIR-BUILD-INDEPENDENT-RESIZE-QA-062 (4-Pass Independent Resize QA Pipeline)
  - DIR-UPDATE-RESIZE-QA-ALIGNMENT-065 (Alignment-Aware Inspector & Adaptive CTA Geometry)
  - DIR-UPGRADE-INDEPENDENT-QA-069 (CTA Typography Fill Ratio 68%-82%, Center/Split-Left Rules, Zero Distortion <0.5%)

Architecturally decoupled from `engine/qa_banner_inspector.py`. Audits multi-size
banner variants (`1200x600`, `300x250`, `800x1500`, and `1080x1080`) against the
frozen `1080x1080` Golden Master manifest and `config/resize_qa_matrix.json`.
"""

from __future__ import annotations

import argparse
import colorsys
import functools
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX_PATH = ROOT_DIR / "config" / "resize_qa_matrix.json"
DEFAULT_MASTER_MANIFEST_PATH = ROOT_DIR / "output" / "TASK_GSSHOP" / "gsshop_master_1080x1080.json"

DEFAULT_ASPECT_EXEMPT_IDS: Set[str] = {
    "z1_bg_winter_backdrop",
    "z2_snow_tier_1_back_blur",
    "z3_snow_tier_2_box_bed",
    "z11_snow_tier_3_front_blur",
    "z12_snow_particles_overlay",
    "z13_logo_live_group",
    "z13_header_frosted_glass_capsule",
    "z13_03_headline_3d_group",
    "z13_04_cta_pill_button",
}

ENVIRONMENT_LAYER_IDS: Set[str] = {
    "z1_bg_winter_backdrop",
    "z2_snow_tier_1_back_blur",
    "z3_snow_tier_2_box_bed",
    "z11_snow_tier_3_front_blur",
    "z12_snow_particles_overlay",
}

SAFE_ZONE_UI_ROLES: Set[str] = {
    "logo",
    "glass_capsule",
    "badge",
    "sub_copy",
    "subcopy",
    "headline",
    "title",
    "cta",
    "cta_button",
    "text",
}

OCCLUSION_TEXT_ROLES: Set[str] = {
    "logo",
    "glass_capsule",
    "badge",
    "sub_copy",
    "subcopy",
    "headline",
    "main_title",
    "title",
    "cta",
    "cta_button",
}

NON_OCCLUDER_MOTION_ROLES: Set[str] = {
    "static_backdrop",
    "snow_dune_back",
    "snow_bed_ground",
    "snow_drift_front",
    "ambient_snow_drift",
    "ui_header_lock",
    "ui_glass_capsule",
    "ui_headline_lock",
    "ui_cta_pulse",
}


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _resolve_repo_path(path_like: str | Path) -> Path:
    p = Path(path_like)
    if p.is_absolute():
        return p
    return ROOT_DIR / p


def load_qa_matrix(matrix_path: Optional[str | Path] = None) -> Dict[str, Any]:
    path = _resolve_repo_path(matrix_path) if matrix_path else DEFAULT_MATRIX_PATH
    if not path.exists():
        raise FileNotFoundError(f"Resize QA matrix config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _get_dimensions(manifest: Dict[str, Any]) -> Tuple[int, int]:
    dims = manifest.get("dimensions", {})
    w = int(round(float(dims.get("width", 0))))
    h = int(round(float(dims.get("height", 0))))
    return w, h


def _bbox_rect(bbox: Dict[str, Any]) -> Tuple[float, float, float, float]:
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = max(0.0, float(bbox.get("width", 0.0)))
    h = max(0.0, float(bbox.get("height", 0.0)))
    return x, y, x + w, y + h


def _bbox_intersection_area(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ax1, ay1, ax2, ay2 = _bbox_rect(a)
    bx1, by1, bx2, by2 = _bbox_rect(b)
    ix = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0.0, min(ay2, by2) - max(ay1, by1))
    return ix * iy


def _find_ui_bbox(manifest: Dict[str, Any], role_key: str) -> Optional[Dict[str, float]]:
    """Locate canonical bounding box for a logical UI role (`logo`, `glass_capsule`, `headline`, `cta`, `badge`, `sub_copy`)."""
    elements = manifest.get("elements") if isinstance(manifest.get("elements"), list) else []
    layers = manifest.get("layers") if isinstance(manifest.get("layers"), list) else []

    role_aliases: Dict[str, Set[str]] = {
        "logo": {"logo"},
        "glass_capsule": {"glass_capsule", "capsule", "subcopy_capsule"},
        "badge": {"badge"},
        "sub_copy": {"sub_copy", "subcopy"},
        "headline": {"headline", "main_title", "title"},
        "cta": {"cta", "cta_button"},
    }
    aliases = role_aliases.get(role_key, {role_key})

    for elem in elements:
        if not isinstance(elem, dict) or not isinstance(elem.get("bbox"), dict):
            continue
        role = str(elem.get("role", "")).lower()
        eid = str(elem.get("id", "")).lower()
        if role in aliases or (role_key == "logo" and "logo" in eid) or (role_key == "cta" and "cta" in eid):
            b = elem["bbox"]
            if float(b.get("width", 0)) > 0 and float(b.get("height", 0)) > 0:
                return {
                    "x": float(b["x"]),
                    "y": float(b["y"]),
                    "width": float(b["width"]),
                    "height": float(b["height"]),
                }

    # Layer fallbacks for glass_capsule, cta, logo, headline
    layer_id_map = {
        "logo": {"z13_logo_live_group"},
        "glass_capsule": {"z13_header_frosted_glass_capsule"},
        "headline": {"z13_03_headline_3d_group"},
        "cta": {"z13_04_cta_pill_button"},
    }
    target_lids = layer_id_map.get(role_key, set())
    for lyr in layers:
        if not isinstance(lyr, dict) or not isinstance(lyr.get("bbox"), dict):
            continue
        if str(lyr.get("layer_id", "")) in target_lids:
            b = lyr["bbox"]
            if float(b.get("width", 0)) > 0 and float(b.get("height", 0)) > 0:
                return {
                    "x": float(b["x"]),
                    "y": float(b["y"]),
                    "width": float(b["width"]),
                    "height": float(b["height"]),
                }

    # Capsule union fallback from badge + sub_copy
    if role_key == "glass_capsule":
        sub_boxes = []
        for elem in elements:
            if isinstance(elem, dict) and isinstance(elem.get("bbox"), dict):
                if str(elem.get("role", "")).lower() in {"badge", "sub_copy", "subcopy"}:
                    sub_boxes.append(elem["bbox"])
        if sub_boxes:
            x1 = min(float(b["x"]) for b in sub_boxes)
            y1 = min(float(b["y"]) for b in sub_boxes)
            x2 = max(float(b["x"]) + float(b["width"]) for b in sub_boxes)
            y2 = max(float(b["y"]) + float(b["height"]) for b in sub_boxes)
            return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}

    return None


@functools.lru_cache(maxsize=128)
def _cached_alpha_norm_bbox(
    resolved_path: str,
    rot_key: float,
    flip_x: bool,
) -> Optional[Tuple[float, float, float, float]]:
    """Return normalized (nx, ny, nw, nh) of painted pixels (alpha > 20) for an RGBA PNG."""
    p = Path(resolved_path)
    if not p.exists():
        return None
    try:
        with Image.open(p) as im:
            rgba = im.convert("RGBA")
            if flip_x:
                rgba = rgba.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            rot_im = (
                rgba.rotate(-rot_key, resample=Image.Resampling.BILINEAR, expand=True)
                if abs(rot_key) >= 1e-3
                else rgba
            )
            alpha = np.array(rot_im.split()[3])
            ys, xs = np.where(alpha > 20)
            if len(xs) == 0:
                return None
            rw, rh = rot_im.size
            x_min, x_max = int(xs.min()), int(xs.max()) + 1
            y_min, y_max = int(ys.min()), int(ys.max()) + 1
            return (x_min / rw, y_min / rh, (x_max - x_min) / rw, (y_max - y_min) / rh)
    except Exception:
        return None


def _effective_layer_bbox(layer: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute alpha-trimmed visual bounding box of a layer so transparent canvas margins
    on 1024x1024 RGBA assets (e.g. fluttering ribbons, rotated cutouts) do not cause
    false cross-column or vertical-gap violations.
    """
    bbox = layer.get("bbox", {})
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = float(bbox.get("width", 0.0))
    h = float(bbox.get("height", 0.0))
    rot = round(float(layer.get("rotation_deg", 0.0) or 0.0), 3)
    asset_path = layer.get("asset_path")

    if not isinstance(asset_path, str) or not asset_path.strip():
        return {"x": x, "y": y, "width": w, "height": h}

    p = _resolve_repo_path(asset_path)
    norm = _cached_alpha_norm_bbox(str(p), rot, bool(layer.get("flip_x")))
    if norm is None:
        return {"x": x, "y": y, "width": w, "height": h}
    nx, ny, nw, nh = norm
    return {
        "x": x + nx * w,
        "y": y + ny * h,
        "width": nw * w,
        "height": nh * h,
    }


def _is_visual_stage_layer(layer: Dict[str, Any]) -> bool:
    """Return True if `layer` belongs to the 3D gift-box / hero-product visual stage (Z4-Z10)."""
    lid = str(layer.get("layer_id", ""))
    lname = str(layer.get("layer_name", "")).upper()
    mrole = str(layer.get("motion_role", "")).lower()
    if (
        lid in ENVIRONMENT_LAYER_IDS
        or mrole in NON_OCCLUDER_MOTION_ROLES
        or lname.startswith("Z13_UI")
        or lname.startswith("Z1_BG")
        or "SNOW" in lname
        or "SPARKLE" in lid.upper()
    ):
        return False
    return True


def _extract_cta_glyph_metrics(
    target_image_path: str | Path,
    cta_bbox: Dict[str, float],
) -> Optional[Dict[str, float]]:
    """
    Extract horizontal pixel span of the white CTA label ('라이브 혜택 받고 쇼핑하기 >')
    inside the rendered CTA pill button, excluding rounded pill ends and top bevel sheen.
    """
    p = _resolve_repo_path(target_image_path)
    if not p.exists():
        return None
    with Image.open(p) as im:
        arr = np.array(im.convert("RGB"))
    img_h, img_w, _ = arr.shape
    x1 = max(0, int(round(cta_bbox["x"])))
    y1 = max(0, int(round(cta_bbox["y"])))
    x2 = min(img_w, int(round(cta_bbox["x"] + cta_bbox["width"])))
    y2 = min(img_h, int(round(cta_bbox["y"] + cta_bbox["height"])))
    bw = x2 - x1
    bh = y2 - y1
    if bw <= 8 or bh <= 8:
        return None

    # Inset vertically to skip top specular bevel highlight & bottom border
    inset_top = max(3, int(round(bh * 0.22)))
    inset_bot = max(2, int(round(bh * 0.16)))
    if y1 + inset_top >= y2 - inset_bot:
        return None

    crop = arr[y1 + inset_top : y2 - inset_bot, x1:x2]
    # White glyph pixels against Azure Blue (#0F78FF) pill fill
    white_mask = (crop[:, :, 0] > 205) & (crop[:, :, 1] > 210) & (crop[:, :, 2] > 220)

    # Ignore outer curved cap edges where snow/border anti-aliasing may intrude
    cap_inset = max(4, int(round(min(bh * 0.35, bw * 0.06))))
    if bw > 2 * cap_inset:
        white_mask[:, :cap_inset] = False
        white_mask[:, bw - cap_inset :] = False

    col_counts = white_mask.sum(axis=0)
    cols = np.where(col_counts >= 1)[0]
    if len(cols) == 0:
        return None

    g_min = float(x1 + int(cols.min()))
    g_max = float(x1 + int(cols.max()) + 1)
    text_w = g_max - g_min
    glyph_mid_x = 0.5 * (g_min + g_max)
    pill_mid_x = cta_bbox["x"] + cta_bbox["width"] / 2.0
    fill_pct = (text_w / cta_bbox["width"]) * 100.0
    return {
        "glyph_min_x": round(g_min, 1),
        "glyph_max_x": round(g_max, 1),
        "text_width_px": round(text_w, 1),
        "cta_width_px": round(cta_bbox["width"], 1),
        "fill_ratio_percent": round(fill_pct, 2),
        "glyph_mid_x": round(glyph_mid_x, 1),
        "pill_mid_x": round(pill_mid_x, 1),
        "center_offset_px": round(abs(glyph_mid_x - pill_mid_x), 2),
    }


def _rgb_to_hue_deg(rgb: Sequence[float]) -> float:
    r, g, b = float(rgb[0]) / 255.0, float(rgb[1]) / 255.0, float(rgb[2]) / 255.0
    h, _, _ = colorsys.rgb_to_hsv(r, g, b)
    return h * 360.0


# ---------------------------------------------------------------------------
# PASS 1: Asset & Ratio Integrity (DIR-062 + DIR-069)
# ---------------------------------------------------------------------------


def audit_aspect_ratio_preservation(
    target_manifest: Dict[str, Any],
    master_manifest: Dict[str, Any],
    max_distortion_pct: float = 0.5,
    exempt_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    PASS 1 (DIR-062 + DIR-069):
    Compare aspect ratio (W / H) of every rigid layer in `target_manifest` against
    the frozen `master_manifest`. If any rigid layer drifts by >= `max_distortion_pct`
    (strict < 0.5% invariant), immediately raise `AssertionError('STRETCHING DETECTED: ...')`.
    """
    exempt: Set[str] = set(DEFAULT_ASPECT_EXEMPT_IDS) if exempt_ids is None else set(exempt_ids)

    master_layers: Dict[str, Dict[str, Any]] = {}
    for lyr in master_manifest.get("layers", []):
        if isinstance(lyr, dict) and lyr.get("layer_id"):
            master_layers[str(lyr["layer_id"])] = lyr

    checked: List[Dict[str, Any]] = []
    violations: List[str] = []
    max_observed_drift = 0.0

    for lyr in target_manifest.get("layers", []):
        if not isinstance(lyr, dict):
            continue
        lid = str(lyr.get("layer_id", ""))
        if not lid or lid in exempt or lid not in master_layers:
            continue

        tb = lyr.get("bbox")
        mb = master_layers[lid].get("bbox")
        if not isinstance(tb, dict) or not isinstance(mb, dict):
            continue

        tw, th = float(tb.get("width", 0.0)), float(tb.get("height", 0.0))
        mw, mh = float(mb.get("width", 0.0)), float(mb.get("height", 0.0))
        if tw <= 0 or th <= 0 or mw <= 0 or mh <= 0:
            violations.append(f"{lid}: invalid zero dimension ({tw}x{th})")
            continue

        t_ratio = tw / th
        m_ratio = mw / mh
        drift_pct = abs(t_ratio - m_ratio) / m_ratio * 100.0
        max_observed_drift = max(max_observed_drift, drift_pct)
        checked.append(
            {
                "layer_id": lid,
                "master_ratio": round(m_ratio, 4),
                "target_ratio": round(t_ratio, 4),
                "drift_percent": round(drift_pct, 3),
            }
        )
        if drift_pct >= max_distortion_pct:
            violations.append(
                f"{lid} (target W/H={t_ratio:.4f} vs master W/H={m_ratio:.4f}, "
                f"drift={drift_pct:.2f}% >= {max_distortion_pct:.2f}%)"
            )

    if violations:
        raise AssertionError("STRETCHING DETECTED: " + "; ".join(violations))

    return {
        "status": "PASS",
        "checked_layers": len(checked),
        "max_drift_percent": round(max_observed_drift, 3),
        "threshold_percent": max_distortion_pct,
        "details": checked,
        "issues": [],
    }


def assert_zero_distortion_integrity(
    target_manifest: Dict[str, Any],
    master_manifest: Dict[str, Any],
    max_distortion_pct: float = 0.5,
    exempt_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """DIR-UPGRADE-INDEPENDENT-QA-069 wrapper around `audit_aspect_ratio_preservation`."""
    return audit_aspect_ratio_preservation(
        target_manifest=target_manifest,
        master_manifest=master_manifest,
        max_distortion_pct=max_distortion_pct,
        exempt_ids=exempt_ids,
    )


# ---------------------------------------------------------------------------
# PASS 2: Safe-Zone & Bleed Margins (DIR-062)
# ---------------------------------------------------------------------------


def audit_safe_zones(
    target_manifest: Dict[str, Any],
    config_margins: Dict[str, Any],
    canvas_size: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    """
    PASS 2 (DIR-062):
    Verify every UI/Text element (Logo, Capsule, Badge, Sub-copy, Headline, CTA)
    stays strictly inside the format-specific safe margins.
    """
    w, h = canvas_size if canvas_size else _get_dimensions(target_manifest)
    top_m = float(config_margins.get("top", 0))
    bot_m = float(config_margins.get("bottom", 0))
    left_m = float(config_margins.get("left", 0))
    right_m = float(config_margins.get("right", 0))

    min_x, min_y = left_m, top_m
    max_x, max_y = w - right_m, h - bot_m

    issues: List[str] = []
    checked_count = 0

    elements = target_manifest.get("elements")
    if not isinstance(elements, list) or len(elements) == 0:
        issues.append("Safe-Zone Audit Failure: 'elements' array missing or empty in manifest")
    else:
        for elem in elements:
            if not isinstance(elem, dict) or not isinstance(elem.get("bbox"), dict):
                continue
            role = str(elem.get("role", elem.get("type", ""))).lower()
            has_text = bool(str(elem.get("text", "")).strip())
            if role not in SAFE_ZONE_UI_ROLES and not has_text:
                continue

            x1, y1, x2, y2 = _bbox_rect(elem["bbox"])
            if x2 <= x1 or y2 <= y1:
                continue
            checked_count += 1
            label = str(elem.get("id") or role or "ui_element")
            vios: List[str] = []
            if x1 < min_x - 0.1:
                vios.append(f"left={x1:.1f}px < {min_x:.0f}px")
            if y1 < min_y - 0.1:
                vios.append(f"top={y1:.1f}px < {min_y:.0f}px")
            if x2 > max_x + 0.1:
                vios.append(f"right={x2:.1f}px > {max_x:.0f}px")
            if y2 > max_y + 0.1:
                vios.append(f"bottom={y2:.1f}px > {max_y:.0f}px")
            if vios:
                issues.append(f"Safe Zone Intrusion ({label}): {', '.join(vios)}")

    # Ensure Logo does not collide with Header Capsule
    logo_box = _find_ui_bbox(target_manifest, "logo")
    cap_box = _find_ui_bbox(target_manifest, "glass_capsule")
    if logo_box and cap_box:
        overlap = _bbox_intersection_area(logo_box, cap_box)
        if overlap > 0.0:
            issues.append(f"Header Collision: Logo overlaps Subcopy Capsule ({overlap:.1f} px²)")

    return {
        "status": "PASS" if not issues else "FAIL",
        "canvas": f"{w}x{h}",
        "safe_margins": {
            "top": int(top_m),
            "bottom": int(bot_m),
            "left": int(left_m),
            "right": int(right_m),
        },
        "checked_elements": checked_count,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# PASS 3: Layout Alignment Rules, Adaptive CTA Geometry, Fill Ratio & Cadence
# (DIR-062 + DIR-065 + DIR-069)
# ---------------------------------------------------------------------------


def assert_layout_alignment_rules(
    target_manifest: Dict[str, Any],
    layout_mode: str,
    size_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    DIR-065 + DIR-069 Alignment-Aware Validation:
      - `SPLIT_LEFT_MODE` / `TWO_COLUMN_SPLIT` (`1200x600`):
          1. Flush-Left vertical grid check: Logo, Subcopy Capsule, 3D Headline, and CTA
             all align on a single vertical left axis (spread <= 2px, anchor X = 50px ± 2px).
          2. Column separation: Left UI right <= 540px, Right Visual Stage left >= 560px
             (gutter >= 20px, 0 px² cross-column overlap).
      - `CENTER_MODE` (`800x1500`, `1080x1080`):
          Logo, Subcopy Capsule, 3D Headline, and CTA center X matches canvas_width / 2 (±2px).
      - `CENTER_AXIS` (`300x250`):
          Subcopy Capsule, 3D Headline, and CTA center X matches canvas_width / 2 (±3px).
    """
    spec = size_spec or {}
    w, _ = _get_dimensions(target_manifest)
    mode_upper = str(layout_mode).upper()
    align_mode = str(
        spec.get(
            "alignment_mode",
            "SPLIT_LEFT_MODE" if mode_upper == "TWO_COLUMN_SPLIT" else "CENTER_MODE",
        )
    ).upper()

    issues: List[str] = []
    metrics: Dict[str, Any] = {"alignment_mode": align_mode}

    if align_mode in {"SPLIT_LEFT_MODE", "TWO_COLUMN_FLUSH_LEFT"} or mode_upper == "TWO_COLUMN_SPLIT":
        anchor_x = float(spec.get("flush_left_anchor_x", 50.0))
        tol_px = float(spec.get("flush_left_tolerance_px", 2.0))
        left_col_max_right = float(spec.get("left_column_max_right_x", 540.0))
        right_col_min_left = float(spec.get("column_split_x", 560.0))
        min_gutter = float(spec.get("min_column_gutter_px", 20.0))
        roles = spec.get("flush_left_roles", ["logo", "glass_capsule", "headline", "cta"])

        lefts: Dict[str, float] = {}
        rights: Dict[str, float] = {}
        for role in roles:
            b = _find_ui_bbox(target_manifest, role)
            if b is None:
                issues.append(f"Flush-Left Check: missing UI block '{role}'")
                continue
            lefts[role] = round(b["x"], 2)
            rights[role] = round(b["x"] + b["width"], 2)
            if abs(b["x"] - anchor_x) > tol_px:
                issues.append(
                    f"Flush-Left Misalignment ({role}): left={b['x']:.1f}px "
                    f"(expected {anchor_x:.0f}px ± {tol_px:.0f}px)"
                )
            if b["x"] + b["width"] > left_col_max_right + 0.1:
                issues.append(
                    f"Left Column Spill ({role}): right={b['x'] + b['width']:.1f}px > {left_col_max_right:.0f}px"
                )

        if len(lefts) >= 2:
            spread = max(lefts.values()) - min(lefts.values())
            metrics["flush_left_spread_px"] = round(spread, 2)
            if spread > tol_px:
                issues.append(
                    f"Flush-Left Axis Broken: left spread={spread:.1f}px > {tol_px:.0f}px ({lefts})"
                )

        metrics["left_column_lefts_px"] = lefts
        max_left_right = max(rights.values()) if rights else 0.0
        metrics["left_column_max_right_px"] = round(max_left_right, 1)

        # Right Column Visual Stage clearance (Z4-Z10 alpha-trimmed visual bboxes)
        right_stage_min_x: Optional[float] = None
        for lyr in target_manifest.get("layers", []):
            if not isinstance(lyr, dict) or not isinstance(lyr.get("bbox"), dict):
                continue
            if not _is_visual_stage_layer(lyr):
                continue
            eff = _effective_layer_bbox(lyr)
            lx = float(eff["x"])
            if right_stage_min_x is None or lx < right_stage_min_x:
                right_stage_min_x = lx
            if lx < right_col_min_left - 0.1:
                issues.append(
                    f"Right Stage Cross-Column Intrusion ({lyr.get('layer_id')}): "
                    f"left={lx:.1f}px < {right_col_min_left:.0f}px"
                )

        if right_stage_min_x is not None:
            gutter = right_stage_min_x - max_left_right
            metrics["right_stage_min_left_px"] = round(right_stage_min_x, 1)
            metrics["column_gutter_px"] = round(gutter, 1)
            if gutter < min_gutter - 0.1:
                issues.append(
                    f"Column Gutter Too Narrow: {gutter:.1f}px < {min_gutter:.0f}px "
                    f"(left_max_right={max_left_right:.1f}px, right_min_left={right_stage_min_x:.1f}px)"
                )

    else:
        # CENTER_MODE (1080x1080, 800x1500 -> <= 2px incl. Logo) or CENTER_AXIS (300x250 -> <= 3px)
        default_tol = 2.0 if align_mode == "CENTER_MODE" else 3.0
        tol_px = float(spec.get("center_axis_tolerance_px", default_tol))
        default_roles = (
            ["logo", "glass_capsule", "headline", "cta"]
            if align_mode == "CENTER_MODE"
            else ["glass_capsule", "headline", "cta"]
        )
        roles = spec.get("center_axis_roles", default_roles)
        canvas_cx = w / 2.0
        offsets: Dict[str, float] = {}

        for role in roles:
            b = _find_ui_bbox(target_manifest, role)
            if b is None:
                issues.append(f"Center-Axis Check: missing UI block '{role}'")
                continue
            cx = b["x"] + b["width"] / 2.0
            delta = abs(cx - canvas_cx)
            offsets[role] = round(delta, 2)
            if delta > tol_px:
                issues.append(
                    f"Center-Axis Violation ({role}): center_x={cx:.1f}px vs canvas_mid={canvas_cx:.1f}px "
                    f"(|Δ|={delta:.1f}px > {tol_px:.0f}px)"
                )
        metrics["canvas_center_x"] = canvas_cx
        metrics["center_offsets_px"] = offsets
        metrics["tolerance_px"] = tol_px

    return {
        "status": "PASS" if not issues else "FAIL",
        "metrics": metrics,
        "issues": issues,
    }


def assert_layout_alignment_mode(
    target_manifest: Dict[str, Any],
    layout_mode: str,
    size_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """DIR-UPDATE-RESIZE-QA-ALIGNMENT-065 alias for `assert_layout_alignment_rules`."""
    return assert_layout_alignment_rules(target_manifest, layout_mode, size_spec=size_spec)


def assert_adaptive_cta_geometry(
    target_manifest: Dict[str, Any],
    layout_mode: str,
    target_image_path: Optional[str | Path] = None,
    size_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    DIR-UPDATE-RESIZE-QA-ALIGNMENT-065:
    Validate CTA pill geometry adaptively per format:
      - 1080x1080 (`MASTER_SQUARE`): CTA width symmetric with Frosted Glass Capsule width.
      - 1200x600 (`TWO_COLUMN_SPLIT`): height in [60, 70]px, width >= 420px,
        left flush with X=50px ± 2px, and internal text optically centered inside pill.
      - 300x250 (`COMPACT_MREC`): height >= 38px.
      - 800x1500 (`TALL_VERTICAL`): CTA dock symmetry with Frosted Glass Capsule.
    """
    spec = size_spec or {}
    cta_rules = spec.get("cta_rules", {})
    cta_box = _find_ui_bbox(target_manifest, "cta")
    cap_box = _find_ui_bbox(target_manifest, "glass_capsule")

    if cta_box is None:
        return {
            "status": "FAIL",
            "metrics": {},
            "issues": ["Adaptive CTA Geometry Failure: CTA element missing in manifest"],
        }

    issues: List[str] = []
    metrics: Dict[str, Any] = {
        "cta_bbox": {k: round(v, 1) for k, v in cta_box.items()},
    }
    mode_upper = str(layout_mode).upper()

    if mode_upper == "TWO_COLUMN_SPLIT":
        h_range = cta_rules.get("height_range_px", [60.0, 70.0])
        min_h, max_h = float(h_range[0]), float(h_range[1])
        min_w = float(spec.get("min_cta_width", 420.0))
        anchor_x = float(cta_rules.get("flush_left_x", spec.get("flush_left_anchor_x", 50.0)))
        tol_x = float(cta_rules.get("flush_left_tolerance_px", 2.0))
        max_text_off = float(cta_rules.get("max_internal_text_center_offset_px", 4.0))

        if not (min_h <= cta_box["height"] <= max_h):
            issues.append(
                f"CTA Height Out of Spec (1200x600): {cta_box['height']:.1f}px not in [{min_h:.0f}, {max_h:.0f}]px"
            )
        if cta_box["width"] < min_w:
            issues.append(f"CTA Width Too Narrow (1200x600): {cta_box['width']:.1f}px < {min_w:.0f}px")
        if abs(cta_box["x"] - anchor_x) > tol_x:
            issues.append(
                f"CTA Flush-Left Misalignment: left={cta_box['x']:.1f}px (expected {anchor_x:.0f}px ± {tol_x:.0f}px)"
            )

        if target_image_path:
            glyph = _extract_cta_glyph_metrics(target_image_path, cta_box)
            if glyph is not None:
                metrics["internal_text_center_offset_px"] = glyph["center_offset_px"]
                if glyph["center_offset_px"] > max_text_off:
                    issues.append(
                        f"CTA Internal Text Off-Center: offset={glyph['center_offset_px']:.1f}px > {max_text_off:.0f}px"
                    )

    elif mode_upper == "COMPACT_MREC":
        min_h = float(cta_rules.get("min_height_px", spec.get("min_cta_height", 38.0)))
        if cta_box["height"] < min_h:
            issues.append(
                f"CTA Height Below Mobile Tap/Legibility Floor (300x250): {cta_box['height']:.1f}px < {min_h:.0f}px"
            )

    elif mode_upper in {"MASTER_SQUARE", "TALL_VERTICAL"}:
        max_diff = float(
            cta_rules.get("max_capsule_width_diff_px", 8.0 if mode_upper == "MASTER_SQUARE" else 16.0)
        )
        if cap_box is not None:
            diff = abs(cta_box["width"] - cap_box["width"])
            metrics["capsule_width_px"] = round(cap_box["width"], 1)
            metrics["cta_capsule_width_diff_px"] = round(diff, 1)
            if diff > max_diff:
                issues.append(
                    f"CTA-Capsule Symmetry Violation ({mode_upper}): "
                    f"|cta_w({cta_box['width']:.1f}) - capsule_w({cap_box['width']:.1f})| = {diff:.1f}px > {max_diff:.0f}px"
                )

    return {
        "status": "PASS" if not issues else "FAIL",
        "metrics": metrics,
        "issues": issues,
    }


def assert_cta_typography_fill_ratio(
    target_image_path: Optional[str | Path],
    target_manifest: Dict[str, Any],
    min_ratio_pct: float = 68.0,
    max_ratio_pct: float = 82.0,
) -> Dict[str, Any]:
    """
    DIR-UPGRADE-INDEPENDENT-QA-069:
    Measure optical fill ratio of CTA text ('라이브 혜택 받고 쇼핑하기 >') relative to
    the total CTA button width. Passes iff `68.0% <= text_width / cta_width * 100 <= 82.0%`.
    Supports explicit `cta_text_bbox` in manifest elements or direct pixel extraction from PNG.
    """
    cta_box = _find_ui_bbox(target_manifest, "cta")
    if cta_box is None or cta_box["width"] <= 0:
        return {
            "status": "FAIL",
            "metrics": {},
            "issues": ["CTA Typography Fill Ratio Failure: CTA bbox missing"],
        }

    # Check if manifest explicitly provides `cta_text_bbox`
    text_w: Optional[float] = None
    source = "pixel_scan"
    for elem in target_manifest.get("elements", []):
        if isinstance(elem, dict) and str(elem.get("role", "")).lower() in {"cta", "cta_button"}:
            tb = elem.get("text_bbox") or elem.get("cta_text_bbox")
            if isinstance(tb, dict) and float(tb.get("width", 0)) > 0:
                text_w = float(tb["width"])
                source = "manifest_text_bbox"
                break

    metrics: Dict[str, Any] = {"cta_width_px": round(cta_box["width"], 1), "source": source}
    if text_w is not None:
        fill_pct = (text_w / cta_box["width"]) * 100.0
        metrics["text_width_px"] = round(text_w, 1)
        metrics["fill_ratio_percent"] = round(fill_pct, 2)
    else:
        if not target_image_path:
            return {
                "status": "FAIL",
                "metrics": metrics,
                "issues": ["CTA Typography Fill Ratio Failure: image path not provided for pixel scan"],
            }
        glyph = _extract_cta_glyph_metrics(target_image_path, cta_box)
        if glyph is None:
            return {
                "status": "FAIL",
                "metrics": metrics,
                "issues": ["CTA Typography Fill Ratio Failure: unable to detect white CTA text pixels"],
            }
        metrics.update(glyph)
        fill_pct = glyph["fill_ratio_percent"]

    issues: List[str] = []
    if not (min_ratio_pct <= fill_pct <= max_ratio_pct):
        issues.append(
            f"CTA Typography Fill Ratio Out of Range: {fill_pct:.1f}% "
            f"(text={metrics['text_width_px']:.1f}px / cta={cta_box['width']:.1f}px; "
            f"required {min_ratio_pct:.0f}%–{max_ratio_pct:.0f}%)"
        )

    return {
        "status": "PASS" if not issues else "FAIL",
        "metrics": metrics,
        "issues": issues,
    }


def audit_layout_integrity(
    target_manifest: Dict[str, Any],
    layout_mode: str,
    size_spec: Optional[Dict[str, Any]] = None,
    master_manifest: Optional[Dict[str, Any]] = None,
    target_image_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    PASS 3 (DIR-062 + DIR-065 + DIR-069):
    Comprehensive layout cadence, alignment mode, adaptive CTA geometry,
    CTA typography fill ratio (68%–82%), and format-specific spacing audit:
      - TWO_COLUMN_SPLIT (1200x600): Left/Right column integrity + zero cross-column overlap.
      - COMPACT_MREC (300x250): High Legibility Font Scale (>= 1.25x linear scale) + zero text occlusion.
      - TALL_VERTICAL (800x1500): 3-Tier Vertical Airflow (gap >= 35px between tiers).
    """
    spec = size_spec or {}
    mode_upper = str(layout_mode).upper()
    issues: List[str] = []
    sub_results: Dict[str, Any] = {}

    # 3A. Alignment Rules (DIR-065 + DIR-069)
    align_res = assert_layout_alignment_rules(target_manifest, mode_upper, size_spec=spec)
    sub_results["assert_layout_alignment_rules"] = align_res
    issues.extend(align_res["issues"])

    # 3B. Adaptive CTA Geometry (DIR-065)
    cta_geo_res = assert_adaptive_cta_geometry(
        target_manifest, mode_upper, target_image_path=target_image_path, size_spec=spec
    )
    sub_results["assert_adaptive_cta_geometry"] = cta_geo_res
    issues.extend(cta_geo_res["issues"])

    # 3C. CTA Typography Fill Ratio (DIR-069)
    fill_range = spec.get("cta_rules", {}).get("fill_ratio_range_percent", [68.0, 82.0])
    cta_fill_res = assert_cta_typography_fill_ratio(
        target_image_path=target_image_path,
        target_manifest=target_manifest,
        min_ratio_pct=float(fill_range[0]),
        max_ratio_pct=float(fill_range[1]),
    )
    sub_results["assert_cta_typography_fill_ratio"] = cta_fill_res
    issues.extend(cta_fill_res["issues"])

    # 3D. Format-Specific Cadence & Optical Spacing (DIR-062)
    cadence_metrics: Dict[str, Any] = {"layout_mode": mode_upper}
    cadence_issues: List[str] = []

    if mode_upper == "TWO_COLUMN_SPLIT":
        # Zero overlap between any Left UI element and any Right Visual Stage object
        ui_boxes = [
            (str(e.get("id") or e.get("role")), e["bbox"])
            for e in target_manifest.get("elements", [])
            if isinstance(e, dict)
            and isinstance(e.get("bbox"), dict)
            and str(e.get("role", "")).lower() in OCCLUSION_TEXT_ROLES
        ]
        overlap_count = 0
        for lyr in target_manifest.get("layers", []):
            if not isinstance(lyr, dict) or not isinstance(lyr.get("bbox"), dict):
                continue
            if not _is_visual_stage_layer(lyr):
                continue
            eff = _effective_layer_bbox(lyr)
            for ui_label, ui_bbox in ui_boxes:
                area = _bbox_intersection_area(ui_bbox, eff)
                if area > 0.0:
                    overlap_count += 1
                    cadence_issues.append(
                        f"Cross-Column Overlap: '{lyr.get('layer_id')}' overlaps '{ui_label}' ({area:.1f} px²)"
                    )
        cadence_metrics["cross_column_overlaps"] = overlap_count

    elif mode_upper == "COMPACT_MREC":
        min_font_scale = float(spec.get("min_legibility_font_scale", 1.25))
        tw, th = _get_dimensions(target_manifest)
        mw, mh = _get_dimensions(master_manifest) if master_manifest else (1080, 1080)
        canvas_scale = min(tw / max(1, mw), th / max(1, mh))
        cadence_metrics["canvas_linear_scale"] = round(canvas_scale, 4)

        scale_ratios: Dict[str, float] = {}
        for role in ("sub_copy", "headline", "cta"):
            tb = _find_ui_bbox(target_manifest, role)
            mb = _find_ui_bbox(master_manifest, role) if master_manifest else None
            if tb and mb and mb["height"] > 0:
                elem_scale = tb["height"] / mb["height"]
                boost = elem_scale / max(1e-6, canvas_scale)
                scale_ratios[role] = round(boost, 3)
                if boost < min_font_scale:
                    cadence_issues.append(
                        f"MREC Legibility Below Threshold ({role}): boost={boost:.2f}x < {min_font_scale:.2f}x "
                        f"(target_h={tb['height']:.1f}px vs master_h={mb['height']:.1f}px)"
                    )
        cadence_metrics["legibility_boost_ratios"] = scale_ratios

        # Zero text occlusion against headline/capsule/cta
        text_boxes = [
            (role, box)
            for role in ("glass_capsule", "headline", "cta")
            if (box := _find_ui_bbox(target_manifest, role)) is not None
        ]
        for lyr in target_manifest.get("layers", []):
            if not isinstance(lyr, dict) or not isinstance(lyr.get("bbox"), dict):
                continue
            if not _is_visual_stage_layer(lyr):
                continue
            eff = _effective_layer_bbox(lyr)
            for t_role, t_box in text_boxes:
                # CTA sits in Z=13 over snow foreground; check headline & capsule occlusion by Z4-Z10
                if t_role == "cta":
                    continue
                area = _bbox_intersection_area(t_box, eff)
                if area > 0.0:
                    cadence_issues.append(
                        f"MREC Text Occlusion: '{lyr.get('layer_id')}' overlaps '{t_role}' ({area:.1f} px²)"
                    )

    elif mode_upper == "TALL_VERTICAL":
        min_gap = float(spec.get("min_vertical_breathing_gap", 35.0))
        tier1_boxes = [
            b
            for role in ("logo", "glass_capsule", "headline")
            if (b := _find_ui_bbox(target_manifest, role)) is not None
        ]
        tier3_box = _find_ui_bbox(target_manifest, "cta")
        tier2_boxes = [
            _effective_layer_bbox(lyr)
            for lyr in target_manifest.get("layers", [])
            if isinstance(lyr, dict)
            and isinstance(lyr.get("bbox"), dict)
            and _is_visual_stage_layer(lyr)
        ]

        if not tier1_boxes or not tier2_boxes or tier3_box is None:
            cadence_issues.append("Tall Vertical 3-Tier Audit Failure: incomplete tier bounding boxes")
        else:
            tier1_bottom = max(b["y"] + b["height"] for b in tier1_boxes)
            tier2_top = min(b["y"] for b in tier2_boxes)
            tier2_bottom = max(b["y"] + b["height"] for b in tier2_boxes)
            tier3_top = tier3_box["y"]

            gap_1_2 = tier2_top - tier1_bottom
            gap_2_3 = tier3_top - tier2_bottom
            cadence_metrics["tier1_bottom_px"] = round(tier1_bottom, 1)
            cadence_metrics["tier2_top_px"] = round(tier2_top, 1)
            cadence_metrics["tier2_bottom_px"] = round(tier2_bottom, 1)
            cadence_metrics["tier3_top_px"] = round(tier3_top, 1)
            cadence_metrics["gap_tier1_to_tier2_px"] = round(gap_1_2, 1)
            cadence_metrics["gap_tier2_to_tier3_px"] = round(gap_2_3, 1)

            if gap_1_2 < min_gap:
                cadence_issues.append(
                    f"Vertical Airflow Tight (Tier 1 -> Tier 2): {gap_1_2:.1f}px < {min_gap:.0f}px"
                )
            if gap_2_3 < min_gap:
                cadence_issues.append(
                    f"Vertical Airflow Tight (Tier 2 -> Tier 3): {gap_2_3:.1f}px < {min_gap:.0f}px"
                )

    sub_results["format_cadence"] = {
        "status": "PASS" if not cadence_issues else "FAIL",
        "metrics": cadence_metrics,
        "issues": cadence_issues,
    }
    issues.extend(cadence_issues)

    return {
        "status": "PASS" if not issues else "FAIL",
        "sub_assertions": sub_results,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# PASS 4: Brand Color Lock (#0F78FF) & Layer / Alpha Completeness (DIR-062)
# ---------------------------------------------------------------------------


def audit_layer_and_alpha_completeness(
    target_manifest: Dict[str, Any],
    layer_classification: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    PASS 4A (DIR-062):
    Confirm zero essential layers or mandatory copy strings were dropped during resize,
    all assets loaded cleanly, and non-backdrop cutout PNGs retain intact RGBA Alpha channels.
    """
    cls_cfg = layer_classification or {}
    mandatory_copy: List[str] = cls_cfg.get(
        "mandatory_copy",
        [
            "MOBILE LIVE",
            "LIVE",
            "단 60분! 할인쿠폰 + 추가혜택이 펑펑",
            "GS SHOP",
            "라이브특가",
            "라이브 혜택 받고 쇼핑하기 >",
        ],
    )
    essential_layers: List[str] = cls_cfg.get(
        "essential_layer_ids",
        [
            "z1_bg_winter_backdrop",
            "z3_snow_tier_2_box_bed",
            "z5_box_back_interior",
            "z7_box_front_rim",
            "z8_knit_sweater",
            "z8_puffer_jacket",
            "z9_box_lid_flying",
            "z13_logo_live_group",
            "z13_04_cta_pill_button",
        ],
    )
    product_groups: Dict[str, List[str]] = cls_cfg.get(
        "essential_product_groups",
        {
            "knit": ["z8_knit_sweater"],
            "puffer": ["z8_puffer_jacket"],
            "tangerine": [
                "z6_tangerine_cluster",
                "z6_tangerine_cluster_copy",
                "z10_flying_tangerine_left",
                "z10_flying_tangerine_right",
            ],
            "tissue": ["z6_toilet_paper", "z6_toilet_paper_copy"],
        },
    )

    issues: List[str] = []

    # 1. Mandatory Copy
    corpus_parts: List[str] = []
    if isinstance(target_manifest.get("texts"), dict):
        corpus_parts.extend(str(v) for v in target_manifest["texts"].values())
    for elem in target_manifest.get("elements", []):
        if isinstance(elem, dict) and elem.get("text"):
            corpus_parts.append(str(elem["text"]))
    corpus = "\n".join(corpus_parts)
    missing_copy = [s for s in mandatory_copy if s not in corpus]
    if missing_copy:
        issues.append(f"Missing Mandatory Copy: {', '.join(repr(s) for s in missing_copy)}")

    # 2. Essential Layers & 4 Hero Product Groups
    present_layer_ids = {
        str(lyr.get("layer_id"))
        for lyr in target_manifest.get("layers", [])
        if isinstance(lyr, dict) and lyr.get("layer_id")
    }
    missing_layers = [lid for lid in essential_layers if lid not in present_layer_ids]
    if missing_layers:
        issues.append(f"Missing Essential Layers: {', '.join(missing_layers)}")

    for prod_name, candidate_ids in product_groups.items():
        if not any(cid in present_layer_ids for cid in candidate_ids):
            issues.append(f"Missing Mandatory Hero Product Group: '{prod_name}'")

    # 3. Asset Load & Alpha Channel Integrity
    for asset in target_manifest.get("assets", []):
        if not isinstance(asset, dict):
            continue
        aid = str(asset.get("id") or asset.get("path") or "unknown")
        if asset.get("loaded") is False:
            issues.append(f"Unloaded Asset: '{aid}' (loaded=False)")
        nat_w = asset.get("natural_width")
        if isinstance(nat_w, (int, float)) and nat_w <= 0:
            issues.append(f"Broken Asset Dimension: '{aid}' natural_width={nat_w}")

    alpha_checked = 0
    checked_paths: Set[str] = set()
    for lyr in target_manifest.get("layers", []):
        if not isinstance(lyr, dict):
            continue
        lid = str(lyr.get("layer_id", ""))
        ap = lyr.get("asset_path")
        if not isinstance(ap, str) or not ap.strip() or lid == "z1_bg_winter_backdrop":
            continue
        if ap in checked_paths:
            continue
        checked_paths.add(ap)
        p = _resolve_repo_path(ap)
        if not p.exists():
            issues.append(f"Missing Layer Asset File ({lid}): {ap}")
            continue
        try:
            with Image.open(p) as im:
                if "A" not in im.getbands():
                    issues.append(f"Alpha Channel Lost ({lid}): {ap} has mode={im.mode} (expected RGBA)")
                else:
                    alpha_arr = np.array(im.getchannel("A"))
                    if int(alpha_arr.min()) >= 250:
                        issues.append(
                            f"Opaque Alpha Flatten ({lid}): {ap} has min_alpha={int(alpha_arr.min())} (no transparency)"
                        )
                    elif int(alpha_arr.max()) <= 10:
                        issues.append(f"Empty Transparent Layer ({lid}): {ap} has max_alpha={int(alpha_arr.max())}")
                alpha_checked += 1
        except Exception as exc:
            issues.append(f"Unreadable Asset ({lid}): {ap} ({exc})")

    return {
        "status": "PASS" if not issues else "FAIL",
        "metrics": {
            "present_layers": len(present_layer_ids),
            "alpha_verified_assets": alpha_checked,
        },
        "issues": issues,
    }


def audit_brand_color_lock(
    target_image_path: str | Path,
    target_manifest: Optional[Dict[str, Any]] = None,
    brand_cfg: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    PASS 4B (DIR-062):
    Sample pixels from the CTA button and gift-box satin ribbon on `target_image_path`
    to verify strict GS SHOP Azure Blue `#0F78FF` (RGB 15, 120, 255 / Hue 214°) lock.
    """
    cfg = brand_cfg or {}
    target_rgb = np.array(cfg.get("rgb", [15, 120, 255]), dtype=np.float32)
    hue_min, hue_max = cfg.get("hue_deg_range", [206.0, 222.0])
    cta_max_med = float(cfg.get("cta_max_median_rgb_distance", 18.0))
    cta_max_p10 = float(cfg.get("cta_max_p10_rgb_distance", 10.0))
    rib_max_med = float(cfg.get("ribbon_max_median_rgb_distance", 30.0))
    rib_max_p10 = float(cfg.get("ribbon_max_p10_rgb_distance", 12.0))

    img_p = _resolve_repo_path(target_image_path)
    if not img_p.exists():
        return {
            "status": "FAIL",
            "metrics": {},
            "issues": [f"Brand Color Lock Failure: image not found ({target_image_path})"],
        }

    # Auto-load sibling manifest if not passed directly
    manifest = target_manifest
    if manifest is None:
        sibling = img_p.with_suffix(".json")
        if sibling.exists():
            try:
                manifest = json.loads(sibling.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = None

    with Image.open(img_p) as im:
        arr = np.array(im.convert("RGB"))
    img_h, img_w, _ = arr.shape

    def _sample_azure_region(
        name: str,
        bbox: Dict[str, float],
        max_med_dist: float,
        max_p10_dist: float,
    ) -> Tuple[Dict[str, Any], List[str]]:
        x1 = max(0, int(round(bbox["x"])))
        y1 = max(0, int(round(bbox["y"])))
        x2 = min(img_w, int(round(bbox["x"] + bbox["width"])))
        y2 = min(img_h, int(round(bbox["y"] + bbox["height"])))
        if x2 <= x1 or y2 <= y1:
            return {}, [f"Brand Color Lock ({name}): invalid sampling bbox"]

        patch = arr[y1:y2, x1:x2].reshape(-1, 3).astype(np.float32)
        # Isolate saturated blue surface pixels (exclude white text, white box, and snow)
        blue_mask = (patch[:, 2] > 150.0) & ((patch[:, 2] - patch[:, 0]) > 90.0)
        blue_px = patch[blue_mask]
        if len(blue_px) < 15:
            return {"blue_pixels": int(len(blue_px))}, [
                f"Brand Color Lock ({name}): insufficient Azure Blue pixels found ({len(blue_px)} px)"
            ]

        median_rgb = np.median(blue_px, axis=0)
        dists = np.linalg.norm(blue_px - target_rgb, axis=1)
        med_dist = float(np.linalg.norm(median_rgb - target_rgb))
        p10_dist = float(np.percentile(dists, 10))
        hue_deg = _rgb_to_hue_deg(median_rgb)
        hex_sample = "#{:02X}{:02X}{:02X}".format(
            int(round(median_rgb[0])), int(round(median_rgb[1])), int(round(median_rgb[2]))
        )

        region_metrics = {
            "blue_pixels": int(len(blue_px)),
            "median_hex": hex_sample,
            "median_rgb": [int(round(c)) for c in median_rgb],
            "median_rgb_distance": round(med_dist, 2),
            "p10_rgb_distance": round(p10_dist, 2),
            "hue_deg": round(hue_deg, 1),
        }
        region_issues: List[str] = []
        if med_dist > max_med_dist or p10_dist > max_p10_dist:
            region_issues.append(
                f"Brand Color Drift ({name}): sampled {hex_sample} "
                f"(median ΔRGB={med_dist:.1f} > {max_med_dist:.0f} or p10={p10_dist:.1f} > {max_p10_dist:.0f}; "
                f"expected GS SHOP Azure Blue #0F78FF)"
            )
        if not (hue_min <= hue_deg <= hue_max):
            region_issues.append(
                f"Brand Hue Drift ({name}): hue={hue_deg:.1f}° outside [{hue_min:.0f}°, {hue_max:.0f}°]"
            )
        return region_metrics, region_issues

    issues: List[str] = []
    metrics: Dict[str, Any] = {"target_hex": "#0F78FF"}

    # 1. CTA button region
    cta_bbox = _find_ui_bbox(manifest, "cta") if isinstance(manifest, dict) else None
    if cta_bbox is None:
        cta_bbox = {"x": 0.0, "y": img_h * 0.75, "width": float(img_w), "height": img_h * 0.25}
    cta_m, cta_i = _sample_azure_region("CTA", cta_bbox, cta_max_med, cta_max_p10)
    metrics["cta"] = cta_m
    issues.extend(cta_i)

    # 2. Gift-box ribbon region (`z7_box_front_rim` or union with ribbon tails)
    ribbon_bbox: Optional[Dict[str, float]] = None
    if isinstance(manifest, dict):
        for lyr in manifest.get("layers", []):
            if isinstance(lyr, dict) and str(lyr.get("layer_id", "")) == "z7_box_front_rim":
                b = lyr.get("bbox")
                if isinstance(b, dict):
                    ribbon_bbox = {
                        "x": float(b["x"]),
                        "y": float(b["y"]),
                        "width": float(b["width"]),
                        "height": float(b["height"]),
                    }
                    break
    if ribbon_bbox is None:
        ribbon_bbox = {"x": img_w * 0.2, "y": img_h * 0.4, "width": img_w * 0.7, "height": img_h * 0.5}
    rib_m, rib_i = _sample_azure_region("Ribbon", ribbon_bbox, rib_max_med, rib_max_p10)
    metrics["ribbon"] = rib_m
    issues.extend(rib_i)

    return {
        "status": "PASS" if not issues else "FAIL",
        "metrics": metrics,
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Markdown Compliance Table Generator (DIR-062 + DIR-065 + DIR-069)
# ---------------------------------------------------------------------------


def generate_qa_compliance_table(results: Dict[str, Any]) -> str:
    """Export a structured Markdown compliance table summarizing all 4 QA passes."""
    target_name = results.get("target_image", "unknown")
    size_key = results.get("size_key", "unknown")
    layout_mode = results.get("layout_mode", "UNKNOWN")
    overall = results.get("status", "FAIL")
    passes = results.get("passes", {})

    lines = [
        f"### Resize QA Compliance Report — `{size_key}` ({layout_mode})",
        f"- **Target**: `{target_name}`",
        f"- **Overall Status**: **{overall}**",
        "",
        "| Pass | Criterion | Measured Metrics | Threshold / Rule | Status |",
        "| :--- | :--- | :--- | :--- | :---: |",
    ]

    p1 = passes.get("pass_1_aspect_ratio", {})
    p1_metric = (
        f"max drift `{p1.get('max_drift_percent', 'N/A')}%` ({p1.get('checked_layers', 0)} rigid layers)"
        if p1.get("status") == "PASS"
        else f"STRETCHING DETECTED ({len(p1.get('issues', []))} violation)"
    )
    lines.append(
        f"| Pass 1 | Asset & Ratio Integrity (`assert_zero_distortion_integrity`) | {p1_metric} | `< {p1.get('threshold_percent', 0.5)}%` | **{p1.get('status', 'FAIL')}** |"
    )

    p2 = passes.get("pass_2_safe_zones", {})
    sm = p2.get("safe_margins", {})
    sm_str = f"T:{sm.get('top','-')}/B:{sm.get('bottom','-')}/L:{sm.get('left','-')}/R:{sm.get('right','-')}px"
    lines.append(
        f"| Pass 2 | Safe-Zone & Bleed Margins (`audit_safe_zones`) | `{p2.get('checked_elements', 0)}` UI elements, `{len(p2.get('issues', []))}` intrusions | `{sm_str}` | **{p2.get('status', 'FAIL')}** |"
    )

    p3 = passes.get("pass_3_layout_integrity", {})
    sub = p3.get("sub_assertions", {})
    align = sub.get("assert_layout_alignment_rules", {})
    cta_geo = sub.get("assert_adaptive_cta_geometry", {})
    cta_fill = sub.get("assert_cta_typography_fill_ratio", {})
    cad = sub.get("format_cadence", {})

    align_m = align.get("metrics", {})
    if align_m.get("alignment_mode") in {"SPLIT_LEFT_MODE", "TWO_COLUMN_FLUSH_LEFT"}:
        align_desc = (
            f"spread=`{align_m.get('flush_left_spread_px', '-')}px`, "
            f"gutter=`{align_m.get('column_gutter_px', '-')}px`"
        )
        align_rule = "Flush-Left `<= 2px`, L<=540, R>=560, gutter>=20px"
    else:
        align_desc = f"offsets=`{align_m.get('center_offsets_px', {})}`"
        align_rule = f"Center-Axis `<= {align_m.get('tolerance_px', 2)}px`"
    lines.append(
        f"| Pass 3a | Layout Alignment (`assert_layout_alignment_rules`) | {align_desc} | {align_rule} | **{align.get('status', 'FAIL')}** |"
    )

    cta_b = cta_geo.get("metrics", {}).get("cta_bbox", {})
    cta_desc = f"`{cta_b.get('width', '-')}x{cta_b.get('height', '-')}px` @ x=`{cta_b.get('x', '-')}`"
    lines.append(
        f"| Pass 3b | Adaptive CTA Geometry (`assert_adaptive_cta_geometry`) | {cta_desc} | Format CTA spec | **{cta_geo.get('status', 'FAIL')}** |"
    )

    fill_m = cta_fill.get("metrics", {})
    lines.append(
        f"| Pass 3c | CTA Typography Fill (`assert_cta_typography_fill_ratio`) | `{fill_m.get('fill_ratio_percent', 'N/A')}%` (`{fill_m.get('text_width_px', '-')}/{fill_m.get('cta_width_px', '-')}px`) | `68% – 82%` | **{cta_fill.get('status', 'FAIL')}** |"
    )

    cad_m = cad.get("metrics", {})
    lines.append(
        f"| Pass 3d | Optical Cadence (`audit_layout_integrity`) | `{json.dumps(cad_m, ensure_ascii=False)}` | Mode cadence rules | **{cad.get('status', 'FAIL')}** |"
    )

    p4a = passes.get("pass_4a_completeness_alpha", {})
    p4a_m = p4a.get("metrics", {})
    lines.append(
        f"| Pass 4a | Layer & Alpha Completeness | `{p4a_m.get('present_layers', 0)}` layers, `{p4a_m.get('alpha_verified_assets', 0)}` RGBA cutouts | 100% copy + 4 heroes + RGBA | **{p4a.get('status', 'FAIL')}** |"
    )

    p4b = passes.get("pass_4b_brand_color_lock", {})
    p4b_m = p4b.get("metrics", {})
    cta_hex = p4b_m.get("cta", {}).get("median_hex", "N/A")
    rib_hex = p4b_m.get("ribbon", {}).get("median_hex", "N/A")
    lines.append(
        f"| Pass 4b | Brand Color Lock (`audit_brand_color_lock`) | CTA=`{cta_hex}`, Ribbon=`{rib_hex}` | Azure Blue `#0F78FF` | **{p4b.get('status', 'FAIL')}** |"
    )

    all_issues = results.get("issues", [])
    if all_issues:
        lines.append("")
        lines.append("**Detected Issues:**")
        for item in all_issues:
            lines.append(f"- {item}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# End-to-End Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_resize_qa_pipeline(
    image_path: str | Path,
    manifest_path: str | Path,
    matrix_path: Optional[str | Path] = None,
    master_manifest_path: Optional[str | Path] = None,
    fail_fast: bool = False,
) -> Dict[str, Any]:
    """Execute the complete 4-Pass Independent Resize QA Pipeline (Fail-Closed)."""
    img_p = _resolve_repo_path(image_path)
    meta_p = _resolve_repo_path(manifest_path)

    # Fail-Closed check for missing inputs
    missing_issues: List[str] = []
    if not img_p.exists():
        missing_issues.append(f"BLOCKED_AWAITING_INPUT: Target image not found: {image_path}")
    if not meta_p.exists():
        missing_issues.append(f"BLOCKED_AWAITING_INPUT: Target manifest not found: {manifest_path}")
    if missing_issues:
        res = {
            "directive_id": "DIR-BUILD-INDEPENDENT-RESIZE-QA-062+065+069",
            "target_image": str(image_path),
            "target_manifest": str(manifest_path),
            "size_key": "MISSING",
            "layout_mode": "UNKNOWN",
            "status": "FAIL",
            "passes": {},
            "issues": missing_issues,
        }
        res["markdown_report"] = generate_qa_compliance_table(res)
        return res

    matrix = load_qa_matrix(matrix_path)
    master_ref = master_manifest_path or matrix.get("master_reference_manifest") or DEFAULT_MASTER_MANIFEST_PATH
    master_p = _resolve_repo_path(master_ref)
    if not master_p.exists():
        raise FileNotFoundError(f"Master reference manifest not found: {master_p}")

    master_manifest = json.loads(master_p.read_text(encoding="utf-8"))
    target_manifest = json.loads(meta_p.read_text(encoding="utf-8"))

    with Image.open(img_p) as im:
        img_w, img_h = im.size
    man_w, man_h = _get_dimensions(target_manifest)
    size_key = f"{img_w}x{img_h}"

    size_specs = matrix.get("size_specifications", {})
    size_spec = size_specs.get(size_key)
    issues: List[str] = []
    if (img_w, img_h) != (man_w, man_h):
        issues.append(f"Dimension Mismatch: PNG is {img_w}x{img_h}px vs manifest {man_w}x{man_h}px")
    if size_spec is None:
        issues.append(f"Unsupported Variant Size: '{size_key}' not registered in config/resize_qa_matrix.json")
        res = {
            "directive_id": "DIR-BUILD-INDEPENDENT-RESIZE-QA-062+065+069",
            "target_image": str(image_path),
            "target_manifest": str(manifest_path),
            "size_key": size_key,
            "layout_mode": "UNSUPPORTED",
            "status": "FAIL",
            "passes": {},
            "issues": issues,
        }
        res["markdown_report"] = generate_qa_compliance_table(res)
        return res

    layout_mode = str(size_spec.get("layout_mode", "UNKNOWN"))
    cls_cfg = matrix.get("layer_classification", {})
    exempt_ids = cls_cfg.get("aspect_exempt_layer_ids", list(DEFAULT_ASPECT_EXEMPT_IDS))
    max_dist_pct = float(size_spec.get("max_aspect_distortion_percent", 0.5))

    # Pass 1: Aspect Ratio Preservation (raises AssertionError on violation)
    try:
        p1_res = audit_aspect_ratio_preservation(
            target_manifest=target_manifest,
            master_manifest=master_manifest,
            max_distortion_pct=max_dist_pct,
            exempt_ids=exempt_ids,
        )
    except AssertionError as exc:
        if fail_fast:
            raise
        p1_res = {
            "status": "FAIL",
            "checked_layers": 0,
            "max_drift_percent": None,
            "threshold_percent": max_dist_pct,
            "issues": [str(exc)],
        }
    issues.extend(p1_res.get("issues", []))

    # Pass 2: Safe-Zone & Bleed Margins
    p2_res = audit_safe_zones(
        target_manifest=target_manifest,
        config_margins=size_spec.get("safe_margins", {}),
        canvas_size=(img_w, img_h),
    )
    issues.extend(p2_res.get("issues", []))

    # Pass 3: Layout Integrity, Alignment Rules, Adaptive CTA & Typography Fill
    p3_res = audit_layout_integrity(
        target_manifest=target_manifest,
        layout_mode=layout_mode,
        size_spec=size_spec,
        master_manifest=master_manifest,
        target_image_path=img_p,
    )
    issues.extend(p3_res.get("issues", []))

    # Pass 4a: Layer & Alpha Completeness
    p4a_res = audit_layer_and_alpha_completeness(
        target_manifest=target_manifest,
        layer_classification=cls_cfg,
    )
    issues.extend(p4a_res.get("issues", []))

    # Pass 4b: Brand Color Lock (#0F78FF)
    p4b_res = audit_brand_color_lock(
        target_image_path=img_p,
        target_manifest=target_manifest,
        brand_cfg=matrix.get("brand_color_lock", {}),
    )
    issues.extend(p4b_res.get("issues", []))

    overall_status = "PASS" if len(issues) == 0 else "FAIL"
    report: Dict[str, Any] = {
        "directive_id": "DIR-BUILD-INDEPENDENT-RESIZE-QA-062+065+069",
        "target_image": str(image_path),
        "target_manifest": str(manifest_path),
        "size_key": size_key,
        "layout_mode": layout_mode,
        "status": overall_status,
        "passes": {
            "pass_1_aspect_ratio": p1_res,
            "pass_2_safe_zones": p2_res,
            "pass_3_layout_integrity": p3_res,
            "pass_4a_completeness_alpha": p4a_res,
            "pass_4b_brand_color_lock": p4b_res,
        },
        "issues": issues,
    }
    report["markdown_report"] = generate_qa_compliance_table(report)
    return report


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Independent Multi-Size Resize QA Inspector (DIR-062 + DIR-065 + DIR-069)"
    )
    parser.add_argument("image_path", help="Path to rendered variant PNG")
    parser.add_argument("manifest_path", help="Path to variant layout manifest JSON")
    parser.add_argument(
        "--matrix",
        default=str(DEFAULT_MATRIX_PATH),
        help="Path to config/resize_qa_matrix.json",
    )
    parser.add_argument(
        "--master",
        default=None,
        help="Override path to Golden Master manifest JSON",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Re-raise AssertionError immediately on Pass 1 stretching failure",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="Optional output path to save full structured JSON report",
    )
    parser.add_argument(
        "--md-report",
        default=None,
        help="Optional output path to save Markdown compliance table",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)
    report = run_resize_qa_pipeline(
        image_path=args.image_path,
        manifest_path=args.manifest_path,
        matrix_path=args.matrix,
        master_manifest_path=args.master,
        fail_fast=args.fail_fast,
    )

    if args.json_report:
        jp = _resolve_repo_path(args.json_report)
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.md_report:
        mp = _resolve_repo_path(args.md_report)
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(report["markdown_report"] + "\n", encoding="utf-8")

    print(report["markdown_report"])
    if report["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
