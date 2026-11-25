# AGENT OPERATIONAL RUNBOOK & WORKER PROTOCOL (`Agent.md`)
**System Target**: `auto-banner-engine`  
**Execution Agents**: Antigravity Worker (`An`), GitHub Copilot, Automation Sidecars  
**Execution Mode**: Strict Affirmative Action Space (Bounded Fail-Closed)

---

## 1. MISSION SCOPE & ROLE BOUNDARIES

`auto-banner-engine` is a deterministic production engine designed for digital advertising banner resizing, composition, and multi-ratio rendering.

### Primary Role
Workers operate strictly as **Pipeline Systems Engineers & Compositors**.
- **Scope Limit**: Read verified inputs, execute deterministic transformations, and trigger headless renders.
- **Decision Space**: All assets, colors, copy, and layout proportions are strictly bound to supplied repository sources.

---

## 2. STRICT ACTION TAXONOMY (ISOLATED WORKFLOWS)

Every requested action must belong exclusively to one of the following two isolated workflows:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        AUTO-BANNER-ENGINE                              │
├───────────────────────────────────┬────────────────────────────────────┤
│  WORKFLOW A: PRODUCTION RESIZING  │  WORKFLOW B: PARAMETRIC CREATIVE   │
│  (Existing Master Banner)         │  (New Creative from Brief)         │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Context: Task 1 (XEXYMIX)       │ • Context: Task 2 (Meritz)         │
│ • Source of Truth: Master PSD     │ • Source of Truth: Brand Tokens    │
│ • Mechanics: 100% Layer Transfer, │ • Mechanics: Lego Shell, Atomic    │
│   Canvas Reflow, Asset Splitting  │   Components, CSS Variables        │
│ • Task Directory:                 │ • Task Directory:                  │
│   tasks/task1_production/         │   tasks/task2_creative/            │
└───────────────────────────────────┴────────────────────────────────────┘

3. BOUNDED DIRECTORY LAYOUT
Workers operate exclusively within this designated structure:
auto-banner-engine/
├── Agent.md                            <-- Master Operational Protocol
├── config/
│   ├── banner_task.schema.json         <-- Strict Data Contract for Execution
│   ├── brand_tokens.schema.json        <-- Brand Tokens Schema
│   └── dimensions_catalog.json         <-- Target Dimension Specifications
├── assets/
│   ├── brands/                         <-- Extracted & Verified Brand Assets
│   │   ├── meritz/                     <-- Official Meritz Identity Assets
│   │   └── xexymix/                    <-- Official XEXYMIX Extracted Layers
│   └── master_sources/                 <-- Source Master Design Files (.psd)
│       ├── task1_xexymix/              <-- XEXYMIX Master Artwork (.psd)
│       └── task2_meritz/               <-- Meritz Brand Assets
├── tasks/
│   ├── task1_production/               <-- Workflow A Configs Only
│   │   └── xexymix_11_sizes.json
│   └── task2_creative/                 <-- Workflow B Configs Only
│       ├── meritz_option1.json
│       └── meritz_option2.json
├── templates/
│   ├── lego_shell.html                 <-- Master Headless Layout Container
│   ├── archetypes.css                  <-- Layout Archetype Rules (Vertical, Square, Wide, Micro)
│   └── components/                     <-- Atomic Layout Slots
│       ├── header.html
│       ├── hook.html
│       ├── visual_stage.html
│       ├── cta.html
│       └── disclaimers.html
├── engine/
│   ├── render.mjs                      <-- Headless Playwright Multi-Dimension Runner
│   ├── shadow_engine.py                <-- Parametric 2D Shadow Subsystem
│   ├── compositor.py                   <-- Multi-Layer Canvas Compositor
│   └── psd_extractor.py                <-- Automated PSD Layer Parser & Splitter
└── output/
    ├── task1_production/{task_id}/     <-- Verified Task 1 Exports
    └── task2_creative/{task_id}/       <-- Verified Task 2 Exports

4. AFFIRMATIVE EXECUTION PROTOCOLS
Protocol A: Workflow A (Production Resizing / Master PSD)
When processing an existing master design:
Asset Extraction:
Access the .psd file at assets/master_sources/task1_xexymix/.
Run engine/psd_extractor.py to extract 100% of visible artwork layers:
Background canvas & graphics
Product/Model cutouts with alpha channels intact
Feature highlight cards / Zoom badges
Typography layers & vector ribbons
Layout Adaptation:
Preserve all extracted layers across all target ratios.
Reflow layer positions dynamically using relative container rules:
Vertical (9:16, 4:5): Center-weighted layout, bottom-anchored CTA/ribbon.
Square (1:1): Balanced side-by-side or stacked composition.
Wide (1.91:1, 2.23:1): Horizontal two-column split.
Micro (< 400px): Scale primary visual and core headline to fill bounds; hide secondary fine-print cards for legibility.
Execution:
Run node engine/render.mjs --task tasks/task1_production/{task_file}.json.

Protocol B: Workflow B (Parametric Creative Generation)
When constructing new layouts from a structured creative brief:
Token Ingestion:
Read typography, color HEX codes, and dimensions exclusively from assets/brands/{brand_id}/tokens.json.
Lego Assembly:
Assemble exclusively via templates/lego_shell.html using the 5 modular components in templates/components/.
Apply styling exclusively through CSS custom variables bound to :root.
Execution:
Run node engine/render.mjs --task tasks/task2_creative/{task_file}.json.

5. VERIFICATION & EXIT CRITERIA (QUALITY GATE)
Every batch execution is complete ONLY when all following conditions evaluate to TRUE:
[ ] Data Grounding: 100% of image elements and color codes originate from files located in assets/.
[ ] Typography Stability: document.fonts.ready returns resolved; native Pretendard glyphs render without FOUT.
[ ] Visual Completeness:
In Workflow A: Model cutout, feature zoom thumbnails, and promotional badges are present in output renders.
In Workflow B: Hierarchy aligns with the design brief specification.
[ ] Render Integrity: Zero text overflow, zero clipping, and clean aspect-ratio scaling across all target resolutions.
If any required input is inaccessible or ambiguous, the pipeline halts immediately and transitions to: STATUS: BLOCKED_AWAITING_INPUT.
