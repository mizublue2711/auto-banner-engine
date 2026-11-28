#!/usr/bin/env python3
"""
MASTER BANNER PREFLIGHT INSPECTOR (`engine/qa_banner_inspector.py`)
Directive: DIR-MASTER-BANNER-PREFLIGHT-022

Kiểm tra thành phẩm Master Banner hoàn thiện trước khi xuất bản hoặc resize
sang 3 biến thể (1200x600, 800x1500, 300x250):
1. Resolution & Dimensions Check: đúng chuẩn 1080x1080px (sai lệch 0px) & dung lượng file
   (hard gate <= 2048 KB, khuyến nghị tối ưu <= 1536 KB).
2. Media Safe Zone Compliance: đối chiếu `config/media_safe_zones_2026.json`
   (pixel border variance scan + kiểm tra bounding box của các phần tử chữ/UI).
3. Mandatory Copy & Elements Audit (fail-closed): kiểm tra đầy đủ text bắt buộc
   và các thành phần 3D decor trong layout manifest JSON.
4. Visual Contrast & Legibility: kiểm tra độ tương phản WCAG 2.1 AA (>= 4.5:1)
   cho khối chữ chính (`GS SHOP 라이브특가`) so với nền.
5. No Broken Assets / Rendering Glitches: phát hiện ảnh lỗi/404/natural_width=0,
   font tiếng Hàn chưa nạp, hoặc ký tự lỗi font (tofu / U+FFFD).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SAFE_ZONES_PATH = ROOT_DIR / "config" / "media_safe_zones_2026.json"
DEFAULT_SPEC_PATH = ROOT_DIR / "specs" / "gsshop_assignment_spec.json"
DEFAULT_REMEDIATION_OUT_PATH = ROOT_DIR / "output" / "TASK_GSSHOP" / "remediation_hints.json"
OCCLUSION_CLEARANCE_BUFFER_PX = 8.0

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1080
HARD_MAX_FILE_SIZE_KB = 2048.0
OPTIMAL_MAX_FILE_SIZE_KB = 1536.0
DEFAULT_PIXEL_SAFE_MARGIN = 40
BORDER_STD_DEV_THRESHOLD = 55.0
WCAG_AA_MIN_CONTRAST = 4.5

REQUIRED_ELEMENTS: List[str] = [
    "MOBILE LIVE",
    "LIVE",
    "단 60분! 할인쿠폰 + 추가혜택이 펑펑",
    "GS SHOP 라이브특가",
    "라이브 혜택 받고 쇼핑하기 >",
    "decor_snowflake",
    "decor_candy_cane",
    "decor_bauble",
    "decor_box_front_rim",
    "decor_box_lid_flying",
]

SAFE_ZONE_TEXT_ROLES = {"logo", "badge", "sub_copy", "subcopy", "headline", "title", "cta", "cta_button", "text"}
OCCLUSION_TEXT_ROLES = {"headline", "main_title", "title", "sub_copy", "subcopy", "badge"}
NON_OCCLUDER_MOTION_ROLES = {
    "static_backdrop",
    "snow_dune_back",
    "snow_bed_ground",
    "snow_drift_front",
    "ambient_snow_drift",
    "ui_header_lock",
    "ui_headline_lock",
    "ui_cta_pulse",
}


def _load_ground_truth_spec(spec_path: Optional[str] = None) -> Dict[str, Any]:
    """Load ground-truth assignment spec from specs/gsshop_assignment_spec.json."""
    path = Path(spec_path) if spec_path else DEFAULT_SPEC_PATH
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _load_safe_margins(
    width: int,
    height: int,
    safe_zones_path: Optional[str] = None,
) -> Dict[str, int]:
    """Load safe margins for `<width>x<height>` from config/media_safe_zones_2026.json."""
    cfg_path = Path(safe_zones_path) if safe_zones_path else DEFAULT_SAFE_ZONES_PATH
    ratio_key = f"{width}x{height}"
    if cfg_path.exists():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            ratio_cfg = data.get("ratios", {}).get(ratio_key)
            if isinstance(ratio_cfg, dict) and isinstance(ratio_cfg.get("safe_margins"), dict):
                sm = ratio_cfg["safe_margins"]
                return {
                    "top": int(sm.get("top", DEFAULT_PIXEL_SAFE_MARGIN)),
                    "bottom": int(sm.get("bottom", DEFAULT_PIXEL_SAFE_MARGIN)),
                    "left": int(sm.get("left", DEFAULT_PIXEL_SAFE_MARGIN)),
                    "right": int(sm.get("right", DEFAULT_PIXEL_SAFE_MARGIN)),
                }
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    return {
        "top": DEFAULT_PIXEL_SAFE_MARGIN,
        "bottom": DEFAULT_PIXEL_SAFE_MARGIN,
        "left": DEFAULT_PIXEL_SAFE_MARGIN,
        "right": DEFAULT_PIXEL_SAFE_MARGIN,
    }


def _parse_color(color: Any) -> Optional[Tuple[int, int, int]]:
    """Parse hex (`#RRGGBB`, `#RGB`), `rgb(r, g, b)`/`rgba(...)`, or 3-element sequence to RGB tuple."""
    if color is None:
        return None
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        try:
            return (int(color[0]), int(color[1]), int(color[2]))
        except (TypeError, ValueError):
            return None
    if isinstance(color, str):
        s = color.strip()
        if s.startswith("#"):
            h = s[1:]
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            if len(h) == 6 and re.fullmatch(r"[0-9a-fA-F]{6}", h):
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
        m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", s, re.IGNORECASE)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    """Compute WCAG 2.1 relative luminance for an sRGB 8-bit color."""
    channels = []
    for c in rgb:
        s = max(0.0, min(1.0, c / 255.0))
        if s <= 0.03928:
            channels.append(s / 12.92)
        else:
            channels.append(((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def compute_wcag_contrast(fg_rgb: Tuple[int, int, int], bg_rgb: Tuple[int, int, int]) -> float:
    """Compute WCAG 2.1 contrast ratio between two RGB colors."""
    l1 = _relative_luminance(fg_rgb)
    l2 = _relative_luminance(bg_rgb)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _sample_local_background_rgb(
    arr: np.ndarray,
    bbox: Dict[str, Any],
    ring_px: int = 8,
) -> Optional[Tuple[int, int, int]]:
    """Sample median RGB of a ring surrounding `bbox` on the rendered banner."""
    h, w, _ = arr.shape
    x = int(round(float(bbox.get("x", 0))))
    y = int(round(float(bbox.get("y", 0))))
    bw = int(round(float(bbox.get("width", 0))))
    bh = int(round(float(bbox.get("height", 0))))
    if bw <= 0 or bh <= 0:
        return None

    x1 = max(0, x - ring_px)
    y1 = max(0, y - ring_px)
    x2 = min(w, x + bw + ring_px)
    y2 = min(h, y + bh + ring_px)
    ix1, iy1 = max(0, x), max(0, y)
    ix2, iy2 = min(w, x + bw), min(h, y + bh)

    samples: List[np.ndarray] = []
    if iy1 > y1:
        samples.append(arr[y1:iy1, x1:x2].reshape(-1, 3))
    if y2 > iy2:
        samples.append(arr[iy2:y2, x1:x2].reshape(-1, 3))
    if ix1 > x1:
        samples.append(arr[iy1:iy2, x1:ix1].reshape(-1, 3))
    if x2 > ix2:
        samples.append(arr[iy1:iy2, ix2:x2].reshape(-1, 3))

    if not samples:
        patch = arr[iy1:iy2, ix1:ix2].reshape(-1, 3)
        if patch.size == 0:
            return None
        med = np.median(patch, axis=0)
    else:
        ring = np.concatenate(samples, axis=0)
        if ring.size == 0:
            return None
        med = np.median(ring, axis=0)

    return (int(round(med[0])), int(round(med[1])), int(round(med[2])))


def _audit_safe_zone_bboxes(
    meta: Dict[str, Any],
    width: int,
    height: int,
    safe_margins: Dict[str, int],
) -> List[str]:
    """Verify all text/UI element bounding boxes stay strictly within safe margins."""
    issues: List[str] = []
    elements = meta.get("elements")
    if not isinstance(elements, list):
        return issues

    min_x = safe_margins["left"]
    min_y = safe_margins["top"]
    max_x = width - safe_margins["right"]
    max_y = height - safe_margins["bottom"]

    for elem in elements:
        if not isinstance(elem, dict):
            continue
        role = str(elem.get("role", elem.get("type", ""))).lower()
        has_text = bool(str(elem.get("text", "")).strip())
        if role not in SAFE_ZONE_TEXT_ROLES and not has_text:
            continue

        bbox = elem.get("bbox")
        if not isinstance(bbox, dict):
            continue

        x = float(bbox.get("x", 0))
        y = float(bbox.get("y", 0))
        bw = float(bbox.get("width", 0))
        bh = float(bbox.get("height", 0))
        if bw <= 0 or bh <= 0:
            continue

        label = elem.get("id") or elem.get("role") or str(elem.get("text", ""))[:24]
        violations = []
        if x < min_x:
            violations.append(f"left={x:.1f}px < {min_x}px")
        if y < min_y:
            violations.append(f"top={y:.1f}px < {min_y}px")
        if x + bw > max_x:
            violations.append(f"right={x + bw:.1f}px > {max_x}px")
        if y + bh > max_y:
            violations.append(f"bottom={y + bh:.1f}px > {max_y}px")

        if violations:
            issues.append(
                f"Safe Zone Intrusion ({label}): {', '.join(violations)}"
            )

    return issues


def _audit_headline_contrast(
    arr: np.ndarray,
    meta: Dict[str, Any],
) -> Tuple[Optional[float], List[str]]:
    """Verify WCAG AA (>= 4.5:1) contrast for the main title (`GS SHOP 라이브특가`)."""
    issues: List[str] = []
    elements = meta.get("elements")
    if not isinstance(elements, list):
        return None, issues

    headline_elem = None
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        role = str(elem.get("role", "")).lower()
        text = str(elem.get("text", ""))
        if role in {"headline", "main_title"} or "GS SHOP 라이브특가" in text:
            headline_elem = elem
            break

    if headline_elem is None:
        return None, issues

    fg_rgb = _parse_color(headline_elem.get("fg_hex") or headline_elem.get("fg_rgb") or headline_elem.get("color"))
    if fg_rgb is None:
        return None, issues

    bg_rgb = _parse_color(headline_elem.get("bg_hex") or headline_elem.get("bg_rgb") or headline_elem.get("background_color"))
    if bg_rgb is None and isinstance(headline_elem.get("bbox"), dict):
        bg_rgb = _sample_local_background_rgb(arr, headline_elem["bbox"])

    if bg_rgb is None:
        return None, issues

    ratio = compute_wcag_contrast(fg_rgb, bg_rgb)
    if ratio < WCAG_AA_MIN_CONTRAST:
        issues.append(
            f"WCAG Contrast Failure (Headline): ratio={ratio:.2f}:1 < {WCAG_AA_MIN_CONTRAST}:1 "
            f"(fg={fg_rgb}, bg={bg_rgb})"
        )
    return round(ratio, 2), issues


def _audit_assets_and_fonts(meta: Dict[str, Any], meta_content: str) -> List[str]:
    """Detect broken/missing assets, unloaded fonts, and tofu replacement glyphs."""
    issues: List[str] = []

    # 1. Broken / missing images
    assets = meta.get("assets")
    if isinstance(assets, list):
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_id = asset.get("id") or asset.get("path") or asset.get("src") or "unknown_asset"
            if asset.get("loaded") is False:
                issues.append(f"Broken Asset: '{asset_id}' failed to load (loaded=False)")
            http_status = asset.get("http_status")
            if isinstance(http_status, int) and http_status >= 400:
                issues.append(f"Broken Asset: '{asset_id}' returned HTTP {http_status}")
            nat_w = asset.get("natural_width")
            if isinstance(nat_w, (int, float)) and nat_w <= 0:
                issues.append(f"Broken Asset: '{asset_id}' has natural_width={nat_w}")
            asset_path = asset.get("path")
            if isinstance(asset_path, str) and asset_path.strip() and not asset_path.startswith(("http://", "https://", "data:")):
                p = Path(asset_path)
                if not p.is_absolute():
                    p = ROOT_DIR / p
                if not p.exists():
                    issues.append(f"Missing Asset File: '{asset_id}' not found at {asset_path}")

    # 1b. Layer asset_path integrity (DIR-REFACTOR-ASSETS-AND-LAYERS-052)
    layers = meta.get("layers")
    if isinstance(layers, list):
        for layer in layers:
            if not isinstance(layer, dict):
                continue
            layer_path = layer.get("asset_path")
            if isinstance(layer_path, str) and layer_path.strip() and not layer_path.startswith(("http://", "https://", "data:")):
                p = Path(layer_path)
                if not p.is_absolute():
                    p = ROOT_DIR / p
                if not p.exists():
                    layer_id = layer.get("layer_id") or layer.get("asset_id") or "unknown_layer"
                    issues.append(f"Missing Layer Asset File: '{layer_id}' not found at {layer_path}")

    # 2. Font loading integrity
    fonts = meta.get("fonts")
    if isinstance(fonts, list):
        if len(fonts) == 0:
            issues.append("Font Glitch: No web fonts loaded in manifest")
        else:
            unloaded = [
                str(f.get("family", "unknown"))
                for f in fonts
                if isinstance(f, dict) and str(f.get("status", "loaded")).lower() != "loaded"
            ]
            if unloaded:
                issues.append(f"Font Load Failure: {', '.join(unloaded)}")

    # 3. Tofu / replacement character check
    glyph_check = meta.get("glyph_check")
    if isinstance(glyph_check, dict) and glyph_check.get("tofu_detected") is True:
        issues.append("Font Glitch: Tofu / missing Korean glyph detected during render")
    if "\ufffd" in meta_content:
        issues.append("Font Glitch: Unicode replacement character (U+FFFD) found in manifest text")

    return issues


def assert_safe_margins(
    meta: Dict[str, Any],
    width: int,
    height: int,
    safe_margins: Dict[str, int],
) -> List[str]:
    """Verify all text/UI element bounding boxes stay strictly within safe margins."""
    return _audit_safe_zone_bboxes(meta, width, height, safe_margins)


def assert_logo_top_left(
    meta: Dict[str, Any],
    spec: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Kiểm tra bounding box của logo bắt buộc phải nằm ở góc trên bên trái (left <= 60px, top <= 60px)."""
    logo_spec = (spec or {}).get("required_elements", {}).get("logo", {})
    max_left = float(logo_spec.get("max_left_px", 60))
    max_top = float(logo_spec.get("max_top_px", 60))

    elements = meta.get("elements")
    if not isinstance(elements, list):
        return ["Logo Top-Left Failure: 'elements' array missing in layout manifest"]

    logo_elem = None
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        role = str(elem.get("role", "")).lower()
        elem_id = str(elem.get("id", "")).lower()
        if role == "logo" or "logo" in elem_id:
            logo_elem = elem
            break

    if logo_elem is None:
        return ["Logo Top-Left Failure: No logo element found in layout manifest"]

    bbox = logo_elem.get("bbox")
    if not isinstance(bbox, dict):
        return ["Logo Top-Left Failure: Logo element has no valid bbox"]

    left = float(bbox.get("x", 0))
    top = float(bbox.get("y", 0))
    violations = []
    if left > max_left:
        violations.append(f"left={left:.1f}px > {max_left:.0f}px")
    if top > max_top:
        violations.append(f"top={top:.1f}px > {max_top:.0f}px")

    if violations:
        return [
            f"Logo Top-Left Violation ({logo_elem.get('id', 'logo')}): "
            f"{', '.join(violations)} (Ground-truth rule: 로고 좌측 상단 고정)"
        ]
    return []


def assert_exact_copy(
    meta: Dict[str, Any],
    meta_content: str,
    spec: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Xác nhận đầy đủ 100% các chuỗi copy bắt buộc theo đề bài gốc."""
    required_strings = (spec or {}).get(
        "mandatory_exact_copy",
        [
            "MOBILE LIVE",
            "LIVE",
            "단 60분! 할인쿠폰 + 추가혜택이 펑펑",
            "GS SHOP",
            "라이브특가",
            "라이브 혜택 받고 쇼핑하기 >",
        ],
    )

    # Collect all text fields from meta.texts and meta.elements for strict check
    corpus_parts: List[str] = []
    texts_obj = meta.get("texts")
    if isinstance(texts_obj, dict):
        corpus_parts.extend(str(v) for v in texts_obj.values())
    elements = meta.get("elements")
    if isinstance(elements, list):
        for elem in elements:
            if isinstance(elem, dict) and elem.get("text"):
                corpus_parts.append(str(elem["text"]))
    corpus = "\n".join(corpus_parts) if corpus_parts else meta_content

    missing = [s for s in required_strings if s not in corpus]
    if missing:
        return [f"Exact Copy Violation: Missing mandatory copy -> {', '.join(repr(m) for m in missing)}"]
    return []


def _bbox_intersection_area(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    ax1 = float(a.get("x", 0))
    ay1 = float(a.get("y", 0))
    ax2 = ax1 + max(0.0, float(a.get("width", 0)))
    ay2 = ay1 + max(0.0, float(a.get("height", 0)))

    bx1 = float(b.get("x", 0))
    by1 = float(b.get("y", 0))
    bx2 = bx1 + max(0.0, float(b.get("width", 0)))
    by2 = by1 + max(0.0, float(b.get("height", 0)))

    ix = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0.0, min(ay2, by2) - max(ay1, by1))
    return ix * iy


def _effective_layer_bbox(layer: Dict[str, Any]) -> Dict[str, float]:
    """
    Return the visual bounding box of a layer. For rotated layers with a local RGBA
    asset_path, trims empty transparent rotated-corner overhang so occlusion checks
    measure real painted pixels rather than empty CSS corner padding.
    """
    bbox = layer.get("bbox", {})
    x = float(bbox.get("x", 0.0))
    y = float(bbox.get("y", 0.0))
    w = float(bbox.get("width", 0.0))
    h = float(bbox.get("height", 0.0))
    rot = float(layer.get("rotation_deg", 0.0) or 0.0)
    asset_path = layer.get("asset_path")

    if not isinstance(asset_path, str) or not asset_path.strip():
        return {"x": x, "y": y, "width": w, "height": h}

    p = Path(asset_path)
    if not p.is_absolute():
        p = ROOT_DIR / p
    if not p.exists():
        return {"x": x, "y": y, "width": w, "height": h}

    try:
        with Image.open(p) as im:
            rgba = im.convert("RGBA")
            if layer.get("flip_x"):
                rgba = rgba.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            rot_im = rgba.rotate(-rot, resample=Image.Resampling.BILINEAR, expand=True) if abs(rot) >= 1e-3 else rgba
            ab = rot_im.getbbox()
            if ab is None:
                return {"x": x, "y": y, "width": w, "height": h}
            rw, rh = rot_im.size
            return {
                "x": x + (ab[0] / rw) * w,
                "y": y + (ab[1] / rh) * h,
                "width": ((ab[2] - ab[0]) / rw) * w,
                "height": ((ab[3] - ab[1]) / rh) * h,
            }
    except Exception:
        return {"x": x, "y": y, "width": w, "height": h}


def assert_logo_capsule_clearance(meta: Dict[str, Any]) -> List[str]:
    """DIR-MASTER-SPATIAL-COORDINATES-056: Verify zero 2D collision between Logo and Header Capsule."""
    elements = meta.get("elements") if isinstance(meta.get("elements"), list) else []
    layers = meta.get("layers") if isinstance(meta.get("layers"), list) else []

    logo_elem = next(
        (
            e for e in elements
            if isinstance(e, dict)
            and isinstance(e.get("bbox"), dict)
            and (str(e.get("role", "")).lower() == "logo" or str(e.get("id", "")).lower() == "ui_logo")
        ),
        None,
    )
    capsule_layer = next(
        (
            lyr for lyr in layers
            if isinstance(lyr, dict)
            and isinstance(lyr.get("bbox"), dict)
            and (
                str(lyr.get("layer_id", "")) == "z13_header_frosted_glass_capsule"
                or str(lyr.get("motion_role", "")) == "ui_glass_capsule"
            )
        ),
        None,
    )
    if logo_elem is None or capsule_layer is None:
        return []

    overlap = _bbox_intersection_area(logo_elem["bbox"], capsule_layer["bbox"])
    if overlap > 0.0:
        return [
            f"Header Anchor Collision: Logo (#ui_logo) overlaps Frosted Glass Capsule "
            f"(overlap_area={overlap:.1f} px² > 0)"
        ]
    return []


def assert_zero_text_occlusion(
    meta: Dict[str, Any],
    spec: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Kiểm tra bounding box của cụm Headline & Sub-copy KHÔNG bị Hero/Decor item nào đè lên (Overlap Area = 0)."""
    issues: List[str] = []
    elements = meta.get("elements")
    layers = meta.get("layers")
    if not isinstance(elements, list) or not isinstance(layers, list):
        return issues

    text_boxes: List[Tuple[str, Dict[str, Any]]] = []
    for elem in elements:
        if not isinstance(elem, dict):
            continue
        role = str(elem.get("role", "")).lower()
        if role in OCCLUSION_TEXT_ROLES and isinstance(elem.get("bbox"), dict):
            label = str(elem.get("id") or role)
            text_boxes.append((label, elem["bbox"]))

    for layer in layers:
        if not isinstance(layer, dict):
            continue
        motion_role = str(layer.get("motion_role", "")).lower()
        layer_name = str(layer.get("layer_name", "")).upper()
        if (
            motion_role in NON_OCCLUDER_MOTION_ROLES
            or layer_name.startswith("Z13_UI")
            or layer_name.startswith("Z1_BG")
            or "SNOW" in layer_name
            or "SPARKLE" in str(layer.get("layer_id", "")).upper()
        ):
            continue
        layer_bbox = layer.get("bbox")
        if not isinstance(layer_bbox, dict):
            continue

        eff_bbox = _effective_layer_bbox(layer)
        layer_id = str(layer.get("layer_id") or layer.get("asset_id") or "unknown_layer")
        for text_label, text_bbox in text_boxes:
            overlap_area = _bbox_intersection_area(text_bbox, eff_bbox)
            if overlap_area > 0.0:
                # For rotated layers with a local RGBA asset, verify true painted-pixel overlap
                rot = float(layer.get("rotation_deg", 0.0) or 0.0)
                asset_path = layer.get("asset_path")
                if abs(rot) >= 1e-3 and isinstance(asset_path, str) and asset_path.strip():
                    p = Path(asset_path)
                    if not p.is_absolute():
                        p = ROOT_DIR / p
                    if p.exists():
                        try:
                            with Image.open(p) as im:
                                rgba = im.convert("RGBA")
                                if layer.get("flip_x"):
                                    rgba = rgba.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                                rot_im = rgba.rotate(-rot, resample=Image.Resampling.BILINEAR, expand=True)
                                lb = layer_bbox
                                lw = max(1, int(round(float(lb.get("width", 1)))))
                                lh = max(1, int(round(float(lb.get("height", 1)))))
                                lx = int(round(float(lb.get("x", 0))))
                                ly = int(round(float(lb.get("y", 0))))
                                scaled_a = np.array(rot_im.resize((lw, lh), Image.Resampling.BILINEAR).split()[3]) > 30
                                tx1 = max(0, int(round(float(text_bbox.get("x", 0)))) - lx)
                                ty1 = max(0, int(round(float(text_bbox.get("y", 0)))) - ly)
                                tx2 = min(lw, int(round(float(text_bbox.get("x", 0)) + float(text_bbox.get("width", 0)))) - lx)
                                ty2 = min(lh, int(round(float(text_bbox.get("y", 0)) + float(text_bbox.get("height", 0)))) - ly)
                                if tx2 <= tx1 or ty2 <= ty1 or not np.any(scaled_a[ty1:ty2, tx1:tx2]):
                                    continue
                        except Exception:
                            pass
                issues.append(
                    f"Text Occlusion Violation: '{layer_id}' overlaps '{text_label}' "
                    f"(overlap_area={overlap_area:.1f} px² > 0)"
                )
    return issues


def assert_vertical_hierarchy_spacing(
    meta: Dict[str, Any],
) -> Tuple[Dict[str, float], List[str]]:
    """
    DIR-REBALANCE-VERTICAL-RHYTHM-048:
    Kiểm định nhịp điệu khoảng cách dọc giữa Logo, Thẻ Kính Mờ (Capsule),
    Khối Chữ 3D (Headline) và dàn sản phẩm/hộp quà bên dưới.
    """
    issues: List[str] = []
    spacing_metrics: Dict[str, float] = {}
    elements = meta.get("elements") if isinstance(meta.get("elements"), list) else []
    layers = meta.get("layers") if isinstance(meta.get("layers"), list) else []

    def _rect(bbox: Dict[str, Any]) -> Dict[str, float]:
        top = float(bbox.get("y", 0.0))
        height = max(0.0, float(bbox.get("height", 0.0)))
        return {"top": top, "bottom": top + height}

    # Locate Logo bbox
    logo_elem = next(
        (
            e for e in elements
            if isinstance(e, dict)
            and isinstance(e.get("bbox"), dict)
            and (str(e.get("role", "")).lower() == "logo" or str(e.get("id", "")).lower() == "ui_logo")
        ),
        None,
    )
    if logo_elem is None:
        issues.append("Vertical Rhythm Failure: Logo element (#ui_logo) missing in manifest")
        return spacing_metrics, issues
    logo_bbox = _rect(logo_elem["bbox"])
    spacing_metrics["logo_top"] = round(logo_bbox["top"], 1)

    # 1. Đo khoảng cách an toàn từ mép trên canvas đến Logo
    if logo_bbox["top"] < 40.0:
        issues.append(f"Logo quá sát mép trên ({logo_bbox['top']:.1f}px < 40px)")

    # Locate Frosted Glass Capsule bbox (prefer decoupled capsule layer; fallback to badge+sub_copy union)
    capsule_layer = next(
        (
            lyr for lyr in layers
            if isinstance(lyr, dict)
            and isinstance(lyr.get("bbox"), dict)
            and (
                str(lyr.get("layer_id", "")) == "z13_header_frosted_glass_capsule"
                or str(lyr.get("motion_role", "")) == "ui_glass_capsule"
            )
        ),
        None,
    )
    capsule_bbox: Optional[Dict[str, float]] = None
    if capsule_layer is not None:
        capsule_bbox = _rect(capsule_layer["bbox"])
    else:
        sub_rects = [
            _rect(e["bbox"])
            for e in elements
            if isinstance(e, dict)
            and isinstance(e.get("bbox"), dict)
            and str(e.get("role", "")).lower() in {"badge", "sub_copy", "subcopy"}
        ]
        if sub_rects:
            capsule_bbox = {
                "top": min(r["top"] for r in sub_rects),
                "bottom": max(r["bottom"] for r in sub_rects),
            }

    # Locate 3D Headline bbox
    headline_elem = next(
        (
            e for e in elements
            if isinstance(e, dict)
            and isinstance(e.get("bbox"), dict)
            and (
                str(e.get("role", "")).lower() in {"headline", "main_title"}
                or str(e.get("id", "")).lower() == "ui_headline"
            )
        ),
        None,
    )

    if capsule_bbox is None or headline_elem is None:
        issues.append("Vertical Rhythm Failure: Capsule or Headline bbox missing in manifest")
        return spacing_metrics, issues

    headline_bbox = _rect(headline_elem["bbox"])
    spacing_metrics["capsule_top"] = round(capsule_bbox["top"], 1)
    spacing_metrics["capsule_bottom"] = round(capsule_bbox["bottom"], 1)
    spacing_metrics["headline_top"] = round(headline_bbox["top"], 1)
    spacing_metrics["headline_bottom"] = round(headline_bbox["bottom"], 1)

    # 2. Đo khoảng dãn cách dòng giữa Thẻ Kính Mờ (Capsule) và Khối Chữ 3D (Headline)
    capsule_to_headline_gap = headline_bbox["top"] - capsule_bbox["bottom"]
    spacing_metrics["capsule_to_headline_gap"] = round(capsule_to_headline_gap, 1)
    if not (18.0 <= capsule_to_headline_gap <= 36.0):
        issues.append(
            f"LỖI KHOẢNG CÁCH DÒNG: Khoảng cách giữa Thẻ Kính Mờ và Headline là "
            f"{capsule_to_headline_gap:.1f}px. Quy chuẩn yêu cầu khoảng dãn cách phải nằm "
            f"trong khoảng [18px, 36px] để đảm bảo nhịp điệu thị giác đều đặn."
        )

    # 3. Đo khoảng dãn tối thiểu giữa Khối Chữ 3D và dàn sản phẩm/hộp quà trung tâm bên dưới
    hl_x1 = float(headline_elem["bbox"].get("x", 0.0))
    hl_x2 = hl_x1 + max(0.0, float(headline_elem["bbox"].get("width", 0.0)))
    burst_items = []
    for lyr in layers:
        if not isinstance(lyr, dict) or not isinstance(lyr.get("bbox"), dict):
            continue
        lname = str(lyr.get("layer_name", "")).upper()
        lid = str(lyr.get("layer_id", ""))
        if lname in {"Z8_BURST_HEROES", "Z9_BOX_LID_FLYING"} or lid.startswith("z10_flying_"):
            eff = _effective_layer_bbox(lyr)
            eff_x1 = float(eff.get("x", 0.0))
            eff_x2 = eff_x1 + max(0.0, float(eff.get("width", 0.0)))
            # Only enforce vertical stack gap for items whose horizontal footprint overlaps the central headline column
            if eff_x2 > hl_x1 + 60.0 and eff_x1 < hl_x2 - 60.0:
                burst_items.append(_rect(eff))
    if burst_items:
        min_hero_gap = min(item["top"] - headline_bbox["bottom"] for item in burst_items)
        spacing_metrics["min_hero_gap"] = round(min_hero_gap, 1)
        if min_hero_gap < 20.0:
            issues.append(
                f"Khoảng cách giữa Headline và sản phẩm quá hẹp ({min_hero_gap:.1f}px < 20px)"
            )

    return spacing_metrics, issues


def assert_mandatory_products(
    meta: Dict[str, Any],
    meta_content: str,
    spec: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Xác nhận có đủ 4 loại sản phẩm bắt buộc (knit, puffer, tangerine, tissue) trong manifest."""
    product_keys: Dict[str, List[str]] = (spec or {}).get("required_elements", {}).get(
        "hero_product_keys",
        {
            "knit": ["knit", "sweater", "니트"],
            "puffer": ["puffer", "padding", "패딩"],
            "tangerine": ["tangerine", "귤"],
            "tissue": ["tissue", "toilet_paper", "휴지"],
        },
    )
    haystack = meta_content.lower()
    missing_products = [
        prod
        for prod, aliases in product_keys.items()
        if not any(alias.lower() in haystack for alias in aliases)
    ]
    if missing_products:
        return [f"Mandatory Products Missing: {', '.join(missing_products)}"]
    return []


def _extract_layer_css_from_template(
    template_path: Optional[Path],
    layer_id: str,
) -> Tuple[str, Optional[float], Optional[float]]:
    """Resolve primary CSS class selector and current `top`/`left` px values from HTML template."""
    default_selector = "." + layer_id.replace("_", "-")
    if template_path is None or not template_path.exists():
        return default_selector, None, None

    try:
        html = template_path.read_text(encoding="utf-8")
    except OSError:
        return default_selector, None, None

    selector = default_selector
    tag_match = re.search(
        r"<[^>]*\bdata-layer-id=[\"']" + re.escape(layer_id) + r"[\"'][^>]*>",
        html,
        re.IGNORECASE,
    )
    if tag_match:
        cls_match = re.search(r"\bclass=[\"']([^\"']+)[\"']", tag_match.group(0), re.IGNORECASE)
        if cls_match:
            classes = [c for c in cls_match.group(1).split() if c != "layer"]
            if classes:
                selector = f".{classes[0]}"

    style_match = re.search(r"<style[^>]*>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    if not style_match:
        return selector, None, None

    style_css = style_match.group(1)
    rule_match = re.search(
        r"(?<![\w-])" + re.escape(selector) + r"\s*\{([^}]*)\}",
        style_css,
        re.MULTILINE,
    )
    if not rule_match:
        return selector, None, None

    body = rule_match.group(1)
    top_m = re.search(r"^\s*top\s*:\s*(-?\d+(?:\.\d+)?)px\s*;", body, re.MULTILINE)
    left_m = re.search(r"^\s*left\s*:\s*(-?\d+(?:\.\d+)?)px\s*;", body, re.MULTILINE)
    cur_top = float(top_m.group(1)) if top_m else None
    cur_left = float(left_m.group(1)) if left_m else None
    return selector, cur_top, cur_left


def build_remediation_hints(
    meta: Dict[str, Any],
    assertions: Dict[str, Dict[str, Any]],
    width: int,
    height: int,
    safe_margins: Dict[str, int],
    spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Prescriptive Remediation Engine (DIR-UPGRADE-PRESCRIPTIVE-INSPECTOR-037):
    Computes exact CSS property updates needed to resolve failing layout assertions.
    """
    template_rel = str(meta.get("template") or "templates/master_1080x1080.html")
    template_path = Path(template_rel)
    if not template_path.is_absolute():
        template_path = ROOT_DIR / template_path

    hints: List[Dict[str, Any]] = []
    elements = meta.get("elements") if isinstance(meta.get("elements"), list) else []
    layers = meta.get("layers") if isinstance(meta.get("layers"), list) else []

    # 1. Prescriptive fix for assert_logo_top_left
    logo_assertion = assertions.get("assert_logo_top_left", {})
    if logo_assertion.get("status") == "FAIL":
        logo_elem = next(
            (
                e
                for e in elements
                if isinstance(e, dict)
                and (str(e.get("role", "")).lower() == "logo" or "logo" in str(e.get("id", "")).lower())
            ),
            None,
        )
        cur_bbox = logo_elem.get("bbox", {}) if isinstance(logo_elem, dict) else {}
        target_top = max(45, int(safe_margins.get("top", 40)))
        target_left = max(50, int(safe_margins.get("left", 40)))

        # Check if parent header layer (.z13-logo-live-group) has a non-zero offset
        companion_patches: List[Dict[str, Any]] = []
        header_layer = next(
            (
                lyr
                for lyr in layers
                if isinstance(lyr, dict) and str(lyr.get("layer_id", "")) == "z13_logo_live_group"
            ),
            None,
        )
        if isinstance(header_layer, dict):
            hb = header_layer.get("bbox", {})
            if float(hb.get("x", 0)) != 0.0 or float(hb.get("y", 0)) != 0.0:
                companion_patches.append(
                    {
                        "target_selector": ".z13-logo-live-group",
                        "reason": (
                            "Normalize header layer container origin to (0, 0) with padding-top so "
                            "absolute top/left on #ui_logo maps 1:1 to canvas coordinates while "
                            "preserving LIVE badge & sub-copy vertical position."
                        ),
                        "recommended_css": {
                            "top": "0px",
                            "left": "0px",
                            "width": f"{width}px",
                            "padding-top": f"{int(round(float(hb.get('y', target_top))))}px",
                        },
                    }
                )

        rec_css = {
            "position": "absolute",
            "top": f"{target_top}px",
            "left": f"{target_left}px",
        }
        hints.append(
            {
                "hint_id": "fix_logo_top_left",
                "assertion": "assert_logo_top_left",
                "element_id": logo_elem.get("id", "ui_logo") if isinstance(logo_elem, dict) else "ui_logo",
                "target_selector": ".mobile-live-logo-wrap",
                "fallback_selector": "#ui_logo",
                "issue": "; ".join(logo_assertion.get("issues", [])),
                "current_bbox": cur_bbox,
                "recommended_css": rec_css,
                "css_declaration": f"position: absolute; top: {target_top}px; left: {target_left}px;",
                "action_summary": (
                    f"Anchor logo to top-left safe zone via position: absolute; "
                    f"top: {target_top}px; left: {target_left}px;"
                ),
                "companion_patches": companion_patches,
            }
        )

    # 2. Prescriptive fix for assert_zero_text_occlusion
    occlusion_assertion = assertions.get("assert_zero_text_occlusion", {})
    if occlusion_assertion.get("status") == "FAIL":
        text_boxes: List[Tuple[str, Dict[str, Any]]] = []
        for elem in elements:
            if not isinstance(elem, dict):
                continue
            role = str(elem.get("role", "")).lower()
            if role in OCCLUSION_TEXT_ROLES and isinstance(elem.get("bbox"), dict):
                text_boxes.append((str(elem.get("id") or role), elem["bbox"]))

        for layer in layers:
            if not isinstance(layer, dict):
                continue
            motion_role = str(layer.get("motion_role", "")).lower()
            layer_name = str(layer.get("layer_name", "")).upper()
            if (
                motion_role in NON_OCCLUDER_MOTION_ROLES
                or layer_name.startswith("Z13_UI")
                or layer_name.startswith("Z1_BG")
                or "SNOW" in layer_name
            ):
                continue
            layer_bbox = layer.get("bbox")
            if not isinstance(layer_bbox, dict):
                continue

            layer_id = str(layer.get("layer_id") or layer.get("asset_id") or "unknown_layer")
            collisions: List[Dict[str, Any]] = []
            max_required_text_bottom = 0.0

            for text_label, text_bbox in text_boxes:
                overlap_area = _bbox_intersection_area(text_bbox, layer_bbox)
                if overlap_area > 0.0:
                    text_bottom_y = float(text_bbox.get("y", 0)) + float(text_bbox.get("height", 0))
                    obj_top_y = float(layer_bbox.get("y", 0))
                    penetration_y = round(text_bottom_y - obj_top_y, 1)
                    max_required_text_bottom = max(max_required_text_bottom, text_bottom_y)
                    collisions.append(
                        {
                            "occluded_text_id": text_label,
                            "text_bbox": text_bbox,
                            "text_bottom_y": round(text_bottom_y, 1),
                            "overlap_area_px2": round(overlap_area, 1),
                            "vertical_penetration_px": penetration_y,
                        }
                    )

            if collisions:
                obj_top_y = float(layer_bbox.get("y", 0))
                raw_penetration = max_required_text_bottom - obj_top_y
                delta_y_px = int(math.ceil(raw_penetration + OCCLUSION_CLEARANCE_BUFFER_PX))
                selector, cur_css_top, _ = _extract_layer_css_from_template(template_path, layer_id)

                current_css: Dict[str, str] = {}
                if cur_css_top is not None:
                    current_css["top"] = f"{cur_css_top:g}px"
                    new_top_px = int(round(cur_css_top + delta_y_px))
                else:
                    new_top_px = int(math.ceil(obj_top_y + delta_y_px))

                rec_css = {"top": f"{new_top_px}px"}
                occluded_ids = ", ".join(c["occluded_text_id"] for c in collisions)
                from_str = f"{current_css['top']} -> " if "top" in current_css else ""

                hints.append(
                    {
                        "hint_id": f"fix_occlusion_{layer_id}",
                        "assertion": "assert_zero_text_occlusion",
                        "layer_id": layer_id,
                        "occluded_elements": occluded_ids,
                        "target_selector": selector,
                        "fallback_selector": f'[data-layer-id="{layer_id}"]',
                        "current_bbox": layer_bbox,
                        "collisions": collisions,
                        "vertical_penetration_px": round(raw_penetration, 1),
                        "clearance_buffer_px": OCCLUSION_CLEARANCE_BUFFER_PX,
                        "delta_y_px": f"+{delta_y_px}px",
                        "delta_y_numeric": delta_y_px,
                        "current_css": current_css,
                        "recommended_css": rec_css,
                        "css_declaration": f"top: {new_top_px}px;",
                        "action_summary": (
                            f"Lower Y-axis (top) by +{delta_y_px}px ({from_str}{new_top_px}px) "
                            f"to clear {occluded_ids} bottom (y={max_required_text_bottom:.1f}px) "
                            f"with {OCCLUSION_CLEARANCE_BUFFER_PX:g}px buffer."
                        ),
                    }
                )

    # 3. Prescriptive fix for assert_safe_margins (if any UI element intrudes border safe zone)
    safe_assertion = assertions.get("assert_safe_margins", {})
    if safe_assertion.get("status") == "FAIL":
        min_x = float(safe_margins["left"])
        min_y = float(safe_margins["top"])
        max_x = float(width - safe_margins["right"])
        max_y = float(height - safe_margins["bottom"])

        for elem in elements:
            if not isinstance(elem, dict) or not isinstance(elem.get("bbox"), dict):
                continue
            role = str(elem.get("role", elem.get("type", ""))).lower()
            has_text = bool(str(elem.get("text", "")).strip())
            if role not in SAFE_ZONE_TEXT_ROLES and not has_text:
                continue
            bbox = elem["bbox"]
            x, y = float(bbox.get("x", 0)), float(bbox.get("y", 0))
            bw, bh = float(bbox.get("width", 0)), float(bbox.get("height", 0))
            if bw <= 0 or bh <= 0:
                continue

            rec_props: Dict[str, str] = {}
            if x < min_x:
                rec_props["left"] = f"{int(math.ceil(min_x))}px"
            elif x + bw > max_x:
                rec_props["left"] = f"{int(math.floor(max_x - bw))}px"
            if y < min_y:
                rec_props["top"] = f"{int(math.ceil(min_y))}px"
            elif y + bh > max_y:
                rec_props["top"] = f"{int(math.floor(max_y - bh))}px"

            if rec_props:
                elem_id = str(elem.get("id") or role or "ui_elem")
                decl = "; ".join(f"{k}: {v}" for k, v in rec_props.items()) + ";"
                hints.append(
                    {
                        "hint_id": f"fix_safe_margin_{elem_id}",
                        "assertion": "assert_safe_margins",
                        "element_id": elem_id,
                        "target_selector": f"#{elem_id}",
                        "current_bbox": bbox,
                        "recommended_css": rec_props,
                        "css_declaration": decl,
                        "action_summary": f"Shift #{elem_id} inside {safe_margins}px safe margins ({decl})",
                    }
                )

    return {
        "directive_id": "DIR-UPGRADE-PRESCRIPTIVE-INSPECTOR-037",
        "banner_id": meta.get("banner_id", "gsshop_master_1080x1080"),
        "template_path": template_rel,
        "status": "PASS" if len(hints) == 0 else "FAIL",
        "total_hints": len(hints),
        "hints": hints,
    }


def audit_master_banner(
    image_path: str,
    layout_meta_path: Optional[str] = None,
    safe_zones_path: Optional[str] = None,
    spec_path: Optional[str] = None,
    require_meta: bool = True,
    remediation_out_path: Optional[str] = None,
) -> Dict[str, Any]:
    if not os.path.exists(image_path):
        return {
            "banner_file": os.path.basename(image_path),
            "status": "FAIL",
            "reason": f"File not found: {image_path}",
            "metrics": {},
            "warnings": [],
            "issues": [f"File not found: {image_path}"],
        }

    with Image.open(image_path) as img:
        w, h = img.size
        img_format = img.format
        arr = np.array(img.convert("RGB"))

    file_size_kb = os.path.getsize(image_path) / 1024.0
    issues: List[str] = []
    warnings: List[str] = []

    # 1. Resolution & Dimensions + File Size Check
    if (w, h) != (TARGET_WIDTH, TARGET_HEIGHT):
        issues.append(f"Dimension Mismatch: Expected {TARGET_WIDTH}x{TARGET_HEIGHT}, got {w}x{h}px")

    if file_size_kb > HARD_MAX_FILE_SIZE_KB:
        issues.append(
            f"File size too large: {file_size_kb:.1f} KB (Target <= {HARD_MAX_FILE_SIZE_KB:.0f} KB)"
        )
    elif file_size_kb > OPTIMAL_MAX_FILE_SIZE_KB:
        warnings.append(
            f"File size optimization advisory: {file_size_kb:.1f} KB > optimal {OPTIMAL_MAX_FILE_SIZE_KB:.0f} KB (1.5 MB)"
        )

    # 2. Media Safe Zone Compliance (Pixel Border Variance Scan)
    safe_margins = _load_safe_margins(w, h, safe_zones_path)
    pixel_margin = min(DEFAULT_PIXEL_SAFE_MARGIN, h // 4, w // 4)
    margins = [
        ("Top", arr[:pixel_margin, :]),
        ("Bottom", arr[-pixel_margin:, :]),
        ("Left", arr[:, :pixel_margin]),
        ("Right", arr[:, -pixel_margin:]),
    ]
    border_std_devs: Dict[str, float] = {}
    for edge_name, strip in margins:
        std_dev = float(np.std(strip))
        border_std_devs[edge_name.lower()] = round(std_dev, 1)
        if std_dev > BORDER_STD_DEV_THRESHOLD:
            issues.append(
                f"Safe Zone Warning: High-contrast graphics/text detected dangerously close to "
                f"{edge_name} border (std_dev={std_dev:.1f} > {BORDER_STD_DEV_THRESHOLD:.0f})"
            )

    # 3. Mandatory Copy & Elements Audit + Manifest Checks (Fail-Closed)
    meta_data: Optional[Dict[str, Any]] = None
    meta_content = ""
    if not layout_meta_path or not os.path.exists(layout_meta_path):
        if require_meta:
            issues.append(
                f"Missing Layout Manifest (Fail-Closed): {layout_meta_path or 'not provided'}"
            )
    else:
        try:
            with open(layout_meta_path, "r", encoding="utf-8") as f:
                meta_content = f.read()
            meta_data = json.loads(meta_content)
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(f"Invalid Layout Manifest JSON ({layout_meta_path}): {exc}")

    if meta_content:
        missing_elements = [elem for elem in REQUIRED_ELEMENTS if elem not in meta_content]
        if missing_elements:
            issues.append(f"Missing Required Elements: {', '.join(missing_elements)}")

    spec = _load_ground_truth_spec(spec_path)
    assertions: Dict[str, Dict[str, Any]] = {}

    headline_contrast: Optional[float] = None
    vertical_rhythm_metrics: Dict[str, float] = {}
    if isinstance(meta_data, dict):
        # 2b. Bounding-Box Safe Zone Check against config/media_safe_zones_2026.json
        safe_margin_issues = assert_safe_margins(meta_data, w, h, safe_margins)
        assertions["assert_safe_margins"] = {
            "status": "PASS" if not safe_margin_issues else "FAIL",
            "issues": safe_margin_issues,
        }
        issues.extend(safe_margin_issues)

        # 3b. Ground-Truth Spec Assertions (DIR-SELF-AUDIT-GROUNDTRUTH-SPEC-035)
        logo_issues = assert_logo_top_left(meta_data, spec)
        assertions["assert_logo_top_left"] = {
            "status": "PASS" if not logo_issues else "FAIL",
            "issues": logo_issues,
        }
        issues.extend(logo_issues)

        copy_issues = assert_exact_copy(meta_data, meta_content, spec)
        assertions["assert_exact_copy"] = {
            "status": "PASS" if not copy_issues else "FAIL",
            "issues": copy_issues,
        }
        issues.extend(copy_issues)

        occlusion_issues = assert_zero_text_occlusion(meta_data, spec)
        assertions["assert_zero_text_occlusion"] = {
            "status": "PASS" if not occlusion_issues else "FAIL",
            "issues": occlusion_issues,
        }
        issues.extend(occlusion_issues)

        product_issues = assert_mandatory_products(meta_data, meta_content, spec)
        assertions["assert_mandatory_products"] = {
            "status": "PASS" if not product_issues else "FAIL",
            "issues": product_issues,
        }
        issues.extend(product_issues)

        vertical_rhythm_metrics, spacing_issues = assert_vertical_hierarchy_spacing(meta_data)
        assertions["assert_vertical_hierarchy_spacing"] = {
            "status": "PASS" if not spacing_issues else "FAIL",
            "issues": spacing_issues,
        }
        issues.extend(spacing_issues)

        logo_cap_issues = assert_logo_capsule_clearance(meta_data)
        assertions["assert_logo_capsule_clearance"] = {
            "status": "PASS" if not logo_cap_issues else "FAIL",
            "issues": logo_cap_issues,
        }
        issues.extend(logo_cap_issues)

        # 4. Visual Contrast & Legibility (WCAG AA >= 4.5:1)
        headline_contrast, contrast_issues = _audit_headline_contrast(arr, meta_data)
        issues.extend(contrast_issues)

        # 5. No Broken Assets / Rendering Glitches
        issues.extend(_audit_assets_and_fonts(meta_data, meta_content))

    remediation_payload: Optional[Dict[str, Any]] = None
    if isinstance(meta_data, dict):
        remediation_payload = build_remediation_hints(
            meta=meta_data,
            assertions=assertions,
            width=w,
            height=h,
            safe_margins=safe_margins,
            spec=spec,
        )
        if remediation_out_path:
            out_p = Path(remediation_out_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(
                json.dumps(remediation_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    status = "PASS" if len(issues) == 0 else "FAIL"

    metrics: Dict[str, Any] = {
        "dimensions": f"{w}x{h}",
        "file_size_kb": round(file_size_kb, 1),
        "format": img_format,
        "safe_margins_px": safe_margins,
        "border_std_dev": border_std_devs,
    }
    if headline_contrast is not None:
        metrics["headline_contrast_ratio"] = headline_contrast
    if vertical_rhythm_metrics:
        metrics["vertical_rhythm_px"] = vertical_rhythm_metrics

    return {
        "banner_file": os.path.basename(image_path),
        "status": status,
        "metrics": metrics,
        "assertions": assertions,
        "remediation": remediation_payload,
        "warnings": warnings,
        "issues": issues,
    }


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Master Banner Preflight & Prescriptive Inspector (DIR-UPGRADE-PRESCRIPTIVE-INSPECTOR-037)"
    )
    parser.add_argument(
        "image_path",
        nargs="?",
        default="output/TASK_GSSHOP/gsshop_master_1080x1080.png",
        help="Path to the rendered Master Banner PNG (default: output/TASK_GSSHOP/gsshop_master_1080x1080.png)",
    )
    parser.add_argument(
        "meta_path",
        nargs="?",
        default="output/TASK_GSSHOP/gsshop_master_1080x1080.json",
        help="Path to the layout element manifest JSON (default: output/TASK_GSSHOP/gsshop_master_1080x1080.json)",
    )
    parser.add_argument(
        "--safe-zones",
        default=str(DEFAULT_SAFE_ZONES_PATH),
        help="Path to media_safe_zones_2026.json",
    )
    parser.add_argument(
        "--spec",
        default=str(DEFAULT_SPEC_PATH),
        help="Path to ground-truth assignment spec JSON (default: specs/gsshop_assignment_spec.json)",
    )
    parser.add_argument(
        "--remediation-out",
        default=str(DEFAULT_REMEDIATION_OUT_PATH),
        help="Output path for prescriptive CSS remediation hints JSON (default: output/TASK_GSSHOP/remediation_hints.json)",
    )
    parser.add_argument(
        "--no-remediation-out",
        action="store_true",
        help="Disable writing remediation_hints.json to disk",
    )
    parser.add_argument(
        "--allow-no-meta",
        action="store_true",
        help="Allow pixel-only audit without a manifest JSON (disables fail-closed manifest requirement)",
    )
    parser.add_argument(
        "--json-report",
        default=None,
        help="Optional output path to save the full JSON preflight report",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    rem_out = None if args.no_remediation_out else args.remediation_out
    report = audit_master_banner(
        image_path=args.image_path,
        layout_meta_path=args.meta_path,
        safe_zones_path=args.safe_zones,
        spec_path=args.spec,
        require_meta=not args.allow_no_meta,
        remediation_out_path=rem_out,
    )

    if args.json_report:
        report_path = Path(args.json_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    status_badge = "\033[92mPASS\033[0m" if report["status"] == "PASS" else "\033[91mFAIL\033[0m"
    print("\n================ MASTER BANNER PREFLIGHT REPORT ================")
    print(f"Target:  {report.get('banner_file')}")
    print(f"Status:  {status_badge}")
    print(f"Metrics: {json.dumps(report.get('metrics', {}), ensure_ascii=False)}")
    if report.get("assertions"):
        print("Ground-Truth Assertions:")
        for name, res in report["assertions"].items():
            badge = "\033[92mPASS\033[0m" if res["status"] == "PASS" else "\033[91mFAIL\033[0m"
            print(f"  [{badge}] {name}")
    if report.get("warnings"):
        print("Warnings:")
        for warn in report["warnings"]:
            print(f"  ℹ️  {warn}")
    if report.get("issues"):
        print("Issues found:")
        for issue in report["issues"]:
            print(f"  ⚠️  {issue}")
    remediation = report.get("remediation")
    if isinstance(remediation, dict) and remediation.get("hints"):
        print(f"Prescriptive Remediation Hints ({remediation['total_hints']} written to {rem_out or 'memory'}):")
        for h in remediation["hints"]:
            print(f"  💊 [{h.get('target_selector')}] {h.get('css_declaration')}  <-- {h.get('action_summary')}")
    print("================================================================\n")

    if report["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
