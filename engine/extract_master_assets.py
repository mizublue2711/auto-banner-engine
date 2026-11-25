"""
Task 1 Master PSD Asset Extractor (`engine/extract_master_assets.py`).

Extracts clean, transparent RGBA layer assets from the 1440x1800 XEXYMIX Master PSD
(`11_40462_261106_젝시믹스_상시소재_10차_러닝_RX 블랙라벨 시그니처 360N 기모 포켓 레깅스.psd`)
into `assets/brands/xexymix/cutouts/`:
  - `base_model_scene.png` (1440x1800 full model + backdrop, all overlays hidden)
  - `card_pocket_full.png` & `card_pocket_clean.png` (with and without leader line)
  - `card_fleece_full.png` & `card_fleece_clean.png` (with and without leader line)
  - `headline_group.png` (exact Korean typography, dark pill, orange highlight)
  - `logo_xexymix.png` (`XEXYMIX_LOGO_M`)
  - `watermark_ai.png` (`* AI Generated`)
  - `promo_master.png` (`블프버튼` fallback from master PSD)
  - `master_assets_manifest.json` (native coordinates & dimensions)
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from psd_tools import PSDImage

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "brands" / "xexymix" / "cutouts"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip()


def find_master_psd() -> Path:
    for folder in (
        ROOT / "assets" / "Task 1 - XEXYMIX",
        ROOT / "assets" / "master_sources" / "task1_xexymix",
    ):
        if folder.exists():
            for f in sorted(folder.iterdir()):
                if f.suffix.lower() == ".psd" and "11_40462" in f.name:
                    return f
    raise FileNotFoundError("Could not locate Master XEXYMIX PSD (`11_40462...psd`).")


def set_visibility_by_names(root_node: Any, visible_names: set[str]) -> Dict[int, bool]:
    """Save current visibility and set top-level children of artboard to visible only if in `visible_names`."""
    saved: Dict[int, bool] = {}
    for child in root_node:
        saved[id(child)] = child.visible
        child.visible = nfc(child.name) in visible_names
    return saved


def restore_visibility(root_node: Any, saved: Dict[int, bool]) -> None:
    for child in root_node:
        if id(child) in saved:
            child.visible = saved[id(child)]


def composite_subset(
    artboard: Any,
    visible_names: set[str],
    hide_sublayer_names: set[str] = frozenset(),
    crop_tight: bool = True,
    use_artboard_canvas: bool = False,
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    w, h = artboard.width, artboard.height
    viewport = (artboard.left, artboard.top, artboard.right, artboard.bottom)
    saved_top = set_visibility_by_names(artboard, visible_names)
    saved_sub: List[Tuple[Any, bool]] = []

    def hide_subs(node: Any) -> None:
        for child in node:
            if nfc(child.name) in hide_sublayer_names:
                saved_sub.append((child, child.visible))
                child.visible = False
            elif child.is_group():
                hide_subs(child)

    try:
        if hide_sublayer_names:
            for child in artboard:
                if child.visible and child.is_group():
                    hide_subs(child)
        if use_artboard_canvas:
            comp = artboard.composite(viewport=viewport)
            comp = comp.convert("RGBA") if comp is not None else Image.new("RGBA", (w, h), (0, 0, 0, 0))
        else:
            # Composite each selected child individually onto a transparent RGBA canvas
            # (avoids artboard's opaque white background fill)
            comp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            for child in artboard:
                if not child.visible:
                    continue
                layer_img = child.composite(viewport=viewport)
                if layer_img is not None:
                    comp.alpha_composite(layer_img.convert("RGBA"), (0, 0))
    finally:
        for layer, prev in saved_sub:
            layer.visible = prev
        restore_visibility(artboard, saved_top)

    if crop_tight:
        bbox = comp.getbbox()
        if bbox is not None:
            return comp.crop(bbox), bbox
    return comp, (0, 0, w, h)


def main() -> None:
    psd_path = find_master_psd()
    print(f"[extract_master_assets] Opening {psd_path.name} ...")
    psd = PSDImage.open(str(psd_path))

    # Locate the single 1440x1800 artboard
    artboard = None
    for layer in psd:
        if layer.kind == "artboard":
            artboard = layer
            break
    if artboard is None:
        artboard = psd

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, Any] = {
        "source_master_psd": str(psd_path.relative_to(ROOT)),
        "master_canvas": {"width": int(artboard.width), "height": int(artboard.height)},
        "assets": {},
    }

    # Exact top-level layer sets in 11_40462...psd
    extractions = [
        (
            "base_model_scene",
            {"레이어 3 복사", "레벨 2", "레이어 64", "레이어 61 복사", "레이어 61", "레이어 60"},
            set(),
            False,
        ),
        (
            "card_pocket_full",
            {"그룹 37", "사이드 삼각 포켓"},
            set(),
            True,
        ),
        (
            "card_pocket_clean",
            {"그룹 37", "사이드 삼각 포켓"},
            {"모양 2", "타원 3"},
            True,
        ),
        (
            "card_fleece_full",
            {"그룹 33", "하이 게이지 편직 및 기모 소재"},
            set(),
            True,
        ),
        (
            "card_fleece_clean",
            {"그룹 33", "하이 게이지 편직 및 기모 소재"},
            {"모양 2", "타원 3"},
            True,
        ),
        (
            "headline_group",
            {"좌측정렬"},
            set(),
            True,
        ),
        (
            "logo_xexymix",
            {"로고"},
            set(),
            True,
        ),
        (
            "watermark_ai",
            {"* AI Generated"},
            set(),
            True,
        ),
        (
            "promo_master",
            {"블프버튼"},
            {"레이어 46"},
            True,
        ),
    ]

    for key, names, hide_subs, crop_tight in extractions:
        img, bbox = composite_subset(
            artboard,
            names,
            hide_subs,
            crop_tight=crop_tight,
            use_artboard_canvas=(key == "base_model_scene"),
        )
        out_path = OUT_DIR / f"{key}.png"
        img.save(out_path, "PNG", optimize=True)
        manifest["assets"][key] = {
            "path": str(out_path.relative_to(ROOT)),
            "width": img.width,
            "height": img.height,
            "master_bbox": {
                "x": int(bbox[0]),
                "y": int(bbox[1]),
                "width": int(bbox[2] - bbox[0]),
                "height": int(bbox[3] - bbox[1]),
            },
        }
        print(f"  [export] {key}: {img.width}x{img.height} bbox={bbox} -> {out_path.relative_to(ROOT)}")

    manifest_path = OUT_DIR / "master_assets_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract_master_assets] Wrote manifest -> {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
