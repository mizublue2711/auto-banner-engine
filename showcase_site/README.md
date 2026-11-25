# AUTO-BANNER // ENGINE — Performance Creative Showcase

Standalone web showcase for the **Chai Communication Assignment** built on the **Swiss Cybernetic Brutalism** design system (`#05050A` obsidian substrate, `#0D0D14` titanium plates, `#222536` 1px hairline borders, `#F4F4F6` laser white ink, and `#00E5FF` / `#00FF66` / `#FFB800` telemetry accents).

---

## 1. How to Preview

### Option A — Local HTTP Server (Recommended)
Run from the repository root (`/Users/macbookpro/auto-banner-engine`) so `../showcase_manifest.json` and `../deliverables/` resolve over HTTP:

```bash
npx serve .
# Open http://localhost:3000/showcase_site/
```

Or with Python:

```bash
python3 -m http.server 8080
# Open http://localhost:8080/showcase_site/
```

### Option B — Direct Offline File Open (`file://`)
Open `showcase_site/index.html` directly in any modern browser. If browser `file://` CORS restrictions block `fetch('../showcase_manifest.json')`, `js/app.js` automatically displays a protocol telemetry notice and hydrates from its embedded deterministic manifest snapshot.

---

## 2. Architecture of the 5 Interactive Zones (+ Deliverables Dock)

1. **Zone 01 — `#zone-hero` (CAD Core & 3D Parallax Viewport)**
   - Responsive `clamp(42px, 8vw, 125px)` Space Grotesk display wordmark with Amber `#FFB800` pipeline badge and `160px` pill Command Bar.
   - 16px Hero CAD Viewport displaying Meritz Option 2 with live mouse-move 3D Parallax Tilt (clamped to `6deg`, automatically disabled on `pointer: coarse` touch devices).
2. **Zone 02 — `#zone-xexymix` (Workflow A: 11-Ratio Production Matrix)**
   - Reactive filter pills (`[ ALL (11) ]`, `[ VERTICAL (4) ]`, `[ SQUARE (2) ]`, `[ WIDE (2) ]`, `[ MICRO (3) ]`) with smooth horizontal `no-scrollbar` overflow on mobile.
   - **HUD Laser Overlay Toggle** rendering 1px vector strokes for Orthogonal Manhattan Stepping, outer silhouette tangent protection, and 0% AI watermark compliance.
3. **Zone 03 — `#zone-meritz` (Workflow B: Dual-Core A/B & Matte Grain Inspector)**
   - Side-by-side comparison of Option 1 (Conservative Corporate) vs. Option 2 (Monumental 3D Zero-Gravity).
   - **Brand Palette Purity Widget** (`#EF3B24`, `#141414`, `#FFFFFF`, `#F2F2F2`) with click-to-copy and 100% compliance badge.
   - **Deep-Zoom Matte Grain Inspector Modal** (`2.35x` cursor & touch-drag loupe) with `overscroll-behavior: contain` to prevent page scroll trapping.
4. **Zone 04 — `#zone-under-the-hood` (Pipeline Telemetry & Multi-Agent Console)**
   - Visualizes the 3-stage deterministic sequence (`Worker Art` → `Worker Compositor` → `Worker QA`) and live QA Telemetry Table (`15/15 Rules Passed`, `< 0.5%` anti-plastic specular, `0px` glyph collision, `PASSED` UTF-16BE `luni` encoding).
5. **Zone 05 — `#zone-manifest-engine` (Manifest-Driven White-Label Sandbox)**
   - Syntax-highlighted live inspector for `showcase_manifest.json` with one-click JSON copy and a **White-Label Reusability Toggle** demonstrating multi-tenant client payload swapping.
6. **Footer — `#deliverables-dock` (Direct Download Hub)**
   - Direct download cards for Task 1 (11× sRGB JPEGs `<= 800KB`), Task 2 Option 1 & Option 2 layered `.psd` masters + `.jpg` previews, and `showcase_manifest.json`.

---

## 3. Manifest Data Schema (`showcase_manifest.json`)

To re-skin or extend this showcase for future client assignments, replace `showcase_manifest.json` at the repository root following this contract:

```json
{
  "engine_version": "1.0.0",
  "client": "<Client Name>",
  "author": "<Pipeline Author>",
  "theme_tokens": {
    "canvas_dark": "#05050A",
    "titanium_plate": "#0D0D14",
    "hairline_border": "#222536",
    "laser_white": "#F4F4F6",
    "status_emerald": "#00FF66",
    "accent_cyan": "#00E5FF",
    "highlight_amber": "#FFB800"
  },
  "tasks": {
    "task1_xexymix": {
      "title": "<Campaign Title>",
      "source_master": "<Master PSD Filename>",
      "total_dimensions": 11,
      "engine_highlights": ["..."],
      "placements": [
        { "id": "01", "name": "Meta Story", "ratio": "9:16", "resolution": "1440x2560", "file": "deliverables/..." }
      ]
    },
    "task2_meritz": {
      "title": "<Creative Title>",
      "brief_source": "<Brief File>",
      "brand_book_source": "<Brand Book File>",
      "brand_palette": { "vermillion_red": "#EF3B24", "obsidian_black": "#141414", "pure_white": "#FFFFFF", "chalk_white": "#F2F2F2" },
      "options": [
        { "option_id": "opt1_conservative", "label": "...", "psd_path": "deliverables/...", "preview_path": "deliverables/...", "art_direction": "..." }
      ],
      "qa_compliance": {
        "total_rules": 15,
        "passed_rules": 15,
        "anti_plastic_specular": "< 0.5%",
        "glyph_collision": "0px",
        "unicode_luni_encoding": "PASSED"
      }
    }
  }
}
```
