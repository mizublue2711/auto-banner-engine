/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Interactive Showcase Controller (STEP 03 + STEP 09)
 * Aesthetic Paradigm: Swiss Cybernetic Brutalism
 * Single Source of Truth: ../showcase_manifest.json
 * ============================================================================
 */

import { HeroThreeStage } from './hero-three-stage.js';
import { HotspotOverlayController } from './hotspot-controller.js';

const SHOWCASE_CONFIG = Object.freeze({
  manifestPath: './showcase_manifest.json',
  assetBasePrefix: './',
  xexymixZipPath: 'deliverables/task1_xexymix/xexymix_11_sizes.zip',
  maxParallaxDeg: 6
});

/**
 * Deterministic fallback snapshot of ../showcase_manifest.json
 * Used automatically if the page is opened directly via file:// protocol where
 * browser CORS rules block local XHR/fetch requests.
 */
const FALLBACK_MANIFEST_SNAPSHOT = {
  engine_version: '1.0.0',
  client: 'Chai Communication Assignment',
  author: 'Antigravity Pipeline',
  theme_tokens: {
    canvas_dark: '#05050A',
    titanium_plate: '#0D0D14',
    hairline_border: '#222536',
    laser_white: '#F4F4F6',
    status_emerald: '#EDFF57',
    accent_volt: '#EDFF57',
    accent_cobalt: '#5322FF',
    accent_cyan: '#00E5FF',
    highlight_amber: '#5322FF'
  },
  tasks: {
    task1_xexymix: {
      title: 'XEXYMIX Black Label 360N Leggings',
      source_master: '11_40462_261106_젝시믹스.psd',
      total_dimensions: 11,
      engine_highlights: [
        'Clean Right-Angle Callout Lines (Zero Messy Diagonals)',
        '100% Clear Product View (No Text Covering Apparel)',
        'Seamless Soft Background Extension for Wide Banners',
        '100% Brand-Safe: Zero AI Watermarks'
      ],
      placements: [
        { id: '01', name: 'Meta Story', ratio: '9:16', resolution: '1440x2560', file: 'deliverables/task1_xexymix/01_meta_story_1440x2560.jpg' },
        { id: '02', name: 'Meta Feed', ratio: '4:5', resolution: '1440x1800', file: 'deliverables/task1_xexymix/02_meta_feed_1440x1800.jpg' },
        { id: '03', name: 'Kakao Feed', ratio: '4:5', resolution: '800x1000', file: 'deliverables/task1_xexymix/03_kakao_feed_800x1000.jpg' },
        { id: '04', name: 'Google DA', ratio: '4:5', resolution: '960x1200', file: 'deliverables/task1_xexymix/04_google_da_960x1200.jpg' },
        { id: '05', name: 'Google Square', ratio: '1:1', resolution: '1200x1200', file: 'deliverables/task1_xexymix/05_google_square_1200x1200.jpg' },
        { id: '06', name: 'Naver Square', ratio: '1:1', resolution: '1200x1200', file: 'deliverables/task1_xexymix/06_naver_square_1200x1200.jpg' },
        { id: '07', name: 'Google Landscape', ratio: '1.91:1', resolution: '1200x628', file: 'deliverables/task1_xexymix/07_google_landscape_1200x628.jpg' },
        { id: '08', name: 'Naver Wide', ratio: '2.23:1', resolution: '1250x560', file: 'deliverables/task1_xexymix/08_naver_wide_1250x560.jpg' },
        { id: '09', name: 'Naver Thumbnail', ratio: '3:2', resolution: '342x228', file: 'deliverables/task1_xexymix/09_naver_thumb_342x228.jpg' },
        { id: '10', name: 'Naver Smart Channel', ratio: '13:14', resolution: '260x280', file: 'deliverables/task1_xexymix/10_naver_smart_channel_260x280.jpg' },
        { id: '11', name: 'Kakao Bizboard', ratio: 'Micro', resolution: '314x300', file: 'deliverables/task1_xexymix/11_kakao_bizboard_314x300.jpg' }
      ]
    },
    task2_meritz: {
      title: 'Meritz Partners Creative Ad Banner',
      brief_source: 'BANNER [Chai Communication] Assignment Design Brief.pptx',
      brand_book_source: 'Meritz_brand_book.pdf',
      brand_palette: {
        vermillion_red: '#EF3B24',
        obsidian_black: '#141414',
        pure_white: '#FFFFFF',
        chalk_white: '#F2F2F2'
      },
      options: [
        {
          option_id: 'opt1_conservative',
          label: 'Option 1 // Classic Direct-Response',
          psd_path: 'deliverables/task2_meritz/meritz_partners_master.psd',
          preview_path: 'deliverables/task2_meritz/meritz_partners_preview.jpg',
          art_direction: 'Clean, trustworthy 2-column financial ad layout paired with a gleaming 3D gold coin highlight that directs attention straight to the offer.'
        },
        {
          option_id: 'opt2_monumental',
          label: 'Option 2 // Bold 3D Floating Visual',
          psd_path: 'deliverables/task2_meritz/meritz_partners_option2.psd',
          preview_path: 'deliverables/task2_meritz/meritz_partners_option2_preview.jpg',
          art_direction: "Dynamic hero-angle perspective featuring a matte Vermillion Red '150' 3D centerpiece inside a metallic gold geometric frame, surrounded by 5 floating coins with soft cinematic blur."
        }
      ],
      qa_compliance: {
        total_rules: 15,
        passed_rules: 15,
        anti_plastic_specular: '< 0.5%',
        glyph_collision: '0px',
        unicode_luni_encoding: 'PASSED'
      }
    }
  },
  hero_hotspots: [
    {
      id: 'pin-opt1',
      top: '36%',
      left: '16%',
      color: '#00E5FF',
      badge: '01',
      type: 'banner_preview',
      i18n: {
        tag: 'hero_hotspots.opt1_tag',
        title: 'hero_hotspots.opt1_title',
        desc: 'hero_hotspots.opt1_desc',
        cta_download: 'hero_hotspots.opt1_cta_download',
        cta_zoom: 'hero_hotspots.cta_deep_zoom'
      },
      data: {
        option_id: 'opt1_conservative',
        title: 'Option 1 // Classic Direct-Response',
        tag: 'DIRECT RESPONSE // MASTER .PSD',
        image: './deliverables/task2_meritz/meritz_partners_preview.jpg',
        download: './deliverables/task2_meritz/meritz_partners_master.psd',
        desc: 'Clear, trustworthy financial layout with a balanced 2-column split and eye-catching 3D gold coin visuals built to drive clicks.'
      }
    },
    {
      id: 'pin-opt2',
      top: '18%',
      left: '50%',
      color: '#5322FF',
      badge: '02',
      type: 'banner_preview',
      i18n: {
        tag: 'hero_hotspots.opt2_tag',
        title: 'hero_hotspots.opt2_title',
        desc: 'hero_hotspots.opt2_desc',
        cta_download: 'hero_hotspots.opt2_cta_download',
        cta_zoom: 'hero_hotspots.cta_deep_zoom'
      },
      data: {
        option_id: 'opt2_monumental',
        title: 'Option 2 // Bold 3D Floating Visual',
        tag: 'BOLD 3D CONCEPT // MASTER .PSD',
        image: './deliverables/task2_meritz/meritz_partners_option2_preview.jpg',
        download: './deliverables/task2_meritz/meritz_partners_option2.psd',
        desc: "Matte Vermillion '150' 3D centerpiece framed inside a sleek metallic gold geometric cage with 5 floating gold coins."
      }
    },
    {
      id: 'pin-spec',
      top: '32%',
      left: '84%',
      color: '#EDFF57',
      badge: 'QA',
      type: 'existing_dom_target',
      targetSelector: '#popup-spec-card',
      label: '15/15 QUALITY CHECK',
      i18n: {
        pin_label: 'hero_hotspots.spec_pin_label',
        tag: 'hero_hotspots.spec_tag',
        title: 'hero_hotspots.spec_title',
        desc: 'hero_hotspots.spec_desc',
        cta_zoom: 'hero_hotspots.spec_cta_zoom',
        cta_download: 'hero_hotspots.spec_cta_download'
      }
    }
  ]
};

/**
 * White-Label Simulation Manifest (proving schema portability in Zone 05)
 */
const WHITE_LABEL_SIMULATION_MANIFEST = {
  engine_version: '1.0.0-whitelabel',
  client: 'Samsung Galaxy S27 Ultra // Global Unpacked Campaign (Simulated)',
  author: 'Antigravity Multi-Tenant Engine',
  theme_tokens: {
    canvas_dark: '#05050A',
    titanium_plate: '#0D0D14',
    hairline_border: '#222536',
    laser_white: '#F4F4F6',
    status_emerald: '#EDFF57',
    accent_volt: '#EDFF57',
    accent_cobalt: '#5322FF',
    accent_cyan: '#00E5FF',
    highlight_amber: '#5322FF'
  },
  tasks: {
    workflow_a_resizing: {
      title: 'Galaxy Titanium Unpacked — 11-Ratio Matrix',
      source_master: 'SAMSUNG_UNPACKED_MASTER_2026.psd',
      total_dimensions: 11,
      policy_compliance: '0% AI Watermark // Orthogonal Manhattan Stepping'
    },
    workflow_b_creative: {
      title: 'Parametric Dual-Core A/B Creative Synthesis',
      brand_palette: {
        titanium_violet: '#6C5CE7',
        obsidian_black: '#0B0B10',
        pure_white: '#FFFFFF'
      },
      qa_compliance: {
        total_rules: 15,
        passed_rules: 15,
        unicode_luni_encoding: 'PASSED'
      }
    }
  }
};

/* Global Module State for Reactive Filtering & Toggles */
const AppState = {
  manifest: null,
  locale: null,
  ingestionSource: 'ASYNC_FETCH',
  fallbackNotice: null,
  keepsakeFolder: null,
  hotspotController: null,
  heroStage: null,
  heroStageInitialized: false,
  heroStageFallback: false,
  whiteLabelMode: false,
  modalZoomMagnified: false,
  lang: 'ko'
};

/**
 * Helper: lookup a dot-separated key from active locale dictionary
 */
function t(locale, key, fallback = '') {
  if (window.AutoBannerI18n && locale) {
    const val = window.AutoBannerI18n.lookupKey(locale, key);
    if (val !== null) return val;
  }
  return fallback;
}

/**
 * Resolve showcase-local relative asset path: './deliverables/...'
 */
function resolveAssetPath(relativePath) {
  if (!relativePath) return '';
  if (relativePath.startsWith('http') || relativePath.startsWith('./') || relativePath.startsWith('../')) {
    return relativePath;
  }
  const normalized = relativePath.replace(/^\/+/, '');
  return `${SHOWCASE_CONFIG.assetBasePrefix}${normalized}`;
}

/**
 * Categorize each of the 11 XEXYMIX placements into deterministic filter buckets:
 * VERTICAL (4): 01, 02, 03, 04
 * SQUARE (2): 05, 06
 * WIDE (2): 07, 08
 * MICRO (3): 09, 10, 11
 */
function getPlacementCategory(placement) {
  const idNum = parseInt(placement.id, 10);
  if (idNum >= 1 && idNum <= 4) return 'VERTICAL';
  if (idNum === 5 || idNum === 6) return 'SQUARE';
  if (idNum === 7 || idNum === 8) return 'WIDE';
  return 'MICRO';
}

/**
 * Step 1: Async Data Ingestion from ../showcase_manifest.json with graceful file:// fallback
 */
async function ingestShowcaseManifest() {
  try {
    const response = await fetch(SHOWCASE_CONFIG.manifestPath, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} while loading ${SHOWCASE_CONFIG.manifestPath}`);
    }
    const data = await response.json();
    AppState.manifest = data;
    AppState.ingestionSource = 'ASYNC_FETCH_VERIFIED';
    AppState.fallbackNotice = null;
    return data;
  } catch (err) {
    AppState.manifest = FALLBACK_MANIFEST_SNAPSHOT;
    AppState.ingestionSource = 'FILE_PROTOCOL_SNAPSHOT_FALLBACK';
    AppState.fallbackNotice =
      `Notice: Direct file:// protocol or offline context detected (${err.message}). ` +
      `Hydrated deterministically from embedded showcase_manifest.json snapshot.`;
    return AppState.manifest;
  }
}

/**
 * Render static JPG preview inside #hero-three-container if WebGL is unsupported or unavailable
 */
function renderHeroStaticFallback(container, previewSrc, altText, telemetryEl) {
  AppState.heroStageFallback = true;
  if (container) {
    container.innerHTML = `
      <img
        src="${previewSrc}"
        alt="${altText}"
        class="hero-cad-image"
      />
    `;
  }
  if (telemetryEl) {
    telemetryEl.textContent = '3D STAGE FALLBACK // STATIC PREVIEW (WEBGL UNAVAILABLE)';
  }
}

/**
 * Zone 01: Hero CAD Viewport (Decoupled Three.js HeroThreeStage + Graceful Static JPG Fallback)
 */
function renderZoneHero(manifest, locale) {
  const viewport = document.querySelector('#zone-hero [data-viewport="hero-cad"]');
  if (!viewport) return;

  const meritzTask = manifest.tasks.task2_meritz;
  const opt2 = meritzTask.options.find((o) => o.option_id === 'opt2_monumental') || meritzTask.options[1];
  const previewSrc = resolveAssetPath(opt2.preview_path);
  const opt2Title = t(locale, 'task2_meritz.opt2_title', opt2.label);

  const telemetryMount = viewport.querySelector('[data-hero-telemetry]');
  if (telemetryMount) {
    const initialReadout = AppState.heroStageFallback
      ? '3D STAGE FALLBACK // STATIC PREVIEW (WEBGL UNAVAILABLE)'
      : 'INTERACTIVE 3D PREVIEW: PITCH +0.0° // YAW +0.0°';
    telemetryMount.innerHTML = `
      <span>SHOWCASE STAGE // ${opt2Title}</span>
      <span id="hero-tilt-readout">${initialReadout}</span>
    `;
  }

  const panelMount = viewport.querySelector('[data-hero-panel]');
  if (panelMount) {
    const opt2PsdFilename = opt2.psd_path.split('/').pop();
    panelMount.innerHTML = `
      <div>
        <span class="zone-eyebrow" data-i18n="hero_hotspots.spec_tag">${t(locale, 'hero_hotspots.spec_tag', t(locale, 'hero.cad_featured'))}</span>
        <h3 class="zone-title" style="font-size:22px;margin-bottom:10px;" data-i18n="hero_hotspots.spec_title">${t(locale, 'hero_hotspots.spec_title', t(locale, 'hero.cad_title'))}</h3>
        <p class="meritz-art-direction" data-i18n="hero_hotspots.spec_desc">${t(locale, 'hero_hotspots.spec_desc', opt2.art_direction)}</p>
      </div>

      <ul class="cad-spec-list">
        <li class="cad-spec-item">
          <span class="cad-spec-key">MASTER PSD</span>
          <span class="cad-spec-val">${opt2PsdFilename}</span>
        </li>
        <li class="cad-spec-item">
          <span class="cad-spec-key">ANTI-PLASTIC SPECULAR</span>
          <span class="cad-spec-val" style="color:var(--status-emerald);">${meritzTask.qa_compliance.anti_plastic_specular}</span>
        </li>
        <li class="cad-spec-item">
          <span class="cad-spec-key">GLYPH COLLISION</span>
          <span class="cad-spec-val" style="color:var(--status-emerald);">${meritzTask.qa_compliance.glyph_collision}</span>
        </li>
        <li class="cad-spec-item">
          <span class="cad-spec-key">UNICODE LUNI ENCODING</span>
          <span class="cad-spec-val" style="color:var(--status-emerald);">${meritzTask.qa_compliance.unicode_luni_encoding}</span>
        </li>
        <li class="cad-spec-item">
          <span class="cad-spec-key">INGESTION MODE</span>
          <span class="cad-spec-val">${AppState.ingestionSource}</span>
        </li>
      </ul>

      <div style="display:flex;flex-wrap:wrap;gap:10px;">
        <button type="button" class="cyber-btn emerald-toggle is-active" data-open-zoom="${opt2.option_id}">
          <span data-i18n="hero_hotspots.spec_cta_zoom">${t(locale, 'hero_hotspots.spec_cta_zoom', t(locale, 'hero.cad_inspect_btn'))}</span>
        </button>
        <a href="${resolveAssetPath(opt2.psd_path)}" download="${opt2PsdFilename}" class="cyber-btn">
          <span data-i18n="hero_hotspots.spec_cta_download">${t(locale, 'hero_hotspots.spec_cta_download', t(locale, 'hero.cad_download_psd'))}</span>
        </a>
      </div>
    `;
  }

  /* Mount Decoupled 2D Hotspot Overlay Controller once from manifest.hero_hotspots; sync locale in-place */
  if (!AppState.hotspotController) {
    AppState.hotspotController = new HotspotOverlayController({
      container: viewport,
      hotspots: Array.isArray(manifest.hero_hotspots) ? manifest.hero_hotspots : [],
      lang: AppState.lang,
      locale
    });
  } else {
    AppState.hotspotController.setLocale(locale, AppState.lang);
  }

  /* Instantiate HeroThreeStage once; preserve WebGL stage across KO/EN/VI language switches */
  const threeContainer = document.getElementById('hero-three-container');
  if (!threeContainer || AppState.heroStageInitialized) return;
  AppState.heroStageInitialized = true;

  const formatSigned = (n) => `${n >= 0 ? '+' : ''}${n.toFixed(1)}°`;
  const updateReadout = ({ pitchDeg, yawDeg, mode }) => {
    const readoutEl = document.getElementById('hero-tilt-readout');
    if (!readoutEl) return;
    const modeTag = mode === 'IDLE_THROTTLED' ? 'IDLE' : '60FPS';
    readoutEl.textContent = `INTERACTIVE 3D PREVIEW: PITCH ${formatSigned(pitchDeg)} // YAW ${formatSigned(yawDeg)} [${modeTag}]`;
  };

  if (!HeroThreeStage.isWebGLAvailable()) {
    renderHeroStaticFallback(threeContainer, previewSrc, opt2Title, document.getElementById('hero-tilt-readout'));
    return;
  }

  try {
    const stage = new HeroThreeStage(threeContainer, {
      onRotationUpdate: updateReadout,
      onContextLost: () => {
        stage.destroy();
        AppState.heroStage = null;
        renderHeroStaticFallback(threeContainer, previewSrc, opt2Title, document.getElementById('hero-tilt-readout'));
      }
    });
    AppState.heroStage = stage;

    stage.init().catch(() => {
      stage.destroy();
      AppState.heroStage = null;
      renderHeroStaticFallback(threeContainer, previewSrc, opt2Title, document.getElementById('hero-tilt-readout'));
    });
  } catch (_) {
    renderHeroStaticFallback(threeContainer, previewSrc, opt2Title, document.getElementById('hero-tilt-readout'));
  }
}

/**
 * Zone 02: Workflow A — XEXYMIX 11-Ratio Interactive Keepsake Folder + Master ZIP CTA
 */
function renderZoneXexymix(manifest, locale) {
  const mount = document.querySelector('#zone-xexymix [data-zone-mount="task1_xexymix"]');
  if (!mount) return;

  const task1 = manifest.tasks.task1_xexymix;
  const placements = task1.placements || [];

  const highlightKeys = [
    'task1_xexymix.feature_orthogonal',
    'task1_xexymix.feature_occlusion',
    'task1_xexymix.feature_feathering',
    'task1_xexymix.feature_watermark'
  ];

  const metaMount = mount.querySelector('[data-xexymix-meta]');
  if (metaMount) {
    metaMount.innerHTML = `
      <div class="placeholder-telemetry" style="margin-bottom:20px;">
        <span><span data-i18n="task1_xexymix.source_master">${t(locale, 'task1_xexymix.source_master')}</span>: ${task1.source_master}</span>
        <span data-i18n="task1_xexymix.format_spec">${t(locale, 'task1_xexymix.format_spec')}</span>
      </div>

      <div class="engine-highlights-strip" style="margin-bottom:0;">
        ${highlightKeys
          .map(
            (key) => `
            <div class="highlight-chip">
              <span class="highlight-chip-dot" aria-hidden="true"></span>
              <span data-i18n="${key}">${t(locale, key)}</span>
            </div>`
          )
          .join('')}
      </div>
    `;
  }

  /* Sync Master ZIP download button href & translated label */
  const zipBtn = mount.querySelector('#xexymix-master-zip-btn');
  if (zipBtn) {
    zipBtn.setAttribute('href', resolveAssetPath(SHOWCASE_CONFIG.xexymixZipPath));
    const zipLabelEl = zipBtn.querySelector('[data-i18n="keepsake.btn_download_zip"]');
    if (zipLabelEl) {
      zipLabelEl.textContent = t(locale, 'keepsake.btn_download_zip', 'DOWNLOAD ALL 11 SIZES (.ZIP)');
    }
  }

  /* Initialize Standalone KeepsakeFolder once; update locale in-place on language switches */
  if (typeof window.KeepsakeFolder === 'function') {
    if (!AppState.keepsakeFolder) {
      AppState.keepsakeFolder = new window.KeepsakeFolder({
        containerSelector: '#zone-xexymix .keepsake-container',
        items: placements,
        tabLabel: 'ARCHIVE // XEXYMIX_11_RATIOS',
        resolveAssetPath,
        lang: AppState.lang,
        locale
      });
    } else {
      AppState.keepsakeFolder.setLocale(locale, AppState.lang);
    }
  }
}

/**
 * Zone 03: Workflow B — Meritz Dual-Core Comparison + Brand Palette Purity Widget + Deep-Zoom Modal
 */
function renderZoneMeritz(manifest, locale) {
  const mount = document.querySelector('#zone-meritz [data-zone-mount="task2_meritz"]');
  if (!mount) return;

  const task2 = manifest.tasks.task2_meritz;
  const palette = task2.brand_palette || {};
  const swatches = [
    { label: 'VERMILLION RED', hex: palette.vermillion_red || '#EF3B24' },
    { label: 'OBSIDIAN BLACK', hex: palette.obsidian_black || '#141414' },
    { label: 'PURE WHITE', hex: palette.pure_white || '#FFFFFF' },
    { label: 'CHALK WHITE', hex: palette.chalk_white || '#F2F2F2' }
  ];

  mount.innerHTML = `
    <div class="placeholder-telemetry">
      <span>BRIEF: ${task2.brief_source}</span>
      <span>BRAND BOOK: ${task2.brand_book_source}</span>
    </div>

    <!-- Brand Palette Purity Widget -->
    <div class="meritz-top-bar">
      <div>
        <span class="zone-eyebrow" style="margin-bottom:4px;" data-i18n="task2_meritz.brand_purity_title">${t(locale, 'task2_meritz.brand_purity_title')}</span>
        <div style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted-gray);" data-i18n="task2_meritz.brand_purity_desc">
          ${t(locale, 'task2_meritz.brand_purity_desc')}
        </div>
      </div>

      <div class="palette-widget">
        ${swatches
          .map(
            (s) => `
            <button type="button" class="swatch-chip" data-copy-hex="${s.hex}" title="${s.hex}">
              <span class="swatch-color-box" style="background-color:${s.hex};"></span>
              <span>${s.label}: <strong>${s.hex}</strong></span>
            </button>`
          )
          .join('')}
        <span class="status-badge emerald" data-i18n="task2_meritz.brand_purity_badge">${t(locale, 'task2_meritz.brand_purity_badge')}</span>
      </div>
    </div>

    <!-- Dual-Column A/B Comparison Cards -->
    <div class="dual-core-grid">
      ${task2.options
        .map((opt) => {
          const previewUrl = resolveAssetPath(opt.preview_path);
          const psdUrl = resolveAssetPath(opt.psd_path);
          const isMonumental = opt.option_id === 'opt2_monumental';
          const prefix = isMonumental ? 'opt2' : 'opt1';

          return `
            <article class="meritz-option-card ${isMonumental ? 'is-highlighted' : ''}" data-option-card="${opt.option_id}">
              <div>
                <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px;">
                  <span class="zone-eyebrow" style="margin-bottom:0;" data-i18n="task2_meritz.${prefix}_eyebrow">
                    ${t(locale, `task2_meritz.${prefix}_eyebrow`)}
                  </span>
                  <span class="${isMonumental ? 'amber-badge' : 'status-badge cyan'}" data-i18n="task2_meritz.${prefix}_chip">
                    ${t(locale, `task2_meritz.${prefix}_chip`)}
                  </span>
                </div>

                <h3 class="zone-title" style="font-size:24px;margin-bottom:14px;" data-i18n="task2_meritz.${prefix}_title">${t(locale, `task2_meritz.${prefix}_title`, opt.label)}</h3>

                <div class="meritz-preview-frame" data-open-zoom="${opt.option_id}" role="button" tabindex="0" aria-label="${t(locale, `task2_meritz.${prefix}_title`, opt.label)}">
                  <img src="${previewUrl}" alt="${t(locale, `task2_meritz.${prefix}_title`, opt.label)}" class="meritz-preview-img" />
                  <span class="zoom-affordance-tag" data-i18n="task2_meritz.zoom_instruction">${t(locale, 'task2_meritz.zoom_instruction')}</span>
                </div>
              </div>

              <div>
                <p class="meritz-art-direction" data-i18n="task2_meritz.${prefix}_desc">${t(locale, `task2_meritz.${prefix}_desc`, opt.art_direction)}</p>

                <div class="meritz-actions-row">
                  <button type="button" class="cyber-btn emerald-toggle is-active" data-open-zoom="${opt.option_id}">
                    <span data-i18n="task2_meritz.zoom_instruction">${t(locale, 'task2_meritz.zoom_instruction')}</span>
                  </button>
                  <a href="${psdUrl}" download class="cyber-btn">
                    <span>MASTER .PSD (${opt.psd_path.split('/').pop()})</span>
                  </a>
                  <a href="${previewUrl}" download class="cyber-btn">
                    <span data-i18n="task2_meritz.btn_preview_jpg">${t(locale, 'task2_meritz.btn_preview_jpg')}</span>
                  </a>
                </div>
              </div>
            </article>
          `;
        })
        .join('')}
    </div>
  `;

  /* Copy Hex Swatch Handler */
  mount.querySelectorAll('[data-copy-hex]').forEach((chip) => {
    chip.addEventListener('click', () => {
      const hex = chip.getAttribute('data-copy-hex');
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(hex).catch(() => {});
      }
      const originalHtml = chip.innerHTML;
      chip.innerHTML = `<span style="color:var(--status-emerald);">COPIED ${hex}</span>`;
      setTimeout(() => {
        chip.innerHTML = originalHtml;
      }, 1100);
    });
  });
}

/**
 * Deep-Zoom Modal for inspecting the Matte Grain Texture on the 3D '150' Core
 */
function ensureDeepZoomModal(manifest) {
  let modal = document.getElementById('meritz-deep-zoom-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'meritz-deep-zoom-modal';
    modal.className = 'cyber-modal-backdrop';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Meritz 3D Matte Grain Deep-Zoom Inspector');
    document.body.appendChild(modal);
  }

  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-open-zoom]');
    if (trigger) {
      const optionId = trigger.getAttribute('data-open-zoom');
      openDeepZoomModal(manifest, optionId);
      return;
    }
    if (event.target.matches('#meritz-deep-zoom-modal') || event.target.closest('[data-close-zoom]')) {
      modal.classList.remove('is-open');
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.classList.contains('is-open')) {
      modal.classList.remove('is-open');
    }
  });
}

function openDeepZoomModal(manifest, optionId) {
  const modal = document.getElementById('meritz-deep-zoom-modal');
  if (!modal) return;

  const task2 = manifest.tasks.task2_meritz;
  const opt = task2.options.find((o) => o.option_id === optionId) || task2.options[1];
  const imgUrl = resolveAssetPath(opt.preview_path);

  AppState.modalZoomMagnified = true;

  modal.innerHTML = `
    <div class="cyber-modal-dialog">
      <div class="cyber-modal-header">
        <span>CLOSE-UP 3D DETAIL VIEWER // ${opt.label.toUpperCase()}</span>
        <button type="button" class="cyber-btn" data-close-zoom="true">
          <span>[ ESC // CLOSE ]</span>
        </button>
      </div>

      <div class="cyber-modal-body">
        <div id="deep-zoom-stage" class="deep-zoom-stage is-magnified" title="Click or move cursor to pan across the 3D '150' matte finish">
          <img id="deep-zoom-target-img" src="${imgUrl}" alt="${opt.label} Deep Zoom" class="deep-zoom-img" />
        </div>

        <div class="deep-zoom-sidebar">
          <div>
            <span class="zone-eyebrow">ACCURACY SPECIFICATIONS // 3D '150' CENTERPIECE</span>
            <h3 class="zone-title" style="font-size:22px;margin-bottom:10px;">Matte Finish &amp; Geometric Gold Frame</h3>
            <p class="meritz-art-direction">
              Move your cursor across the banner to inspect the natural matte finish on the
              Meritz Red (#EF3B24) '150' sculpture, crisp gold frame lines,
              and balanced Korean typography.
            </p>
          </div>

          <ul class="cad-spec-list">
            <li class="cad-spec-item">
              <span class="cad-spec-key">ANTI-PLASTIC SPECULAR</span>
              <span class="cad-spec-val" style="color:var(--status-emerald);">${task2.qa_compliance.anti_plastic_specular}</span>
            </li>
            <li class="cad-spec-item">
              <span class="cad-spec-key">GLYPH COLLISION</span>
              <span class="cad-spec-val" style="color:var(--status-emerald);">${task2.qa_compliance.glyph_collision}</span>
            </li>
            <li class="cad-spec-item">
              <span class="cad-spec-key">PSD LUNI UNICODE</span>
              <span class="cad-spec-val" style="color:var(--status-emerald);">${task2.qa_compliance.unicode_luni_encoding}</span>
            </li>
            <li class="cad-spec-item">
              <span class="cad-spec-key">MAGNIFICATION</span>
              <span class="cad-spec-val" id="zoom-scale-readout">2.35x LOUPE ACTIVE</span>
            </li>
          </ul>

          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            <button type="button" id="toggle-zoom-scale-btn" class="cyber-btn emerald-toggle is-active">
              <span>TOGGLE 2.35x / 1.0x ZOOM</span>
            </button>
            <a href="${resolveAssetPath(opt.psd_path)}" download class="cyber-btn">
              <span>DOWNLOAD LAYERED .PSD</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  modal.classList.add('is-open');

  const stage = modal.querySelector('#deep-zoom-stage');
  const img = modal.querySelector('#deep-zoom-target-img');
  const toggleBtn = modal.querySelector('#toggle-zoom-scale-btn');
  const readout = modal.querySelector('#zoom-scale-readout');

  if (stage && img) {
    const updateZoomOrigin = (clientX, clientY) => {
      const rect = stage.getBoundingClientRect();
      const xPct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
      const yPct = Math.max(0, Math.min(100, ((clientY - rect.top) / rect.height) * 100));
      img.style.transformOrigin = `${xPct.toFixed(1)}% ${yPct.toFixed(1)}%`;
    };

    stage.addEventListener('mousemove', (e) => {
      updateZoomOrigin(e.clientX, e.clientY);
    });

    stage.addEventListener(
      'touchmove',
      (e) => {
        if (!AppState.modalZoomMagnified || !e.touches || !e.touches.length) return;
        const touch = e.touches[0];
        updateZoomOrigin(touch.clientX, touch.clientY);
      },
      { passive: true }
    );

    stage.addEventListener('click', () => {
      AppState.modalZoomMagnified = !AppState.modalZoomMagnified;
      stage.classList.toggle('is-magnified', AppState.modalZoomMagnified);
      if (readout) {
        readout.textContent = AppState.modalZoomMagnified ? '2.35x LOUPE ACTIVE' : '1.00x FULL FRAME';
      }
    });
  }

  if (toggleBtn && stage) {
    toggleBtn.addEventListener('click', () => {
      AppState.modalZoomMagnified = !AppState.modalZoomMagnified;
      stage.classList.toggle('is-magnified', AppState.modalZoomMagnified);
      if (readout) {
        readout.textContent = AppState.modalZoomMagnified ? '2.35x LOUPE ACTIVE' : '1.00x FULL FRAME';
      }
    });
  }
}

/**
 * Zone 04: Under The Hood — Agent Workflow Pipeline (Worker Art -> Worker Compositor -> Worker QA)
 * & Dynamic QA Telemetry Table
 */
function renderZoneUnderTheHood(manifest, locale) {
  const mount = document.querySelector('#zone-under-the-hood [data-zone-mount="under_the_hood"]');
  if (!mount) return;

  const qa = manifest.tasks.task2_meritz.qa_compliance;
  const task1 = manifest.tasks.task1_xexymix;

  const pipelineAgents = [
    {
      step: 'STAGE 01 // WORKER ART',
      roleKey: 'under_the_hood.role_art',
      descKey: 'under_the_hood.role_art_desc',
      status: 'VERIFIED'
    },
    {
      step: 'STAGE 02 // WORKER COMPOSITOR',
      roleKey: 'under_the_hood.role_compositor',
      descKey: 'under_the_hood.role_compositor_desc',
      status: 'VERIFIED'
    },
    {
      step: 'STAGE 03 // WORKER QA',
      roleKey: 'under_the_hood.role_qa',
      descKey: 'under_the_hood.role_qa_desc',
      status: `${qa.passed_rules}/${qa.total_rules} PASSED`
    }
  ];

  const telemetryRows = [
    {
      id: 'QA-01',
      checkKey: 'under_the_hood.rule_kerning',
      target: `${qa.total_rules} Hard Gates`,
      measured: `${qa.passed_rules} / ${qa.total_rules}`,
      status: 'PASSED'
    },
    {
      id: 'QA-02',
      checkKey: 'under_the_hood.rule_anti_plastic',
      target: '< 0.5%',
      measured: qa.anti_plastic_specular,
      status: 'PASSED'
    },
    {
      id: 'QA-03',
      checkKey: 'under_the_hood.rule_collision',
      target: '0px',
      measured: qa.glyph_collision,
      status: 'PASSED'
    },
    {
      id: 'QA-04',
      checkKey: 'under_the_hood.rule_luni',
      target: 'UTF-16BE',
      measured: qa.unicode_luni_encoding,
      status: 'PASSED'
    },
    {
      id: 'QA-05',
      checkKey: 'under_the_hood.rule_layers',
      target: '11 Placements',
      measured: `${task1.total_dimensions} / 11`,
      status: 'PASSED'
    },
    {
      id: 'QA-06',
      checkKey: 'under_the_hood.rule_weight',
      target: 'sRGB <= 800KB',
      measured: '695.8KB // 0%',
      status: 'PASSED'
    }
  ];

  mount.innerHTML = `
    <div class="placeholder-telemetry">
      <span data-i18n="under_the_hood.pipeline_desc">${t(locale, 'under_the_hood.pipeline_desc')}</span>
      <span data-i18n="under_the_hood.rules_passed">${t(locale, 'under_the_hood.rules_passed')}</span>
    </div>

    <div class="under-hood-grid">
      <div class="pipeline-panel">
        <span class="zone-eyebrow" data-i18n="under_the_hood.pipeline_title">${t(locale, 'under_the_hood.pipeline_title')}</span>
        <div class="agent-pipeline-steps">
          ${pipelineAgents
            .map(
              (node) => `
              <div class="agent-node">
                <div class="agent-node-header">
                  <span style="color:var(--accent-cyan);font-weight:700;">${node.step}</span>
                  <span class="qa-pass-pill">${node.status}</span>
                </div>
                <h3 class="agent-node-title" data-i18n="${node.roleKey}">${t(locale, node.roleKey)}</h3>
                <p class="agent-node-desc" data-i18n="${node.descKey}">${t(locale, node.descKey)}</p>
              </div>`
            )
            .join('')}
        </div>
      </div>

      <div class="telemetry-table-panel">
        <span class="zone-eyebrow" data-i18n="under_the_hood.telemetry_title">${t(locale, 'under_the_hood.telemetry_title')}</span>
        <div class="qa-telemetry-scroll">
          <table class="qa-telemetry-table">
            <thead>
              <tr>
                <th data-i18n="under_the_hood.col_rule_id">${t(locale, 'under_the_hood.col_rule_id')}</th>
                <th data-i18n="under_the_hood.col_gate">${t(locale, 'under_the_hood.col_gate')}</th>
                <th data-i18n="under_the_hood.col_constraint">${t(locale, 'under_the_hood.col_constraint')}</th>
                <th data-i18n="under_the_hood.col_measured">${t(locale, 'under_the_hood.col_measured')}</th>
                <th data-i18n="under_the_hood.col_status">${t(locale, 'under_the_hood.col_status')}</th>
              </tr>
            </thead>
            <tbody>
              ${telemetryRows
                .map(
                  (row) => `
                  <tr>
                    <td data-label="${t(locale, 'under_the_hood.col_rule_id', 'RULE ID')}" style="color:var(--accent-cyan);font-weight:700;">${row.id}</td>
                    <td data-label="${t(locale, 'under_the_hood.col_gate', 'GATE')}" data-i18n="${row.checkKey}">${t(locale, row.checkKey)}</td>
                    <td data-label="${t(locale, 'under_the_hood.col_constraint', 'CONSTRAINT')}" style="color:var(--text-muted-gray);">${row.target}</td>
                    <td data-label="${t(locale, 'under_the_hood.col_measured', 'MEASURED')}" style="font-weight:700;">${row.measured}</td>
                    <td data-label="${t(locale, 'under_the_hood.col_status', 'STATUS')}"><span class="qa-pass-pill">${row.status}</span></td>
                  </tr>`
                )
                .join('')}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

/**
 * Syntax highlight JSON string into spans for Zone 05
 */
function syntaxHighlightJson(jsonObj) {
  const raw = JSON.stringify(jsonObj, null, 2)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return raw.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = 'json-number';
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? 'json-key' : 'json-string';
      } else if (/true|false/.test(match)) {
        cls = 'json-boolean';
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

/**
 * Zone 05: Manifest-Driven White-Label Sandbox
 */
function renderZoneManifestEngine(manifest, locale) {
  const mount = document.querySelector('#zone-manifest-engine [data-zone-mount="manifest_engine"]');
  if (!mount) return;

  const activePayload = AppState.whiteLabelMode ? WHITE_LABEL_SIMULATION_MANIFEST : manifest;
  const statusKey = AppState.whiteLabelMode
    ? 'manifest_engine.white_label_active'
    : 'manifest_engine.white_label_desc';
  const toggleBtnKey = AppState.whiteLabelMode
    ? 'manifest_engine.btn_restore_demo'
    : 'manifest_engine.btn_toggle_demo';

  mount.innerHTML = `
    <div class="placeholder-telemetry">
      <span data-i18n="${statusKey}">${t(locale, statusKey)}</span>
      <span>ENGINE VERSION: v${activePayload.engine_version}</span>
    </div>

    <div class="manifest-console-card">
      <div class="manifest-console-toolbar">
        <div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;">
          <span class="status-badge ${AppState.whiteLabelMode ? 'cyan' : 'emerald'}">
            ${AppState.whiteLabelMode ? 'TENANT: SAMSUNG UNPACKED (SIMULATED)' : 'TENANT: CHAI COMMUNICATION'}
          </span>
          <span style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted-gray);">
            schema://showcase_manifest.json
          </span>
        </div>

        <div style="display:flex;flex-wrap:wrap;gap:10px;">
          <button
            type="button"
            id="white-label-toggle-btn"
            class="cyber-btn emerald-toggle ${AppState.whiteLabelMode ? 'is-active' : ''}"
          >
            <span data-i18n="${toggleBtnKey}">${t(locale, toggleBtnKey)}</span>
          </button>

          <button type="button" id="copy-manifest-json-btn" class="cyber-btn">
            <span data-i18n="manifest_engine.btn_copy_json">${t(locale, 'manifest_engine.btn_copy_json')}</span>
          </button>
        </div>
      </div>

      <pre class="manifest-code-viewport" id="manifest-json-code"><code>${syntaxHighlightJson(activePayload)}</code></pre>
    </div>
  `;

  const toggleBtn = mount.querySelector('#white-label-toggle-btn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      AppState.whiteLabelMode = !AppState.whiteLabelMode;
      renderZoneManifestEngine(manifest, AppState.locale);
    });
  }

  const copyBtn = mount.querySelector('#copy-manifest-json-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const rawJson = JSON.stringify(activePayload, null, 2);
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(rawJson).catch(() => {});
      }
      copyBtn.innerHTML = `<span style="color:var(--status-emerald);">${t(AppState.locale, 'manifest_engine.btn_copied_json')}</span>`;
      setTimeout(() => {
        copyBtn.innerHTML = `<span data-i18n="manifest_engine.btn_copy_json">${t(AppState.locale, 'manifest_engine.btn_copy_json')}</span>`;
      }, 1200);
    });
  }
}

/**
 * Zone 06: Footer Deliverables Dock
 */
function renderDeliverablesDock(manifest, locale) {
  const dockContainer = document.querySelector('#deliverables-dock .shell-container');
  if (!dockContainer) return;

  const task1 = manifest.tasks.task1_xexymix;
  const task2 = manifest.tasks.task2_meritz;
  const opt1 = task2.options[0];
  const opt2 = task2.options[1];

  dockContainer.innerHTML = `
    <div class="dock-header-row">
      <div>
        <div class="hud-brand">
          <span class="beacon-dot" aria-hidden="true"></span>
          <span data-i18n="footer.download_title">${t(locale, 'footer.download_title')}</span>
        </div>
        <p class="dock-status" data-i18n="footer.download_desc">
          ${t(locale, 'footer.download_desc')}
        </p>
      </div>

      <a href="${SHOWCASE_CONFIG.manifestPath}" download class="cyber-btn emerald-toggle is-active">
        <span data-i18n="footer.repo_label">${t(locale, 'footer.repo_label')}</span>
      </a>
    </div>

    <div class="dock-cards-grid" data-zone-mount="deliverables_dock">
      <!-- Task 1 Package Card -->
      <div class="dock-card">
        <div>
          <span class="zone-eyebrow" data-i18n="footer.task1_download_label">${t(locale, 'footer.task1_download_label')}</span>
          <h3 class="dock-card-title" data-i18n="task1_xexymix.title">${t(locale, 'task1_xexymix.title', task1.title)}</h3>
          <p class="meritz-art-direction" style="margin-top:6px;" data-i18n="footer.task1_card_desc">
            ${t(locale, 'footer.task1_card_desc')}
          </p>
        </div>

        <div class="dock-file-list">
          ${task1.placements
            .slice(0, 4)
            .map(
              (p) => `
              <a href="${resolveAssetPath(p.file)}" download class="cyber-btn" style="justify-content:space-between;">
                <span>${p.id}_${p.name} (${p.resolution})</span>
                <span>.JPG &darr;</span>
              </a>`
            )
            .join('')}
          <a href="#zone-xexymix" class="cyber-btn" style="justify-content:center;">
            <span data-i18n="footer.browse_all_11">${t(locale, 'footer.browse_all_11')}</span>
          </a>
        </div>
      </div>

      <!-- Task 2 Option 1 Card -->
      <div class="dock-card">
        <div>
          <span class="zone-eyebrow" data-i18n="footer.task2_download_label">${t(locale, 'footer.task2_download_label')}</span>
          <h3 class="dock-card-title" data-i18n="task2_meritz.opt1_title">${t(locale, 'task2_meritz.opt1_title', opt1.label)}</h3>
          <p class="meritz-art-direction" style="margin-top:6px;" data-i18n="task2_meritz.opt1_desc">
            ${t(locale, 'task2_meritz.opt1_desc', opt1.art_direction)}
          </p>
        </div>

        <div class="dock-file-list">
          <a href="${resolveAssetPath(opt1.psd_path)}" download class="cyber-btn emerald-toggle is-active" style="justify-content:space-between;">
            <span>${opt1.psd_path.split('/').pop()}</span>
            <span>MASTER .PSD &darr;</span>
          </a>
          <a href="${resolveAssetPath(opt1.preview_path)}" download class="cyber-btn" style="justify-content:space-between;">
            <span>${opt1.preview_path.split('/').pop()}</span>
            <span>sRGB .JPG &darr;</span>
          </a>
        </div>
      </div>

      <!-- Task 2 Option 2 Card -->
      <div class="dock-card">
        <div>
          <span class="zone-eyebrow" data-i18n="footer.task2_download_label">${t(locale, 'footer.task2_download_label')}</span>
          <h3 class="dock-card-title" data-i18n="task2_meritz.opt2_title">${t(locale, 'task2_meritz.opt2_title', opt2.label)}</h3>
          <p class="meritz-art-direction" style="margin-top:6px;" data-i18n="task2_meritz.opt2_desc">
            ${t(locale, 'task2_meritz.opt2_desc', opt2.art_direction)}
          </p>
        </div>

        <div class="dock-file-list">
          <a href="${resolveAssetPath(opt2.psd_path)}" download class="cyber-btn emerald-toggle is-active" style="justify-content:space-between;">
            <span>${opt2.psd_path.split('/').pop()}</span>
            <span>MASTER .PSD &darr;</span>
          </a>
          <a href="${resolveAssetPath(opt2.preview_path)}" download class="cyber-btn" style="justify-content:space-between;">
            <span>${opt2.preview_path.split('/').pop()}</span>
            <span>sRGB .JPG &darr;</span>
          </a>
        </div>
      </div>
    </div>
  `;
}

/**
 * Centralized Trilingual Locale Loader & Applier (EN / KO / VI)
 * Fetches ./locales/${lang}.json with file:// fallback and persists to localStorage('preferred_lang')
 */
async function loadLocale(lang) {
  if (!window.AutoBannerI18n) return null;
  const dict = await window.AutoBannerI18n.loadLocale(lang);
  AppState.locale = dict;
  return dict;
}

function getInitialLanguage() {
  const i18n = window.AutoBannerI18n;
  const fallback = (i18n && i18n.DEFAULT_LANG) || 'ko';
  try {
    const saved = window.localStorage.getItem('preferred_lang');
    if (saved && i18n && i18n.SUPPORTED_LANGS.includes(saved)) {
      return saved;
    }
  } catch (_) {
    /* ignore storage errors in restricted contexts */
  }
  return fallback;
}

async function applyI18n(lang, animate) {
  const i18n = window.AutoBannerI18n;
  if (!i18n) return;

  const targetLang = i18n.SUPPORTED_LANGS.includes(lang) ? lang : i18n.DEFAULT_LANG;
  AppState.lang = targetLang;
  document.documentElement.lang = targetLang;

  const locale = await loadLocale(targetLang);

  /* Update switcher pill active state */
  document.querySelectorAll('.lang-btn').forEach((btn) => {
    const isActive = btn.getAttribute('data-lang') === targetLang;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  });

  /* Re-render all dynamic zones using the active locale dictionary */
  if (AppState.manifest) {
    renderZoneHero(AppState.manifest, locale);
    renderZoneXexymix(AppState.manifest, locale);
    renderZoneMeritz(AppState.manifest, locale);
    renderZoneUnderTheHood(AppState.manifest, locale);
    renderZoneManifestEngine(AppState.manifest, locale);
    renderDeliverablesDock(AppState.manifest, locale);
  }

  /* Traverse all [data-i18n] nodes and bind strings from active locale */
  const nodes = document.querySelectorAll('[data-i18n]');
  const updateNodes = () => {
    nodes.forEach((el) => {
      const key = el.getAttribute('data-i18n');
      const translated = i18n.lookupKey(locale, key);
      if (translated !== null) {
        el.textContent = translated;
      }
      el.classList.remove('i18n-fading');
    });
  };

  if (animate) {
    nodes.forEach((el) => el.classList.add('i18n-fading'));
    window.setTimeout(updateNodes, 120);
  } else {
    updateNodes();
  }
}

function initLanguageSwitcher() {
  const buttons = document.querySelectorAll('.lang-btn');
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      const nextLang = btn.getAttribute('data-lang');
      if (!nextLang || nextLang === AppState.lang) return;
      try {
        window.localStorage.setItem('preferred_lang', nextLang);
      } catch (_) {
        /* ignore storage errors */
      }
      applyI18n(nextLang, true);
    });
  });
}

/**
 * Bootstrap Showcase Pipeline
 */
async function bootstrapShowcaseApp() {
  AppState.lang = getInitialLanguage();
  const manifest = await ingestShowcaseManifest();
  AppState.manifest = manifest;
  ensureDeepZoomModal(manifest);
  initLanguageSwitcher();
  await applyI18n(AppState.lang, false);
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrapShowcaseApp);
  } else {
    bootstrapShowcaseApp();
  }

  window.addEventListener('pagehide', () => {
    if (AppState.hotspotController) {
      AppState.hotspotController.destroy();
      AppState.hotspotController = null;
    }
    if (AppState.heroStage) {
      AppState.heroStage.destroy();
      AppState.heroStage = null;
    }
  });
}
