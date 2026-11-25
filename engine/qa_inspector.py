"""
Automated Production QA Inspector (`engine/qa_inspector.py`).

Verifies Workflow A (Task 1 Production Resizing) outputs against the task manifest
and extracted Size Guide matrix:
  1. File existence & valid PNG format
  2. Exact pixel dimensions (width x height)
  3. Visual presence of Full Model inside `model_zone`
  4. Visual presence of Yellow Promotional Ribbon/Badge inside `promo_sticker_zone`
  5. Visual presence of Feature Cards inside `feature_card_zone` on standard/square/wide
     viewports, and confirmation of micro omission rule on micro viewports.

Usage:
  python3 engine/qa_inspector.py --workflow A --task tasks/task1_production/xexymix_11_sizes.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def crop_zone_rgb(arr: np.ndarray, zone_px: Dict[str, int]) -> np.ndarray:
    h, w, _ = arr.shape
    x1 = max(0, min(w, int(zone_px["x"])))
    y1 = max(0, min(h, int(zone_px["y"])))
    x2 = max(x1, min(w, int(zone_px["x"] + zone_px["width"])))
    y2 = max(y1, min(h, int(zone_px["y"] + zone_px["height"])))
    return arr[y1:y2, x1:x2]


def check_model_presence(arr: np.ndarray, model_zone: Dict[str, Any]) -> Dict[str, Any]:
    region = crop_zone_rgb(arr, model_zone["px"])
    if region.size == 0:
        return {"passed": False, "detail": "empty model_zone"}
    std_val = float(region.std())
    # Model leggings (dark grey) + skin/top + fence creates rich luminance variance (> 25)
    passed = std_val >= 22.0
    return {"passed": passed, "detail": f"std={std_val:.1f}"}


def check_promo_yellow_presence(arr: np.ndarray, promo_zone: Dict[str, Any]) -> Dict[str, Any]:
    region = crop_zone_rgb(arr, promo_zone["px"])
    if region.size == 0:
        return {"passed": False, "detail": "empty promo_sticker_zone"}
    r = region[..., 0].astype(np.int16)
    g = region[..., 1].astype(np.int16)
    b = region[..., 2].astype(np.int16)
    # Signature XEXYMIX After Black Friday neon yellow (#D9FF00 / #E6FF00)
    yellow_mask = (r >= 175) & (g >= 195) & (b <= 115) & ((g - b) >= 100)
    yellow_ratio = float(yellow_mask.mean())
    yellow_pixels = int(yellow_mask.sum())
    passed = yellow_pixels >= 120 and yellow_ratio >= 0.015
    return {"passed": passed, "detail": f"yellow_px={yellow_pixels} ({yellow_ratio*100:.1f}%)"}


def check_feature_cards_presence(
    arr: np.ndarray,
    fc_zone: Dict[str, Any],
    is_micro: bool,
) -> Dict[str, Any]:
    if is_micro or not fc_zone.get("visible", False):
        return {"passed": True, "detail": "omitted_micro_ok"}
    region = crop_zone_rgb(arr, fc_zone["px"])
    if region.size == 0:
        return {"passed": False, "detail": "empty feature_card_zone"}
    # Feature cards contain high-contrast brown/fleece textures, thermometer icon, and crisp white borders
    std_val = float(region.std())
    bright_border = ((region[..., 0] >= 225) & (region[..., 1] >= 225) & (region[..., 2] >= 225)).mean()
    passed = std_val >= 20.0 and bright_border >= 0.005
    return {"passed": passed, "detail": f"std={std_val:.1f}, border={bright_border*100:.1f}%"}


def inspect_workflow_a(task_path: Path) -> int:
    task = json.loads(task_path.read_text(encoding="utf-8"))
    matrix_path = ROOT / task["size_guide_matrix"]
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    out_dir = ROOT / task["output_dir"]

    specs_by_slug = {ab["slug"]: ab for ab in matrix["artboards"]}
    targets: List[Dict[str, Any]] = task["target_dimensions"]

    print(f"=== QA INSPECTOR | WORKFLOW A | {task['task_id']} ===")
    print(f"Output Dir: {out_dir.relative_to(ROOT)}")
    print("-" * 104)
    print(f"{'PLACEMENT':22s} | {'TARGET':10s} | {'ACTUAL':10s} | {'MODEL':10s} | {'PROMO':18s} | {'CARDS':16s} | {'STATUS'}")
    print("-" * 104)

    all_passed = True
    results = []

    for t in targets:
        slug = t["name"]
        tw, th = int(t["width"]), int(t["height"])
        png_path = out_dir / f"{slug}.png"
        spec = specs_by_slug.get(slug)

        if not png_path.exists():
            all_passed = False
            print(f"{slug:22s} | {tw}x{th:<5d} | {'MISSING':10s} | {'FAIL':10s} | {'FAIL':18s} | {'FAIL':16s} | FAILED")
            continue

        img = Image.open(png_path).convert("RGB")
        aw, ah = img.size
        dim_ok = (aw == tw) and (ah == th)
        arr = np.array(img)

        model_res = check_model_presence(arr, spec["zones"]["model_zone"]) if spec else {"passed": False, "detail": "no spec"}
        promo_res = check_promo_yellow_presence(arr, spec["zones"]["promo_sticker_zone"]) if spec else {"passed": False, "detail": "no spec"}
        cards_res = check_feature_cards_presence(arr, spec["zones"]["feature_card_zone"], bool(spec["is_micro"])) if spec else {"passed": False, "detail": "no spec"}

        row_ok = dim_ok and model_res["passed"] and promo_res["passed"] and cards_res["passed"]
        if not row_ok:
            all_passed = False

        status = "PASSED" if row_ok else "FAILED"
        print(
            f"{slug:22s} | {tw}x{th:<5d} | {aw}x{ah:<5d} | "
            f"{('OK ' if model_res['passed'] else 'ERR') + model_res['detail']:10s} | "
            f"{('OK ' if promo_res['passed'] else 'ERR') + promo_res['detail']:18s} | "
            f"{('OK ' if cards_res['passed'] else 'ERR') + cards_res['detail']:16s} | {status}"
        )
        results.append({"slug": slug, "passed": row_ok, "dim_ok": dim_ok, "model": model_res, "promo": promo_res, "cards": cards_res})

    print("-" * 104)
    passed_count = sum(1 for r in results if r["passed"])
    print(f"SUMMARY: {passed_count}/{len(targets)} PASSED | OVERALL: {'PASSED' if all_passed else 'FAILED'}")
    return 0 if all_passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated QA Inspector for auto-banner-engine")
    parser.add_argument("--workflow", required=True, choices=["A", "B"], help="Workflow type (A or B)")
    parser.add_argument("--task", required=True, help="Path to task JSON manifest")
    args = parser.parse_args()

    task_path = Path(args.task)
    if not task_path.is_absolute():
        task_path = ROOT / task_path

    if args.workflow == "A":
        sys.exit(inspect_workflow_a(task_path))
    else:
        print("Workflow B inspection is not part of Task 1 scope.")
        sys.exit(0)


if __name__ == "__main__":
    main()
