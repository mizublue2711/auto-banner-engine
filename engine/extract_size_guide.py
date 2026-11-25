"""
Task 1 Size Guide Matrix & Native Promo Badge Extractor (`engine/extract_size_guide.py`).

Parses `(Size Guide) 애프터블프 딱지 가이드.psd` using `psd-tools`:
- Iterates through all 11 artboards.
- Extracts exact artboard-relative pixel and normalized bounding coordinates for:
  1. `model_zone`
  2. `feature_card_zone`
  3. `headline_zone`
  4. `promo_sticker_zone`
  5. `logo_zone` & `watermark_zone`
- Exports each artboard's native yellow promotional ribbon / starburst badge
  to `assets/brands/xexymix/badges/{slug}_promo.png`.
- Saves the structured specification to `config/task1_size_guide_matrix.json`.
"""

from __future__ import annotations

import json
import os
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from psd_tools import PSDImage

ROOT = Path(__file__).resolve().parent.parent

SIZE_GUIDE_CANDIDATES = [
    ROOT / "assets" / "Task 1 - XEXYMIX" / "(Size Guide) 애프터블프 딱지 가이드.psd",
    ROOT / "assets" / "master_sources" / "task1_xexymix" / "(Size Guide) 애프터블프 딱지 가이드.psd",
]

OUT_MATRIX = ROOT / "config" / "task1_size_guide_matrix.json"
OUT_BADGES_DIR = ROOT / "assets" / "brands" / "xexymix" / "badges"

# Canonical mapping from Korean artboard names (NFC-normalized) to Task 1 slugs
ARTBOARD_MAP: Dict[str, Dict[str, Any]] = {
    "메타_1440x2560": {"slug": "meta_story_9_16", "layout_type": "vertical_9_16", "order": 1},
    "메타_1440x1800": {"slug": "meta_feed_4_5", "layout_type": "vertical_4_5", "order": 2},
    "카카오모먼트_800x1000": {"slug": "kakao_feed_4_5", "layout_type": "vertical_4_5", "order": 3},
    "구글DA_960x1200": {"slug": "google_da_4_5", "layout_type": "vertical_4_5", "order": 4},
    "구글DA_1200x1200": {"slug": "google_da_square", "layout_type": "square", "order": 5},
    "네이버GFA_1200x1200": {"slug": "naver_gfa_square", "layout_type": "square", "order": 6},
    "구글DA_1200x628": {"slug": "google_da_landscape", "layout_type": "wide", "order": 7},
    "네이버GFA_1250x560": {"slug": "naver_gfa_wide", "layout_type": "wide", "order": 8},
    "네이버GFA_342x228": {"slug": "naver_thumb_small", "layout_type": "micro", "order": 9},
    "네이버스마트채널_260x280": {"slug": "naver_smart_channel", "layout_type": "micro", "order": 10},
    "카카오비즈보드_314x300": {"slug": "kakao_bizboard", "layout_type": "micro", "order": 11},
}


def find_size_guide_psd() -> Path:
    for p in SIZE_GUIDE_CANDIDATES:
        if p.exists():
            return p
    # Fallback: match by NFD/NFC filename inside assets/Task 1 - XEXYMIX
    task1_dir = ROOT / "assets" / "Task 1 - XEXYMIX"
    if task1_dir.exists():
        for f in task1_dir.iterdir():
            if f.suffix.lower() == ".psd" and "Size Guide" in f.name:
                return f
    raise FileNotFoundError("Could not locate `(Size Guide) 애프터블프 딱지 가이드.psd`.")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def clamp_bbox(
    bbox: Tuple[int, int, int, int], w: int, h: int
) -> Tuple[int, int, int, int]:
    l, t, r, b = bbox
    l = max(0, min(w, l))
    t = max(0, min(h, t))
    r = max(l, min(w, r))
    b = max(t, min(h, b))
    return (l, t, r, b)


def make_zone(
    x: int,
    y: int,
    zw: int,
    zh: int,
    cw: int,
    ch: int,
    anchor: str = "top_left",
    visible: bool = True,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    zone: Dict[str, Any] = {
        "visible": visible,
        "anchor": anchor,
        "px": {"x": int(x), "y": int(y), "width": int(zw), "height": int(zh)},
        "rel": {
            "x": round(x / cw, 4) if cw else 0.0,
            "y": round(y / ch, 4) if ch else 0.0,
            "width": round(zw / cw, 4) if cw else 0.0,
            "height": round(zh / ch, 4) if ch else 0.0,
        },
    }
    if extra:
        zone.update(extra)
    return zone


def union_visible_leaf_bbox(
    node: Any,
    ab_left: int,
    ab_top: int,
    ab_w: int,
    ab_h: int,
    exclude_names: Tuple[str, ...] = (),
) -> Optional[Tuple[int, int, int, int]]:
    xs1, ys1, xs2, ys2 = [], [], [], []

    def walk(cur: Any) -> None:
        if not cur.visible:
            return
        cname = nfc(cur.name)
        if any(ex in cname.lower() for ex in exclude_names):
            return
        if cur.is_group():
            for child in cur:
                walk(child)
        else:
            if cur.width > 0 and cur.height > 0:
                l = cur.left - ab_left
                t = cur.top - ab_top
                r = cur.right - ab_left
                b = cur.bottom - ab_top
                # Ignore full-canvas backdrop gradients/overlays when computing tight UI bounds
                if (r - l) >= ab_w * 0.98 and (b - t) >= ab_h * 0.95:
                    return
                l, t, r, b = clamp_bbox((l, t, r, b), ab_w, ab_h)
                if r > l and b > t:
                    xs1.append(l)
                    ys1.append(t)
                    xs2.append(r)
                    ys2.append(b)

    walk(node)
    if not xs1:
        return None
    return (min(xs1), min(ys1), max(xs2), max(ys2))


def find_group_by_names(artboard: Any, names: Tuple[str, ...]) -> Optional[Any]:
    target = {nfc(n) for n in names}
    # Prefer direct children first
    for child in artboard:
        if child.visible and nfc(child.name) in target:
            return child
    # Recursive search
    def walk(node: Any) -> Optional[Any]:
        for child in node:
            if not child.visible:
                continue
            if nfc(child.name) in target:
                return child
            if child.is_group():
                hit = walk(child)
                if hit is not None:
                    return hit
        return None

    return walk(artboard)


def find_leaf_by_substr(artboard: Any, substrs: Tuple[str, ...]) -> Optional[Any]:
    def walk(node: Any) -> Optional[Any]:
        for child in node:
            if not child.visible:
                continue
            cname = nfc(child.name)
            if not child.is_group() and child.width > 0 and child.height > 0:
                if any(s.lower() in cname.lower() for s in substrs):
                    return child
            if child.is_group():
                hit = walk(child)
                if hit is not None:
                    return hit
        return None

    return walk(artboard)


def export_promo_badge(
    artboard: Any,
    promo_group: Any,
    slug: str,
    is_micro: bool,
) -> Tuple[Optional[str], Optional[Tuple[int, int, int, int]]]:
    """
    Composite the native promo group onto an artboard-sized transparent canvas,
    excluding any embedded brand logo layers (on micro artboards) and full-height
    vignette/backdrop helper layers (e.g. `레이어 63..67`), then trim to non-empty alpha.
    """
    ab_left, ab_top, ab_right, ab_bottom = artboard.bbox
    ab_w = ab_right - ab_left
    ab_h = ab_bottom - ab_top

    canvas = Image.new("RGBA", (ab_w, ab_h), (0, 0, 0, 0))

    # Temporarily hide logo layers inside micro promo groups or full-height vignette layers
    hidden_temporarily: List[Any] = []

    def filter_children(node: Any) -> None:
        for child in node:
            if not child.visible:
                continue
            cname = nfc(child.name)
            if is_micro and not child.is_group() and ("logo" in cname.lower() or "xexymix" in cname.lower()):
                child.visible = False
                hidden_temporarily.append(child)
                continue
            # Full-height overlay layers inside 블프버튼 (e.g. 레이어 63..67) are dark left-side gradients
            # that belong to the hoodie sample background, not the yellow promo ribbon itself.
            if (
                not child.is_group()
                and cname.startswith("레이어 ")
                and child.height >= ab_h * 0.90
            ):
                child.visible = False
                hidden_temporarily.append(child)
                continue
            if child.is_group():
                filter_children(child)

    try:
        filter_children(promo_group)
        comp = promo_group.composite(viewport=(ab_left, ab_top, ab_right, ab_bottom))
        if comp is not None:
            comp = comp.convert("RGBA")
            canvas.alpha_composite(comp, (0, 0))
    finally:
        for layer in hidden_temporarily:
            layer.visible = True

    alpha_bbox = canvas.getbbox()
    if alpha_bbox is None:
        return None, None

    cropped = canvas.crop(alpha_bbox)
    OUT_BADGES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_BADGES_DIR / f"{slug}_promo.png"
    cropped.save(out_path, "PNG", optimize=True)
    rel_path = str(out_path.relative_to(ROOT))
    return rel_path, alpha_bbox


def derive_zones_for_artboard(
    artboard: Any,
    slug: str,
    layout_type: str,
) -> Dict[str, Any]:
    ab_left, ab_top, ab_right, ab_bottom = artboard.bbox
    w = ab_right - ab_left
    h = ab_bottom - ab_top
    is_micro = layout_type == "micro"

    # 1. Promo Sticker Zone + Native Badge Export
    promo_group = find_group_by_names(artboard, ("블프버튼", "블프", "Group 20"))
    badge_rel_path: Optional[str] = None
    promo_bbox: Optional[Tuple[int, int, int, int]] = None
    if promo_group is not None:
        badge_rel_path, promo_bbox = export_promo_badge(artboard, promo_group, slug, is_micro)

    if promo_bbox is None:
        # Safe fallback
        ph = int(h * 0.16)
        promo_bbox = (0, h - ph, w, h)

    px1, py1, px2, py2 = promo_bbox
    promo_zone = make_zone(
        px1,
        py1,
        px2 - px1,
        py2 - py1,
        w,
        h,
        anchor="bottom_right" if is_micro else "bottom_center",
        visible=True,
        extra={"native_badge_path": badge_rel_path},
    )

    # 2. Logo Zone
    logo_layer = find_leaf_by_substr(artboard, ("XEXYMIX_LOGO_M", "logo"))
    if logo_layer is not None:
        lx1, ly1, lx2, ly2 = clamp_bbox(
            (logo_layer.left - ab_left, logo_layer.top - ab_top, logo_layer.right - ab_left, logo_layer.bottom - ab_top),
            w,
            h,
        )
        logo_zone = make_zone(lx1, ly1, lx2 - lx1, ly2 - ly1, w, h, anchor="top_left", visible=True)
    else:
        logo_zone = make_zone(int(w * 0.055), int(h * 0.047), int(w * 0.24), int(h * 0.03), w, h, anchor="top_left", visible=True)

    # 3. AI Watermark Zone
    wm_layer = find_leaf_by_substr(artboard, ("AI Generated",))
    if wm_layer is not None and not is_micro:
        wx1, wy1, wx2, wy2 = clamp_bbox(
            (wm_layer.left - ab_left, wm_layer.top - ab_top, wm_layer.right - ab_left, wm_layer.bottom - ab_top),
            w,
            h,
        )
        watermark_zone = make_zone(wx1, wy1, wx2 - wx1, wy2 - wy1, w, h, anchor="top_right", visible=True)
    else:
        watermark_zone = make_zone(int(w * 0.78), int(h * 0.048), int(w * 0.16), int(h * 0.016), w, h, anchor="top_right", visible=False)

    # 4. Headline Zone (extracted from 카피 group on standard/square/wide, safe-derived on micro)
    copy_group = find_group_by_names(artboard, ("카피",))
    copy_bbox = (
        union_visible_leaf_bbox(copy_group, ab_left, ab_top, w, h)
        if copy_group is not None
        else None
    )
    if copy_bbox is not None:
        hx1, hy1, hx2, hy2 = copy_bbox
        headline_zone = make_zone(hx1, hy1, hx2 - hx1, hy2 - hy1, w, h, anchor="bottom_left", visible=True)
    else:
        # Micro viewports: headline positioned cleanly alongside/below logo, above bottom badge
        if slug == "kakao_bizboard":
            # Logo & badge are on the right side (x≈156..306), model on left
            headline_zone = make_zone(int(w * 0.44), int(h * 0.42), int(w * 0.52), int(h * 0.26), w, h, anchor="middle_right", visible=True)
        elif slug == "naver_smart_channel":
            # Logo & badge on left side (x≈10..113), model on right
            headline_zone = make_zone(int(w * 0.04), int(h * 0.44), int(w * 0.54), int(h * 0.22), w, h, anchor="middle_left", visible=True)
        else:
            # naver_thumb_small (342x228): logo top-left, badge bottom-left, model right
            headline_zone = make_zone(int(w * 0.04), int(h * 0.42), int(w * 0.54), int(h * 0.24), w, h, anchor="middle_left", visible=True)

    # 5. Model Zone & Feature Card Zone (strictly grounded to layout archetype and extracted safe bounds)
    if layout_type == "vertical_4_5":
        # Exact master 1440x1800 proportions: model on right, 2 stacked feature cards upper-left
        model_zone = make_zone(int(w * 0.42), 0, int(w * 0.58), h, w, h, anchor="center_right", visible=True, extra={"crop_focus_x": 0.62, "crop_focus_y": 0.48})
        fc_top = max(logo_zone["px"]["y"] + logo_zone["px"]["height"] + int(h * 0.03), int(h * 0.12))
        fc_bottom = min(headline_zone["px"]["y"] - int(h * 0.03), int(h * 0.58))
        feature_card_zone = make_zone(
            int(w * 0.06),
            fc_top,
            int(w * 0.44),
            max(100, fc_bottom - fc_top),
            w,
            h,
            anchor="top_left",
            visible=True,
            extra={"arrangement": "stacked_vertical", "use_leader_lines": True},
        )
    elif layout_type == "vertical_9_16":
        # Tall 1440x2560: model full-height right-weighted, 2 stacked cards in upper-left, headline mid-lower, promo below
        model_zone = make_zone(int(w * 0.36), 0, int(w * 0.64), h, w, h, anchor="center_right", visible=True, extra={"crop_focus_x": 0.66, "crop_focus_y": 0.46})
        fc_top = max(logo_zone["px"]["y"] + logo_zone["px"]["height"] + int(h * 0.04), int(h * 0.14))
        fc_bottom = min(headline_zone["px"]["y"] - int(h * 0.04), int(h * 0.50))
        feature_card_zone = make_zone(
            int(w * 0.065),
            fc_top,
            int(w * 0.42),
            max(200, fc_bottom - fc_top),
            w,
            h,
            anchor="top_left",
            visible=True,
            extra={"arrangement": "stacked_vertical", "use_leader_lines": False},
        )
    elif layout_type == "square":
        # 1200x1200: model on right 54%, 2 compact cards side-by-side or stacked on upper-left, headline lower-left
        model_zone = make_zone(int(w * 0.46), 0, int(w * 0.54), h, w, h, anchor="center_right", visible=True, extra={"crop_focus_x": 0.64, "crop_focus_y": 0.42})
        fc_top = max(logo_zone["px"]["y"] + logo_zone["px"]["height"] + int(h * 0.035), int(h * 0.12))
        fc_bottom = min(headline_zone["px"]["y"] - int(h * 0.035), int(h * 0.56))
        feature_card_zone = make_zone(
            int(w * 0.055),
            fc_top,
            int(w * 0.44),
            max(140, fc_bottom - fc_top),
            w,
            h,
            anchor="top_left",
            visible=True,
            extra={"arrangement": "row_horizontal", "use_leader_lines": False},
        )
    elif layout_type == "wide":
        # 1200x628 & 1250x560: left column = logo + 2 small side-by-side cards + headline + promo; right column = model
        model_zone = make_zone(int(w * 0.54), 0, int(w * 0.46), h, w, h, anchor="center_right", visible=True, extra={"crop_focus_x": 0.68, "crop_focus_y": 0.36})
        fc_left = logo_zone["px"]["x"]
        fc_top = logo_zone["px"]["y"] + logo_zone["px"]["height"] + int(h * 0.025)
        # Ensure headline never collides with feature cards when Size Guide 카피 sits high (e.g. google_da_landscape)
        min_fc_h = int(h * 0.21)
        min_hl_y = fc_top + min_fc_h + int(h * 0.02)
        if headline_zone["px"]["y"] < min_hl_y:
            max_hl_bottom = promo_zone["px"]["y"] - int(h * 0.025)
            new_hl_h = max(110, max_hl_bottom - min_hl_y)
            headline_zone = make_zone(
                headline_zone["px"]["x"],
                min_hl_y,
                headline_zone["px"]["width"],
                new_hl_h,
                w,
                h,
                anchor="bottom_left",
                visible=True,
            )
        fc_bottom = headline_zone["px"]["y"] - int(h * 0.02)
        feature_card_zone = make_zone(
            fc_left,
            fc_top,
            int(w * 0.36),
            max(90, fc_bottom - fc_top),
            w,
            h,
            anchor="top_left",
            visible=True,
            extra={"arrangement": "row_horizontal", "use_leader_lines": False},
        )
    else:
        # Micro (< 400px): omit fine-print feature cards; frame model cleanly opposite logo/badge
        if slug == "kakao_bizboard":
            # Right-aligned logo/badge -> model framed on left
            model_zone = make_zone(0, 0, int(w * 0.60), h, w, h, anchor="center_left", visible=True, extra={"crop_focus_x": 0.66, "crop_focus_y": 0.42, "flip_x": True})
        else:
            # Left-aligned logo/badge -> model framed on right
            model_zone = make_zone(int(w * 0.38), 0, int(w * 0.62), h, w, h, anchor="center_right", visible=True, extra={"crop_focus_x": 0.68, "crop_focus_y": 0.42, "flip_x": False})
        feature_card_zone = make_zone(0, 0, 0, 0, w, h, anchor="none", visible=False, extra={"omitted_reason": "micro_viewport_legibility"})

    return {
        "slug": slug,
        "artboard_name": nfc(artboard.name),
        "width": int(w),
        "height": int(h),
        "aspect_ratio": round(w / h, 4),
        "layout_type": layout_type,
        "is_micro": is_micro,
        "artboard_origin": {"left": int(ab_left), "top": int(ab_top)},
        "zones": {
            "model_zone": model_zone,
            "feature_card_zone": feature_card_zone,
            "headline_zone": headline_zone,
            "promo_sticker_zone": promo_zone,
            "logo_zone": logo_zone,
            "watermark_zone": watermark_zone,
        },
    }


def main() -> None:
    psd_path = find_size_guide_psd()
    print(f"[extract_size_guide] Opening {psd_path.name} ...")
    psd = PSDImage.open(str(psd_path))

    artboards_out: List[Tuple[int, Dict[str, Any]]] = []
    for layer in psd:
        if layer.kind != "artboard":
            continue
        aname = nfc(layer.name)
        meta = ARTBOARD_MAP.get(aname)
        if meta is None:
            print(f"  [skip] Unmapped artboard: {aname}")
            continue
        print(f"  [parse] {aname} ({layer.width}x{layer.height}) -> {meta['slug']}")
        spec = derive_zones_for_artboard(layer, meta["slug"], meta["layout_type"])
        artboards_out.append((meta["order"], spec))

    artboards_out.sort(key=lambda item: item[0])
    ordered_specs = [spec for _, spec in artboards_out]

    matrix = {
        "schema_version": "1.0",
        "task_id": "TASK1_XEXYMIX_11_SIZES",
        "source_size_guide_psd": str(psd_path.relative_to(ROOT)),
        "artboard_count": len(ordered_specs),
        "artboards": ordered_specs,
    }

    OUT_MATRIX.parent.mkdir(parents=True, exist_ok=True)
    OUT_MATRIX.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract_size_guide] Wrote {len(ordered_specs)} artboards -> {OUT_MATRIX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
