#!/usr/bin/env python3
"""Slice a 3x3 decor grid image into individual transparent PNG assets."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

DEFAULT_INPUT = Path("assets/brands/gsshop/raw/9 christmas items azure blue.jpg")
DEFAULT_OUTPUT_DIR = Path("assets/brands/gsshop/decors")

DEFAULT_ITEM_MAPPING = [
    {"index": 0, "name": "decor_snowman.png", "row": 0, "col": 0},
    {"index": 1, "name": "decor_snowflake.png", "row": 0, "col": 1},
    {"index": 2, "name": "decor_gift_box.png", "row": 0, "col": 2},
    {"index": 3, "name": "decor_bauble.png", "row": 1, "col": 0},
    {"index": 4, "name": "decor_tree.png", "row": 1, "col": 1},
    {"index": 5, "name": "decor_candy_cane.png", "row": 1, "col": 2},
    {"index": 6, "name": "decor_santa_hat.png", "row": 2, "col": 0},
    {"index": 7, "name": "decor_gingerbread.png", "row": 2, "col": 1},
    {"index": 8, "name": "decor_stocking.png", "row": 2, "col": 2},
]


def slice_and_remove_bg(
    input_path: Path,
    output_dir: Path,
    rows: int = 3,
    cols: int = 3,
    inset: float = 0.0,
    model: str = "u2net",
    feather: int = 1,
) -> list[Path]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Source grid image not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    bg_remover = Path(__file__).resolve().parent / "bg_remover.py"

    exported: list[Path] = []
    with Image.open(input_path) as grid_img:
        width, height = grid_img.size
        cell_w = width / cols
        cell_h = height / rows
        pad_x = cell_w * max(0.0, inset)
        pad_y = cell_h * max(0.0, inset)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            for item in DEFAULT_ITEM_MAPPING:
                row = item["row"]
                col = item["col"]
                if row >= rows or col >= cols:
                    continue

                x0 = int(round(col * cell_w + pad_x))
                y0 = int(round(row * cell_h + pad_y))
                x1 = int(round((col + 1) * cell_w - pad_x))
                y1 = int(round((row + 1) * cell_h - pad_y))

                crop = grid_img.crop((x0, y0, x1, y1))
                temp_crop = tmp_root / f"crop_{item['index']}_{item['name']}"
                crop.save(temp_crop, "PNG")

                dest = output_dir / item["name"]
                subprocess.run(
                    [
                        sys.executable,
                        str(bg_remover),
                        "--input",
                        str(temp_crop),
                        "--output",
                        str(dest),
                        "--model",
                        model,
                        "--feather",
                        str(feather),
                    ],
                    check=True,
                )
                exported.append(dest)

    return exported


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Slice a grid image into individual transparent PNG cutouts."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Source grid image.")
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory."
    )
    parser.add_argument("--rows", type=int, default=3, help="Number of grid rows.")
    parser.add_argument("--cols", type=int, default=3, help="Number of grid columns.")
    parser.add_argument(
        "--inset",
        type=float,
        default=0.0,
        help="Fractional inset margin per cell side (e.g. 0.05 for 5%%).",
    )
    parser.add_argument("--model", default="u2net", help="rembg model passed to bg_remover.py.")
    parser.add_argument("--feather", type=int, default=1, help="Feather radius passed to bg_remover.py.")
    args = parser.parse_args()

    exported = slice_and_remove_bg(
        input_path=args.input,
        output_dir=args.output_dir,
        rows=args.rows,
        cols=args.cols,
        inset=args.inset,
        model=args.model,
        feather=args.feather,
    )
    print(f"Exported {len(exported)} decor items to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
