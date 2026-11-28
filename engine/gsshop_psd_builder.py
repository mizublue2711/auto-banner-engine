#!/usr/bin/env python3
"""
DIR-EXPORT-LAYERED-PSD-032: GS SHOP Layered Master PSD Builder
(`engine/gsshop_psd_builder.py`)

Compiles the GS SHOP 1080x1080 Master Banner (`DIR-MASTER-ASSEMBLY-FINAL-031`)
into a fully editable, multi-layer RGB 8-bit Adobe Photoshop PSD with 5 structured
Layer Groups and 19 independent transparent RGBA raster layers (ZERO flattening):

  ├── 05_UI_Lockup (Topmost)
  │    ├── CTA_Pill_Button
  │    ├── Headline_3D
  │    └── Header_Logo_Live
  ├── 04_Atmosphere_Particles
  │    ├── Snow_Particles_Overlay
  │    └── Snow_Tier_3_Front
  ├── 03_Floating_Heroes_and_Decor
  │    ├── Decor_Flying_Lid
  │    ├── Flying_Single_Tangerine
  │    ├── Decor_Snowflake
  │    ├── Decor_Candy_Cane
  │    ├── Decor_Bauble
  │    ├── Burst_Puffer_Jacket
  │    ├── Burst_Knit_Sweater
  │    └── Shopping_Bag_Pink
  ├── 02_GiftBox_and_Tucked_Items
  │    ├── Box_Front_Rim
  │    ├── Tucked_Tangerine_Cluster
  │    ├── Tucked_Toilet_Paper
  │    ├── Box_Back_Interior
  │    ├── Box_Contact_Shadow
  │    └── Snow_Tier_2_Box_Bed
  └── 01_Backdrop (Bottom-most)
       ├── Snow_Tier_1_Back
       └── Background_Winter

Output:
  /Users/macbookpro/auto-banner-engine/output/TASK_GSSHOP/gsshop_master_1080x1080.psd
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageCms, ImageFilter
from psd_tools import PSDImage
from psd_tools.constants import Resource, Tag
from psd_tools.psd.image_resources import ImageResource

ROOT = Path(__file__).resolve().parent.parent
GSSHOP_DIR = ROOT / "assets" / "brands" / "gsshop"
LAYERS_DIR = GSSHOP_DIR / "layers"
FONTS_DIR = ROOT / "assets" / "fonts"

DEFAULT_OUT_PSD = ROOT / "output" / "TASK_GSSHOP" / "gsshop_master_1080x1080.psd"
CANVAS_W = 1080
CANVAS_H = 1080

SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


# ==============================================================================
# IMAGE & CSS-PARITY TRANSFORM HELPERS
# ==============================================================================
def load_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(f"Required GS SHOP asset missing: {path}")
    with Image.open(path) as im:
        return im.convert("RGBA").copy()


def apply_opacity(img: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 0.999:
        return img
    arr = np.array(img.convert("RGBA"), dtype=np.float32)
    arr[..., 3] = np.clip(arr[..., 3] * opacity, 0.0, 255.0)
    return Image.fromarray(np.round(arr).astype(np.uint8), mode="RGBA")


def add_drop_shadow(
    img: Image.Image,
    offset_x: int,
    offset_y: int,
    blur_radius: float,
    color_rgba: Tuple[int, int, int, int],
) -> Tuple[Image.Image, int, int]:
    """
    Replicate CSS `filter: drop-shadow(offset_x offset_y blur color)` on a tight RGBA
    layer, returning `(composited_img, pad_left, pad_top)` so the caller can shift
    `(left - pad_left, top - pad_top)` without clipping the shadow.
    """
    pad = int(math.ceil(blur_radius * 2.5)) + max(abs(offset_x), abs(offset_y)) + 4
    nw = img.width + pad * 2
    nh = img.height + pad * 2

    # Build colored shadow silhouette from alpha channel
    alpha = img.split()[3]
    sh_canvas = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
    sh_alpha = Image.new("L", (nw, nh), 0)
    sh_alpha.paste(alpha, (pad + offset_x, pad + offset_y))
    sh_alpha = sh_alpha.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    r, g, b, a_max = color_rgba
    a_arr = (np.array(sh_alpha, dtype=np.float32) * (a_max / 255.0)).clip(0.0, 255.0)
    sh_arr = np.zeros((nh, nw, 4), dtype=np.uint8)
    sh_arr[..., 0] = r
    sh_arr[..., 1] = g
    sh_arr[..., 2] = b
    sh_arr[..., 3] = np.round(a_arr).astype(np.uint8)
    sh_canvas = Image.fromarray(sh_arr, mode="RGBA")

    fg_canvas = Image.new("RGBA", (nw, nh), (0, 0, 0, 0))
    fg_canvas.paste(img, (pad, pad))
    out = Image.alpha_composite(sh_canvas, fg_canvas)
    return out, pad, pad


def rotate_css(
    img: Image.Image,
    css_deg: float,
    origin_x_frac: float = 0.5,
    origin_y_frac: float = 0.5,
) -> Tuple[Image.Image, float, float]:
    """
    Rotate an RGBA image by `css_deg` (positive = clockwise, matching CSS `rotate()`),
    around `(origin_x_frac * w, origin_y_frac * h)` in the original image's coordinate frame.
    Returns `(rotated_img, dx, dy)` where `(left + dx, top + dy)` is the exact new top-left
    placement so the pivot stays pinned in stage space.
    """
    if abs(css_deg) < 1e-4:
        return img, 0.0, 0.0

    w, h = img.size
    px = w * origin_x_frac
    py = h * origin_y_frac
    cx = w * 0.5
    cy = h * 0.5

    # PIL rotate() is counter-clockwise around image center, so pass -css_deg
    rot = img.rotate(-css_deg, resample=Image.Resampling.BICUBIC, expand=True)
    rw, rh = rot.size

    # Where did the original pivot (px, py) land inside `rot`?
    rad = math.radians(css_deg)
    vx, vy = px - cx, py - cy
    rvx = vx * math.cos(rad) - vy * math.sin(rad)
    rvy = vx * math.sin(rad) + vy * math.cos(rad)
    new_px = rw * 0.5 + rvx
    new_py = rh * 0.5 + rvy

    dx = px - new_px
    dy = py - new_py
    return rot, dx, dy


def render_cropped_band(
    src: Image.Image,
    box_left: int,
    box_top: int,
    box_w: int,
    box_h: int,
    img_left: float,
    img_top: float,
    img_w: int,
    img_h: int,
) -> Tuple[Image.Image, int, int]:
    """
    Replicate a CSS container (`overflow: hidden` at `box_left, box_top, box_w, box_h`)
    containing an inner stretched `<img>` at `(img_left, img_top, img_w, img_h)`.
    Returns `(cropped_rgba, box_left, box_top)`.
    """
    scaled = src.resize((img_w, img_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    canvas.paste(scaled, (int(round(img_left)), int(round(img_top))), scaled)
    return canvas, box_left, box_top


def render_header_layers_via_playwright(tmp_dir: Path) -> Tuple[Image.Image, Image.Image]:
    """
    Rasterize the Z=13 header elements into two separate, independent 1080x160 RGBA layers
    matching `templates/master_1080x1080.html` (DIR-UI-APPLE-GLASS-CAPSULE-038, Option A):
      1. `Header_Mobile_Live_Logo` (`MOBILE LIVE logo.png` anchored at top: 45px, left: 50px)
      2. `Header_Glass_Capsule` (Apple Frosted Glass Capsule centered 12px above GS SHOP at y=135px)
    """
    logo_png = tmp_dir / "header_mobile_live_logo.png"
    capsule_png = tmp_dir / "header_glass_capsule.png"
    logo_url = (LAYERS_DIR / "13_ui_mobile_live_logo.png").as_uri()
    font_bold = (FONTS_DIR / "Pretendard-Bold.woff2").as_uri()
    font_eb = (FONTS_DIR / "Pretendard-ExtraBold.woff2").as_uri()

    base_styles = f"""
  @font-face {{
    font-family: "Pretendard";
    src: url("{font_bold}") format("woff2");
    font-weight: 700; font-style: normal;
  }}
  @font-face {{
    font-family: "Pretendard";
    src: url("{font_eb}") format("woff2");
    font-weight: 800; font-style: normal;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{
    width: 1080px; height: 160px;
    background: transparent;
    overflow: hidden;
    font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", sans-serif;
    -webkit-font-smoothing: antialiased;
    text-rendering: geometricPrecision;
  }}
"""

    logo_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<style>{base_styles}
  .mobile-live-logo-wrap {{
    position: absolute;
    top: 48px;
    left: 50px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 258px;
    height: 34px;
    overflow: hidden;
  }}
  .mobile-live-logo-img {{
    width: 344px;
    height: 258px;
    max-width: none;
    max-height: none;
    flex-shrink: 0;
    object-fit: contain;
    display: block;
  }}
</style>
</head>
<body>
  <div class="mobile-live-logo-wrap">
    <img class="mobile-live-logo-img" src="{logo_url}" alt="MOBILE LIVE" />
  </div>
</body>
</html>"""

    # Shared CSS for the Top Frosted Glass Capsule (1:1 match with master_1080x1080.html)
    capsule_css = f"""{base_styles}
  .capsule-stage {{
    position: relative;
    width: 1080px;
    height: 200px;
  }}
  .z13-glass-capsule-layer {{
    position: absolute;
    top: 100px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .glass-subcopy-capsule {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 580px;
    gap: 18px;
    padding: 10px 28px 10px 14px;
    background: rgba(255, 255, 255, 0.72);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.85);
    border-radius: 9999px;
    box-shadow: 0 6px 24px -2px rgba(15, 23, 42, 0.10),
                0 1px 3px rgba(255, 255, 255, 0.6) inset;
    margin: 0 auto;
  }}
  .glass-badge-live {{
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: #DC2626;
    color: #FFFFFF;
    padding: 7px 16px;
    border-radius: 9999px;
    font-size: 18px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: 0.6px;
    box-shadow: 0 2px 8px rgba(220, 38, 38, 0.35);
    flex-shrink: 0;
  }}
  .live-dot {{
    width: 9px;
    height: 9px;
    background-color: #FFFFFF;
    border-radius: 50%;
    display: inline-block;
  }}
  .glass-divider {{
    width: 1px;
    height: 22px;
    background: rgba(15, 23, 42, 0.16);
    flex-shrink: 0;
  }}
  .glass-subcopy-text {{
    color: #0F172A;
    font-size: 25px;
    font-weight: 800;
    line-height: 1.18;
    letter-spacing: -0.2px;
    white-space: nowrap;
  }}
"""

    def _make_capsule_variant(extra_css: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8" /><style>{capsule_css}{extra_css}</style></head>
<body>
  <div class="capsule-stage">
    <div class="z13-glass-capsule-layer">
      <div class="glass-subcopy-capsule" id="ui_glass_capsule">
        <div class="glass-badge-live">
          <span class="live-dot"></span>
          <span class="live-text">LIVE</span>
        </div>
        <div class="glass-divider"></div>
        <span class="glass-subcopy-text">단 60분! 할인쿠폰 + 추가혜택이 펑펑</span>
      </div>
    </div>
  </div>
</body>
</html>"""

    # Decoupled sub-layers for Header_Frosted_Glass_Capsule group
    cap_bg_html = _make_capsule_variant(".glass-badge-live, .glass-divider, .glass-subcopy-text { visibility: hidden; }")
    cap_badge_html = _make_capsule_variant(".glass-subcopy-capsule { background: transparent; border-color: transparent; box-shadow: none; backdrop-filter: none; } .glass-divider, .glass-subcopy-text { visibility: hidden; }")
    cap_divider_html = _make_capsule_variant(".glass-subcopy-capsule { background: transparent; border-color: transparent; box-shadow: none; backdrop-filter: none; } .glass-badge-live, .glass-subcopy-text { visibility: hidden; }")
    cap_text_html = _make_capsule_variant(".glass-subcopy-capsule { background: transparent; border-color: transparent; box-shadow: none; backdrop-filter: none; } .glass-badge-live, .glass-divider { visibility: hidden; }")

    # Shared CSS for the Bottom CTA Pill (1:1 match with master_1080x1080.html, synced width injected dynamically)
    cta_css = f"""{base_styles}
  .cta-stage {{
    position: relative;
    width: 1080px;
    height: 180px;
  }}
  .z13-cta-button {{
    position: absolute;
    bottom: 50px;
    left: 50%;
    transform: translateX(-50%);
    box-sizing: border-box;
    width: __SYNCED_W__px;
    height: 70px;
    padding: 0 45px;
    border-radius: 9999px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    background: linear-gradient(
      180deg,
      #3392FF 0%,
      #1982FF 18%,
      #0F78FF 56%,
      #0C6CEB 88%,
      #167BFF 100%
    );
    border: 1.5px solid rgba(130, 194, 255, 0.78);
    box-shadow:
      0 12px 26px -4px rgba(15, 120, 255, 0.42),
      0 4px 12px rgba(15, 120, 255, 0.24),
      inset 0 2px 3px rgba(255, 255, 255, 0.42),
      inset 0 -3px 6px rgba(15, 92, 214, 0.30),
      inset 0 -1px 2px rgba(110, 184, 255, 0.38);
  }}
  .z13-cta-button::before {{
    content: "";
    position: absolute;
    top: 1px;
    left: 16px;
    right: 16px;
    height: 18px;
    border-radius: 9999px;
    background: linear-gradient(
      180deg,
      rgba(255, 255, 255, 0.44) 0%,
      rgba(255, 255, 255, 0.14) 48%,
      rgba(255, 255, 255, 0.00) 100%
    );
    pointer-events: none;
  }}
  .cta-pill-label {{
    position: relative;
    z-index: 1;
    color: #FFFFFF;
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    white-space: nowrap;
  }}
  .cta-text {{
    font-size: 30px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: 1.4px;
    text-shadow: 0 2px 4px rgba(4, 48, 120, 0.38);
  }}
  .cta-chevron {{
    width: 14px;
    height: 22px;
    flex-shrink: 0;
    display: block;
    filter: drop-shadow(0 2px 3px rgba(4, 48, 120, 0.38));
  }}
"""

    def _make_cta_variant(extra_css: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8" /><style>{cta_css}{extra_css}</style></head>
<body>
  <div class="cta-stage">
    <div class="z13-cta-button">
      <span class="cta-pill-label">
        <span class="cta-text">라이브 혜택 받고 쇼핑하기</span>
        <svg class="cta-chevron" viewBox="0 0 12 20" fill="none" aria-hidden="true">
          <path d="M2.2 2.2L9.8 10L2.2 17.8" stroke="#FFFFFF" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
    </div>
  </div>
</body>
</html>"""

    cta_bg_html = _make_cta_variant(".cta-pill-label { visibility: hidden; }")
    cta_text_html = _make_cta_variant(".z13-cta-button { background: transparent; border-color: transparent; box-shadow: none; } .z13-cta-button::before { display: none; }")

    # DIR-UI-POLISH-SPARKLES-058: Exact 1:1 bauble snow-dust & 4-point sparkle bokeh overlay (240x240)
    bauble_sparkles_html = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8" /><style>* { margin: 0; padding: 0; } html, body { width: 240px; height: 240px; background: transparent; overflow: hidden; }</style></head>
<body>
  <svg width="240" height="240" viewBox="0 0 240 240" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <radialGradient id="baubleBokehSoft" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0.95" />
        <stop offset="45%" stop-color="#E0F2FE" stop-opacity="0.58" />
        <stop offset="100%" stop-color="#BAE6FD" stop-opacity="0" />
      </radialGradient>
      <filter id="baubleStarGlow" x="-45%" y="-45%" width="190%" height="190%">
        <feGaussianBlur stdDeviation="2.0" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>
    <circle cx="176" cy="112" r="10.5" fill="url(#baubleBokehSoft)" opacity="0.72" />
    <circle cx="64" cy="114" r="9.0" fill="url(#baubleBokehSoft)" opacity="0.68" />
    <circle cx="152" cy="176" r="8.5" fill="url(#baubleBokehSoft)" opacity="0.66" />
    <circle cx="96" cy="56" r="7.5" fill="url(#baubleBokehSoft)" opacity="0.65" />
    <circle cx="192" cy="84" r="6.5" fill="url(#baubleBokehSoft)" opacity="0.62" />
    <circle cx="78" cy="178" r="7.0" fill="url(#baubleBokehSoft)" opacity="0.64" />
    <circle cx="114" cy="188" r="6.0" fill="url(#baubleBokehSoft)" opacity="0.60" />
    <g filter="url(#baubleStarGlow)">
      <path d="M174 58 L176.6 69.4 L188 72 L176.6 74.6 L174 86 L171.4 74.6 L160 72 L171.4 69.4 Z" fill="#FFFFFF" opacity="0.85" />
      <path d="M68 153 L70.1 161.9 L79 164 L70.1 166.1 L68 175 L65.9 166.1 L57 164 L65.9 161.9 Z" fill="#FFFFFF" opacity="0.82" />
      <path d="M182 141 L183.9 149.1 L192 151 L183.9 152.9 L182 161 L180.1 152.9 L172 151 L180.1 149.1 Z" fill="#FFFFFF" opacity="0.78" />
      <path d="M74 62 L75.7 69.3 L83 71 L75.7 72.7 L74 80 L72.3 72.7 L65 71 L72.3 69.3 Z" fill="#FFFFFF" opacity="0.76" />
      <path d="M136 45 L137.3 50.7 L143 52 L137.3 53.3 L136 59 L134.7 53.3 L129 52 L134.7 50.7 Z" fill="#E0F2FE" opacity="0.74" />
      <path d="M138 178 L139.3 183.7 L145 185 L139.3 186.3 L138 192 L136.7 186.3 L131 185 L136.7 183.7 Z" fill="#FFFFFF" opacity="0.72" />
    </g>
    <circle cx="158" cy="54" r="2.4" fill="#FFFFFF" opacity="0.82" />
    <circle cx="194" cy="118" r="2.2" fill="#FFFFFF" opacity="0.78" />
    <circle cx="164" cy="166" r="2.6" fill="#FFFFFF" opacity="0.80" />
    <circle cx="96" cy="174" r="2.1" fill="#E0F2FE" opacity="0.72" />
    <circle cx="56" cy="96" r="2.3" fill="#FFFFFF" opacity="0.76" />
    <circle cx="62" cy="138" r="1.9" fill="#FFFFFF" opacity="0.70" />
    <circle cx="116" cy="48" r="2.0" fill="#FFFFFF" opacity="0.74" />
    <circle cx="186" cy="172" r="1.8" fill="#E0F2FE" opacity="0.68" />
    <circle cx="199" cy="100" r="1.6" fill="#FFFFFF" opacity="0.65" />
    <circle cx="88" cy="84" r="1.7" fill="#FFFFFF" opacity="0.66" />
    <circle cx="168" cy="94" r="1.8" fill="#FFFFFF" opacity="0.72" />
    <circle cx="52" cy="152" r="1.5" fill="#E0F2FE" opacity="0.62" />
  </svg>
</body>
</html>"""

    files = {
        "logo": (tmp_dir / "header_logo.html", tmp_dir / "header_logo.png", logo_html),
        "cap_bg": (tmp_dir / "cap_bg.html", tmp_dir / "cap_bg.png", cap_bg_html),
        "cap_badge": (tmp_dir / "cap_badge.html", tmp_dir / "cap_badge.png", cap_badge_html),
        "cap_divider": (tmp_dir / "cap_divider.html", tmp_dir / "cap_divider.png", cap_divider_html),
        "cap_text": (tmp_dir / "cap_text.html", tmp_dir / "cap_text.png", cap_text_html),
        "cta_bg": (tmp_dir / "cta_bg.html", tmp_dir / "cta_bg.png", cta_bg_html),
        "cta_text": (tmp_dir / "cta_text.html", tmp_dir / "cta_text.png", cta_text_html),
        "bauble_sparkles": (tmp_dir / "bauble_sparkles.html", tmp_dir / "bauble_sparkles.png", bauble_sparkles_html),
    }
    for key, (hpath, _ppath, content) in files.items():
        hpath.write_text(content, encoding="utf-8")

    node_script = """
import fs from 'node:fs';
import { chromium } from 'playwright';
import { pathToFileURL } from 'node:url';

const [
  logoHtml, logoPng,
  capBgHtml, capBgPng,
  capBadgeHtml, capBadgePng,
  capDivHtml, capDivPng,
  capTxtHtml, capTxtPng,
  ctaBgHtml, ctaBgPng,
  ctaTxtHtml, ctaTxtPng,
  sparklesHtml, sparklesPng,
] = process.argv.slice(1);

const browser = await chromium.launch({ headless: true, timeout: 15000 });
try {
  const page = await browser.newPage({ viewport: { width: 1080, height: 200 }, deviceScaleFactor: 1 });

  // Measure exact rendered width of top glass capsule first
  await page.goto(pathToFileURL(capBgHtml).href, { waitUntil: 'load', timeout: 15000 });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(200);
  const syncedW = await page.evaluate(() => Math.round(document.getElementById('ui_glass_capsule').getBoundingClientRect().width));

  // Inject exact synced width into CTA HTML files
  for (const ctaHtml of [ctaBgHtml, ctaTxtHtml]) {
    const raw = fs.readFileSync(ctaHtml, 'utf-8');
    fs.writeFileSync(ctaHtml, raw.replaceAll('__SYNCED_W__', String(syncedW)), 'utf-8');
  }

  const jobs = [
    [logoHtml, logoPng],
    [capBgHtml, capBgPng],
    [capBadgeHtml, capBadgePng],
    [capDivHtml, capDivPng],
    [capTxtHtml, capTxtPng],
    [ctaBgHtml, ctaBgPng],
    [ctaTxtHtml, ctaTxtPng],
  ];
  for (const [htmlPath, outPng] of jobs) {
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'load', timeout: 15000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(150);
    await page.screenshot({ path: outPng, omitBackground: true, timeout: 15000 });
  }

  // Render 240x240 bauble sparkle bokeh layer with exact transparent bounds
  await page.setViewportSize({ width: 240, height: 240 });
  await page.goto(pathToFileURL(sparklesHtml).href, { waitUntil: 'load', timeout: 15000 });
  await page.waitForTimeout(80);
  await page.screenshot({ path: sparklesPng, omitBackground: true, timeout: 15000 });
} finally {
  await browser.close();
}
"""
    cmd_args = [
        "node",
        "--input-type=module",
        "-e",
        node_script,
    ]
    for key in ("logo", "cap_bg", "cap_badge", "cap_divider", "cap_text", "cta_bg", "cta_text", "bauble_sparkles"):
        cmd_args.extend([str(files[key][0]), str(files[key][1])])

    subprocess.run(
        cmd_args,
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    out = {}
    for key, (_hpath, ppath, _content) in files.items():
        with Image.open(ppath) as im:
            out[key] = im.convert("RGBA").copy()
    return out


def add_pixel_layer(
    group,
    img: Image.Image,
    name: str,
    left: int,
    top: int,
    unicode_name: str | None = None,
) -> None:
    """
    Create an independent transparent RGBA PixelLayer inside `group`, clipped cleanly
    to non-empty alpha bounds if helpful while preserving exact stage coordinates.
    """
    rgba = img.convert("RGBA")
    pl = group.create_pixel_layer(rgba, name=name, top=int(round(top)), left=int(round(left)))
    if unicode_name:
        pl.tagged_blocks.set_data(Tag.UNICODE_LAYER_NAME, unicode_name)


def tight_crop_with_offset(img: Image.Image, left: float, top: float) -> Tuple[Image.Image, int, int]:
    """Crop empty transparent border around a layer while updating (left, top) identically."""
    bbox = img.getbbox()
    if bbox is None:
        return img, int(round(left)), int(round(top))
    cropped = img.crop(bbox)
    return cropped, int(round(left + bbox[0])), int(round(top + bbox[1]))


# ==============================================================================
# MAIN LAYERED PSD COMPILER (DIR-EXPORT-LAYERED-PSD-032)
# ==============================================================================
def build_gsshop_master_psd(out_psd: Path = DEFAULT_OUT_PSD) -> Path:
    print("[PSD] Compiling GS SHOP 1080x1080 Layered Master PSD (DIR-EXPORT-LAYERED-PSD-032)...")

    # Load all source RGBA assets from canonical single-source-of-truth LAYERS_DIR
    im_bg = load_rgba(LAYERS_DIR / "01_background_sky.png")
    im_snow1 = load_rgba(LAYERS_DIR / "02_snow_tier_1_back.png")
    im_snow2 = load_rgba(LAYERS_DIR / "03_snow_tier_2_box_bed.png")
    im_snow3 = load_rgba(LAYERS_DIR / "11_snow_tier_3_front_waves.png")
    im_particles = load_rgba(LAYERS_DIR / "12_snow_particles_overlay.png")

    im_box_shadow = load_rgba(LAYERS_DIR / "04_decor_box_contact_shadow.png")
    im_box_back = load_rgba(LAYERS_DIR / "05_decor_box_back_interior.png")
    im_box_front = load_rgba(LAYERS_DIR / "07_decor_box_front_rim.png")
    im_box_lid = load_rgba(LAYERS_DIR / "09_decor_box_lid_flying.png")
    im_ribbon_left = load_rgba(LAYERS_DIR / "07_decor_ribbon_flutter_left.png")
    im_ribbon_right = load_rgba(LAYERS_DIR / "07_decor_ribbon_flutter_right.png")

    im_toilet = load_rgba(LAYERS_DIR / "06_hero_toilet_paper.png")
    im_tangerine_cluster = load_rgba(LAYERS_DIR / "06_hero_tangerines_cluster.png")

    im_knit = load_rgba(LAYERS_DIR / "08_hero_knit_sweater.png")
    im_puffer = load_rgba(LAYERS_DIR / "08_hero_puffer_jacket.png")
    im_bag = load_rgba(LAYERS_DIR / "08_hero_shopping_bag_pink.png")

    im_fly_tangerine = load_rgba(LAYERS_DIR / "10_decor_flying_tangerine.png")
    im_fly_leaves = load_rgba(LAYERS_DIR / "10_decor_tangerine_leaves.png")
    im_snowflake = load_rgba(LAYERS_DIR / "10_decor_snowflake.png")
    im_candy_cane = load_rgba(LAYERS_DIR / "10_decor_candy_cane.png")
    im_bauble = load_rgba(LAYERS_DIR / "10_decor_bauble.png")

    im_headline = load_rgba(LAYERS_DIR / "13_ui_headline_3d.png")

    # Rasterize crisp decoupled UI layers (MOBILE LIVE logo, Header Frosted Glass Capsule sub-layers, Bottom CTA Pill sub-layers)
    with tempfile.TemporaryDirectory(prefix="gsshop_psd_ui_") as td:
        ui_layers = render_header_layers_via_playwright(Path(td))

    # Export standalone 32-bit RGBA UI PNGs to canonical LAYERS_DIR for downstream motion/Remotion pipelines
    cap_comp = Image.new("RGBA", ui_layers["cap_bg"].size, (0, 0, 0, 0))
    for k in ("cap_bg", "cap_badge", "cap_divider", "cap_text"):
        cap_comp = Image.alpha_composite(cap_comp, ui_layers[k])
    cap_crop, _, _ = tight_crop_with_offset(cap_comp, 0, 0)
    cap_crop.save(LAYERS_DIR / "13_ui_frosted_glass_capsule.png", format="PNG")

    cta_comp = Image.new("RGBA", ui_layers["cta_bg"].size, (0, 0, 0, 0))
    for k in ("cta_bg", "cta_text"):
        cta_comp = Image.alpha_composite(cta_comp, ui_layers[k])
    cta_crop, _, _ = tight_crop_with_offset(cta_comp, 0, 0)
    cta_crop.save(LAYERS_DIR / "14_ui_cta_pill_button.png", format="PNG")

    # Initialize 1080x1080 RGB 8-bit PSD (bottom-to-top stacking -> 05_UI_Lockup at top in Photoshop)
    psd = PSDImage.new("RGBA", (CANVAS_W, CANVAS_H))

    # ==========================================================================
    # GROUP 1 (Bottom): 01_Backdrop
    #   ├── Snow_Tier_1_Back (snow_tier_1_back_blur.png)
    #   └── Background_Winter (01_bg_winter_backdrop.png)
    # ==========================================================================
    grp_01 = psd.create_group(name="01_Backdrop", open_folder=True)

    bg_layer = im_bg.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS)
    add_pixel_layer(grp_01, bg_layer, "Background_Winter", left=0, top=0, unicode_name="Background_Winter (01_bg_winter_backdrop.png)")

    snow1_img, s1_x, s1_y = render_cropped_band(
        im_snow1, box_left=0, box_top=750, box_w=1080, box_h=330,
        img_left=-94, img_top=-472, img_w=1268, img_h=990,
    )
    add_pixel_layer(grp_01, snow1_img, "Snow_Tier_1_Back", left=s1_x, top=s1_y, unicode_name="Snow_Tier_1_Back (snow_tier_1_back_blur.png)")

    # ==========================================================================
    # GROUP 2: 02_GiftBox_and_Tucked_Items
    #   ├── Box_Front_Rim (decor_box_front_rim.png)
    #   ├── Tucked_Tangerine_Cluster (tangerine_overflow_cluster.png)
    #   ├── Tucked_Toilet_Paper (gsshop_toilet_paper_alpha.png)
    #   ├── Box_Back_Interior (decor_box_back_interior.png)
    #   ├── Box_Contact_Shadow (decor_box_contact_shadow.png)
    #   └── Snow_Tier_2_Box_Bed (snow_tier_2_box_bed.png)
    # ==========================================================================
    grp_02 = psd.create_group(name="02_GiftBox_and_Tucked_Items", open_folder=True)

    # 2.1 Snow_Tier_2_Box_Bed (DIR-FORGE-SNOW-WAVES-041: native 1080x1080 full-bleed 7-wave bed)
    snow2_c, s2_x, s2_y = tight_crop_with_offset(im_snow2, 0, 0)
    add_pixel_layer(grp_02, snow2_c, "Snow_Tier_2_Box_Bed", left=s2_x, top=s2_y, unicode_name="Snow_Tier_2_Box_Bed (snow_tier_2_box_bed.png)")

    # 2.2 Box_Contact_Shadow (+30px for DIR-REBALANCE-VERTICAL-RHYTHM-048: stage 175, 401, opacity 0.88)
    box_sh = apply_opacity(im_box_shadow.resize((701, 701), Image.Resampling.LANCZOS), 0.88)
    box_sh_c, bsh_x, bsh_y = tight_crop_with_offset(box_sh, 175.0, 401.0)
    add_pixel_layer(grp_02, box_sh_c, "Box_Contact_Shadow", left=bsh_x, top=bsh_y, unicode_name="Box_Contact_Shadow (decor_box_contact_shadow.png)")

    # 2.3 Box_Back_Interior (Pure White #FFFFFF box cavity: 701x701 at stage 175, 401 + cool-slate separation shadow)
    box_back = im_box_back.resize((701, 701), Image.Resampling.LANCZOS)
    box_back_sh, bb_px, bb_py = add_drop_shadow(box_back, 0, 10, 14.0, (15, 35, 75, 41))
    box_back_c, bb_x, bb_y = tight_crop_with_offset(box_back_sh, 175.0 - bb_px, 401.0 - bb_py)
    add_pixel_layer(grp_02, box_back_c, "Box_Back_Interior", left=bb_x, top=bb_y, unicode_name="Box_Back_Interior (decor_box_back_interior.png)")

    # 2.4 Tucked_Toilet_Paper (tissue_1: left=335, top=541, rot=-7deg)
    tp_scaled = im_toilet.resize((264, 264), Image.Resampling.LANCZOS)
    tp_rot, tp_dx, tp_dy = rotate_css(tp_scaled, -7.0)
    tp_sh, tp_px, tp_py = add_drop_shadow(tp_rot, 0, 10, 12.0, (15, 23, 42, 56))
    tp_c, tp_x, tp_y = tight_crop_with_offset(tp_sh, 335 + tp_dx - tp_px, 541 + tp_dy - tp_py)
    add_pixel_layer(grp_02, tp_c, "Tucked_Toilet_Paper", left=tp_x, top=tp_y, unicode_name="Tucked_Toilet_Paper (Lốc giấy Kleenex)")

    # 2.4b Tucked_Toilet_Paper copy (tissue_2 duplicate: left=402, top=450, rot=-7deg)
    tp2_c, tp2_x, tp2_y = tight_crop_with_offset(tp_sh, 402 + tp_dx - tp_px, 450 + tp_dy - tp_py)
    add_pixel_layer(grp_02, tp2_c, "Tucked_Toilet_Paper copy", left=tp2_x, top=tp2_y, unicode_name="Tucked_Toilet_Paper (Lốc giấy Kleenex) copy")

    # 2.5 Tucked_Tangerine_Cluster (tangerine_1: left=459, top=669, rot=2deg)
    tc_scaled = im_tangerine_cluster.resize((207, 207), Image.Resampling.LANCZOS)
    tc_rot, tc_dx, tc_dy = rotate_css(tc_scaled, 2.0)
    tc_sh, tc_px, tc_py = add_drop_shadow(tc_rot, 0, 10, 12.0, (15, 23, 42, 61))
    tc_c, tc_x, tc_y = tight_crop_with_offset(tc_sh, 459 + tc_dx - tc_px, 669 + tc_dy - tc_py)
    add_pixel_layer(grp_02, tc_c, "Tucked_Tangerine_Cluster", left=tc_x, top=tc_y, unicode_name="Tucked_Tangerine_Cluster (tangerine_overflow_cluster.png)")

    # 2.5b Tucked_Tangerine_Cluster copy (tangerine_2 duplicate: left=548, top=647, rot=2deg)
    tc2_c, tc2_x, tc2_y = tight_crop_with_offset(tc_sh, 548 + tc_dx - tc_px, 647 + tc_dy - tc_py)
    add_pixel_layer(grp_02, tc2_c, "Tucked_Tangerine_Cluster copy", left=tc2_x, top=tc2_y, unicode_name="Tucked_Tangerine_Cluster (tangerine_overflow_cluster.png) copy")

    # 2.6 Box_Front_Rim (Pure White #FFFFFF + Azure Blue #0F78FF satin ribbons: 701x701 at stage 175, 401 -> 0.0px seam)
    box_front = im_box_front.resize((701, 701), Image.Resampling.LANCZOS)
    box_front_sh, bf_px, bf_py = add_drop_shadow(box_front, 0, 14, 18.0, (15, 35, 75, 61))
    box_front_c, bf_x, bf_y = tight_crop_with_offset(box_front_sh, 175.0 - bf_px, 401.0 - bf_py)
    add_pixel_layer(grp_02, box_front_c, "Box_Front_Rim", left=bf_x, top=bf_y, unicode_name="Box_Front_Rim (decor_box_front_rim.png)")

    # 2.7 Ribbon_Flutter_Left (DIR-SEAMLESS-BOX-RIBBON-050: shared-camera 1:1 at 701x701, stage 175, 401)
    rib_l = im_ribbon_left.resize((701, 701), Image.Resampling.LANCZOS)
    rib_l_sh, rl_px, rl_py = add_drop_shadow(rib_l, 0, 7, 8.0, (30, 58, 138, 77))
    rib_l_c, rl_x, rl_y = tight_crop_with_offset(rib_l_sh, 175.0 - rl_px, 401.0 - rl_py)
    add_pixel_layer(grp_02, rib_l_c, "Ribbon_Flutter_Left", left=rl_x, top=rl_y, unicode_name="Ribbon_Flutter_Left (decor_ribbon_flutter_left.png)")

    # 2.8 Ribbon_Flutter_Right (DIR-SEAMLESS-BOX-RIBBON-050: shared-camera 1:1 at 701x701, stage 175, 401)
    rib_r = im_ribbon_right.resize((701, 701), Image.Resampling.LANCZOS)
    rib_r_sh, rr_px, rr_py = add_drop_shadow(rib_r, 0, 7, 8.0, (30, 58, 138, 77))
    rib_r_c, rr_x, rr_y = tight_crop_with_offset(rib_r_sh, 175.0 - rr_px, 401.0 - rr_py)
    add_pixel_layer(grp_02, rib_r_c, "Ribbon_Flutter_Right", left=rr_x, top=rr_y, unicode_name="Ribbon_Flutter_Right (decor_ribbon_flutter_right.png)")

    # ==========================================================================
    # GROUP 3: 03_Floating_Heroes_and_Decor
    #   ├── Decor_Flying_Lid
    #   ├── Flying_Single_Tangerine
    #   ├── Decor_Snowflake
    #   ├── Decor_Candy_Cane
    #   ├── Decor_Bauble
    #   ├── Burst_Puffer_Jacket
    #   ├── Burst_Knit_Sweater
    #   └── Shopping_Bag_Pink
    # ==========================================================================
    grp_03 = psd.create_group(name="03_Floating_Heroes_and_Decor", open_folder=True)

    # 3.1 Shopping_Bag_Pink (DIR-MASTER-TRIANGLE-BURST-059: top: 398, left: 736, w: 245, rot: 28deg)
    bag_s = im_bag.resize((245, 245), Image.Resampling.LANCZOS)
    bag_r, bag_dx, bag_dy = rotate_css(bag_s, 28.0)
    bag_sh, bag_px, bag_py = add_drop_shadow(bag_r, 0, 14, 16.0, (15, 23, 42, 56))
    bag_c, bag_x, bag_y = tight_crop_with_offset(bag_sh, 736 + bag_dx - bag_px, 398 + bag_dy - bag_py)
    add_pixel_layer(grp_03, bag_c, "Shopping_Bag_Pink", left=bag_x, top=bag_y, unicode_name="Shopping_Bag_Pink (08_hero_shopping_bag_pink.png)")

    # 3.2 Burst_Knit_Sweater (DIR-MASTER-SPATIAL-COORDINATES-056: top: 500, left: 225, w: 340, rot: -16deg)
    knit_s = im_knit.resize((340, 340), Image.Resampling.LANCZOS)
    knit_r, knit_dx, knit_dy = rotate_css(knit_s, -16.0)
    knit_sh, knit_px, knit_py = add_drop_shadow(knit_r, 0, 16, 16.0, (15, 23, 42, 64))
    knit_c, knit_x, knit_y = tight_crop_with_offset(knit_sh, 225 + knit_dx - knit_px, 500 + knit_dy - knit_py)
    add_pixel_layer(grp_03, knit_c, "Burst_Knit_Sweater", left=knit_x, top=knit_y, unicode_name="Burst_Knit_Sweater (08_hero_knit_sweater.png)")

    # 3.3 Burst_Puffer_Jacket (DIR-MASTER-TRIANGLE-BURST-059: 112% scale -> 428x428, top: 456, left: 508, rot: 17deg)
    puf_s = im_puffer.resize((428, 428), Image.Resampling.LANCZOS)
    puf_r, puf_dx, puf_dy = rotate_css(puf_s, 17.0)
    puf_sh, puf_px, puf_py = add_drop_shadow(puf_r, 0, 18, 19.0, (10, 25, 49, 51))
    puf_c, puf_x, puf_y = tight_crop_with_offset(puf_sh, 508 + puf_dx - puf_px, 456 + puf_dy - puf_py)
    add_pixel_layer(grp_03, puf_c, "Burst_Puffer_Jacket", left=puf_x, top=puf_y, unicode_name="Burst_Puffer_Jacket (08_hero_puffer_jacket.png)")

    # 3.4 Decor_Bauble (DIR-MASTER-TRIANGLE-BURST-059: top: 301, left: 861, w: 88, rot: 18deg -> Right -45deg axis)
    bau_s = im_bauble.resize((88, 88), Image.Resampling.LANCZOS)
    bau_r, bau_dx, bau_dy = rotate_css(bau_s, 18.0)
    bau_sh, bau_px, bau_py = add_drop_shadow(bau_r, -8, 10, 6.0, (56, 189, 248, 92))
    bau_c, bau_x, bau_y = tight_crop_with_offset(bau_sh, 861 + bau_dx - bau_px, 301 + bau_dy - bau_py)
    add_pixel_layer(grp_03, bau_c, "Decor_Bauble", left=bau_x, top=bau_y, unicode_name="Decor_Bauble (10_decor_bauble.png)")

    # 3.4b Decor_Bauble_Sparkles (aligned with bauble at top: 225, left: 785)
    ui_layers["bauble_sparkles"].save(LAYERS_DIR / "10_decor_bauble_sparkles.png", format="PNG")
    sp_c, sp_x, sp_y = tight_crop_with_offset(ui_layers["bauble_sparkles"], 785.0, 225.0)
    add_pixel_layer(grp_03, sp_c, "Decor_Bauble_Sparkles", left=sp_x, top=sp_y, unicode_name="Decor_Bauble_Sparkles (10_decor_bauble_sparkles.png)")

    # 3.5 Decor_Candy_Cane (DIR-MASTER-TRIANGLE-BURST-059: top: 302, left: 132, flipX then rotate -25deg -> Left +45deg axis)
    cc_s = im_candy_cane.resize((116, 116), Image.Resampling.LANCZOS).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    cc_r, cc_dx, cc_dy = rotate_css(cc_s, -25.0)
    cc_sh, cc_px, cc_py = add_drop_shadow(cc_r, 7, 9, 6.0, (56, 189, 248, 82))
    cc_c, cc_x, cc_y = tight_crop_with_offset(cc_sh, 132 - 15 + cc_dx - cc_px, 302 - 15 + cc_dy - cc_py)
    add_pixel_layer(grp_03, cc_c, "Decor_Candy_Cane", left=cc_x, top=cc_y, unicode_name="Decor_Candy_Cane (10_decor_candy_cane.png)")

    # 3.6 Decor_Snowflake (DIR-UI-POLISH-SPARKLES-058: shifted 15px left -> top: 645, left: 207, w: 95 for sweater clearance)
    sf_s = im_snowflake.resize((120, 120), Image.Resampling.LANCZOS).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    sf_r, sf_dx, sf_dy = rotate_css(sf_s, -14.0)
    sf_sh, sf_px, sf_py = add_drop_shadow(sf_r, 8, 6, 7.0, (255, 255, 255, 210))
    sf_c, sf_x, sf_y = tight_crop_with_offset(sf_sh, 207 - 12 + sf_dx - sf_px, 645 - 12 + sf_dy - sf_py)
    add_pixel_layer(grp_03, sf_c, "Decor_Snowflake", left=sf_x, top=sf_y, unicode_name="Decor_Snowflake (10_decor_snowflake.png)")

    # 3.6b Decor_Snowflake copy (snowflake_2 duplicate: top: 609, left: 847, w: 98, rot: 1deg)
    sf2_s = im_snowflake.resize((124, 124), Image.Resampling.LANCZOS).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    sf2_r, sf2_dx, sf2_dy = rotate_css(sf2_s, 1.0)
    sf2_sh, sf2_px, sf2_py = add_drop_shadow(sf2_r, 8, 6, 7.0, (255, 255, 255, 210))
    sf2_c, sf2_x, sf2_y = tight_crop_with_offset(sf2_sh, 847 - 12 + sf2_dx - sf2_px, 609 - 12 + sf2_dy - sf2_py)
    add_pixel_layer(grp_03, sf2_c, "Decor_Snowflake copy", left=sf2_x, top=sf2_y, unicode_name="Decor_Snowflake (10_decor_snowflake.png) copy")

    # 3.7a Flying_Tangerine_Left (DIR-MASTER-TRIANGLE-BURST-059: Left +45deg axis, top: 439, left: 269, w: 92, rot: -22deg)
    ft_pad = 40
    ft_box_l = Image.new("RGBA", (92 + ft_pad * 2, 92 + ft_pad * 2), (0, 0, 0, 0))
    ft_fruit_l = im_fly_tangerine.resize((116, 116), Image.Resampling.LANCZOS).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    ft_box_l.alpha_composite(ft_fruit_l, (ft_pad - 12, ft_pad - 10))
    ft_leaves = im_fly_leaves.resize((61, 61), Image.Resampling.LANCZOS)
    ft_leaves_r, fl_dx, fl_dy = rotate_css(ft_leaves, -10.0)
    ft_box_l.alpha_composite(ft_leaves_r, (int(round(ft_pad + 13 + fl_dx)), int(round(ft_pad - 26 + fl_dy))))
    ft_rot_l, ftl_dx, ftl_dy = rotate_css(ft_box_l, -22.0)
    ft_sh_l, ftl_px, ftl_py = add_drop_shadow(ft_rot_l, 5, 11, 6.0, (249, 115, 22, 82))
    ftl_c, ftl_x, ftl_y = tight_crop_with_offset(ft_sh_l, 269 - ft_pad + ftl_dx - ftl_px, 439 - ft_pad + ftl_dy - ftl_py)
    add_pixel_layer(grp_03, ftl_c, "Flying_Tangerine_Left", left=ftl_x, top=ftl_y, unicode_name="Flying_Tangerine_Left (10_decor_flying_tangerine + leaves)")

    # 3.7b Flying_Tangerine_Right (DIR-MASTER-TRIANGLE-BURST-059: Right -45deg axis, top: 440, left: 720, w: 90, rot: 22deg)
    ft_box_r = Image.new("RGBA", (90 + ft_pad * 2, 90 + ft_pad * 2), (0, 0, 0, 0))
    ft_fruit_r = im_fly_tangerine.resize((116, 116), Image.Resampling.LANCZOS)
    ft_box_r.alpha_composite(ft_fruit_r, (ft_pad - 12, ft_pad - 10))
    ft_box_r.alpha_composite(ft_leaves_r, (int(round(ft_pad + 13 + fl_dx)), int(round(ft_pad - 26 + fl_dy))))
    ft_rot_r, ftr_dx, ftr_dy = rotate_css(ft_box_r, 22.0)
    ft_sh_r, ftr_px, ftr_py = add_drop_shadow(ft_rot_r, 5, 11, 6.0, (249, 115, 22, 82))
    ftr_c, ftr_x, ftr_y = tight_crop_with_offset(ft_sh_r, 720 - ft_pad + ftr_dx - ftr_px, 440 - ft_pad + ftr_dy - ftr_py)
    add_pixel_layer(grp_03, ftr_c, "Flying_Tangerine_Right", left=ftr_x, top=ftr_y, unicode_name="Flying_Tangerine_Right (10_decor_flying_tangerine + leaves)")

    # 3.8 Decor_Flying_Lid (DIR-MASTER-SPATIAL-COORDINATES-056: top: 428, left: 54, w: 335, h: 228, inner 552x552, rot: -15deg)
    lid_s = im_box_lid.resize((552, 552), Image.Resampling.LANCZOS)
    lid_r, lid_dx, lid_dy = rotate_css(lid_s, -15.0, origin_x_frac=(54 + 167.5 - (-16.0)) / 552.0, origin_y_frac=(428 + 114.0 - 386.0) / 552.0)
    lid_sh, lid_px, lid_py = add_drop_shadow(lid_r, 0, 18, 18.0, (10, 25, 49, 51))
    lid_c, lid_x, lid_y = tight_crop_with_offset(lid_sh, -16.0 + lid_dx - lid_px, 386.0 + lid_dy - lid_py)
    add_pixel_layer(grp_03, lid_c, "Decor_Flying_Lid", left=lid_x, top=lid_y, unicode_name="Decor_Flying_Lid (09_decor_box_lid_flying.png)")

    # ==========================================================================
    # GROUP 4: 04_Atmosphere_Particles
    #   ├── Snow_Particles_Overlay (02_snow_particles_overlay.png)
    #   └── Snow_Tier_3_Front (snow_tier_3_front_blur.png)
    # ==========================================================================
    grp_04 = psd.create_group(name="04_Atmosphere_Particles", open_folder=True)

    # 4.1 Snow_Tier_3_Front (DIR-FORGE-SNOW-WAVES-041: native 1080x1080 full-bleed 7-wave foreground)
    snow3_c, s3_x, s3_y = tight_crop_with_offset(im_snow3, 0, 0)
    add_pixel_layer(grp_04, snow3_c, "Snow_Tier_3_Front", left=s3_x, top=s3_y, unicode_name="Snow_Tier_3_Front (snow_tier_3_front_blur.png)")

    # 4.2 Snow_Particles_Overlay (0, 0, 1080, 1080, opacity 0.92)
    sp_layer = apply_opacity(im_particles.resize((CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS), 0.92)
    add_pixel_layer(grp_04, sp_layer, "Snow_Particles_Overlay", left=0, top=0, unicode_name="Snow_Particles_Overlay (02_snow_particles_overlay.png)")

    # ==========================================================================
    # GROUP 5 (Topmost): 05_UI_Lockup (DIR-DECOUPLE-UI-CAPSULES-043)
    #   ├── [FOLDER] Bottom_CTA_Pill (Independent Layer Group — synced width)
    #   │    ├── CTA_Label_Text ("라이브 혜택 받고 쇼핑하기 >")
    #   │    └── CTA_Pill_Background (Glossy Azure 3D Pill)
    #   ├── Headline_3D (03_headline_3d_group.png)
    #   ├── [FOLDER] Header_Frosted_Glass_Capsule (Independent Layer Group)
    #   │    ├── Capsule_Subcopy_Text ("단 60분! 할인쿠폰 + 추가혜택이 펑펑")
    #   │    ├── Capsule_Divider_Hairline
    #   │    ├── Capsule_Badge_LIVE ("LIVE")
    #   │    └── Capsule_Glass_Background (Apple Frosted Glass Pill)
    #   └── Header_Mobile_Live_Logo (MOBILE LIVE top-left anchor)
    # ==========================================================================
    grp_05 = psd.create_group(name="05_UI_Lockup", open_folder=True)

    # 5.1 Header_Mobile_Live_Logo (top: 40px, left: 50px, 258x34px)
    logo_c, logo_x, logo_y = tight_crop_with_offset(ui_layers["logo"], 0, 0)
    add_pixel_layer(grp_05, logo_c, "Header_Mobile_Live_Logo", left=logo_x, top=logo_y, unicode_name="Header_Mobile_Live_Logo (MOBILE LIVE)")

    # 5.2 [FOLDER] Header_Frosted_Glass_Capsule (Independent Layer Group)
    grp_capsule = grp_05.create_group(name="Header_Frosted_Glass_Capsule", open_folder=True)
    for key, lname, uname in [
        ("cap_bg", "Capsule_Glass_Background", "Capsule_Glass_Background (Apple Frosted Glass)"),
        ("cap_badge", "Capsule_Badge_LIVE", "Capsule_Badge_LIVE (LIVE Red Pill)"),
        ("cap_divider", "Capsule_Divider_Hairline", "Capsule_Divider_Hairline"),
        ("cap_text", "Capsule_Subcopy_Text", "Capsule_Subcopy_Text (단 60분! 할인쿠폰 + 추가혜택이 펑펑)"),
    ]:
        c_img, c_x, c_y = tight_crop_with_offset(ui_layers[key], 0, 0)
        add_pixel_layer(grp_capsule, c_img, lname, left=c_x, top=c_y, unicode_name=uname)

    # 5.3 Headline_3D (DIR-MASTER-TRIANGLE-BURST-059: 110% Hero Hook centered at top: 182px, w: 1025px, h: 266px)
    hl_s = im_headline.resize((1025, 266), Image.Resampling.LANCZOS)
    # Centered horizontally at x = (1080 - 1025)/2 = 27.5; vertically centered in 226px box + 4px margin-top
    hl_c, hl_x, hl_y = tight_crop_with_offset(hl_s, (CANVAS_W - 1025) / 2.0, 182 - (266 - 226) / 2.0 + 2.0)
    add_pixel_layer(grp_05, hl_c, "Headline_3D", left=hl_x, top=hl_y, unicode_name="Headline_3D (GS SHOP 라이브특가 — 13_ui_headline_3d.png)")

    # 5.4 [FOLDER] Bottom_CTA_Pill (Independent Layer Group — exact synced width, bottom: 50px -> stage y offset = 1080 - 180 = 900)
    grp_cta = grp_05.create_group(name="Bottom_CTA_Pill", open_folder=True)
    cta_stage_top = CANVAS_H - 180
    for key, lname, uname in [
        ("cta_bg", "CTA_Pill_Background", "CTA_Pill_Background (Glossy Azure Pill)"),
        ("cta_text", "CTA_Label_Text", "CTA_Label_Text (라이브 혜택 받고 쇼핑하기 >)"),
    ]:
        c_img, c_x, c_y = tight_crop_with_offset(ui_layers[key], 0, cta_stage_top)
        add_pixel_layer(grp_cta, c_img, lname, left=c_x, top=c_y, unicode_name=uname)

    # Embed standard sRGB ICC profile
    try:
        psd.image_resources[Resource.ICC_PROFILE] = ImageResource(key=Resource.ICC_PROFILE, data=SRGB_ICC)
    except Exception:
        pass

    out_psd.parent.mkdir(parents=True, exist_ok=True)
    psd.save(str(out_psd))

    # Reload PSD to verify structure, nested groups, layers, and non-flattened integrity
    reloaded = PSDImage.open(str(out_psd))
    size_bytes = out_psd.stat().st_size
    size_mb = size_bytes / (1024.0 * 1024.0)

    print(f"\n[OK] Exported Layered PSD: {out_psd} ({CANVAS_W}x{CANVAS_H}, RGB 8-bit, {size_mb:.2f} MB)")
    print("[PSD] Verified Layer Tree (Top -> Bottom as displayed in Photoshop):")
    total_pixel_layers = 0
    total_groups = 0

    def _print_tree(container, indent: str = "  ") -> None:
        nonlocal total_pixel_layers, total_groups
        items = list(reversed(list(container)))
        for idx, item in enumerate(items):
            is_last = idx == len(items) - 1
            branch = "└──" if is_last else "├──"
            if item.is_group():
                total_groups += 1
                print(f"{indent}{branch} [FOLDER] {item.name}")
                next_indent = indent + ("     " if is_last else "│    ")
                _print_tree(item, next_indent)
            else:
                total_pixel_layers += 1
                print(f"{indent}{branch} {item.name}  ({item.width}x{item.height} @ left={item.left}, top={item.top})")

    _print_tree(reloaded)
    print(f"[PSD] Total Groups: {total_groups} | Total Independent Pixel Layers: {total_pixel_layers}\n")
    return out_psd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GS SHOP Layered Master PSD Builder (DIR-EXPORT-LAYERED-PSD-032)")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUT_PSD),
        help=f"Output PSD file path (default: {DEFAULT_OUT_PSD})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    build_gsshop_master_psd(Path(args.output))
