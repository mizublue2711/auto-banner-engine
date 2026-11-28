#!/usr/bin/env python3
"""
DIR-BUILD-RESIZE-ENGINE-063: GS SHOP Automated Multi-Size Banner Resizing Engine
(`engine/resize_banner_engine.py`)

Automates end-to-end compilation, Playwright high-resolution RGBA 32-bit PNG rendering,
DOM bounding-box manifest extraction, and pixel-exact multi-layer Photoshop (.psd)
packaging for all 3 GS SHOP adaptive banner variations:
  - 1200x600 (Landscape 2:1, Two-Column Split + DIR-ENFORCE-FLUSH-LEFT-ALIGNMENT-064)
  - 300x250  (MREC 6:5, Compact High-Legibility)
  - 800x1500 (Vertical Story 1:1.875, Tall 3-Tier Stacking)

Outputs:
  - PNGs:      output/TASK_GSSHOP/variations/gsshop_{width}x{height}.png
  - Manifests: output/TASK_GSSHOP/variations/gsshop_{width}x{height}.json
  - PSDs:      output/TASK_GSSHOP/variations/psd/gsshop_{width}x{height}.psd
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageCms
from psd_tools import PSDImage
from psd_tools.constants import Resource, Tag
from psd_tools.psd.image_resources import ImageResource

try:
    from jinja2 import Environment, FileSystemLoader  # type: ignore
except ImportError:
    Environment = None  # type: ignore
    FileSystemLoader = None  # type: ignore

ROOT_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = ROOT_DIR / "templates"
LAYERS_DIR = ROOT_DIR / "assets" / "brands" / "gsshop" / "layers"
FONTS_DIR = ROOT_DIR / "assets" / "fonts"
SAFE_ZONES_PATH = ROOT_DIR / "config" / "media_safe_zones_2026.json"
SPEC_PATH = ROOT_DIR / "specs" / "gsshop_assignment_spec.json"

VARIATIONS_DIR = ROOT_DIR / "output" / "TASK_GSSHOP" / "variations"
PSD_DIR = VARIATIONS_DIR / "psd"

SRGB_ICC = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

DEFAULT_COPY: Dict[str, str] = {
    "logo": "MOBILE LIVE",
    "badge": "LIVE",
    "sub_copy": "단 60분! 할인쿠폰 + 추가혜택이 펑펑",
    "headline": "GS SHOP 라이브특가",
    "cta": "라이브 혜택 받고 쇼핑하기 >",
    "cta_label": "라이브 혜택 받고 쇼핑하기",
}


@dataclass(frozen=True)
class VariationSpec:
    key: str
    width: int
    height: int
    format_label: str
    template_file: str
    burst_origin: Tuple[int, int]
    flush_left_axis_x: Optional[int] = None

    @property
    def banner_id(self) -> str:
        return f"gsshop_{self.width}x{self.height}"

    @property
    def template_path(self) -> Path:
        return TEMPLATES_DIR / self.template_file

    @property
    def png_path(self) -> Path:
        return VARIATIONS_DIR / f"gsshop_{self.width}x{self.height}.png"

    @property
    def json_path(self) -> Path:
        return VARIATIONS_DIR / f"gsshop_{self.width}x{self.height}.json"

    @property
    def psd_path(self) -> Path:
        return PSD_DIR / f"gsshop_{self.width}x{self.height}.psd"


VARIATIONS: List[VariationSpec] = [
    VariationSpec(
        key="1200x600",
        width=1200,
        height=600,
        format_label="Landscape (2:1)",
        template_file="gsshop_1200x600.html",
        burst_origin=(885, 360),
        flush_left_axis_x=50,
    ),
    VariationSpec(
        key="300x250",
        width=300,
        height=250,
        format_label="MREC (6:5)",
        template_file="gsshop_300x250.html",
        burst_origin=(150, 165),
        flush_left_axis_x=None,
    ),
    VariationSpec(
        key="800x1500",
        width=800,
        height=1500,
        format_label="Vertical Story (1:1.875)",
        template_file="gsshop_800x1500.html",
        burst_origin=(400, 960),
        flush_left_axis_x=None,
    ),
]


# ==============================================================================
# MASTER-EQUIVALENT 5-GROUP PSD LAYER HIERARCHY (Bottom -> Top Stacking Order)
# Matches `engine/gsshop_psd_builder.py` (5 top-level groups + 2 nested UI groups)
# ==============================================================================
PSD_CAPTURE_SPEC: List[Dict[str, Any]] = [
    # Group 1 (Bottom): 01_Backdrop
    {
        "group": "01_Backdrop",
        "subgroup": None,
        "id": "bg_winter",
        "layer_id": "z1_bg_winter_backdrop",
        "name": "Background_Winter",
        "unicode_name": "Background_Winter (01_background_sky.png)",
        "mode": "layer",
        "full_canvas": True,
    },
    {
        "group": "01_Backdrop",
        "subgroup": None,
        "id": "snow_tier_1",
        "layer_id": "z2_snow_tier_1_back_blur",
        "name": "Snow_Tier_1_Back",
        "unicode_name": "Snow_Tier_1_Back (02_snow_tier_1_back.png)",
        "mode": "layer",
    },
    # Group 2: 02_GiftBox_and_Tucked_Items
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "snow_tier_2",
        "layer_id": "z3_snow_tier_2_box_bed",
        "name": "Snow_Tier_2_Box_Bed",
        "unicode_name": "Snow_Tier_2_Box_Bed (03_snow_tier_2_box_bed.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "box_shadow",
        "layer_id": "z4_box_contact_shadow",
        "name": "Box_Contact_Shadow",
        "unicode_name": "Box_Contact_Shadow (04_decor_box_contact_shadow.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "box_back",
        "layer_id": "z5_box_back_interior",
        "name": "Box_Back_Interior",
        "unicode_name": "Box_Back_Interior (05_decor_box_back_interior.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "toilet_paper",
        "layer_id": "z6_toilet_paper",
        "name": "Tucked_Toilet_Paper",
        "unicode_name": "Tucked_Toilet_Paper (06_hero_toilet_paper.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "toilet_paper_copy",
        "layer_id": "z6_toilet_paper_copy",
        "name": "Tucked_Toilet_Paper copy",
        "unicode_name": "Tucked_Toilet_Paper (06_hero_toilet_paper.png) copy",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "tangerine_cluster",
        "layer_id": "z6_tangerine_cluster",
        "name": "Tucked_Tangerine_Cluster",
        "unicode_name": "Tucked_Tangerine_Cluster (06_hero_tangerines_cluster.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "tangerine_cluster_copy",
        "layer_id": "z6_tangerine_cluster_copy",
        "name": "Tucked_Tangerine_Cluster copy",
        "unicode_name": "Tucked_Tangerine_Cluster (06_hero_tangerines_cluster.png) copy",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "box_front_rim",
        "layer_id": "z7_box_front_rim",
        "name": "Box_Front_Rim",
        "unicode_name": "Box_Front_Rim (07_decor_box_front_rim.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "ribbon_left",
        "layer_id": "z7_ribbon_flutter_left",
        "name": "Ribbon_Flutter_Left",
        "unicode_name": "Ribbon_Flutter_Left (07_decor_ribbon_flutter_left.png)",
        "mode": "layer",
    },
    {
        "group": "02_GiftBox_and_Tucked_Items",
        "subgroup": None,
        "id": "ribbon_right",
        "layer_id": "z7_ribbon_flutter_right",
        "name": "Ribbon_Flutter_Right",
        "unicode_name": "Ribbon_Flutter_Right (07_decor_ribbon_flutter_right.png)",
        "mode": "layer",
    },
    # Group 3: 03_Floating_Heroes_and_Decor
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "shopping_bag",
        "layer_id": "z8_shopping_bag_pink",
        "name": "Shopping_Bag_Pink",
        "unicode_name": "Shopping_Bag_Pink (08_hero_shopping_bag_pink.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "knit_sweater",
        "layer_id": "z8_knit_sweater",
        "name": "Burst_Knit_Sweater",
        "unicode_name": "Burst_Knit_Sweater (08_hero_knit_sweater.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "puffer_jacket",
        "layer_id": "z8_puffer_jacket",
        "name": "Burst_Puffer_Jacket",
        "unicode_name": "Burst_Puffer_Jacket (08_hero_puffer_jacket.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "bauble",
        "layer_id": "z10_decor_bauble",
        "name": "Decor_Bauble",
        "unicode_name": "Decor_Bauble (10_decor_bauble.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "bauble_sparkles",
        "layer_id": "z10_decor_bauble_sparkles",
        "name": "Decor_Bauble_Sparkles",
        "unicode_name": "Decor_Bauble_Sparkles (10_decor_bauble_sparkles.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "candy_cane",
        "layer_id": "z10_decor_candy_cane",
        "name": "Decor_Candy_Cane",
        "unicode_name": "Decor_Candy_Cane (10_decor_candy_cane.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "snowflake",
        "layer_id": "z10_decor_snowflake",
        "name": "Decor_Snowflake",
        "unicode_name": "Decor_Snowflake (10_decor_snowflake.png)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "snowflake_copy",
        "layer_id": "z10_decor_snowflake_copy",
        "name": "Decor_Snowflake copy",
        "unicode_name": "Decor_Snowflake (10_decor_snowflake.png) copy",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "flying_tangerine_left",
        "layer_id": "z10_flying_tangerine_left",
        "name": "Flying_Tangerine_Left",
        "unicode_name": "Flying_Tangerine_Left (10_decor_flying_tangerine + leaves)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "flying_tangerine_right",
        "layer_id": "z10_flying_tangerine_right",
        "name": "Flying_Tangerine_Right",
        "unicode_name": "Flying_Tangerine_Right (10_decor_flying_tangerine + leaves)",
        "mode": "layer",
    },
    {
        "group": "03_Floating_Heroes_and_Decor",
        "subgroup": None,
        "id": "flying_lid",
        "layer_id": "z9_box_lid_flying",
        "name": "Decor_Flying_Lid",
        "unicode_name": "Decor_Flying_Lid (09_decor_box_lid_flying.png)",
        "mode": "layer",
    },
    # Group 4: 04_Atmosphere_Particles
    {
        "group": "04_Atmosphere_Particles",
        "subgroup": None,
        "id": "snow_tier_3",
        "layer_id": "z11_snow_tier_3_front_blur",
        "name": "Snow_Tier_3_Front",
        "unicode_name": "Snow_Tier_3_Front (11_snow_tier_3_front_waves.png)",
        "mode": "layer",
    },
    {
        "group": "04_Atmosphere_Particles",
        "subgroup": None,
        "id": "snow_particles",
        "layer_id": "z12_snow_particles_overlay",
        "name": "Snow_Particles_Overlay",
        "unicode_name": "Snow_Particles_Overlay (12_snow_particles_overlay.png)",
        "mode": "layer",
    },
    # Group 5 (Topmost): 05_UI_Lockup
    {
        "group": "05_UI_Lockup",
        "subgroup": None,
        "id": "ui_logo",
        "layer_id": "z13_logo_live_group",
        "name": "Header_Mobile_Live_Logo",
        "unicode_name": "Header_Mobile_Live_Logo (MOBILE LIVE)",
        "mode": "layer",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": "Header_Frosted_Glass_Capsule",
        "id": "cap_bg",
        "layer_id": "z13_header_frosted_glass_capsule",
        "name": "Capsule_Glass_Background",
        "unicode_name": "Capsule_Glass_Background (Apple Frosted Glass)",
        "mode": "cap_bg",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": "Header_Frosted_Glass_Capsule",
        "id": "cap_badge",
        "layer_id": "z13_header_frosted_glass_capsule",
        "name": "Capsule_Badge_LIVE",
        "unicode_name": "Capsule_Badge_LIVE (LIVE Red Pill)",
        "mode": "cap_badge",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": "Header_Frosted_Glass_Capsule",
        "id": "cap_divider",
        "layer_id": "z13_header_frosted_glass_capsule",
        "name": "Capsule_Divider_Hairline",
        "unicode_name": "Capsule_Divider_Hairline",
        "mode": "cap_divider",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": "Header_Frosted_Glass_Capsule",
        "id": "cap_text",
        "layer_id": "z13_header_frosted_glass_capsule",
        "name": "Capsule_Subcopy_Text",
        "unicode_name": "Capsule_Subcopy_Text (단 60분! 할인쿠폰 + 추가혜택이 펑펑)",
        "mode": "cap_text",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": None,
        "id": "ui_headline",
        "layer_id": "z13_03_headline_3d_group",
        "name": "Headline_3D",
        "unicode_name": "Headline_3D (GS SHOP 라이브특가 — 13_ui_headline_3d.png)",
        "mode": "layer",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": "Bottom_CTA_Pill",
        "id": "cta_bg",
        "layer_id": "z13_04_cta_pill_button",
        "name": "CTA_Pill_Background",
        "unicode_name": "CTA_Pill_Background (Glossy Azure Pill)",
        "mode": "cta_bg",
    },
    {
        "group": "05_UI_Lockup",
        "subgroup": "Bottom_CTA_Pill",
        "id": "cta_text",
        "layer_id": "z13_04_cta_pill_button",
        "name": "CTA_Label_Text",
        "unicode_name": "CTA_Label_Text (라이브 혜택 받고 쇼핑하기 >)",
        "mode": "cta_text",
    },
]


# ==============================================================================
# STEP 1: JINJA2 / HTML TEMPLATE COMPILER
# ==============================================================================
def load_safe_margins(width: int, height: int) -> Dict[str, int]:
    ratio_key = f"{width}x{height}"
    if SAFE_ZONES_PATH.exists():
        try:
            data = json.loads(SAFE_ZONES_PATH.read_text(encoding="utf-8"))
            ratio_cfg = data.get("ratios", {}).get(ratio_key, {})
            sm = ratio_cfg.get("safe_margins")
            if isinstance(sm, dict):
                return {
                    "top": int(sm.get("top", 40)),
                    "bottom": int(sm.get("bottom", 40)),
                    "left": int(sm.get("left", 40)),
                    "right": int(sm.get("right", 40)),
                }
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    return {"top": 40, "bottom": 40, "left": 40, "right": 40}


def load_copy_context() -> Dict[str, str]:
    copy = dict(DEFAULT_COPY)
    if SPEC_PATH.exists():
        try:
            spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
            req = spec.get("required_elements", {})
            if req.get("logo", {}).get("text"):
                copy["logo"] = req["logo"]["text"]
            if req.get("badge_and_subcopy", {}).get("badge_text"):
                copy["badge"] = req["badge_and_subcopy"]["badge_text"]
            if req.get("badge_and_subcopy", {}).get("subcopy_text"):
                copy["sub_copy"] = req["badge_and_subcopy"]["subcopy_text"]
            if req.get("main_title_3d", {}).get("full_text"):
                copy["headline"] = req["main_title_3d"]["full_text"]
            if req.get("cta_button", {}).get("text"):
                cta_full = req["cta_button"]["text"]
                copy["cta"] = cta_full
                copy["cta_label"] = cta_full.rstrip(" >").strip()
        except (OSError, json.JSONDecodeError):
            pass
    return copy


def _resolve_dotted(context: Dict[str, Any], expr: str) -> str:
    cur: Any = context
    for part in expr.strip().split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(f"Template variable not found in context: {expr!r}")
    return str(cur)


def compile_template(spec: VariationSpec, out_html: Path, copy: Dict[str, str]) -> Path:
    """
    Compile Jinja2/HTML template into a self-contained HTML file with resolved
    canonical `file://` URIs for assets and fonts. Uses Jinja2 if available, with
    a deterministic built-in `{{ var }}` Jinja2-syntax compiler fallback.
    """
    if not spec.template_path.exists():
        raise FileNotFoundError(f"Template not found: {spec.template_path}")

    context: Dict[str, Any] = {
        "banner_id": spec.banner_id,
        "width": spec.width,
        "height": spec.height,
        "format_label": spec.format_label,
        "asset_base": LAYERS_DIR.resolve().as_uri(),
        "font_base": FONTS_DIR.resolve().as_uri(),
        "copy": copy,
    }

    if Environment is not None and FileSystemLoader is not None:
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=False)
        rendered = env.get_template(spec.template_file).render(**context)
    else:
        raw = spec.template_path.read_text(encoding="utf-8")
        rendered = re.sub(
            r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}",
            lambda m: _resolve_dotted(context, m.group(1)),
            raw,
        )

    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(rendered, encoding="utf-8")
    return out_html


# ==============================================================================
# STEP 2: PLAYWRIGHT RENDERER + MANIFEST + ISOLATED LAYER CAPTURE
# ==============================================================================
PLAYWRIGHT_BATCH_JS = r"""
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const [jobsJsonPath] = process.argv.slice(1);
const jobs = JSON.parse(fs.readFileSync(jobsJsonPath, 'utf-8'));

function buildIsolationCss(entry) {
  const base = `
    html, body, .stage { background: transparent !important; }
    .layer { visibility: hidden !important; }
    [data-layer-id="${entry.layer_id}"] { visibility: visible !important; }
  `;
  if (entry.mode === 'layer') return base;
  if (entry.mode === 'cap_bg') {
    return base + `
      .glass-badge-live, .glass-divider, .glass-subcopy-text { visibility: hidden !important; }
    `;
  }
  if (entry.mode === 'cap_badge') {
    return base + `
      .glass-subcopy-capsule {
        background: transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
      }
      .glass-divider, .glass-subcopy-text { visibility: hidden !important; }
    `;
  }
  if (entry.mode === 'cap_divider') {
    return base + `
      .glass-subcopy-capsule {
        background: transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
      }
      .glass-badge-live, .glass-subcopy-text { visibility: hidden !important; }
    `;
  }
  if (entry.mode === 'cap_text') {
    return base + `
      .glass-subcopy-capsule {
        background: transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
      }
      .glass-badge-live, .glass-divider { visibility: hidden !important; }
    `;
  }
  if (entry.mode === 'cta_bg') {
    return base + `
      .cta-pill-label { visibility: hidden !important; }
    `;
  }
  if (entry.mode === 'cta_text') {
    return base + `
      .z13-cta-button {
        background: transparent !important;
        border-color: transparent !important;
        box-shadow: none !important;
      }
      .z13-cta-button::before { display: none !important; }
    `;
  }
  return base;
}

const browser = await chromium.launch({ headless: true, timeout: 30000 });
try {
  for (const job of jobs) {
    const context = await browser.newContext({
      viewport: { width: job.width, height: job.height },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    page.setDefaultTimeout(30000);

    const failedRequests = [];
    page.on('requestfailed', (req) => {
      failedRequests.push({ url: req.url(), error: req.failure()?.errorText || 'failed' });
    });

    await page.goto(pathToFileURL(job.compiled_html).href, { waitUntil: 'load', timeout: 30000 });
    await page.evaluate(async () => {
      await document.fonts.ready;
      const imgs = Array.from(document.querySelectorAll('img'));
      await Promise.all(
        imgs.map((img) =>
          img.complete
            ? Promise.resolve()
            : new Promise((resolve) => {
                img.addEventListener('load', resolve, { once: true });
                img.addEventListener('error', resolve, { once: true });
              })
        )
      );
    });
    await page.waitForTimeout(250);

    // 1. Capture full-composite PNG at exact viewport
    fs.mkdirSync(path.dirname(job.raw_png), { recursive: true });
    await page.screenshot({
      path: job.raw_png,
      type: 'png',
      clip: { x: 0, y: 0, width: job.width, height: job.height },
      timeout: 30000,
    });

    // 2. Extract DOM-measured layout manifest
    const manifest = await page.evaluate((meta) => {
      const round1 = (n) => Math.round(n * 10) / 10;

      const layerEls = Array.from(document.querySelectorAll('[data-layer-id]'));
      const layers = layerEls
        .map((el) => {
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          const img = el.querySelector('img');
          return {
            z_index: Number.parseInt(el.dataset.zIndex || style.zIndex || '0', 10),
            layer_id: el.dataset.layerId,
            layer_name: el.dataset.layerName || '',
            asset_id: img ? img.dataset.assetId || img.id || null : null,
            asset_path: img ? img.dataset.repoPath || null : null,
            bbox: {
              x: round1(rect.x),
              y: round1(rect.y),
              width: round1(rect.width),
              height: round1(rect.height),
            },
            rotation_deg: Number.parseFloat(el.dataset.rotationDeg || '0'),
            flip_x: el.dataset.flipX === 'true',
            motion_role: el.dataset.motionRole || 'static',
            parallax_depth: Number.parseFloat(el.dataset.parallax || '0'),
          };
        })
        .sort((a, b) => a.z_index - b.z_index);

      const uiEls = Array.from(document.querySelectorAll('[data-ui-role]'));
      const elements = uiEls.map((el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const parentLayer = el.closest('[data-z-index]');
        const zVal = Number.parseInt(
          el.dataset.zIndex || (parentLayer ? parentLayer.dataset.zIndex : '') || style.zIndex || '13',
          10
        );
        const entry = {
          id: el.id || el.dataset.uiRole,
          role: el.dataset.uiRole,
          text: (el.dataset.uiText || el.textContent || '').trim(),
          z_index: Number.isNaN(zVal) ? 13 : zVal,
          bbox: {
            x: round1(rect.x),
            y: round1(rect.y),
            width: round1(rect.width),
            height: round1(rect.height),
          },
        };
        if (el.dataset.fgHex) {
          entry.fg_hex = el.dataset.fgHex;
        } else if (style.color) {
          entry.color = style.color;
        }
        return entry;
      });

      const texts = {};
      for (const el of elements) {
        if (el.role !== 'glass_capsule') {
          texts[el.role] = el.text;
        }
      }

      const imgEls = Array.from(document.querySelectorAll('img'));
      const assets = imgEls.map((img) => ({
        id: img.dataset.assetId || img.id || 'unnamed_asset',
        path: img.dataset.repoPath || img.getAttribute('src') || '',
        loaded: Boolean(img.complete && img.naturalWidth > 0),
        natural_width: img.naturalWidth,
        natural_height: img.naturalHeight,
      }));

      const fontMap = new Map();
      for (const f of document.fonts) {
        const family = f.family.replace(/^["']|["']$/g, '');
        const key = `${family}:${f.weight}`;
        if (!fontMap.has(key) || f.status === 'loaded') {
          fontMap.set(key, { family, weight: String(f.weight), status: f.status });
        }
      }
      const fonts = Array.from(fontMap.values()).filter((f) => f.status === 'loaded');

      const bodyText = document.body.innerText || '';
      const tofuDetected = bodyText.includes('\uFFFD');

      const out = {
        directive_id: 'DIR-BUILD-RESIZE-ENGINE-063',
        banner_id: meta.banner_id,
        format: meta.format_label,
        execution_mode: 'MULTI_SIZE_ADAPTIVE_RESIZE',
        dimensions: { width: meta.width, height: meta.height },
        safe_margins: meta.safe_margins,
        burst_origin: { x: meta.burst_origin[0], y: meta.burst_origin[1] },
        template: meta.template_rel,
        output_image: meta.png_rel,
        output_psd: meta.psd_rel,
        texts,
        elements,
        layers,
        assets,
        fonts,
        glyph_check: {
          tofu_detected: tofuDetected,
          verified_text_length: bodyText.trim().length,
        },
      };

      if (meta.flush_left_axis_x !== null && meta.flush_left_axis_x !== undefined) {
        const targetIds = ['ui_logo', 'ui_subcopy_capsule', 'ui_headline', 'ui_cta_dock'];
        const leftCoords = {};
        for (const tid of targetIds) {
          const node = document.getElementById(tid);
          if (node) {
            leftCoords[tid] = round1(node.getBoundingClientRect().x);
          }
        }
        const vals = Object.values(leftCoords);
        const maxDev = vals.length
          ? round1(Math.max(...vals.map((v) => Math.abs(v - meta.flush_left_axis_x))))
          : null;
        out.flush_left_alignment = {
          directive_id: 'DIR-ENFORCE-FLUSH-LEFT-ALIGNMENT-064',
          axis_x_px: meta.flush_left_axis_x,
          component_left_x: leftCoords,
          max_deviation_px: maxDev,
          aligned: maxDev !== null && maxDev <= 0.5,
        };
      }
      return out;
    }, job.meta);

    if (failedRequests.length > 0) {
      manifest.failed_requests = failedRequests;
    }

    fs.mkdirSync(path.dirname(job.json_path), { recursive: true });
    fs.writeFileSync(job.json_path, JSON.stringify(manifest, null, 2) + '\n', 'utf-8');

    // 3. Per-layer isolated transparent RGBA capture for pixel-exact layered PSD
    fs.mkdirSync(job.layers_out_dir, { recursive: true });
    for (const entry of job.capture_layers) {
      const css = buildIsolationCss(entry);
      await page.evaluate((cssText) => {
        let styleEl = document.getElementById('__psd_iso_style__');
        if (!styleEl) {
          styleEl = document.createElement('style');
          styleEl.id = '__psd_iso_style__';
          document.head.appendChild(styleEl);
        }
        styleEl.textContent = cssText;
      }, css);

      const outPath = path.join(job.layers_out_dir, `${entry.id}.png`);
      await page.screenshot({
        path: outPath,
        type: 'png',
        omitBackground: true,
        clip: { x: 0, y: 0, width: job.width, height: job.height },
        timeout: 30000,
      });
    }

    await context.close();
  }
} finally {
  await browser.close();
}
"""


def render_all_via_playwright(jobs: List[Dict[str, Any]], tmp_dir: Path) -> None:
    jobs_path = tmp_dir / "playwright_jobs.json"
    jobs_path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")

    proc = subprocess.run(
        ["node", "--input-type=module", "-e", PLAYWRIGHT_BATCH_JS, str(jobs_path)],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Playwright batch render failed (exit {proc.returncode}):\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )


def ensure_rgba_32bit_png(raw_png: Path, out_png: Path, expected_size: Tuple[int, int]) -> Tuple[int, int, str]:
    """Ensure final PNG output is exact viewport dimensions in RGBA 32-bit mode."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(raw_png) as im:
        rgba = im.convert("RGBA")
        if rgba.size != expected_size:
            raise ValueError(f"Viewport mismatch for {out_png.name}: got {rgba.size}, expected {expected_size}")
        rgba.save(out_png, format="PNG", optimize=True)
        return rgba.width, rgba.height, rgba.mode


# ==============================================================================
# STEP 3: MULTI-LAYER PSD PACKAGER (EXACT MASTER 5-GROUP STRUCTURE)
# ==============================================================================
def tight_crop_with_offset(img: Image.Image) -> Tuple[Image.Image, int, int]:
    """Crop empty transparent margin while preserving exact stage (left, top)."""
    bbox = img.getbbox()
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0)), 0, 0
    return img.crop(bbox), int(bbox[0]), int(bbox[1])


def _clean_psd_layer_alpha(img: Image.Image) -> Image.Image:
    """Zero out RGB where alpha==0 and remove premultiplication dark-halo pixels on anti-aliased rims."""
    import numpy as np
    from scipy.ndimage import binary_dilation, distance_transform_edt, maximum_filter, minimum_filter

    arr = np.array(img.convert("RGBA"), dtype=np.uint8)
    alpha_u8 = arr[:, :, 3]
    rgb_u8 = arr[:, :, :3].copy()
    rgb_u8[alpha_u8 == 0] = 0

    a = alpha_u8.astype(np.float32) / 255.0
    rgb_f = rgb_u8.astype(np.float32) / 255.0
    luma = 0.2126 * rgb_f[:, :, 0] + 0.7152 * rgb_f[:, :, 1] + 0.0722 * rgb_f[:, :, 2]

    opaque = a >= 0.99
    if np.any(opaque) and np.any(alpha_u8 < 250):
        near_op = binary_dilation(opaque, iterations=2)
        partial = (a > 0.05) & (a < 0.95) & near_op
        op_luma = np.where(opaque, luma, 1.0)
        nbr_min = minimum_filter(op_luma, size=3, mode="nearest")
        has_op_nbr = maximum_filter(opaque.astype(np.uint8), size=3, mode="nearest") > 0
        dark_halo = partial & has_op_nbr & (nbr_min > 0.15) & (luma < 0.50 * nbr_min)
        if np.any(dark_halo):
            _, (ny, nx) = distance_transform_edt(~opaque, return_indices=True)
            hy, hx = np.where(dark_halo)
            rgb_u8[hy, hx] = rgb_u8[ny[hy, hx], nx[hy, hx]]

    return Image.fromarray(np.dstack([rgb_u8, alpha_u8]), mode="RGBA")


def add_pixel_layer(
    container: Any,
    img: Image.Image,
    name: str,
    left: int,
    top: int,
    unicode_name: Optional[str] = None,
) -> None:
    cleaned = _clean_psd_layer_alpha(img)
    pl = container.create_pixel_layer(cleaned, name=name, top=int(top), left=int(left))
    if unicode_name:
        pl.tagged_blocks.set_data(Tag.UNICODE_LAYER_NAME, unicode_name)


def build_layered_psd(
    spec: VariationSpec,
    layers_dir: Path,
) -> Tuple[Path, int, int]:
    """
    Assemble an independent, non-flattened RGB 8-bit Adobe Photoshop PSD
    matching the 5-group / 2-nested-UI-folder hierarchy of `gsshop_master_1080x1080.psd`.
    """
    psd = PSDImage.new("RGBA", (spec.width, spec.height))
    top_groups: Dict[str, Any] = {}
    sub_groups: Dict[Tuple[str, str], Any] = {}

    for entry in PSD_CAPTURE_SPEC:
        grp_name = entry["group"]
        if grp_name not in top_groups:
            top_groups[grp_name] = psd.create_group(name=grp_name, open_folder=True)
        parent = top_groups[grp_name]

        sub_name = entry.get("subgroup")
        if sub_name:
            sub_key = (grp_name, sub_name)
            if sub_key not in sub_groups:
                sub_groups[sub_key] = parent.create_group(name=sub_name, open_folder=True)
            target_container = sub_groups[sub_key]
        else:
            target_container = parent

        layer_png = layers_dir / f"{entry['id']}.png"
        if not layer_png.exists():
            raise FileNotFoundError(f"Captured layer PNG missing: {layer_png}")

        with Image.open(layer_png) as raw_im:
            rgba = raw_im.convert("RGBA")
            if entry.get("full_canvas"):
                cropped, left, top = rgba.copy(), 0, 0
            else:
                cropped, left, top = tight_crop_with_offset(rgba)

        add_pixel_layer(
            target_container,
            cropped,
            name=entry["name"],
            left=left,
            top=top,
            unicode_name=entry.get("unicode_name"),
        )

    # Embed standard sRGB ICC profile
    try:
        psd.image_resources[Resource.ICC_PROFILE] = ImageResource(
            key=Resource.ICC_PROFILE,
            data=SRGB_ICC,
        )
    except Exception:
        pass

    spec.psd_path.parent.mkdir(parents=True, exist_ok=True)
    psd.save(str(spec.psd_path))

    # Reload to verify structural integrity (groups & independent pixel layers)
    reloaded = PSDImage.open(str(spec.psd_path))
    total_groups = 0
    total_layers = 0

    def _count(node: Any) -> None:
        nonlocal total_groups, total_layers
        for child in node:
            if child.is_group():
                total_groups += 1
                _count(child)
            else:
                total_layers += 1

    _count(reloaded)
    return spec.psd_path, total_groups, total_layers


# ==============================================================================
# ORCHESTRATOR & CLI ENTRYPOINT
# ==============================================================================
def format_size(num_bytes: int) -> str:
    kb = num_bytes / 1024.0
    if kb >= 1024.0:
        return f"{kb / 1024.0:.2f} MB"
    return f"{kb:.1f} KB"


def run_engine(selected_sizes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    VARIATIONS_DIR.mkdir(parents=True, exist_ok=True)
    PSD_DIR.mkdir(parents=True, exist_ok=True)

    copy = load_copy_context()
    targets = [
        v for v in VARIATIONS
        if not selected_sizes or v.key in selected_sizes
    ]
    if not targets:
        raise ValueError(f"No matching variations for sizes: {selected_sizes}")

    results: List[Dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="gsshop_resize_engine_") as td:
        tmp_root = Path(td)
        playwright_jobs: List[Dict[str, Any]] = []

        for spec in targets:
            work_dir = tmp_root / spec.key
            compiled_html = work_dir / f"{spec.banner_id}.html"
            raw_png = work_dir / f"{spec.banner_id}_raw.png"
            iso_layers_dir = work_dir / "layers"

            compile_template(spec, compiled_html, copy)
            safe_margins = load_safe_margins(spec.width, spec.height)

            playwright_jobs.append(
                {
                    "key": spec.key,
                    "width": spec.width,
                    "height": spec.height,
                    "compiled_html": str(compiled_html),
                    "raw_png": str(raw_png),
                    "json_path": str(spec.json_path),
                    "layers_out_dir": str(iso_layers_dir),
                    "capture_layers": [
                        {"id": item["id"], "layer_id": item["layer_id"], "mode": item["mode"]}
                        for item in PSD_CAPTURE_SPEC
                    ],
                    "meta": {
                        "banner_id": spec.banner_id,
                        "format_label": spec.format_label,
                        "width": spec.width,
                        "height": spec.height,
                        "safe_margins": safe_margins,
                        "burst_origin": list(spec.burst_origin),
                        "flush_left_axis_x": spec.flush_left_axis_x,
                        "template_rel": f"templates/{spec.template_file}",
                        "png_rel": f"output/TASK_GSSHOP/variations/gsshop_{spec.width}x{spec.height}.png",
                        "psd_rel": f"output/TASK_GSSHOP/variations/psd/gsshop_{spec.width}x{spec.height}.psd",
                    },
                }
            )

        print(f"[ENGINE] Rendering {len(targets)} GS SHOP variations via Playwright Chromium...")
        render_all_via_playwright(playwright_jobs, tmp_root)

        for spec, job in zip(targets, playwright_jobs):
            w, h, mode = ensure_rgba_32bit_png(Path(job["raw_png"]), spec.png_path, (spec.width, spec.height))
            psd_path, num_groups, num_layers = build_layered_psd(spec, Path(job["layers_out_dir"]))

            png_bytes = spec.png_path.stat().st_size
            json_bytes = spec.json_path.stat().st_size
            psd_bytes = psd_path.stat().st_size

            manifest_data = json.loads(spec.json_path.read_text(encoding="utf-8"))
            all_assets_ok = all(a.get("loaded") for a in manifest_data.get("assets", []))
            flush_audit = manifest_data.get("flush_left_alignment")

            results.append(
                {
                    "size": spec.key,
                    "format": spec.format_label,
                    "png_status": f"OK ({w}x{h} {mode})",
                    "psd_status": f"OK ({num_groups} groups / {num_layers} layers)",
                    "json_status": f"OK ({len(manifest_data.get('layers', []))} layers, assets={'OK' if all_assets_ok else 'ERR'})",
                    "png_size": format_size(png_bytes),
                    "psd_size": format_size(psd_bytes),
                    "json_size": format_size(json_bytes),
                    "png_path": str(spec.png_path.relative_to(ROOT_DIR)),
                    "json_path": str(spec.json_path.relative_to(ROOT_DIR)),
                    "psd_path": str(psd_path.relative_to(ROOT_DIR)),
                    "flush_left_alignment": flush_audit,
                }
            )

    print("\n" + "=" * 116)
    print("GS SHOP MULTI-SIZE RESIZE ENGINE — COMPLETION SUMMARY (DIR-BUILD-RESIZE-ENGINE-063)")
    print("=" * 116)
    print(f"{'Size':<11} | {'PNG Status':<22} | {'PSD Status':<28} | {'PNG Size':<10} | {'PSD Size':<10} | {'PNG Path'}")
    print("-" * 116)
    for r in results:
        print(
            f"{r['size']:<11} | {r['png_status']:<22} | {r['psd_status']:<28} | "
            f"{r['png_size']:<10} | {r['psd_size']:<10} | {r['png_path']}"
        )
    print("=" * 116)

    for r in results:
        if r.get("flush_left_alignment"):
            fa = r["flush_left_alignment"]
            print(
                f"[FLUSH-LEFT AUDIT 1200x600] axis_x={fa['axis_x_px']}px | "
                f"aligned={fa['aligned']} (max_dev={fa['max_deviation_px']}px) | "
                f"coords={fa['component_left_x']}"
            )
    return results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GS SHOP Automated Multi-Size Banner Resizing Engine (DIR-BUILD-RESIZE-ENGINE-063)"
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        choices=[v.key for v in VARIATIONS],
        help="Optional subset of sizes to build (default: all 3 sizes: 1200x600 300x250 800x1500)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_engine(args.sizes)
