#!/usr/bin/env node
/**
 * DIR-ASSEMBLE-COSRX-MASTER-1200x1200-077: Final Master Banner Assembler
 * Renders `templates/cosrx_master_1200x1200.html` at exact 1200x1200px via Playwright (timeout=15000ms),
 * captures `output/TASK_COSRX/cosrx_master_1200x1200.png`, and exports the DOM-verified
 * 13-layer layout manifest `output/TASK_COSRX/cosrx_master_1200x1200.json`.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, "..");

const TEMPLATE_PATH = path.join(ROOT_DIR, "templates", "cosrx_master_1200x1200.html");
const OUT_DIR = path.join(ROOT_DIR, "output", "TASK_COSRX");
const OUT_PNG = path.join(OUT_DIR, "cosrx_master_1200x1200.png");
const OUT_JSON = path.join(OUT_DIR, "cosrx_master_1200x1200.json");

async function main() {
  if (!fs.existsSync(TEMPLATE_PATH)) {
    throw new Error(`Master template not found: ${TEMPLATE_PATH}`);
  }
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true, timeout: 15000 });
  try {
    const context = await browser.newContext({
      viewport: { width: 1200, height: 1200 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);

    const failedRequests = [];
    page.on("requestfailed", (req) => {
      failedRequests.push({ url: req.url(), error: req.failure()?.errorText || "failed" });
    });

    const templateUrl = pathToFileURL(TEMPLATE_PATH).href;
    await page.goto(templateUrl, { waitUntil: "load", timeout: 15000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(500);

    // Capture exact 1200x1200 PNG
    await page.screenshot({
      path: OUT_PNG,
      type: "png",
      clip: { x: 0, y: 0, width: 1200, height: 1200 },
      timeout: 15000,
    });

    // Extract complete DOM-measured manifest for QA & downstream motion
    const manifest = await page.evaluate(() => {
      const round1 = (n) => Math.round(n * 10) / 10;

      // 1. Layers in strict Painter's Algorithm order (Z=1 -> Z=10)
      const layerEls = Array.from(document.querySelectorAll("[data-layer-id]"));
      const layers = layerEls
        .map((el) => {
          const rect = el.getBoundingClientRect();
          const style = window.getComputedStyle(el);
          const img = el.querySelector("img");
          return {
            z_index: Number.parseInt(el.dataset.zIndex || style.zIndex || "0", 10),
            layer_id: el.dataset.layerId,
            layer_name: el.dataset.layerName || "",
            asset_id: img ? img.dataset.assetId || img.id || null : null,
            asset_path: img ? img.dataset.repoPath || null : null,
            bbox: {
              x: round1(rect.x),
              y: round1(rect.y),
              width: round1(rect.width),
              height: round1(rect.height),
            },
            rotation_deg: Number.parseFloat(el.dataset.rotationDeg || "0"),
            flip_x: el.dataset.flipX === "true",
            motion_role: el.dataset.motionRole || "static",
            parallax_depth: Number.parseFloat(el.dataset.parallax || "0"),
          };
        })
        .sort((a, b) => a.z_index - b.z_index);

      // 2. UI / Text Elements (for Safe Zone & WCAG Contrast QA)
      const uiEls = Array.from(document.querySelectorAll("[data-ui-role]"));
      const elements = uiEls.map((el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        const parentLayer = el.closest("[data-z-index]");
        const zVal = Number.parseInt(
          el.dataset.zIndex || (parentLayer ? parentLayer.dataset.zIndex : "") || style.zIndex || "13",
          10
        );
        const entry = {
          id: el.id || el.dataset.uiRole,
          role: el.dataset.uiRole,
          text: (el.dataset.uiText || el.textContent || "").trim(),
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
        texts[el.role] = el.text;
      }

      // 3. Asset load verification
      const imgEls = Array.from(document.querySelectorAll("img"));
      const assets = imgEls.map((img) => ({
        id: img.dataset.assetId || img.id || "unnamed_asset",
        path: img.dataset.repoPath || img.getAttribute("src") || "",
        loaded: Boolean(img.complete && img.naturalWidth > 0),
        natural_width: img.naturalWidth,
        natural_height: img.naturalHeight,
      }));

      // 4. Web font verification
      const fontMap = new Map();
      for (const f of document.fonts) {
        const family = f.family.replace(/^["']|["']$/g, "");
        const key = `${family}:${f.weight}`;
        if (!fontMap.has(key) || f.status === "loaded") {
          fontMap.set(key, {
            family,
            weight: String(f.weight),
            status: f.status,
          });
        }
      }
      const fonts = Array.from(fontMap.values()).filter((f) => f.status === "loaded");

      // 5. Tofu / U+FFFD glyph check
      const bodyText = document.body.innerText || "";
      const tofuDetected = bodyText.includes("\uFFFD");

      return {
        directive_id: "DIR-REFACTOR-ASSETS-AND-LAYERS-052",
        banner_id: "cosrx_master_1200x1200",
        execution_mode: "CANONICAL_ASSET_UNIFICATION",
        dimensions: { width: 1200, height: 1200 },
        safe_margins_px: 40,
        burst_origin: { x: 540, y: 680 },
        template: "templates/cosrx_master_1200x1200.html",
        output_image: "output/TASK_COSRX/cosrx_master_1200x1200.png",
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
    });

    if (failedRequests.length > 0) {
      manifest.failed_requests = failedRequests;
    }

    fs.writeFileSync(OUT_JSON, JSON.stringify(manifest, null, 2) + "\n", "utf-8");

    const sizeKb = (fs.statSync(OUT_PNG).size / 1024).toFixed(1);
    console.log(`[ASSEMBLER] Rendered ${OUT_PNG} (${sizeKb} KB)`);
    console.log(`[ASSEMBLER] Exported ${OUT_JSON} (${manifest.layers.length} layers, ${manifest.assets.length} assets, ${manifest.fonts.length} fonts)`);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("[ASSEMBLER] Fatal error:", err);
  process.exit(1);
});

// end of assembler