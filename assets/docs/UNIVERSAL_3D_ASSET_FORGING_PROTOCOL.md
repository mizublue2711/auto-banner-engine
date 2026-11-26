# UNIVERSAL 3D ASSET FORGING PROTOCOL (SOP-FORGE-3D)
**Authoritative Pipeline Specification for Procedural 3D Asset Casting, Safe PBR Shading, and Zero-Fringe Transparency**

This operational protocol establishes the authoritative engineering standard for synthesizing, texturing, rendering, and verifying independent 3D assets across creative engines, interactive WebGL applications, and automated banner generation pipelines. The protocol eliminates ad-hoc manual cropping, permanently deprecates low-resolution bitmap slicing, and ensures full interoperability between real-time 3D environments and high-resolution 2D marketing compositions.

---

## 1. Executive Protocol & Core Directives

The practice of manually slicing flat reference sheets or extracting cropped bitmaps introduces severe visual defects, including non-anti-aliased stepped edges, resolution degradation upon scaling, and destructive gray halos caused by background color bleeding. To guarantee uncompromising visual fidelity and pipeline determinism across all automated workflows, all engineering personnel and autonomous agents must strictly abide by three non-negotiable operational directives.

### Zero Tolerance Directives

*   **Permanent Deprecation of Bitmap Slicing**: Assets must never be cropped, keyed, or sliced from pre-rendered bitmap collages or reference photography. Every asset must be authored or cast from scratch utilizing parametric mathematical routines, procedural vector stencils, or headless 3D render pipelines.
*   **Native RGBA Transparency (Zero Matting / Defringing)**: All 3D assets must be rendered directly onto an empty frame buffer with an absolute alpha value of zero (`alpha = 0`). Post-render background removal, chroma keying, color thresholding, and defringing algorithms are strictly prohibited, as they destroy anti-aliased perimeter pixels and create discolored contact halos.
*   **PBR Albedo Safety Clamping**: Pure white (`#FFFFFF` with 100% reflectance) does not exist in physically based rendering environments and triggers destructive specular overexposure. All white surfaces, snow accents, and ceramic highlights must be clamped within an 80% to 85% reflectance ceiling (`#DCE4EC` to `#EDF2F7`).

---

## 2. Canvas Geometry & Mathematical Bounding Matrix

Deterministic rendering requires strict adherence to resolution standards and safe margin constraints. Centering assets within bounded canvas coordinates prevents boundary clipping and preserves geometric proportions across automated layout engines.

### Bounding Matrices by Asset Classification

The pipeline recognizes two canonical geometric form factors, each tailored to distinct operational consumers:

| Parameter | Square 3D Component / Decor | Rectangular Decal & Brand Badge |
| :--- | :--- | :--- |
| **Canvas Dimensions** | 1024 × 1024 pixels | 2048 × 1024 pixels (Strict 2:1 Ratio) |
| **Aspect Ratio Mandate** | 1:1 Uniform | 2:1 Enforced (Anti-Distortion Standard) |
| **Safe Margin** | Exactly 40 pixels on all four sides | Exactly 40 pixels on all four sides |
| **Active Geometry Bounding Box** | Centered within 944 × 944 pixels | Centered within 1968 × 944 pixels |
| **Background Fill** | Pure RGBA Transparent (`0x00000000`) | Pure RGBA Transparent (`0x00000000`) |
| **Color Space** | sRGB with Linear Internal Processing | sRGB with Linear Internal Processing |

Embedding rectangular badges or labels into square canvas textures forces artificial UV stretching in WebGL scene graphs, severely distorting subsequent 2D graphic compositing. Rectangular elements must preserve the 2:1 aspect ratio across all generation passes.

---

## 3. PBR Colorimetrics & Shading Stack

Achieving a tactile clay, smooth porcelain, or glossy enamel aesthetic requires structured balance across ambient occlusion, surface roughness, and directional specular illumination.

### Colorimetric Thresholds and Lighting Standards

*   **Primary Hue Mapping**: Brand tokens define the primary chromatic identity. For festive and winter motifs, the baseline azure blue is locked to `#0F78FF`, complemented by subtle cool-ice blue ambient tones (`#E0F2FE`).
*   **Metallic Accents**: Structural caps, hooks, and metallic fasteners must resolve to desaturated silver-gray tones (`#E2E8F0`) with heightened specular reflection and reduced surface roughness.
*   **Soft Ambient Shadows**: Contact ambient occlusion and crevice shadows must utilize semi-transparent ambient passes (`rgba(15, 120, 255, 0.15)`) rather than dirty black shadows, preserving clean translucency.
*   **Specular Key Lighting**: The primary directional key light must be positioned at the top-left (approximately 45-degree elevation), producing crisp, natural specular highlights on curved tubular geometry and spherical crowns.

---

## 4. The 5-Stage Procedural Forging Workflow

Every asset forging task must progress sequentially through five bounded execution phases. Bypassing any phase invalidates the asset package.

### Workflow Sequence

1.  **Stage 1 — Specification & Token Lock**: Retrieve the task schema and lock all operational tokens, including destination paths (`assets/brands/<brand>/decors/`), canvas bounding parameters, and clamped color hex values.
2.  **Stage 2 — Geometry & Vector Foundation**: Define the underlying geometric structure. Utilize procedural splines, extrusions, CSG operations, or immutable `.svg` vector stencils. Enforce smooth chamfers, beveled perimeters, and uniform tubular thickness to prevent paper-thin edges.
3.  **Stage 3 — Material Shading & Lighting**: Assign PBR shader attributes. Apply clamped diffuse albedo, tune specular highlights for porcelain or glossy sheen, and cast directional light from the designated top-left anchor.
4.  **Stage 4 — Native RGBA Alpha Rendering**: Execute the render pass directly to target resolution. The renderer must output 32-bit PNG files with pristine per-pixel alpha transparency, clean anti-aliasing, and zero background canvas interaction.
5.  **Stage 5 — Automated QA Audit Gate**: Subject the rendered output to automated pixel verification scripts to validate boundary clearance, resolution fidelity, and color channel cleanliness.

---

## 5. Procedural Synthesis Reference Implementation

To eliminate ambiguity for autonomous agents and technical artists, the following standalone Python script demonstrates the mathematical generation of a 3D volumetric beveled holiday ornament with native alpha transparency and clamped PBR albedo.

### Native Procedural Generator (`engine/procedural_forge.py`)

```python
#!/usr/bin/env python3
"""
Procedural 3D Asset Forging Engine
Generates pristine 3D decor elements directly onto transparent RGBA canvases.
"""

import math
import numpy as np
from PIL import Image

def generate_3d_bauble(output_path, size=1024, margin=40):
    canvas = np.zeros((size, size, 4), dtype=np.float32)
    center = size / 2.0
    radius = (size - 2 * margin) / 2.0 - 20.0

    # Directional Key Light (Top-Left Anchor)
    light_dir = np.array([-0.577, -0.577, 0.577], dtype=np.float32)
    light_dir /= np.linalg.norm(light_dir)

    # Color Palette Tokens
    azure_blue = np.array([15.0 / 255.0, 120.0 / 255.0, 255.0 / 255.0], dtype=np.float32)
    clamped_white = np.array([237.0 / 255.0, 242.0 / 255.0, 247.0 / 255.0], dtype=np.float32)
    silver_cap = np.array([226.0 / 255.0, 232.0 / 255.0, 240.0 / 255.0], dtype=np.float32)

    y_indices, x_indices = np.indices((size, size), dtype=np.float32)
    dx = x_indices - center
    dy = y_indices - center
    dist_sq = dx**2 + dy**2
    sphere_mask = dist_sq <= radius**2

    # Spherical Normal Computation
    dz = np.zeros_like(dx)
    dz[sphere_mask] = np.sqrt(radius**2 - dist_sq[sphere_mask])
    
    nx = np.zeros_like(dx)
    ny = np.zeros_like(dy)
    nz = np.zeros_like(dz)
    
    nx[sphere_mask] = dx[sphere_mask] / radius
    ny[sphere_mask] = dy[sphere_mask] / radius
    nz[sphere_mask] = dz[sphere_mask] / radius

    # Diffuse Dot Product
    n_dot_l = np.maximum(0.0, -(nx * light_dir[0] + ny * light_dir[1] + nz * light_dir[2]))

    # Specular Blinn-Phong Component
    view_dir = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    half_vec = light_dir + view_dir
    half_vec /= np.linalg.norm(half_vec)
    n_dot_h = np.maximum(0.0, -(nx * half_vec[0] + ny * half_vec[1] + nz * half_vec[2]))
    specular = (n_dot_h ** 32.0) * 0.45

    # Decorative Stripe Pattern
    stripe_freq = 0.04
    pattern = np.sin((dx + dy) * stripe_freq)
    stripe_mask = pattern > 0.0

    # Base Color Blending
    base_color = np.zeros((size, size, 3), dtype=np.float32)
    base_color[stripe_mask] = azure_blue
    base_color[~stripe_mask] = clamped_white

    # Composite Shading
    ambient_illumination = 0.35
    shaded_rgb = base_color * (ambient_illumination + 0.65 * n_dot_l[:, :, None]) + specular[:, :, None]
    shaded_rgb = np.clip(shaded_rgb, 0.0, 1.0)

    # Sub-pixel Anti-Aliased Alpha Edge
    edge_dist = np.sqrt(dist_sq) - radius
    alpha = np.clip(0.5 - edge_dist, 0.0, 1.0)

    canvas[..., :3] = shaded_rgb * 255.0
    canvas[..., 3] = alpha * 255.0

    result_img = Image.fromarray(canvas.astype(np.uint8), mode='RGBA')
    result_img.save(output_path, 'PNG')
    print(f"[OK] Pristine 3D asset forged at: {output_path}")

if __name__ == '__main__':
    generate_3d_bauble("decor_bauble_sample.png")
```

---

## 6. Multi-Target Output Specifications

Asset packages must be structured according to their intended operational pipeline: 2D automated banner compositing or interactive 3D WebGL runtime consumption.

### Target Classification & Artifact Delivery

#### A. Automated 2D Marketing Decor Target
For static banner compositing, Remotion graphic sequences, and UI illustrations, deliver a single master asset:
*   **File Path**: `assets/brands/<brand_id>/decors/<asset_name>.png`
*   **Encoding**: 32-bit PNG (RGBA with 8 bits per channel)
*   **Resolution**: 1024 × 1024 pixels (or 2048 × 1024 pixels for 2:1 rectangular elements)
*   **Alpha Channel**: 100% transparent exterior with sub-pixel edge blending.

#### B. Interactive WebGL Runtime Target (6-File PBR Contract)
For interactive real-time 3D viewers, such as mattress brand badges and physical components, cast the authoritative six-file package into the master vault:

| File Name | Format | Channel Space | Functional Role in Three.js Scene Graph |
| :--- | :--- | :--- | :--- |
| `01_baseColor.png` | PNG-32 (Alpha) | sRGB | Delit diffuse albedo bound to `material.map`. Strictly free of baked cast shadows. |
| `02_normal.png` | PNG-24/32 | Linear | OpenGL Tangent Space (+Y up) recreation of micro-stitching and beveled relief. |
| `03_roughness.png` | PNG-8/24 | Linear | Grayscale roughness distribution contrasting matte substrates and lustrous sheen threads. |
| `04_height.png` | PNG-16/24 | Linear | Micro-elevation displacement map driving structural surface embossing. |
| `05_ambientOcclusion.png` | PNG-8/24 | Linear | Contact ambient occlusion in embroidery crevices and perimeter joints. |
| `06_beauty_render_4k.png` | PNG-32 (Alpha) | sRGB | 4K front orthographic master render with clean alpha cutout for 2D fallback slots. |

---

## 7. Automated Quality Assurance Gate

Manual visual inspection is insufficient for detecting single-pixel clipping and subtle background fringing. Every generated asset must pass programmatic verification via `engine/qa_asset_auditor.py`.

### Automated Verification Script (`engine/qa_asset_auditor.py`)

```python
#!/usr/bin/env python3
"""
Automated QA Asset Auditor for SOP-FORGE-3D
Validates image dimensions, alpha channel integrity, and boundary margin clearance.
"""

import sys
import os
from PIL import Image
import numpy as np

def audit_asset(file_path, expected_size=(1024, 1024), margin=40):
    print(f"--> Auditing: {file_path}")
    if not os.path.exists(file_path):
        print(f"[FAIL] File not found: {file_path}")
        return False

    with Image.open(file_path) as img:
        if img.mode != 'RGBA':
            print(f"[FAIL] Invalid color mode: {img.mode}. Must be RGBA.")
            return False

        if img.size != expected_size:
            print(f"[FAIL] Dimension mismatch: Got {img.size}, expected {expected_size}.")
            return False

        arr = np.array(img)
        alpha = arr[:, :, 3]

        if np.all(alpha == 255):
            print("[FAIL] Image is completely opaque. Native alpha channel missing.")
            return False
        if np.all(alpha == 0):
            print("[FAIL] Image is completely transparent.")
            return False

        h, w = alpha.shape
        top_slice = alpha[0:margin, :]
        bottom_slice = alpha[h - margin:h, :]
        left_slice = alpha[:, 0:margin]
        right_slice = alpha[:, w - margin:w]

        clipped_pixels = (
            np.count_nonzero(top_slice > 0) +
            np.count_nonzero(bottom_slice > 0) +
            np.count_nonzero(left_slice > 0) +
            np.count_nonzero(right_slice > 0)
        )

        if clipped_pixels > 0:
            print(f"[FAIL] Boundary violation: {clipped_pixels} non-transparent pixels in safe margin.")
            return False

        rgb = arr[:, :, :3]
        opaque_mask = alpha > 200
        if np.any(opaque_mask):
            max_val = np.max(rgb[opaque_mask])
            if max_val >= 254:
                print(f"[WARN] Albedo clamp breached: Maximum luminance reached {max_val}. Clamp to 247 recommended.")

    print(f"[PASS] {os.path.basename(file_path)} fully compliant with SOP-FORGE-3D.")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 qa_asset_auditor.py <path_to_directory_or_file>")
        sys.exit(1)

    target = sys.argv[1]
    targets = []
    if os.path.isdir(target):
        for root, _, files in os.walk(target):
            for f in files:
                if f.endswith('.png'):
                    targets.append(os.path.join(root, f))
    else:
        targets.append(target)

    all_passed = True
    for t in targets:
        if not audit_asset(t):
            all_passed = False

    if not all_passed:
        print("\n❌ QA AUDIT FAILED: One or more assets breached protocol.")
        sys.exit(1)
    else:
        print("\n✅ QA AUDIT PASSED: 100% compliant with SOP-FORGE-3D.")
        sys.exit(0)
```

---

## 8. Operational Directives & Agent Execution Templates

To eliminate instructional drift and preserve token budgets across future tasks, project managers and lead architects must issue micro-ticket directives formatted according to the standard template below.

### Universal Agent Directive Template

```markdown
# [TASK DIRECTIVE] SOP-FORGE-3D: <Item Name>

**Directive ID:** DIR-FORGE-<PROJECT>-<ID>
**Target Actor:** An (Antigravity Worker)
**Protocol Authority:** SOP-FORGE-3D / CAVP-v2.0
**Target Directory:** assets/brands/<brand>/decors/

### 1. Technical Specifications
- **Target Filename:** <file_name>.png
- **Canvas Dimensions:** 1024x1024 px (Safe margin 40px, centered geometry)
- **Palette Tokens:**
  - Primary Base: #<HEX>
  - Secondary Accent: #<HEX>
  - Albedo Snow White (Clamped): #EDF2F7
  - Ambient Shadow: rgba(15, 120, 255, 0.15)
- **Surface Aesthetics:** Smooth 3D Porcelain/Clay, rounded bevels, top-left directional highlight.

### 2. Operational Rules
1. Do not crop or slice from bitmap references. Synthesize natively from scratch.
2. Render directly onto an empty transparent canvas with native Alpha = 0.
3. Validate output before handoff:
   python3 engine/qa_asset_auditor.py assets/brands/<brand>/decors/<file_name>.png
```
