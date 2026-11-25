"""
Automated PSD Brand & Token Extractor (`psd-tools`).
Parses client `.psd` files to extract layer trees, text typography (font names,
sizes, colors), solid fills, and transparent layer cutouts, and emits
`brand_tokens.schema.json`-compliant `tokens.json` files.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from psd_tools import PSDImage


def _rgb_to_hex(r: float, g: float, b: float) -> str:
    ri = max(0, min(255, int(round(r * 255 if r <= 1.0 and g <= 1.0 and b <= 1.0 else r))))
    gi = max(0, min(255, int(round(g * 255 if r <= 1.0 and g <= 1.0 and b <= 1.0 else g))))
    bi = max(0, min(255, int(round(b * 255 if r <= 1.0 and g <= 1.0 and b <= 1.0 else b))))
    return f"#{ri:02X}{gi:02X}{bi:02X}"


def _extract_type_info(layer: Any) -> Dict[str, Any]:
    info: Dict[str, Any] = {"text": getattr(layer, "text", "").strip()}
    try:
        ed = layer.engine_dict
        style_run = ed.get("StyleRun", {})
        run_array = style_run.get("RunArray", [])
        if run_array:
            ss = run_array[0].get("StyleSheet", {}).get("StyleSheetData", {})
            if "FontSize" in ss:
                info["font_size"] = float(ss["FontSize"])
            if "FillColor" in ss:
                vals = ss["FillColor"].get("Values", [])
                if len(vals) >= 4:
                    info["color_hex"] = _rgb_to_hex(vals[1], vals[2], vals[3])
        font_set = ed.get("ResourceDict", {}).get("FontSet", [])
        if font_set:
            info["fonts"] = [str(f.get("Name", "")) for f in font_set if f.get("Name")]
    except Exception:
        pass
    return info


def parse_psd(psd_path: str) -> Dict[str, Any]:
    psd = PSDImage.open(psd_path)
    layers_out: List[Dict[str, Any]] = []
    colors_found: List[str] = []
    fonts_found: List[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        for layer in node:
            entry: Dict[str, Any] = {
                "name": layer.name,
                "kind": layer.kind,
                "visible": bool(layer.visible),
                "bbox": [int(layer.left), int(layer.top), int(layer.right), int(layer.bottom)],
                "size": [int(layer.width), int(layer.height)],
                "depth": depth,
            }
            if layer.kind == "type":
                tinfo = _extract_type_info(layer)
                entry["type"] = tinfo
                if tinfo.get("color_hex"):
                    colors_found.append(tinfo["color_hex"])
                for fn in tinfo.get("fonts", []):
                    if fn not in fonts_found:
                        fonts_found.append(fn)
            layers_out.append(entry)
            if layer.is_group():
                walk(layer, depth + 1)

    walk(psd)
    return {
        "psd_path": psd_path,
        "canvas_size": [psd.width, psd.height],
        "layer_count": len(layers_out),
        "fonts_found": fonts_found,
        "colors_found": list(dict.fromkeys(colors_found)),
        "layers": layers_out,
    }


def export_matching_layer(psd_path: str, name_query: str, out_png: str) -> bool:
    psd = PSDImage.open(psd_path)
    q = name_query.lower()

    def find_layer(node: Any):
        for layer in node:
            if q in layer.name.lower() and layer.width > 0 and layer.height > 0:
                return layer
            if layer.is_group():
                hit = find_layer(layer)
                if hit is not None:
                    return hit
        return None

    target = find_layer(psd)
    if target is None:
        return False
    os.makedirs(os.path.dirname(os.path.abspath(out_png)), exist_ok=True)
    im = target.composite()
    im.save(out_png, "PNG", optimize=True)
    print(f"Exported layer '{target.name}' ({im.size[0]}x{im.size[1]}) -> {out_png}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract brand tokens & layers from client PSD files.")
    parser.add_argument("--psd", required=True, help="Path to input .psd file")
    parser.add_argument("--report", help="Optional JSON report output path")
    parser.add_argument("--export-layer", nargs=2, metavar=("NAME_SUBSTR", "OUT_PNG"), help="Export first matching layer to PNG")
    parser.add_argument("--write-tokens", help="Output path for brand_tokens.schema.json-compliant tokens.json")
    parser.add_argument("--brand-id", default="brand", help="Brand ID for tokens.json")
    parser.add_argument("--brand-name", default="Brand", help="Brand Name for tokens.json")
    parser.add_argument("--logo-url", default="", help="Logo URL for tokens.json")
    args = parser.parse_args()

    data = parse_psd(args.psd)
    print(f"Parsed {args.psd}: {data['canvas_size'][0]}x{data['canvas_size'][1]}, {data['layer_count']} layers, fonts={data['fonts_found']}, colors={data['colors_found']}")

    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        Path(args.report).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.export_layer:
        ok = export_matching_layer(args.psd, args.export_layer[0], args.export_layer[1])
        if not ok:
            print(f"Warning: no layer matching '{args.export_layer[0]}' found.")

    if args.write_tokens:
        colors = data["colors_found"]
        tokens = {
            "$schema": "../../../config/brand_tokens.schema.json",
            "brand_id": args.brand_id,
            "brand_name": args.brand_name,
            "logo_url": args.logo_url,
            "colors": {
                "primary": colors[0] if len(colors) > 0 else "#111111",
                "accent": colors[1] if len(colors) > 1 else "#D9FF00",
                "surface": "#111315",
                "text_headline": "#FFFFFF",
                "text_muted": "#9CA3AF",
                "cta_text": "#111111",
            },
            "typography": {
                "font_family": "Pretendard",
                "font_weights": {"regular": 400, "semibold": 600, "bold": 700, "hook": 900},
                "letter_spacing": {"tight": "-0.04em", "normal": "-0.02em", "wide": "0.02em"},
            },
            "ui": {
                "cta_radius": "999px",
                "badge_style": "outlined",
                "elevation": {"y": 14, "blur": 24, "opacity": 0.22},
            },
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.write_tokens)), exist_ok=True)
        Path(args.write_tokens).write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.write_tokens}")


if __name__ == "__main__":
    main()
