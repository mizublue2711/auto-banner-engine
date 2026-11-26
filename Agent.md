# UNIVERSAL AGENT RUNBOOK & WORKER PROTOCOL (`AGENT.md`)
**System Target**: `auto-banner-engine` (Headless Parameterized Design Engine)  
**Execution Actors**: Antigravity Worker, GitHub Copilot, n8n Automation Engine, Dify AI Orchestrator  
**Execution Mode**: Strict Affirmative Action Space (Bounded Fail-Closed)

---

## 1. SYSTEM MISSION & BOUNDARIES
The system processes structured JSON task payloads and verified design tokens into deterministic, publication-ready digital advertising banners across all standard programmatic ad ratios.

### Worker Persona & Operating Boundary
- **Role**: Deterministic Systems Engineer & Programmatic Compositor.
- **Whitelist Boundary**:
  1. Read inputs solely from parameterized locations: `config/`, `assets/brands/{brand_id}/`, `assets/campaigns/{campaign_id}/`.
  2. Execute structural modifications strictly via defined schemas and atomic layout templates.
  3. Validate output compliance with `dimensions_catalog.json` and platform safe zone rules.
- **Fail-Closed Rule**: If an asset, font, color token, or required safe-zone dimension is missing, ambiguous, or unverifiable, halt execution immediately with status: `BLOCKED_AWAITING_INPUT`.

---

## 2. STANDARDIZED WORKSPACE ARCHITECTURE
All operations occur within this dynamic multi-tenant structure:

```text
auto-banner-engine/
├── AGENT.md                               <-- Master Operational Protocol
├── config/
│   ├── banner_task.schema.json            <-- Data Contract for All Banner Tasks
│   ├── brand_tokens.schema.json           <-- Brand Identity Token Contract
│   ├── media_safe_zones_2026.json         <-- Platform Rules (Meta, Google, Naver, Kakao, Criteo)
│   └── dimensions_catalog.json            <-- Master Standard Dimension Specs
├── assets/
│   ├── fonts/                             <-- Verified Typography (Pretendard, Montserrat, etc.)
│   ├── shared/                            <-- Universal Badges, Ribbons, Arrows, Gradients
│   └── brands/{brand_id}/                 <-- Brand-Scoped Isolated Assets
│       ├── tokens.json                    <-- Colors, Typography Scale, Spacing Rules
│       ├── logos/                         <-- Vector/Transparent Alpha Logos
│       └── products/                      <-- Transparent Alpha PNG Product Cutouts
├── tasks/{campaign_id}/                   <-- Parameterized Task Descriptors
│   ├── task_manifest.json                 <-- Execution Matrix for the Campaign
│   └── variants/*.json                    <-- Specific Ratio Configurations
├── templates/
│   ├── lego_shell.html                    <-- Headless Container Canvas
│   ├── archetypes.css                     <-- Dynamic Responsive Form Factor Rules
│   └── components/                        <-- Atomic Visual Slots
│       ├── header.html                    <-- Brand Logo & Indicator Zone
│       ├── hook.html                      <-- Primary Title & Sub-copy Hierarchy
│       ├── visual_stage.html              <-- Product Cluster, Shadows & AI Key Visual
│       ├── cta.html                       <-- Button, Arrow, Countdown, Badge
│       └── disclaimers.html               <-- Legal Notice & Fine Print
├── engine/
│   ├── render.mjs                         <-- Playwright Headless Multi-Ratio Renderer
│   ├── resizer.py                         <-- Geometric Layer Reflow & Safe Zone Calculator
│   ├── shadow_engine.py                   <-- Parametric Product Grounding & Shadow Generator
│   └── qa_inspector.py                    <-- Automated Pixel & Safe Zone Gatekeeper
└── output/{campaign_id}/{task_id}/        <-- Verified Output Deliverables

3. CORE EXECUTION WORKFLOWS
Pipeline 1: Adaptive Production Resizing (Master Artwork Reflow)
Applies when scaling an existing Master Key Visual (GenAI stage, master visual, or cutout composition) to multi-ratio media:
Asset Staging: Store master key visual and cutouts in assets/brands/{brand_id}/ or campaign folder.
Dimension Mapping: Query media_safe_zones_2026.json for target ratio (1:1, 9:16, 1.91:1, 2:3, etc.).
Safe Zone Ingestion: Calculate bounded coordinate limits for text, CTA, and product focus.
Reflow Strategy:
Vertical (9:16): Stacked hierarchy; safe margins at top and bottom for native platform UI.
Square (1:1): Centered balanced composition or dynamic diagonal balance.
Horizontal (1.91:1): Split 2-column or 3-zone horizontal arrangement.
CLI Execution: python engine/resizer.py --task tasks/{campaign_id}/{task_file}.json
Pipeline 2: Parametric Modular Composition (Lego Assembler)
Applies when generating fresh creative variants directly from brief inputs:
Token Ingestion: Load brand rules from assets/brands/{brand_id}/tokens.json.
Component Hydration: Bind typography, colors, and layout slots into templates/components/ through CSS custom properties.
Shadow & Depth Synthesis: Ensure product cutouts receive natural grounding shadows via shadow_engine.py or CSS filters.
Headless Render: node engine/render.mjs --task tasks/{campaign_id}/{task_file}.json

4. VERIFICATION & EXIT CRITERIA (QA GATE)
Execution is marked COMPLETE only when qa_inspector.py verifies:
[ ] Data Grounding: 100% of images, colors, and text strings originate from verified configuration files.
[ ] Safe Zone Compliance: Zero essential text, logos, or CTA buttons intrude into platform-prohibited UI overlay zones.
[ ] Typography Integrity: Zero text overflow, zero line wrapping anomalies, clean font rendering without FOUT.
[ ] Asset Fidelity: Visual cutouts retain clean alpha boundaries with no jagged edges or color fringing.
[ ] Deterministic Export: Output files match target resolutions with strict pixel precision.
