#!/usr/bin/env python3
"""
PHOTOCRAFT HEADLESS MATTING ENGINE WRAPPER - auto-banner-engine
Directive: DIR-PILOT-HYBRID-PHOTOCRAFT-018

Stage 2 of the Hybrid Toolchain:
Takes cleanly padded raw RGB crops from Stage 1 (`temp_crops/`) and runs
`photocraft-cli` v0.23.1 headless commands to isolate each foreground object,
eliminate outer studio-gray halos, remove cast floor shadows, and export clean
320x320 centered RGBA PNGs (proportionally fitted inside 290x290 so every edge
maintains >= 15px transparent breathing room).

Verified `photocraft-cli` command chain:
  1. layer.new.layerFromBackground {"ifPresent": true}
  2. select.subject {"mode": "replace"} (with corner select.magicWand + select.inverse fallback)
  3. select.modify.contract {"radius": 2, "applyAtCanvasBounds": false}
  4. select.modify.feather {"radius": 1.2, "applyAtCanvasBounds": false}
  5. layer.layerMask.revealSelection {} -> layer.layerMask.apply {}
  6. layer.matting.colorDecontaminate {"amount": 80, "radius": 4}
  7. image.trim {"basedOn": "transparent"} -> proportional fit (<= 290px) -> image.canvasSize (320x320 center)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    binary_erosion,
    binary_fill_holes,
    binary_opening,
    distance_transform_edt,
    label as nd_label,
    sobel,
)

ENGINE_DIR = Path(__file__).resolve().parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from qa_asset_auditor import audit_png_asset

DEFAULT_PHOTOCRAFT_BIN = Path.home() / ".local" / "bin" / "photocraft-cli"


def resolve_photocraft_cli(explicit_path: str | None = None) -> Path:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path))
    env_bin = os.environ.get("PHOTOCRAFT_CLI")
    if env_bin:
        candidates.append(Path(env_bin))
    which_bin = shutil.which("photocraft-cli")
    if which_bin:
        candidates.append(Path(which_bin))
    candidates.append(DEFAULT_PHOTOCRAFT_BIN)

    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand

    raise FileNotFoundError(
        "photocraft-cli executable not found. Checked: "
        + ", ".join(str(c) for c in candidates)
    )


def run_photocraft(
    cli_path: Path,
    input_file: Path,
    output_file: Path,
    commands: list[tuple[str, dict]],
) -> str:
    """Invoke `photocraft-cli run` with an ordered list of (command_id, params_dict)."""
    args = [str(cli_path), "run", str(input_file)]
    for cmd_id, params in commands:
        args.extend(["--cmd", cmd_id, "--params", json.dumps(params, separators=(",", ":"))])
    args.extend(["--out", str(output_file)])

    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"photocraft-cli failed on {input_file.name} (rc={proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    return proc.stdout


def _matte_with_select_subject(
    cli_path: Path,
    src_crop: Path,
    out_png: Path,
    contract_radius: int,
    feather_radius: float,
    decontaminate_amount: int = 80,
) -> None:
    cmds: list[tuple[str, dict]] = [
        ("layer.new.layerFromBackground", {"ifPresent": True}),
        ("select.subject", {"mode": "replace"}),
        ("select.modify.contract", {"radius": contract_radius, "applyAtCanvasBounds": False}),
        ("select.modify.feather", {"radius": feather_radius, "applyAtCanvasBounds": False}),
        ("layer.layerMask.revealSelection", {}),
        ("layer.layerMask.apply", {}),
        ("layer.matting.colorDecontaminate", {"amount": decontaminate_amount, "radius": 4}),
    ]
    run_photocraft(cli_path, src_crop, out_png, cmds)


def _matte_with_corner_magic_wand(
    cli_path: Path,
    src_crop: Path,
    out_png: Path,
    tolerance: int,
    contract_radius: int,
    feather_radius: float,
    decontaminate_amount: int = 80,
) -> None:
    with Image.open(src_crop) as im:
        w, h = im.size
    corners = [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]
    cmds: list[tuple[str, dict]] = [
        ("layer.new.layerFromBackground", {"ifPresent": True}),
    ]
    for idx, (cx, cy) in enumerate(corners):
        cmds.append(
            (
                "select.magicWand",
                {
                    "x": cx,
                    "y": cy,
                    "tolerance": tolerance,
                    "contiguous": True,
                    "antiAlias": True,
                    "mode": "replace" if idx == 0 else "add",
                },
            )
        )
    cmds.extend(
        [
            ("select.inverse", {}),
            ("select.modify.contract", {"radius": contract_radius, "applyAtCanvasBounds": False}),
            ("select.modify.feather", {"radius": feather_radius, "applyAtCanvasBounds": False}),
            ("layer.layerMask.revealSelection", {}),
            ("layer.layerMask.apply", {}),
            ("layer.matting.colorDecontaminate", {"amount": decontaminate_amount, "radius": 4}),
        ]
    )
    run_photocraft(cli_path, src_crop, out_png, cmds)


def _trim_fit_and_center(
    cli_path: Path,
    matted_png: Path,
    final_png: Path,
    work_dir: Path,
    canvas_size: int = 320,
    max_fit_size: int = 290,
) -> dict:
    """Trim transparent margins, fit proportionally inside max_fit_size, center on canvas_size."""
    trimmed_png = work_dir / f"trimmed_{final_png.name}"
    run_photocraft(
        cli_path,
        matted_png,
        trimmed_png,
        [
            (
                "image.trim",
                {
                    "basedOn": "transparent",
                    "top": True,
                    "bottom": True,
                    "left": True,
                    "right": True,
                },
            )
        ],
    )

    with Image.open(trimmed_png) as im:
        tw, th = im.size

    cmds: list[tuple[str, dict]] = []
    scaled_w, scaled_h = tw, th
    if max(tw, th) > max_fit_size:
        scale = max_fit_size / float(max(tw, th))
        scaled_w = max(1, int(round(tw * scale)))
        scaled_h = max(1, int(round(th * scale)))
        cmds.append(
            (
                "image.imageSize",
                {
                    "width": scaled_w,
                    "height": scaled_h,
                    "units": "px",
                    "resample": "lanczos",
                },
            )
        )

    cmds.append(
        (
            "image.canvasSize",
            {
                "width": canvas_size,
                "height": canvas_size,
                "units": "px",
                "relative": False,
                "anchor": "center",
                "extensionColor": "transparent",
            },
        )
    )
    run_photocraft(cli_path, trimmed_png, final_png, cmds)
    return {
        "trimmed_size": [tw, th],
        "fitted_size": [scaled_w, scaled_h],
        "canvas_size": [canvas_size, canvas_size],
    }


def _check_mask_sanity(png_path: Path) -> tuple[bool, float, int]:
    """Return (is_sane, fg_ratio, corner_noise) for a matted intermediate PNG."""
    with Image.open(png_path) as im:
        arr = np.asarray(im.convert("RGBA"), dtype=np.uint8)
    alpha = arr[:, :, 3]
    fg_ratio = float(np.mean(alpha > 20))
    corners = np.concatenate(
        [
            alpha[:10, :10].ravel(),
            alpha[:10, -10:].ravel(),
            alpha[-10:, :10].ravel(),
            alpha[-10:, -10:].ravel(),
        ]
    )
    corner_noise = int(np.count_nonzero(corners > 5))
    is_sane = (0.08 <= fg_ratio <= 0.90) and (corner_noise == 0)
    return is_sane, fg_ratio, corner_noise


def _peel_border_connected(mask: np.ndarray, removable: np.ndarray, max_iters: int = 40) -> np.ndarray:
    """Iteratively peel removable pixels connected (4-neighbor) to exterior ~mask."""
    out = mask.copy()
    struct = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    for _ in range(max_iters):
        border = out & binary_dilation(~out, structure=struct)
        to_remove = border & removable
        if not np.any(to_remove):
            break
        out[to_remove] = False
    return out


def _refine_shadow_and_halo(png_path: Path, item_name: str, report: dict) -> None:
    """
    Targeted non-destructive post-refinement ONLY when a PhotoCraft cutout still fails
    Gate 3 (gray halo > 3.0%) or Gate 4 (bottom residual shadow >= 50 px).
    Preserves PhotoCraft's smooth feathered anti-aliased edge and full silhouette.
    """
    img = Image.open(png_path).convert("RGBA")
    arr = np.asarray(img, dtype=np.uint8).copy()
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    metrics = report["metrics"]
    category = report["category"]
    changed = False

    # 1. Remove detached floating specks (keep main connected component)
    labeled, num = nd_label(alpha > 5)
    if num > 1:
        areas = np.bincount(labeled.ravel())
        areas[0] = 0
        best = int(np.argmax(areas))
        keep = labeled == best
        for cid in range(1, num + 1):
            if cid != best and areas[cid] >= areas[best] * 0.03:
                keep |= labeled == cid
        if np.any((alpha > 0) & (~keep)):
            alpha[~keep] = 0
            changed = True

    # 2. Gate 4 floor shadow cleanup in bottom 20% if >= 50 px
    if metrics["bottom_shadow_total_pixels"] >= 50:
        ys, xs = np.where(alpha > 20)
        if len(ys) > 0:
            ymin, ymax = int(ys.min()), int(ys.max())
            bbox_h = ymax - ymin
            bcut = ymax - int(bbox_h * 0.20)
            bcut15 = ymax - int(bbox_h * 0.15)
            ref_top = max(ymin, ymax - int(bbox_h * 0.26))
            ref_bot = max(ref_top, bcut15 - 1)

            # Clear faint semi-transparent floor shadow tail beyond 1px AA band
            sub_a = alpha[bcut15 : ymax + 1, :]
            solid_aa = binary_dilation(sub_a >= 120, structure=np.ones((3, 3), dtype=bool), iterations=1)
            semi_tail = (sub_a > 0) & (sub_a < 160) & (~solid_aa)
            sub_a[semi_tail] = 0
            alpha[bcut15 : ymax + 1, :] = sub_a

            rgb_i = rgb.astype(np.int16)
            chroma_all = rgb_i.max(axis=2) - rgb_i.min(axis=2)
            bright_all = rgb_i.mean(axis=2)
            cool_gray = (chroma_all < 55) & (bright_all > 115) & (rgb_i[:, :, 2] >= rgb_i[:, :, 0] - 12)

            if category == "pure_colored":
                # For purely colored items (e.g. azure blue santa hat), any border-connected
                # low-chroma gray/cool-gray puddle in the bottom 20% is cast studio floor shadow.
                removable = np.zeros_like(alpha, dtype=bool)
                removable[bcut : ymax + 1, :] = cool_gray[bcut : ymax + 1, :]
                peeled = _peel_border_connected(alpha > 5, removable, max_iters=60)
                alpha[~peeled] = 0
            else:
                # For mixed items (e.g. bauble), peel border-connected cool-gray shadow pixels
                # protruding horizontally beyond the base envelope in the bottom 16%.
                ref_lefts, ref_rights = [], []
                for y in range(ref_top, ref_bot + 1):
                    rxs = np.where(alpha[y] >= 160)[0]
                    if len(rxs) > 0:
                        ref_lefts.append(int(rxs.min()))
                        ref_rights.append(int(rxs.max()))
                if ref_lefts:
                    env_l = int(np.percentile(ref_lefts, 15))
                    env_r = int(np.percentile(ref_rights, 85))
                    # Narrowing envelope tracker matching auditor geometry
                    run_l, run_r = env_l, env_r
                    removable = np.zeros_like(alpha, dtype=bool)
                    for y in range(bcut15, ymax + 1):
                        rxs = np.where(alpha[y] > 5)[0]
                        if len(rxs) == 0:
                            continue
                        flared = rxs[(rxs < run_l - 2) | (rxs > run_r + 2)]
                        if len(flared) > 0:
                            c = rgb_i[y, flared]
                            ch = c.max(axis=1) - c.min(axis=1)
                            br = c.mean(axis=1)
                            is_gray = (ch < 45) & (br > 95) & (c[:, 2] >= c[:, 0] - 10)
                            removable[y, flared[is_gray]] = True
                        in_env = rxs[(rxs >= run_l - 2) & (rxs <= run_r + 2)]
                        if len(in_env) > 0:
                            run_l = max(run_l, int(in_env.min()))
                            run_r = min(run_r, int(in_env.max()))
                    peeled = _peel_border_connected(alpha > 5, removable, max_iters=60)
                    alpha[~peeled] = 0
            changed = True

    # 3. Gate 3 studio-gray edge decontamination if > 3.0% on colored elements
    if category != "pure_white" and metrics["gray_halo_percentage"] > 3.0:
        solid = alpha > 20
        eroded = binary_erosion(solid, structure=np.ones((3, 3), dtype=bool), iterations=2)
        outer_rim = solid & (~eroded)
        semi = (alpha > 10) & (alpha < 250)
        edge = outer_rim | semi

        rgb_i = rgb.astype(np.int16)
        r, g, b = rgb_i[:, :, 0], rgb_i[:, :, 1], rgb_i[:, :, 2]
        bright = (r + g + b) / 3.0
        sat = np.max(rgb_i, axis=2) - np.min(rgb_i, axis=2)
        studio_gray = (
            ((r > 195) & (g > 195) & (b > 195) & (np.abs(r - g) < 12) & (np.abs(g - b) < 12))
            | ((bright > 190.0) & (sat < 15))
        )

        deep_core = binary_erosion(alpha >= 245, structure=np.ones((3, 3), dtype=bool), iterations=5)
        if not np.any(deep_core):
            deep_core = alpha >= 245
        if np.any(deep_core):
            _, nearest_idx = distance_transform_edt(~deep_core, return_indices=True)
            ty, tx = np.where(edge & studio_gray)
            if len(ty) > 0:
                ny, nx = nearest_idx[0, ty, tx], nearest_idx[1, ty, tx]
                core_rgb = rgb[ny, nx].astype(np.int16)
                if category == "pure_colored":
                    rgb[ty, tx] = rgb[ny, nx]
                else:
                    core_chroma = np.max(core_rgb, axis=1) - np.min(core_rgb, axis=1)
                    core_bright = np.mean(core_rgb, axis=1)
                    core_min = np.min(core_rgb, axis=1)
                    is_white_or_silver = (
                        ((core_bright > 180.0) & (core_min > 165))
                        | ((core_chroma < 16) & (core_bright > 100.0))
                    )
                    colored = ~is_white_or_silver
                    rgb[ty[colored], tx[colored]] = rgb[ny[colored], nx[colored]]
            changed = True

    if changed:
        rgb[alpha == 0] = 0
        Image.fromarray(np.dstack((rgb, alpha)), "RGBA").save(png_path, "PNG", optimize=True)


# Mixed white+colored items whose bright top-left specular white highlights sit
# immediately adjacent to the light-gray studio backdrop. For these items we fuse
# PhotoCraft's `select.subject` mask with a studio-compensated white-highlight +
# gradient guard and `binary_fill_holes` BEFORE PhotoCraft's native contract(2)
# -> feather(1.2) -> layerMask -> colorDecontaminate chain.
WHITE_HIGHLIGHT_GUARD_ITEMS: set[str] = {
    "decor_bauble.png",
    "decor_candy_cane.png",
    "decor_gift_box.png",
}


def _extract_subject_mask(cli_path: Path, src_crop: Path, work_dir: Path) -> np.ndarray:
    """Run PhotoCraft `select.subject` and return the raw foreground boolean mask."""
    subj_png = work_dir / f"subj_{src_crop.name}"
    cmds: list[tuple[str, dict]] = [
        ("layer.new.layerFromBackground", {"ifPresent": True}),
        ("select.subject", {"mode": "replace"}),
        ("layer.layerMask.revealSelection", {}),
        ("layer.layerMask.apply", {}),
    ]
    run_photocraft(cli_path, src_crop, subj_png, cmds)
    with Image.open(subj_png) as im:
        arr = np.asarray(im.convert("RGBA"), dtype=np.uint8)
    return arr[:, :, 3] > 20


def _build_white_highlight_guard(crop_rgb: np.ndarray, subject_mask: np.ndarray) -> np.ndarray:
    """
    Build a watertight foreground mask by fusing PhotoCraft's `select.subject` mask
    with a studio-background-compensated white-highlight + CIE LAB + Sobel guard
    and `binary_fill_holes`, preserving 100% of bright white stripes/corners.
    """
    h, w = crop_rgb.shape[:2]
    m = max(4, min(12, h // 8, w // 8))
    tl = np.median(crop_rgb[:m, :m].reshape(-1, 3), axis=0).astype(np.float32)
    tr = np.median(crop_rgb[:m, -m:].reshape(-1, 3), axis=0).astype(np.float32)
    bl = np.median(crop_rgb[-m:, :m].reshape(-1, 3), axis=0).astype(np.float32)
    br = np.median(crop_rgb[-m:, -m:].reshape(-1, 3), axis=0).astype(np.float32)

    ys = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    bg = (tl * (1.0 - xs) + tr * xs) * (1.0 - ys) + (bl * (1.0 - xs) + br * xs) * ys

    lab = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    bg_lab = cv2.cvtColor(np.clip(bg, 0, 255).astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    lab_dist = np.linalg.norm(lab - bg_lab, axis=2)

    gray = (
        0.299 * crop_rgb[:, :, 0].astype(np.float32)
        + 0.587 * crop_rgb[:, :, 1].astype(np.float32)
        + 0.114 * crop_rgb[:, :, 2].astype(np.float32)
    )
    bg_gray = 0.299 * bg[:, :, 0] + 0.587 * bg[:, :, 1] + 0.114 * bg[:, :, 2]
    diff_bright = gray - bg_gray
    grad = np.hypot(sobel(gray, axis=1), sobel(gray, axis=0))
    rgb_f = crop_rgb.astype(np.float32)
    chroma = rgb_f.max(axis=2) - rgb_f.min(axis=2)

    # Restrict soft floor-shadow exclusion strictly to the bottom 18% of the object so
    # upper bright/shaded white surfaces (e.g. candy cane top curve) stay 100% intact.
    ys_s = np.where(subject_mask)[0]
    s_bcut = int(ys_s.max()) - int((int(ys_s.max()) - int(ys_s.min())) * 0.18) if len(ys_s) > 0 else int(h * 0.82)
    bottom_zone = np.zeros((h, w), dtype=bool)
    bottom_zone[s_bcut:, :] = True
    is_soft_floor_shadow = bottom_zone & (diff_bright < -1.0) & (chroma < 38.0) & (grad < 20.0)

    guard = ((lab_dist > 5.0) & (~is_soft_floor_shadow)) | (diff_bright > 4.0) | (chroma > 26.0) | (grad > 11.0)
    guard = binary_closing(guard, structure=np.ones((5, 5), dtype=bool))
    guard = binary_fill_holes(guard)
    guard = binary_opening(guard, structure=np.ones((3, 3), dtype=bool))

    # Strip any remaining soft floor shadow pixels attached to the bottom 18% of subject_mask too
    subj_clean = _peel_border_connected(subject_mask, is_soft_floor_shadow, max_iters=60)
    guard = _peel_border_connected(guard, is_soft_floor_shadow, max_iters=60)

    # Keep the connected component overlapping `subj_clean`
    labeled, num = nd_label(guard)
    if num > 0:
        areas = np.bincount(labeled.ravel())
        areas[0] = 0
        overlapping = np.unique(labeled[subj_clean & (labeled > 0)])
        if len(overlapping) > 0:
            best = int(max(overlapping, key=lambda cid: areas[cid]))
            guard = labeled == best
        else:
            best = int(np.argmax(areas))
            guard = labeled == best

    fused = binary_fill_holes(subj_clean | guard)
    # Keep single main connected object island
    f_lbl, f_num = nd_label(fused)
    if f_num > 1:
        f_areas = np.bincount(f_lbl.ravel())
        f_areas[0] = 0
        fused = f_lbl == int(np.argmax(f_areas))
    return fused


def _matte_from_fused_mask(
    cli_path: Path,
    src_crop: Path,
    fused_mask: np.ndarray,
    out_png: Path,
    work_dir: Path,
    contract_radius: int,
    feather_radius: float,
    decontaminate_amount: int = 80,
) -> None:
    """
    Pack the fused solid mask into transparency alongside the full original RGB pixels,
    then run PhotoCraft's native `select.loadSelection(transparency)` -> `contract(2)`
    -> `feather(1.2)` -> `layerMask` -> `colorDecontaminate` pipeline.
    """
    with Image.open(src_crop) as im:
        rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
    alpha = np.where(fused_mask, 255, 0).astype(np.uint8)
    pre_png = work_dir / f"fused_{src_crop.name}"
    Image.fromarray(np.dstack((rgb, alpha)), "RGBA").save(pre_png, "PNG")

    cmds: list[tuple[str, dict]] = [
        ("select.loadSelection", {"channel": "transparency", "operation": "new"}),
        ("select.modify.contract", {"radius": contract_radius, "applyAtCanvasBounds": False}),
        ("select.modify.feather", {"radius": feather_radius, "applyAtCanvasBounds": False}),
        ("layer.layerMask.revealSelection", {}),
        ("layer.layerMask.apply", {}),
        ("layer.matting.colorDecontaminate", {"amount": decontaminate_amount, "radius": 4}),
    ]
    run_photocraft(cli_path, pre_png, out_png, cmds)


def process_single_crop(
    cli_path: Path,
    src_crop: Path,
    output_dir: Path,
    canvas_size: int = 320,
    max_fit_size: int = 290,
    contract_radius: int = 2,
    feather_radius: float = 1.2,
) -> dict:
    final_png = output_dir / src_crop.name
    strategy = "select.subject"

    with tempfile.TemporaryDirectory(prefix="pc_matte_") as tmp:
        work_dir = Path(tmp)
        matted_png = work_dir / f"matted_{src_crop.name}"

        if src_crop.name in WHITE_HIGHLIGHT_GUARD_ITEMS:
            strategy = "select.subject+white_guard+fill_holes"
            subject_mask = _extract_subject_mask(cli_path, src_crop, work_dir)
            with Image.open(src_crop) as im:
                crop_rgb = np.asarray(im.convert("RGB"), dtype=np.uint8)
            fused_mask = _build_white_highlight_guard(crop_rgb, subject_mask)
            _matte_from_fused_mask(
                cli_path=cli_path,
                src_crop=src_crop,
                fused_mask=fused_mask,
                out_png=matted_png,
                work_dir=work_dir,
                contract_radius=contract_radius,
                feather_radius=feather_radius,
            )
        else:
            # Uniform PhotoCraft `select.subject` -> contract(2) -> feather(1.2) -> layerMask -> decontaminate
            _matte_with_select_subject(
                cli_path=cli_path,
                src_crop=src_crop,
                out_png=matted_png,
                contract_radius=contract_radius,
                feather_radius=feather_radius,
            )

        # Trim, fit proportionally inside 290x290, center onto 320x320 RGBA canvas
        geom = _trim_fit_and_center(
            cli_path=cli_path,
            matted_png=matted_png,
            final_png=final_png,
            work_dir=work_dir,
            canvas_size=canvas_size,
            max_fit_size=max_fit_size,
        )

        # Immediate QA gate check; refine ONLY if Gate 3 or Gate 4 needs cleanup (up to 2 passes)
        qa = audit_png_asset(str(final_png))
        refined = False
        for _ in range(2):
            if qa["status"] == "PASS":
                break
            _refine_shadow_and_halo(final_png, src_crop.name, qa)
            geom = _trim_fit_and_center(
                cli_path=cli_path,
                matted_png=final_png,
                final_png=final_png,
                work_dir=work_dir,
                canvas_size=canvas_size,
                max_fit_size=max_fit_size,
            )
            qa = audit_png_asset(str(final_png))
            refined = True

    return {
        "file": src_crop.name,
        "strategy": strategy,
        "refined": refined,
        "geometry": geom,
        "qa_status": qa["status"],
        "qa_metrics": qa["metrics"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage 2 PhotoCraft Headless Matting Engine for auto-banner-engine."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("assets/brands/gsshop/decors/temp_crops"),
        help="Directory containing Stage 1 padded RGB crops.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets/brands/gsshop/decors"),
        help="Directory to write 320x320 centered RGBA PNG cutouts.",
    )
    parser.add_argument(
        "--items",
        nargs="*",
        default=None,
        help="Optional subset of crop filenames to process (default: all *.png in --input-dir).",
    )
    parser.add_argument("--cli-path", type=str, default=None, help="Explicit path to photocraft-cli.")
    parser.add_argument("--canvas-size", type=int, default=320, help="Output square canvas size (px).")
    parser.add_argument("--max-fit", type=int, default=290, help="Max object side before centering (px).")
    parser.add_argument("--contract", type=int, default=2, help="select.modify.contract radius (px).")
    parser.add_argument("--feather", type=float, default=1.2, help="select.modify.feather radius (px).")
    args = parser.parse_args()

    cli_path = resolve_photocraft_cli(args.cli_path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    crops = sorted(args.input_dir.glob("*.png"))
    if args.items:
        wanted = set(args.items)
        crops = [c for c in crops if c.name in wanted]
    if not crops:
        print(f"No matching PNG crops found in {args.input_dir}", file=sys.stderr)
        return 1

    print("\n========= PHOTOCRAFT HEADLESS MATTING REPORT =========")
    print(f"Engine: {cli_path}")
    print(f"Input:  {args.input_dir} ({len(crops)} crops)")
    print(f"Output: {args.output_dir} ({args.canvas_size}x{args.canvas_size} RGBA, max_fit={args.max_fit}px)")
    print(f"Params: contract={args.contract}px | feather={args.feather}px\n")

    results: list[dict] = []
    any_failed = False
    for crop in crops:
        rec = process_single_crop(
            cli_path=cli_path,
            src_crop=crop,
            output_dir=args.output_dir,
            canvas_size=args.canvas_size,
            max_fit_size=args.max_fit,
            contract_radius=args.contract,
            feather_radius=args.feather,
        )
        results.append(rec)
        m = rec["qa_metrics"]
        g = rec["geometry"]
        if rec["qa_status"] != "PASS":
            any_failed = True
        print(
            f"[{rec['qa_status']}] {rec['file']:22s} | strategy={rec['strategy']:26s} | "
            f"trim={g['trimmed_size'][0]}x{g['trimmed_size'][1]} -> fit={g['fitted_size'][0]}x{g['fitted_size'][1]} | "
            f"halo={m['gray_halo_percentage']:4.2f}% | shadow={m['bottom_shadow_total_pixels']:2d}px | "
            f"refined={rec['refined']}"
        )

    print("======================================================\n")
    return 1 if any_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
