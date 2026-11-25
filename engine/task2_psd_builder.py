#!/usr/bin/env python3
"""
Task 2 Layered Master PSD & Preview Builder — Meritz Partners
(`engine/task2_psd_builder.py`).

Compiles the official Meritz Brand Book (`assets/brands/meritz/Meritz_brand_book.pdf`)
compliant 1200x1200 performance banner into:
  - `deliverables/task2_meritz/meritz_partners_master.psd` (7 structured layer groups)
  - `deliverables/task2_meritz/meritz_partners_preview.jpg` (sRGB, Quality 95)

Required Top-Level PSD Layer Groups:
  [BACKGROUND], [LOGO], [FEATURE_ICONS], [HEADLINE], [HERO_VISUAL], [CTA_BUTTON], [LEGAL]

Typography uses native `assets/fonts/Pretendard-*.woff2` rasterized cleanly per layer
via headless Playwright Chromium, with automatic fallback to macOS `AppleSDGothicNeo.ttc`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageCms, ImageDraw, ImageFilter, ImageFont
from psd_tools import PSDImage
from psd_tools.constants import Resource, Tag
from psd_tools.psd.image_resources import ImageResource

ROOT = Path(__file__).resolve().parent.parent
TOKENS_PATH = ROOT / "assets" / "brands" / "meritz" / "tokens.json"
LOGO_PATH = ROOT / "assets" / "logos" / "meritz" / "logo.png"
VISUALS_DIR = ROOT / "assets" / "brands" / "meritz" / "visuals"
FONTS_DIR = ROOT / "assets" / "fonts"
DELIVERABLES_DIR = ROOT / "deliverables" / "task2_meritz"

# Exact mandatory legal disclaimer strings (Task 2 Compliance Gate)
LEGAL_LINE_1 = "*‘24년 8월 ~ ‘25년 7월 수익자의 첫 달 평균 금액 기준, 수익은 보험체결 후 발생, 개인차 있음"
LEGAL_LINE_2 = "*보험업법상 보험설계사를 모집하는 것으로 정규 또는 비정규 직원 채용과는 무관"

SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def hex_to_rgba(hex_str: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    clean = hex_str.strip().lstrip("#")
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16), alpha)


def render_html_layers_via_playwright(
    specs: List[Dict[str, object]],
    tmp_dir: Path,
) -> Dict[str, Image.Image]:
    """
    Rasterize transparent RGBA PNG layers using native Pretendard `.woff2` fonts
    in a single headless Chromium session.
    """
    font_css = f"""
      @font-face {{
        font-family: 'Pretendard';
        src: url('file://{(FONTS_DIR / "Pretendard-Regular.woff2").as_posix()}') format('woff2');
        font-weight: 400; font-style: normal;
      }}
      @font-face {{
        font-family: 'Pretendard';
        src: url('file://{(FONTS_DIR / "Pretendard-SemiBold.woff2").as_posix()}') format('woff2');
        font-weight: 600; font-style: normal;
      }}
      @font-face {{
        font-family: 'Pretendard';
        src: url('file://{(FONTS_DIR / "Pretendard-Bold.woff2").as_posix()}') format('woff2');
        font-weight: 700; font-style: normal;
      }}
      @font-face {{
        font-family: 'Pretendard';
        src: url('file://{(FONTS_DIR / "Pretendard-ExtraBold.woff2").as_posix()}') format('woff2');
        font-weight: 800; font-style: normal;
      }}
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      html, body {{
        background: transparent;
        font-family: 'Pretendard', -apple-system, 'Apple SD Gothic Neo', sans-serif;
        -webkit-font-smoothing: antialiased;
        text-rendering: geometricPrecision;
      }}
    """

    manifest_path = tmp_dir / "layers.json"

    manifest = {"fontCss": font_css, "layers": []}
    for spec in specs:
        manifest["layers"].append({
            "id": spec["id"],
            "width": int(spec["width"]),
            "height": int(spec["height"]),
            "html": spec["html"],
            "out": str(tmp_dir / f"{spec['id']}.png"),
        })
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    node_script = """
import fs from 'node:fs';
import { chromium } from 'playwright';

const manifest = JSON.parse(fs.readFileSync(process.argv[1], 'utf-8'));
const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 1 });

for (const item of manifest.layers) {
  await page.setViewportSize({ width: item.width, height: item.height });
  const doc = `<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8" /><style>${manifest.fontCss}</style></head><body style="width:${item.width}px;height:${item.height}px;overflow:hidden;">${item.html}</body></html>`;
  await page.setContent(doc, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: item.out, omitBackground: true });
}
await browser.close();
"""

    subprocess.run(
        ["node", "--input-type=module", "-e", node_script, str(manifest_path)],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )

    out: Dict[str, Image.Image] = {}
    for spec in specs:
        p = tmp_dir / f"{spec['id']}.png"
        with Image.open(p) as im:
            out[str(spec["id"])] = im.convert("RGBA").copy()
    return out


def render_text_fallback_pil(
    text: str,
    width: int,
    height: int,
    font_size: int,
    color: Tuple[int, int, int, int],
    weight: str = "bold",
    align: str = "left",
) -> Image.Image:
    """Fallback PIL rasterizer using macOS AppleSDGothicNeo.ttc if Chromium is unavailable."""
    idx_map = {"regular": 0, "semibold": 4, "bold": 6, "extrabold": 14}
    ttc_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    try:
        font = ImageFont.truetype(ttc_path, font_size, index=idx_map.get(weight, 6))
    except Exception:
        font = ImageFont.load_default()
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (width - tw) // 2 if align == "center" else 0
    y = max(0, (height - th) // 2 - bbox[1])
    draw.text((x, y), text, font=font, fill=color)
    return img


def add_layer(
    group,
    img: Image.Image,
    ascii_name: str,
    left: int,
    top: int,
    unicode_name: str | None = None,
) -> None:
    """
    Create a PixelLayer inside `group` with ASCII Pascal name and optional full
    Photoshop Unicode Layer Name (`luni` tagged block) so Hangul & curly quotes
    round-trip cleanly in Photoshop and `psd_tools`.
    """
    pl = group.create_pixel_layer(img.convert("RGBA"), name=ascii_name, top=top, left=left)
    if unicode_name:
        pl.tagged_blocks.set_data(Tag.UNICODE_LAYER_NAME, unicode_name)


def build_background_layers(
    w: int,
    h: int,
    chalk_rgba: Tuple[int, int, int, int],
    white_rgba: Tuple[int, int, int, int],
    red_rgba: Tuple[int, int, int, int],
) -> List[Tuple[str, Image.Image, int, int]]:
    # 1. Full Chalk White (#F2F2F2) institutional canvas
    bg_chalk = Image.new("RGBA", (w, h), chalk_rgba)

    # 2. Pure White (#FFFFFF) architectural card frame with crisp hairline border
    inset = int(round(w * 0.03))  # 36px on 1200
    card_w = w - inset * 2
    card_h = h - inset * 2
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle(
        (0, 0, card_w - 1, card_h - 1),
        radius=12,
        fill=white_rgba,
        outline=(218, 218, 218, 255),
        width=2,
    )
    # Top institutional Vermillion Red architectural accent bar (6px tall)
    cd.rectangle((0, 0, card_w - 1, 6), fill=red_rgba)

    # 3. Hairline architectural structural dividers (header & legal footer rules)
    rules = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rules)
    margin_x = int(round(w * 0.068))  # 82px
    rd.line([(margin_x, int(round(h * 0.132))), (w - margin_x, int(round(h * 0.132)))], fill=(230, 230, 230, 255), width=2)
    rd.line([(margin_x, int(round(h * 0.856))), (w - margin_x, int(round(h * 0.856)))], fill=(230, 230, 230, 255), width=2)

    return [
        ("canvas_chalk_white", bg_chalk, 0, 0),
        ("architectural_card_white", card, inset, inset),
        ("structural_divider_rules", rules, 0, 0),
    ]


def build_cta_layers(
    w: int,
    h: int,
    red_rgba: Tuple[int, int, int, int],
    label_img: Image.Image,
) -> List[Tuple[str, Image.Image, int, int, str | None]]:
    btn_w = int(round(w * 0.56))   # 672px
    btn_h = int(round(h * 0.095))  # 114px
    btn_x = (w - btn_w) // 2
    btn_y = int(round(h * 0.725))  # 870px

    # Tight architectural elevation shadow
    pad = 36
    sh = Image.new("RGBA", (btn_w + pad * 2, btn_h + pad * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle(
        (pad, pad + 8, pad + btn_w, pad + btn_h + 8),
        radius=10,
        fill=(20, 20, 20, 42),
    )
    sh = sh.filter(ImageFilter.GaussianBlur(radius=14))

    # Crisp Vermillion Red (#EF3B24) architectural CTA rectangle
    btn = Image.new("RGBA", (btn_w, btn_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(btn)
    bd.rounded_rectangle((0, 0, btn_w - 1, btn_h - 1), radius=10, fill=red_rgba)

    return [
        ("cta_shadow", sh, btn_x - pad, btn_y - pad, None),
        ("cta_bg_meritz_red", btn, btn_x, btn_y, "CTA Button (#EF3B24)"),
        ("cta_label", label_img, btn_x, btn_y, "꿀부업 시작 바로가기 >"),
    ]


def build_task2_psd(
    width: int = 1200,
    height: int = 1200,
    out_dir: Path = DELIVERABLES_DIR,
) -> Tuple[Path, Path]:
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    red_hex = tokens["colors"]["accent"]          # #EF3B24
    obsidian_hex = tokens["colors"]["primary"]    # #141414
    white_hex = tokens["colors"]["surface"]       # #FFFFFF
    chalk_hex = tokens["colors"].get("canvas", "#F2F2F2")
    muted_hex = tokens["colors"]["text_muted"]    # #5A5D62

    red_rgba = hex_to_rgba(red_hex)
    obsidian_rgba = hex_to_rgba(obsidian_hex)
    white_rgba = hex_to_rgba(white_hex)
    chalk_rgba = hex_to_rgba(chalk_hex)
    muted_rgba = hex_to_rgba(muted_hex)

    # Verify required input assets exist
    required_files = [
        LOGO_PATH,
        VISUALS_DIR / "hero_coin_3d.png",
        VISUALS_DIR / "icon_sprout_beginner.png",
        VISUALS_DIR / "icon_flexible_growth.png",
        VISUALS_DIR / "icon_honey_sidejob.png",
    ]
    for f in required_files:
        if not f.exists():
            raise FileNotFoundError(f"Required Task 2 input missing: {f}")

    # Load verified raster assets
    logo_src = Image.open(LOGO_PATH).convert("RGBA")
    hero_coin_src = Image.open(VISUALS_DIR / "hero_coin_3d.png").convert("RGBA")
    icon_sprout_src = Image.open(VISUALS_DIR / "icon_sprout_beginner.png").convert("RGBA")
    icon_growth_src = Image.open(VISUALS_DIR / "icon_flexible_growth.png").convert("RGBA")
    icon_honey_src = Image.open(VISUALS_DIR / "icon_honey_sidejob.png").convert("RGBA")

    # Layout geometry (scaled cleanly relative to 1200x1200)
    sx = width / 1200.0
    sy = height / 1200.0

    # Prepare Playwright HTML specs for crisp native Pretendard typography & architectural tags
    btn_w = int(round(width * 0.56))
    btn_h = int(round(height * 0.095))

    html_specs = [
        {
            "id": "top_badges",
            "width": int(round(440 * sx)),
            "height": int(round(58 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;width:100%;height:100%;">
              <div style="display:inline-flex;align-items:center;gap:10px;height:46px;padding:0 18px 0 46px;background:{white_hex};border:1.5px solid {obsidian_hex};border-radius:6px;font-size:21px;font-weight:700;color:{obsidian_hex};letter-spacing:-0.02em;">
                경력무관
              </div>
              <div style="display:inline-flex;align-items:center;height:46px;padding:0 18px;background:{chalk_hex};border:1.5px solid {obsidian_hex};border-radius:6px;font-size:21px;font-weight:700;color:{obsidian_hex};letter-spacing:-0.02em;">
                나이 무관
              </div>
            </div>""",
        },
        {
            "id": "headline_eyebrow",
            "width": int(round(620 * sx)),
            "height": int(round(52 * sy)),
            "html": f"""
            <div style="display:flex;align-items:center;gap:14px;width:100%;height:100%;">
              <span style="display:inline-block;width:7px;height:28px;background:{red_hex};"></span>
              <span style="font-size:30px;font-weight:700;color:{red_hex};letter-spacing:-0.03em;line-height:1;">초보자도 첫달부터 수익+</span>
            </div>""",
        },
        {
            "id": "headline_sub",
            "width": int(round(640 * sx)),
            "height": int(round(88 * sy)),
            "html": f"""
            <div style="display:flex;align-items:center;width:100%;height:100%;">
              <span style="font-size:66px;font-weight:700;color:{obsidian_hex};letter-spacing:-0.035em;line-height:1.05;">첫달 평균 수익</span>
            </div>""",
        },
        {
            "id": "headline_main",
            "width": int(round(690 * sx)),
            "height": int(round(215 * sy)),
            "html": f"""
            <div style="display:flex;align-items:baseline;width:100%;height:100%;padding-top:4px;">
              <span style="font-size:184px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.045em;line-height:0.96;">150</span>
              <span style="font-size:138px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.04em;line-height:0.96;margin-left:4px;">만원</span>
            </div>""",
        },
        {
            "id": "proof_cards_bg",
            "width": int(round(1036 * sx)),
            "height": int(round(142 * sy)),
            "html": f"""
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;width:100%;height:100%;">
              <div style="background:{chalk_hex};border:1.5px solid #DFDFDF;border-radius:8px;padding:20px 18px 20px 102px;display:flex;flex-direction:column;justify-content:center;gap:6px;">
                <div style="font-size:25px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.03em;line-height:1.1;">경력무관</div>
                <div style="font-size:18px;font-weight:600;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">초보자 누구나 시작</div>
              </div>
              <div style="background:{chalk_hex};border:1.5px solid #DFDFDF;border-radius:8px;padding:20px 18px 20px 102px;display:flex;flex-direction:column;justify-content:center;gap:6px;">
                <div style="font-size:25px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.03em;line-height:1.1;">첫달부터 수익+</div>
                <div style="font-size:18px;font-weight:600;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">체결 즉시 실적 반영</div>
              </div>
              <div style="background:{chalk_hex};border:1.5px solid #DFDFDF;border-radius:8px;padding:20px 18px 20px 102px;display:flex;flex-direction:column;justify-content:center;gap:6px;">
                <div style="font-size:25px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.03em;line-height:1.1;">나이 안보는 부업</div>
                <div style="font-size:18px;font-weight:600;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">원하는 시간 꿀부업</div>
              </div>
            </div>""",
        },
        {
            "id": "cta_label",
            "width": btn_w,
            "height": btn_h,
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:40px;font-weight:800;color:{white_hex};letter-spacing:-0.025em;line-height:1;">꿀부업 시작 바로가기 &gt;</span>
            </div>""",
        },
        {
            "id": "legal_line_1",
            "width": int(round(1040 * sx)),
            "height": int(round(36 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:20px;font-weight:400;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">{LEGAL_LINE_1}</span>
            </div>""",
        },
        {
            "id": "legal_line_2",
            "width": int(round(1040 * sx)),
            "height": int(round(36 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:20px;font-weight:400;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">{LEGAL_LINE_2}</span>
            </div>""",
        },
    ]

    try:
        with tempfile.TemporaryDirectory(prefix="meritz_psd_") as td:
            rendered = render_html_layers_via_playwright(html_specs, Path(td))
    except Exception as exc:
        print(f"[WARN] Playwright typography render unavailable ({exc}); falling back to PIL AppleSDGothicNeo.")
        rendered = {
            "top_badges": render_text_fallback_pil("경력무관  |  나이 무관", int(440 * sx), int(58 * sy), 22, obsidian_rgba, "bold", "center"),
            "headline_eyebrow": render_text_fallback_pil("초보자도 첫달부터 수익+", int(620 * sx), int(52 * sy), 30, red_rgba, "bold", "left"),
            "headline_sub": render_text_fallback_pil("첫달 평균 수익", int(640 * sx), int(88 * sy), 64, obsidian_rgba, "bold", "left"),
            "headline_main": render_text_fallback_pil("150만원", int(690 * sx), int(215 * sy), 160, obsidian_rgba, "extrabold", "left"),
            "proof_cards_bg": render_text_fallback_pil("경력무관  ·  첫달부터 수익+  ·  나이 안보는 부업", int(1036 * sx), int(142 * sy), 26, obsidian_rgba, "bold", "center"),
            "cta_label": render_text_fallback_pil("꿀부업 시작 바로가기 >", btn_w, btn_h, 40, white_rgba, "extrabold", "center"),
            "legal_line_1": render_text_fallback_pil(LEGAL_LINE_1, int(1040 * sx), int(36 * sy), 20, muted_rgba, "regular", "center"),
            "legal_line_2": render_text_fallback_pil(LEGAL_LINE_2, int(1040 * sx), int(36 * sy), 20, muted_rgba, "regular", "center"),
        }

    # Assemble Layered Master PSD (bottom-to-top stacking order)
    psd = PSDImage.new("RGBA", (width, height))

    # 1. [BACKGROUND]
    grp_bg = psd.create_group(name="[BACKGROUND]", open_folder=True)
    for lname, lim, lx, ly in build_background_layers(width, height, chalk_rgba, white_rgba, red_rgba):
        add_layer(grp_bg, lim, lname, lx, ly)

    # 2. [LOGO] — Official Meritz Partners Logo (loaded verbatim from assets/logos/meritz/logo.png)
    grp_logo = psd.create_group(name="[LOGO]", open_folder=True)
    logo_target_w = int(round(296 * sx))
    logo_target_h = max(1, int(round(logo_target_w * (logo_src.height / logo_src.width))))
    logo_resized = logo_src.resize((logo_target_w, logo_target_h), Image.Resampling.LANCZOS)
    add_layer(grp_logo, logo_resized, "meritz_partners_logo", left=int(round(82 * sx)), top=int(round(80 * sy)), unicode_name="Meritz Partners Official Logo (logo.png)")

    # 3. [FEATURE_ICONS] — Top-right badge cluster + 3-column geometric infographic proof-point strip
    grp_icons = psd.create_group(name="[FEATURE_ICONS]", open_folder=True)
    # Top-right tag frames & labels
    top_badges_x = int(round(678 * sx))
    top_badges_y = int(round(71 * sy))
    add_layer(grp_icons, rendered["top_badges"], "top_badges_frame", left=top_badges_x, top=top_badges_y, unicode_name="Top Badges (경력무관 / 나이 무관)")

    # Small geometric sprout icon seated cleanly inside the left padding of the `경력무관` top tag
    mini_sprout_sz = int(round(28 * sx))
    mini_sprout = icon_sprout_src.resize((mini_sprout_sz, mini_sprout_sz), Image.Resampling.LANCZOS)
    add_layer(
        grp_icons,
        mini_sprout,
        "top_badge_icon_sprout",
        left=top_badges_x + int(round(188 * sx)),
        top=top_badges_y + int(round(15 * sy)),
        unicode_name="Top Badge Icon (경력무관)",
    )

    # 3-Column Structured Proof-Point Strip (y = 668..810)
    strip_x = int(round(82 * sx))
    strip_y = int(round(668 * sy))
    add_layer(grp_icons, rendered["proof_cards_bg"], "proof_cards_grid", left=strip_x, top=strip_y, unicode_name="Proof-Point Infographic Grid")

    icon_sz = int(round(68 * sx))
    col_step = int(round(351 * sx))  # (1036 - 32) / 3 + 16 ≈ 350.7
    icon_offset_x = int(round(18 * sx))
    icon_offset_y = int(round(37 * sy))
    for i, (src_icon, ascii_id, label_ko) in enumerate([
        (icon_sprout_src, "icon_sprout_beginner", "Icon: 경력무관 (Sprout Geometric)"),
        (icon_growth_src, "icon_flexible_growth", "Icon: 첫달부터 수익+ (Financial Growth)"),
        (icon_honey_src, "icon_honey_sidejob", "Icon: 나이 안보는 부업 (Hexagonal Side Revenue)"),
    ]):
        ic = src_icon.resize((icon_sz, icon_sz), Image.Resampling.LANCZOS)
        add_layer(
            grp_icons,
            ic,
            ascii_id,
            left=strip_x + i * col_step + icon_offset_x,
            top=strip_y + icon_offset_y,
            unicode_name=label_ko,
        )

    # 4. [HEADLINE] — Institutional High-Contrast Obsidian Black Typography
    grp_headline = psd.create_group(name="[HEADLINE]", open_folder=True)
    add_layer(grp_headline, rendered["headline_eyebrow"], "headline_eyebrow", left=int(round(82 * sx)), top=int(round(226 * sy)), unicode_name="초보자도 첫달부터 수익+")
    add_layer(grp_headline, rendered["headline_sub"], "headline_sub", left=int(round(82 * sx)), top=int(round(290 * sy)), unicode_name="첫달 평균 수익")
    add_layer(grp_headline, rendered["headline_main"], "headline_main_150", left=int(round(76 * sx)), top=int(round(378 * sy)), unicode_name="150만원")

    # Crisp Vermillion Red horizontal institutional rule beneath 150
    rule_w, rule_h = int(round(92 * sx)), int(round(6 * sy))
    red_rule = Image.new("RGBA", (rule_w, rule_h), red_rgba)
    add_layer(grp_headline, red_rule, "headline_red_accent_rule", left=int(round(84 * sx)), top=int(round(602 * sy)))

    # 5. [HERO_VISUAL] — Chiseled 3D Bullion Coin hovering cleanly beside/above `만원`
    grp_hero = psd.create_group(name="[HERO_VISUAL]", open_folder=True)
    coin_sz = int(round(405 * sx))
    coin_resized = hero_coin_src.resize((coin_sz, coin_sz), Image.Resampling.LANCZOS)
    add_layer(
        grp_hero,
        coin_resized,
        "hero_coin_3d",
        left=int(round(738 * sx)),
        top=int(round(206 * sy)),
        unicode_name="Hero 3D Bullion Coin (hero_coin_3d.png)",
    )

    # 6. [CTA_BUTTON] — Sharp Vermillion Red (#EF3B24) Architectural CTA
    grp_cta = psd.create_group(name="[CTA_BUTTON]", open_folder=True)
    for lname, lim, lx, ly, uname in build_cta_layers(width, height, red_rgba, rendered["cta_label"]):
        add_layer(grp_cta, lim, lname, lx, ly, unicode_name=uname)

    # 7. [LEGAL] — Mandatory 2-Line Institutional Disclaimers (verbatim Unicode layer names)
    grp_legal = psd.create_group(name="[LEGAL]", open_folder=True)
    legal_x = (width - rendered["legal_line_1"].width) // 2
    add_layer(grp_legal, rendered["legal_line_1"], "legal_disclaimer_1", left=legal_x, top=int(round(1056 * sy)), unicode_name=LEGAL_LINE_1)
    add_layer(grp_legal, rendered["legal_line_2"], "legal_disclaimer_2", left=legal_x, top=int(round(1094 * sy)), unicode_name=LEGAL_LINE_2)

    # Embed sRGB ICC Profile in PSD image resources
    try:
        psd.image_resources[Resource.ICC_PROFILE] = ImageResource(key=Resource.ICC_PROFILE, data=SRGB_ICC)
    except Exception:
        pass

    out_dir.mkdir(parents=True, exist_ok=True)
    psd_path = out_dir / "meritz_partners_master.psd"
    jpg_path = out_dir / "meritz_partners_preview.jpg"

    psd.save(str(psd_path))

    # Reload saved PSD and composite to guarantee 100% parity between master PSD and preview JPEG
    reloaded = PSDImage.open(str(psd_path))
    preview_rgb = reloaded.composite().convert("RGB")
    preview_rgb.save(
        str(jpg_path),
        "JPEG",
        quality=95,
        subsampling=0,
        optimize=True,
        icc_profile=SRGB_ICC,
    )

    print(f"[OK] Compiled Master PSD:  {psd_path.relative_to(ROOT)} ({width}x{height}, {psd_path.stat().st_size / 1024:.1f} KB)")
    print(f"[OK] Exported Preview JPG: {jpg_path.relative_to(ROOT)} (sRGB Q95, {jpg_path.stat().st_size / 1024:.1f} KB)")
    return psd_path, jpg_path


def build_task2_option2_psd(
    width: int = 1200,
    height: int = 1200,
    out_dir: Path = DELIVERABLES_DIR,
    task_path: Path | None = None,
) -> Tuple[Path, Path]:
    """
    Compiles Task 2 Option 2 (High-Concept Creative Hook — Zero-Gravity Architecture)
    into `deliverables/task2_meritz/meritz_partners_option2.psd` and
    `deliverables/task2_meritz/meritz_partners_option2_preview.jpg`.
    """
    tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    red_hex = tokens["colors"]["accent"]          # #EF3B24
    obsidian_hex = tokens["colors"]["primary"]    # #141414
    white_hex = tokens["colors"]["surface"]       # #FFFFFF
    chalk_hex = tokens["colors"].get("canvas", "#F2F2F2")
    muted_hex = tokens["colors"]["text_muted"]    # #5A5D62

    red_rgba = hex_to_rgba(red_hex)
    obsidian_rgba = hex_to_rgba(obsidian_hex)
    white_rgba = hex_to_rgba(white_hex)
    chalk_rgba = hex_to_rgba(chalk_hex)
    muted_rgba = hex_to_rgba(muted_hex)

    # Load Option 2 task config (defaults to tasks/task2_creative/meritz_option2.json)
    cfg_path = task_path or (ROOT / "tasks" / "task2_creative" / "meritz_option2.json")
    task_cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    content = task_cfg.get("content", {})
    eyebrow_text = content.get("sub_headline", "초보자도 첫달부터 수익+")
    cta_text = content.get("cta_text", "꿀부업 시작 바로가기 >")
    disclaimers = content.get("disclaimers", [LEGAL_LINE_1, LEGAL_LINE_2])
    legal_1 = disclaimers[0] if len(disclaimers) > 0 else LEGAL_LINE_1
    legal_2 = disclaimers[1] if len(disclaimers) > 1 else LEGAL_LINE_2

    hero_rel = content.get("visual_stage_asset", "assets/brands/meritz/visuals/hero_option2_scene.png")
    hero_path = Path(hero_rel) if Path(hero_rel).is_absolute() else (ROOT / hero_rel)

    required_files = [
        LOGO_PATH,
        hero_path,
        VISUALS_DIR / "icon_sprout_beginner.png",
        VISUALS_DIR / "icon_flexible_growth.png",
        VISUALS_DIR / "icon_honey_sidejob.png",
    ]
    for f in required_files:
        if not f.exists():
            raise FileNotFoundError(f"Required Task 2 Option 2 input missing: {f}")

    logo_src = Image.open(LOGO_PATH).convert("RGBA")
    hero_scene_src = Image.open(hero_path).convert("RGBA")
    icon_sprout_src = Image.open(VISUALS_DIR / "icon_sprout_beginner.png").convert("RGBA")
    icon_growth_src = Image.open(VISUALS_DIR / "icon_flexible_growth.png").convert("RGBA")
    icon_honey_src = Image.open(VISUALS_DIR / "icon_honey_sidejob.png").convert("RGBA")

    sx = width / 1200.0
    sy = height / 1200.0
    btn_w = int(round(width * 0.56))
    btn_h = int(round(height * 0.095))

    cta_html_text = cta_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    html_specs = [
        {
            "id": "top_badges",
            "width": int(round(440 * sx)),
            "height": int(round(58 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:flex-end;align-items:center;gap:12px;width:100%;height:100%;">
              <div style="display:inline-flex;align-items:center;gap:10px;height:46px;padding:0 18px 0 46px;background:{white_hex};border:1.5px solid {obsidian_hex};border-radius:6px;font-size:21px;font-weight:700;color:{obsidian_hex};letter-spacing:-0.02em;">
                경력무관
              </div>
              <div style="display:inline-flex;align-items:center;height:46px;padding:0 18px;background:{chalk_hex};border:1.5px solid {obsidian_hex};border-radius:6px;font-size:21px;font-weight:700;color:{obsidian_hex};letter-spacing:-0.02em;">
                나이 무관
              </div>
            </div>""",
        },
        {
            "id": "headline_eyebrow",
            "width": int(round(620 * sx)),
            "height": int(round(46 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;gap:12px;width:100%;height:100%;">
              <span style="display:inline-block;width:6px;height:24px;background:{red_hex};"></span>
              <span style="font-size:27px;font-weight:700;color:{red_hex};letter-spacing:-0.03em;line-height:1;">{eyebrow_text}</span>
            </div>""",
        },
        {
            "id": "headline_sub",
            "width": int(round(780 * sx)),
            "height": int(round(88 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:70px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.035em;line-height:1.05;">첫달 평균 수익</span>
            </div>""",
        },
        {
            "id": "headline_unit_manwon",
            "width": int(round(190 * sx)),
            "height": int(round(96 * sy)),
            "html": f"""
            <div style="display:flex;align-items:center;width:100%;height:100%;">
              <span style="font-size:74px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.04em;line-height:0.96;">만원</span>
            </div>""",
        },
        {
            "id": "proof_cards_bg",
            "width": int(round(1036 * sx)),
            "height": int(round(104 * sy)),
            "html": f"""
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;width:100%;height:100%;">
              <div style="background:{chalk_hex};border:1.5px solid #DFDFDF;border-radius:8px;padding:14px 16px 14px 86px;display:flex;flex-direction:column;justify-content:center;gap:4px;">
                <div style="font-size:22px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.03em;line-height:1.1;">경력무관</div>
                <div style="font-size:16px;font-weight:600;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">초보자 누구나 시작</div>
              </div>
              <div style="background:{chalk_hex};border:1.5px solid #DFDFDF;border-radius:8px;padding:14px 16px 14px 86px;display:flex;flex-direction:column;justify-content:center;gap:4px;">
                <div style="font-size:22px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.03em;line-height:1.1;">첫달부터 수익+</div>
                <div style="font-size:16px;font-weight:600;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">체결 즉시 실적 반영</div>
              </div>
              <div style="background:{chalk_hex};border:1.5px solid #DFDFDF;border-radius:8px;padding:14px 16px 14px 86px;display:flex;flex-direction:column;justify-content:center;gap:4px;">
                <div style="font-size:22px;font-weight:800;color:{obsidian_hex};letter-spacing:-0.03em;line-height:1.1;">나이 안보는 부업</div>
                <div style="font-size:16px;font-weight:600;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">원하는 시간 꿀부업</div>
              </div>
            </div>""",
        },
        {
            "id": "cta_label",
            "width": btn_w,
            "height": btn_h,
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:40px;font-weight:800;color:{white_hex};letter-spacing:-0.025em;line-height:1;">{cta_html_text}</span>
            </div>""",
        },
        {
            "id": "legal_line_1",
            "width": int(round(1040 * sx)),
            "height": int(round(36 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:20px;font-weight:400;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">{legal_1}</span>
            </div>""",
        },
        {
            "id": "legal_line_2",
            "width": int(round(1040 * sx)),
            "height": int(round(36 * sy)),
            "html": f"""
            <div style="display:flex;justify-content:center;align-items:center;width:100%;height:100%;">
              <span style="font-size:20px;font-weight:400;color:{muted_hex};letter-spacing:-0.02em;line-height:1.2;">{legal_2}</span>
            </div>""",
        },
    ]

    try:
        with tempfile.TemporaryDirectory(prefix="meritz_psd_opt2_") as td:
            rendered = render_html_layers_via_playwright(html_specs, Path(td))
    except Exception as exc:
        print(f"[WARN] Playwright typography render unavailable ({exc}); falling back to PIL AppleSDGothicNeo.")
        rendered = {
            "top_badges": render_text_fallback_pil("경력무관  |  나이 무관", int(440 * sx), int(58 * sy), 22, obsidian_rgba, "bold", "center"),
            "headline_eyebrow": render_text_fallback_pil(eyebrow_text, int(620 * sx), int(46 * sy), 27, red_rgba, "bold", "center"),
            "headline_sub": render_text_fallback_pil("첫달 평균 수익", int(760 * sx), int(84 * sy), 66, obsidian_rgba, "extrabold", "center"),
            "headline_unit_manwon": render_text_fallback_pil("만원", int(270 * sx), int(138 * sy), 112, obsidian_rgba, "extrabold", "left"),
            "proof_cards_bg": render_text_fallback_pil("경력무관  ·  첫달부터 수익+  ·  나이 안보는 부업", int(1036 * sx), int(104 * sy), 24, obsidian_rgba, "bold", "center"),
            "cta_label": render_text_fallback_pil(cta_text, btn_w, btn_h, 40, white_rgba, "extrabold", "center"),
            "legal_line_1": render_text_fallback_pil(legal_1, int(1040 * sx), int(36 * sy), 20, muted_rgba, "regular", "center"),
            "legal_line_2": render_text_fallback_pil(legal_2, int(1040 * sx), int(36 * sy), 20, muted_rgba, "regular", "center"),
        }

    psd = PSDImage.new("RGBA", (width, height))

    # 1. [BACKGROUND] — Chalk White canvas + Pure White architectural card (pristine breathing room)
    grp_bg = psd.create_group(name="[BACKGROUND]", open_folder=True)
    bg_layers = build_background_layers(width, height, chalk_rgba, white_rgba, red_rgba)
    for lname, lim, lx, ly in bg_layers:
        add_layer(grp_bg, lim, lname, lx, ly)

    # 2. [LOGO] — Official Meritz Partners Logo
    grp_logo = psd.create_group(name="[LOGO]", open_folder=True)
    logo_target_w = int(round(296 * sx))
    logo_target_h = max(1, int(round(logo_target_w * (logo_src.height / logo_src.width))))
    logo_resized = logo_src.resize((logo_target_w, logo_target_h), Image.Resampling.LANCZOS)
    add_layer(grp_logo, logo_resized, "meritz_partners_logo", left=int(round(82 * sx)), top=int(round(78 * sy)), unicode_name="Meritz Partners Official Logo (logo.png)")

    # 3. [FEATURE_ICONS] — Top-right institutional tags + compact 3-column proof strip
    grp_icons = psd.create_group(name="[FEATURE_ICONS]", open_folder=True)
    top_badges_x = int(round(678 * sx))
    top_badges_y = int(round(70 * sy))
    add_layer(grp_icons, rendered["top_badges"], "top_badges_frame", left=top_badges_x, top=top_badges_y, unicode_name="Top Badges (경력무관 / 나이 무관)")

    mini_sprout_sz = int(round(28 * sx))
    mini_sprout = icon_sprout_src.resize((mini_sprout_sz, mini_sprout_sz), Image.Resampling.LANCZOS)
    add_layer(
        grp_icons,
        mini_sprout,
        "top_badge_icon_sprout",
        left=top_badges_x + int(round(188 * sx)),
        top=top_badges_y + int(round(15 * sy)),
        unicode_name="Top Badge Icon (경력무관)",
    )

    strip_x = int(round(82 * sx))
    strip_y = int(round(744 * sy))
    add_layer(grp_icons, rendered["proof_cards_bg"], "proof_cards_grid", left=strip_x, top=strip_y, unicode_name="Proof-Point Infographic Grid")

    icon_sz = int(round(56 * sx))
    col_step = int(round(350 * sx))
    icon_offset_x = int(round(16 * sx))
    icon_offset_y = int(round(24 * sy))
    for i, (src_icon, ascii_id, label_ko) in enumerate([
        (icon_sprout_src, "icon_sprout_beginner", "Icon: 경력무관 (Sprout Geometric)"),
        (icon_growth_src, "icon_flexible_growth", "Icon: 첫달부터 수익+ (Financial Growth)"),
        (icon_honey_src, "icon_honey_sidejob", "Icon: 나이 안보는 부업 (Hexagonal Side Revenue)"),
    ]):
        ic = src_icon.resize((icon_sz, icon_sz), Image.Resampling.LANCZOS)
        add_layer(
            grp_icons,
            ic,
            ascii_id,
            left=strip_x + i * col_step + icon_offset_x,
            top=strip_y + icon_offset_y,
            unicode_name=label_ko,
        )

    # 4. [HERO_VISUAL] — Positioned strictly BELOW [HEADLINE] so zero text glyphs are ever occluded;
    #    shifted +30px right (198 -> 228) & +15px down (216 -> 231) for optical centering & rhythm
    grp_hero = psd.create_group(name="[HERO_VISUAL]", open_folder=True)
    hero_sz = int(round(596 * sx))
    hero_resized = hero_scene_src.resize((hero_sz, hero_sz), Image.Resampling.LANCZOS)
    add_layer(
        grp_hero,
        hero_resized,
        "hero_option2_scene",
        left=int(round(228 * sx)),
        top=int(round(231 * sy)),
        unicode_name="Zero-Gravity 3D Hero Hook (hero_option2_scene.png)",
    )

    # 5. [HEADLINE] — Stacked strictly ABOVE [HERO_VISUAL] in PSD layer hierarchy;
    #    "만원" shifted +30px right (744 -> 774) & +15px down (478 -> 493) in lockstep with core
    grp_headline = psd.create_group(name="[HEADLINE]", open_folder=True)
    eyebrow_x = (width - rendered["headline_eyebrow"].width) // 2
    sub_x = (width - rendered["headline_sub"].width) // 2
    add_layer(grp_headline, rendered["headline_eyebrow"], "headline_eyebrow", left=eyebrow_x, top=int(round(156 * sy)), unicode_name=eyebrow_text)
    add_layer(grp_headline, rendered["headline_sub"], "headline_sub", left=sub_x, top=int(round(196 * sy)), unicode_name="첫달 평균 수익")

    unit_x = int(round(774 * sx))
    unit_y = int(round(493 * sy))
    add_layer(grp_headline, rendered["headline_unit_manwon"], "headline_unit_manwon", left=unit_x, top=unit_y, unicode_name="만원 (3D 150 Unit Lockup)")

    # Proportionally shortened Vermillion Red institutional accent rule beneath "만원"
    rule_w, rule_h = int(round(58 * sx)), int(round(5 * sy))
    red_rule = Image.new("RGBA", (rule_w, rule_h), red_rgba)
    add_layer(grp_headline, red_rule, "headline_red_accent_rule", left=unit_x + int(round(3 * sx)), top=unit_y + int(round(88 * sy)))

    # 6. [CTA_BUTTON] — Sharp Vermillion Red (#EF3B24) Architectural CTA
    grp_cta = psd.create_group(name="[CTA_BUTTON]", open_folder=True)
    for lname, lim, lx, ly, uname in build_cta_layers(width, height, red_rgba, rendered["cta_label"]):
        add_layer(grp_cta, lim, lname, lx, ly, unicode_name=uname)

    # 7. [LEGAL] — Mandatory 2-Line Institutional Disclaimers
    grp_legal = psd.create_group(name="[LEGAL]", open_folder=True)
    legal_x = (width - rendered["legal_line_1"].width) // 2
    add_layer(grp_legal, rendered["legal_line_1"], "legal_disclaimer_1", left=legal_x, top=int(round(1054 * sy)), unicode_name=legal_1)
    add_layer(grp_legal, rendered["legal_line_2"], "legal_disclaimer_2", left=legal_x, top=int(round(1092 * sy)), unicode_name=legal_2)

    try:
        psd.image_resources[Resource.ICC_PROFILE] = ImageResource(key=Resource.ICC_PROFILE, data=SRGB_ICC)
    except Exception:
        pass

    out_dir.mkdir(parents=True, exist_ok=True)
    psd_path = out_dir / "meritz_partners_option2.psd"
    jpg_path = out_dir / "meritz_partners_option2_preview.jpg"

    psd.save(str(psd_path))

    reloaded = PSDImage.open(str(psd_path))
    preview_rgb = reloaded.composite().convert("RGB")
    preview_rgb.save(
        str(jpg_path),
        "JPEG",
        quality=95,
        subsampling=0,
        optimize=True,
        icc_profile=SRGB_ICC,
    )

    print(f"[OK] Compiled Option 2 PSD:  {psd_path.relative_to(ROOT)} ({width}x{height}, {psd_path.stat().st_size / 1024:.1f} KB)")
    print(f"[OK] Exported Preview JPG:   {jpg_path.relative_to(ROOT)} (sRGB Q95, {jpg_path.stat().st_size / 1024:.1f} KB)")
    return psd_path, jpg_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile Task 2 Meritz Partners Layered Master PSD & Preview.")
    parser.add_argument("--option", type=int, choices=[1, 2], default=1, help="Creative option to compile (1=Master, 2=Zero-Gravity Architecture).")
    parser.add_argument("--task", default=None, help="Optional Task 2 JSON config path (used with --option 2).")
    parser.add_argument("--width", type=int, default=1200, help="Canvas width in px (default: 1200).")
    parser.add_argument("--height", type=int, default=1200, help="Canvas height in px (default: 1200).")
    parser.add_argument("--out-dir", default=str(DELIVERABLES_DIR), help="Deliverables output directory.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir

    if args.option == 2:
        task_path = None
        if args.task:
            task_path = Path(args.task)
            if not task_path.is_absolute():
                task_path = ROOT / task_path
        build_task2_option2_psd(width=args.width, height=args.height, out_dir=out_dir, task_path=task_path)
    else:
        build_task2_psd(width=args.width, height=args.height, out_dir=out_dir)


if __name__ == "__main__":
    main()
