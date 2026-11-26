#!/usr/bin/env python3
"""
STRICT ASSET QA AUDITOR - auto-banner-engine
Directives:
  - DIR-RADICAL-HALO-AND-SHADOW-STRIP-016
  - DIR-SMART-CONTOUR-CROP-AND-AUDIT-017

Anti-false-PASS visual quality auditor enforcing 5 strict criteria:
1. Corner Purity (4 corners 10x10 must have 0 noisy pixels).
2. Strict Light-Gray Studio Halo Check on Transition Edge (outer 2px solid shell
   UNION semi-transparent border):
   - Studio light-gray predicate:
     R, G, B > 195 AND |R - G| < 12 AND |G - B| < 12
     (also tracks brightness > 190 & saturation < 15).
   - Purely colored items (tree, gingerbread, santa_hat, stocking):
     FAILS unconditionally if > 3.0% of transition edge pixels are light-gray studio.
   - Mixed colored + white items (bauble, candy_cane, gift_box, snowman):
     FAILS if > 3.0% of transition edge pixels adjacent to colored deep-interior
     surfaces (sampled 5px deep inside core) are light-gray studio.
   - Purely white item (snowflake):
     Audited strictly on corner purity, boundary clipping, and floor-shadow elimination.
3. Residual Floor Shadow Check at Bottom 15%:
   - Semi-transparent shadow residue (5 < Alpha < 160): FAILS if > 120 px.
   - Opaque horizontal floor shadow protrusion (Alpha >= 160, low-chroma gray
     flaring horizontally beyond object base envelope): FAILS if > 80 px.
4. Boundary Contact Audit (check_object_clipping):
   - FAILS immediately if any object pixel (alpha > 30) touches the 1px outer
     canvas boundary (Top, Bottom, Left, Right).
5. Bounding Box & Transparency Metrics + JSON audit manifest.
"""

from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion, distance_transform_edt

PURE_WHITE_ITEMS = ("decor_snowflake",)
MIXED_WHITE_ITEMS = ("decor_bauble", "decor_candy_cane", "decor_gift_box", "decor_snowman")

MAX_STUDIO_HALO_RATIO = 0.03  # Strict 3.0% hard ceiling — no exceptions
MAX_BOTTOM_SHADOW_TOTAL_PX = 49  # Strict < 50 bottom residual shadow pixels (Gate 4)
MAX_SEMI_SHADOW_PX = 49
MAX_OPAQUE_SHADOW_PROTRUSION_PX = 49


def _classify_item(filename: str) -> str:
    stem = os.path.splitext(filename)[0].lower()
    if any(k in stem for k in PURE_WHITE_ITEMS):
        return "pure_white"
    if any(k in stem for k in MIXED_WHITE_ITEMS):
        return "mixed"
    return "pure_colored"


def _detect_opaque_shadow_protrusion(
    alpha: np.ndarray,
    rgb: np.ndarray,
    ymin: int,
    ymax: int,
) -> int:
    """
    Detect opaque (Alpha >= 160) low-chroma gray/cool-gray floor shadow pixels
    in the bottom 15% that protrude horizontally beyond the object's base envelope
    established just above the shadow band.
    """
    bbox_h = ymax - ymin
    if bbox_h < 20:
        return 0

    bcut = ymax - int(bbox_h * 0.15)
    ref_top = max(ymin, ymax - int(bbox_h * 0.24))
    ref_bot = max(ref_top, bcut - 1)

    ref_lefts = []
    ref_rights = []
    for y in range(ref_top, ref_bot + 1):
        rxs = np.where(alpha[y] >= 160)[0]
        if len(rxs) > 0:
            ref_lefts.append(int(rxs.min()))
            ref_rights.append(int(rxs.max()))

    if not ref_lefts:
        return 0

    # Reference base envelope immediately above bottom 15%
    env_left = int(np.percentile(ref_lefts, 15))
    env_right = int(np.percentile(ref_rights, 85))

    rgb_i = rgb.astype(np.int16)
    protruding_count = 0
    running_left = env_left
    running_right = env_right

    for y in range(bcut, ymax + 1):
        rxs = np.where(alpha[y] >= 160)[0]
        if len(rxs) == 0:
            continue
        # Any pixel flaring outward past the non-expanding base envelope (+3px curve tol)
        flared = rxs[(rxs < running_left - 3) | (rxs > running_right + 3)]
        if len(flared) > 0:
            c = rgb_i[y, flared]
            chroma = c.max(axis=1) - c.min(axis=1)
            bright = c.mean(axis=1)
            # Low-chroma gray/cool-gray floor shadow
            is_gray_shadow = (chroma < 40) & (bright > 100) & (c[:, 2] >= c[:, 0] - 8)
            protruding_count += int(np.sum(is_gray_shadow))

        # Track narrowing envelope (only tighten inward if interior narrows cleanly)
        in_env = rxs[(rxs >= running_left - 3) & (rxs <= running_right + 3)]
        if len(in_env) > 0:
            running_left = max(running_left, int(in_env.min()))
            running_right = min(running_right, int(in_env.max()))

    return protruding_count


def check_object_clipping(cropped_image_path: str) -> dict:
    """
    Kiểm tra xem ảnh sau khi cắt có bị chém đứt mép/phạm vào vật thể gốc hay không.
    Nguyên lý: Nếu pixel vật thể (alpha > 30) chạm sát vào đúng đường biên 1px
    ngoài cùng của ảnh (Top/Bottom/Left/Right) -> BỊ CẮT PHẠM.
    """
    img = Image.open(cropped_image_path).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    h, w = alpha.shape

    # Extract the 4 outermost 1px borders
    border_top = alpha[0, :]
    border_bottom = alpha[h - 1, :]
    border_left = alpha[:, 0]
    border_right = alpha[:, w - 1]

    # Count object pixels (alpha > 30) touching each outer boundary
    clipping_top = int(np.sum(border_top > 30))
    clipping_bottom = int(np.sum(border_bottom > 30))
    clipping_left = int(np.sum(border_left > 30))
    clipping_right = int(np.sum(border_right > 30))

    total_clipped_pixels = (
        clipping_top + clipping_bottom + clipping_left + clipping_right
    )
    is_clipped = total_clipped_pixels > 0

    clipped_edges = []
    if clipping_top > 0:
        clipped_edges.append(f"Top ({clipping_top}px)")
    if clipping_bottom > 0:
        clipped_edges.append(f"Bottom ({clipping_bottom}px)")
    if clipping_left > 0:
        clipped_edges.append(f"Left ({clipping_left}px)")
    if clipping_right > 0:
        clipped_edges.append(f"Right ({clipping_right}px)")

    return {
        "is_clipped": is_clipped,
        "total_clipped_pixels": total_clipped_pixels,
        "clipped_edges": clipped_edges,
        "edge_counts": {
            "top": clipping_top,
            "bottom": clipping_bottom,
            "left": clipping_left,
            "right": clipping_right,
        },
        "status": "FAIL (CLIPPED)" if is_clipped else "PASS (COMPLETE)",
    }


def audit_png_asset(image_path: str) -> dict:
    filename = os.path.basename(image_path)
    category = _classify_item(filename)

    raw_img = Image.open(image_path)
    orig_w, orig_h = raw_img.size
    orig_mode = raw_img.mode
    img = raw_img.convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]

    # 1. Corner Purity (4 corners 10x10)
    corners = np.concatenate(
        [
            alpha[:10, :10].flatten(),
            alpha[:10, -10:].flatten(),
            alpha[-10:, :10].flatten(),
            alpha[-10:, -10:].flatten(),
        ]
    )
    corner_artifacts = int(np.count_nonzero(corners > 5))

    # 2. Bounding Box & Solid Area
    solid_mask = alpha > 20
    ys, xs = np.where(solid_mask)
    if len(ys) == 0:
        return {
            "file": filename,
            "category": category,
            "status": "FAIL",
            "reason": "Empty / Fully Transparent Image",
            "issues": ["Empty / Fully Transparent Image"],
        }

    ymin, ymax, xmin, xmax = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
    bbox_w = xmax - xmin
    bbox_h = ymax - ymin

    # 3. Strict Light-Gray Studio Halo Check on Transition Edge
    # Includes BOTH outer 2px opaque shell AND semi-transparent transition border
    # so thick opaque white/gray sticker borders can never slip past QA.
    eroded_2px = binary_erosion(solid_mask, structure=np.ones((3, 3), dtype=bool), iterations=2)
    outer_rim = solid_mask & (~eroded_2px)
    semi_mask = (alpha > 10) & (alpha < 250)
    transition_edge = outer_rim | semi_mask

    gray_halo_ratio = 0.0
    evaluated_edge_px = 0
    contaminated_edge_px = 0

    if np.any(transition_edge) and category != "pure_white":
        ty, tx = np.where(transition_edge)
        edge_rgb = rgb[ty, tx].astype(np.int16)
        r, g, b = edge_rgb[:, 0], edge_rgb[:, 1], edge_rgb[:, 2]

        # Exact Directive Step 2 light-gray studio predicate:
        # R,G,B > 195 and abs(R-G) < 12 and abs(G-B) < 12
        studio_light_gray = (
            (r > 195)
            & (g > 195)
            & (b > 195)
            & (np.abs(r - g) < 12)
            & (np.abs(g - b) < 12)
        )
        # Also include Section 3 studio-gray predicate (brightness > 190 & saturation < 15)
        brightness = (r + g + b) / 3.0
        saturation = np.max(edge_rgb, axis=1) - np.min(edge_rgb, axis=1)
        studio_strict = studio_light_gray | ((brightness > 190.0) & (saturation < 15))

        if category == "pure_colored":
            # Unconditional check across 100% of transition edge + outer 2px opaque shell
            evaluated_edge_px = int(len(ty))
            contaminated_edge_px = int(np.sum(studio_strict))
            gray_halo_ratio = float(contaminated_edge_px / max(1, evaluated_edge_px))
        else:
            # Mixed colored + white items: sample 5px deep inside solid core so a 3-5px
            # opaque halo can never masquerade as a white interior surface.
            deep_core = binary_erosion(
                alpha >= 245, structure=np.ones((3, 3), dtype=bool), iterations=5
            )
            if not np.any(deep_core):
                deep_core = alpha >= 245
            _, nearest_idx = distance_transform_edt(~deep_core, return_indices=True)
            ny, nx = nearest_idx[0, ty, tx], nearest_idx[1, ty, tx]
            core_rgb = rgb[ny, nx].astype(np.int16)
            core_chroma = np.max(core_rgb, axis=1) - np.min(core_rgb, axis=1)
            core_bright = np.mean(core_rgb, axis=1)
            core_min = np.min(core_rgb, axis=1)

            # Deep core is colored/dark (e.g., blue stripe/bow/scarf, dark charcoal hat,
            # brown arm) vs naturally white (including cool-bounce white) or metallic silver.
            core_is_white_or_silver = (
                ((core_bright > 180.0) & (core_min > 165))
                | ((core_chroma < 16) & (core_bright > 100.0))
            )
            core_is_colored = ~core_is_white_or_silver
            evaluated_edge_px = int(np.sum(core_is_colored))
            if evaluated_edge_px > 0:
                contaminated_edge_px = int(np.sum(studio_strict & core_is_colored))
                gray_halo_ratio = float(contaminated_edge_px / evaluated_edge_px)
            else:
                gray_halo_ratio = 0.0

    # 4. Detect Floor Shadow Residue at Bottom 15% (Semi-Transparent beyond 1px AA + Opaque Protrusion)
    bottom_cut = ymax - int(bbox_h * 0.15)
    bottom_alpha = alpha[bottom_cut : ymax + 1, xmin : xmax + 1]
    solid_bottom_aa_band = binary_dilation(
        bottom_alpha >= 120, structure=np.ones((3, 3), dtype=bool), iterations=1
    )
    # Only flag semi-transparent floor shadow tails extending beyond the clean 1px AA contour
    semi_shadow_mask = (bottom_alpha > 5) & (bottom_alpha < 160) & (~solid_bottom_aa_band)
    bottom_shadow_count = int(np.sum(semi_shadow_mask))
    opaque_shadow_protrusion = _detect_opaque_shadow_protrusion(alpha, rgb, ymin, ymax)

    # 5. Boundary Contact Clipping Audit (1px outermost canvas borders)
    clipping = check_object_clipping(image_path)
    total_bottom_shadow_px = bottom_shadow_count + opaque_shadow_protrusion

    # --- STRICT PASS / FAIL EVALUATION (NO EXCEPTIONS) ---
    issues = []
    if clipping["is_clipped"]:
        issues.append(
            f"Object clipped at 1px canvas boundary: {clipping['total_clipped_pixels']} px "
            f"on {', '.join(clipping['clipped_edges'])}."
        )
    if corner_artifacts > 0:
        issues.append(f"Dirty corners: {corner_artifacts} noisy pixels in 10x10 margins.")
    if category != "pure_white" and gray_halo_ratio > MAX_STUDIO_HALO_RATIO:
        issues.append(
            f"Studio light-gray halo exceeds 3.0% strict limit: "
            f"{gray_halo_ratio * 100:.2f}% ({contaminated_edge_px}/{evaluated_edge_px} edge px)."
        )
    if total_bottom_shadow_px > MAX_BOTTOM_SHADOW_TOTAL_PX:
        issues.append(
            f"Residual bottom floor shadow must be < 50 px: got {total_bottom_shadow_px} px "
            f"(semi={bottom_shadow_count}, opaque_protrusion={opaque_shadow_protrusion})."
        )

    status = "PASS" if len(issues) == 0 else "FAIL"

    return {
        "file": filename,
        "category": category,
        "status": status,
        "dimensions": {
            "width": orig_w,
            "height": orig_h,
            "mode": orig_mode,
        },
        "clipping": clipping,
        "bbox": {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "width": bbox_w,
            "height": bbox_h,
        },
        "metrics": {
            "clipped_pixels": clipping["total_clipped_pixels"],
            "corner_artifacts": corner_artifacts,
            "gray_halo_percentage": round(gray_halo_ratio * 100, 2),
            "contaminated_edge_px": contaminated_edge_px,
            "evaluated_edge_px": evaluated_edge_px,
            "bottom_shadow_pixels": bottom_shadow_count,
            "opaque_shadow_protrusion_px": opaque_shadow_protrusion,
            "bottom_shadow_total_pixels": total_bottom_shadow_px,
            "transparency_ratio": round(float((alpha == 0).sum() / alpha.size) * 100, 1),
        },
        "issues": issues,
    }


def main() -> int:
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "assets/brands/gsshop/decors/"
    png_files = sorted(glob.glob(os.path.join(target_dir, "*.png")))

    if not png_files:
        print(f"No PNG files found in {target_dir}")
        return 1

    print("\n============= STRICT ASSET QUALITY AUDIT REPORT =============")
    print(f"Scanning target: {target_dir} ({len(png_files)} files)")
    print(f"Strict Thresholds: Clipped Px == 0 | Corners == 0 | Studio Gray Halo <= {MAX_STUDIO_HALO_RATIO * 100:.1f}% | "
          f"Bottom Shadow Total < 50 px\n")

    results = []
    failed_count = 0
    for f in png_files:
        report = audit_png_asset(f)
        results.append(report)
        status_color = "\033[92mPASS\033[0m" if report["status"] == "PASS" else "\033[91mFAIL\033[0m"
        m = report["metrics"]
        clip = report["clipping"]
        dim = report.get("dimensions", {})
        dim_str = f"{dim.get('width', '?')}x{dim.get('height', '?')} {dim.get('mode', '?')}"
        print(f"[{status_color}] {report['file']} ({report['category']} | {dim_str})")
        print(
            f"       • Boundary Clipping: {clip['status']} ({m['clipped_pixels']} px) | "
            f"Studio Gray Halo: {m['gray_halo_percentage']}% "
            f"({m['contaminated_edge_px']}/{m['evaluated_edge_px']} px) | "
            f"Bottom Shadow: {m['bottom_shadow_total_pixels']} px "
            f"(semi={m['bottom_shadow_pixels']}, opaque={m['opaque_shadow_protrusion_px']}) | "
            f"Corners: {m['corner_artifacts']}"
        )
        if report["issues"]:
            failed_count += 1
            for issue in report["issues"]:
                print(f"       ⚠️  {issue}")
        print()

    print(f"Summary: {len(png_files) - failed_count} PASSED / {failed_count} FAILED")
    print("=============================================================\n")

    manifest_path = os.path.join(target_dir, "qa_audit_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as out:
        json.dump(results, out, indent=2)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
