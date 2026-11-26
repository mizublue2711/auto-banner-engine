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
  assemblyObserver: null,
  lang: 'ko'
};

const ASSEMBLY_MODAL_DELAY_MS = 220;
const REMOTION_SETTLE_DURATION_MS = 1950;
const REPLAY_DEBOUNCE_MS = 180;
const PRELOAD_TIMEOUT_MS = 800;

const assemblyTimers = new WeakMap();
const assemblyRunTokens = new WeakMap();
const assemblyReplayTimestamps = new WeakMap();
const ASSET_PRELOAD_CACHE = new Map();

const XEXYMIX_CUTOUT_ASSETS = Object.freeze({
  modelCutout: './assets/cutouts/xexymix/base_model_scene.png',
  logo: './assets/cutouts/xexymix/logo_xexymix.png',
  pocketCard: './assets/cutouts/xexymix/card_pocket_clean.png',
  fleeceCard: './assets/cutouts/xexymix/card_fleece_clean.png',
  promoStory: './assets/cutouts/xexymix/meta_story_9_16_promo.png',
  promoMaster: './assets/cutouts/xexymix/promo_master.png',
  promoWide: './assets/cutouts/xexymix/naver_gfa_wide_promo.png',
  promoThumb: './assets/cutouts/xexymix/naver_thumb_small_promo.png',
  promoSmart: './assets/cutouts/xexymix/naver_smart_channel_promo.png',
  promoBizboard: './assets/cutouts/xexymix/kakao_bizboard_promo.png'
});

const MERITZ_CUTOUT_ASSETS = Object.freeze({
  logo: './assets/cutouts/meritz/logo.png',
  coin3d: './assets/cutouts/meritz/hero_coin_3d.png',
  heroOption2: './assets/cutouts/meritz/hero_option2_scene.png',
  iconSprout: './assets/cutouts/meritz/icon_sprout_beginner.png',
  iconGrowth: './assets/cutouts/meritz/icon_flexible_growth.png',
  iconHoney: './assets/cutouts/meritz/icon_honey_sidejob.png'
});

/**
 * Safeguard 4: Asset Preload & Pop-In Prevention
 * Pre-decodes cutout PNGs before spring animations begin so zero blank frames slide in.
 */
function preloadImageAsset(url) {
  if (!url || typeof Image === 'undefined') return Promise.resolve();
  if (ASSET_PRELOAD_CACHE.has(url)) {
    return ASSET_PRELOAD_CACHE.get(url);
  }
  const promise = new Promise((resolve) => {
    const img = new Image();
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      resolve();
    };
    const timeoutId = window.setTimeout(finish, PRELOAD_TIMEOUT_MS);
    const done = () => {
      window.clearTimeout(timeoutId);
      finish();
    };
    img.onload = () => {
      if (typeof img.decode === 'function') {
        img.decode().then(done, done);
      } else {
        done();
      }
    };
    img.onerror = done;
    img.src = url;
    if (img.complete && img.naturalWidth > 0) {
      if (typeof img.decode === 'function') {
        img.decode().then(done, done);
      } else {
        done();
      }
    }
  });
  ASSET_PRELOAD_CACHE.set(url, promise);
  return promise;
}

function preloadSceneAssets(urls) {
  const unique = Array.from(new Set((urls || []).filter(Boolean)));
  if (!unique.length) return Promise.resolve();
  return Promise.all(unique.map((u) => preloadImageAsset(u)));
}

function prewarmAllCutoutAssets() {
  const allPaths = [
    ...Object.values(XEXYMIX_CUTOUT_ASSETS),
    ...Object.values(MERITZ_CUTOUT_ASSETS)
  ].map((p) => resolveAssetPath(p));
  preloadSceneAssets(allPaths).catch(() => {});
}

function clearAssemblyTimers(containerElement) {
  const existing = assemblyTimers.get(containerElement);
  if (!existing) return;
  if (existing.startTimerId) window.clearTimeout(existing.startTimerId);
  if (existing.completeTimerId) window.clearTimeout(existing.completeTimerId);
  if (existing.rafId) window.cancelAnimationFrame(existing.rafId);
  assemblyTimers.delete(containerElement);
}

/**
 * Safeguard 1: Deterministic DOM Teardown & Clean Unmounting
 * Cancels active timers, Web Animations, invalidates in-flight async preloads via
 * monotonic runToken, and wipes all prior discrete layer nodes before mounting new ones.
 */
function teardownAssemblyStage(stageCanvas) {
  if (!stageCanvas) return 0;
  const nextToken = (assemblyRunTokens.get(stageCanvas) || 0) + 1;
  assemblyRunTokens.set(stageCanvas, nextToken);
  clearAssemblyTimers(stageCanvas);

  if (typeof stageCanvas.getAnimations === 'function') {
    try {
      stageCanvas.getAnimations({ subtree: true }).forEach((anim) => anim.cancel());
    } catch (_) {
      /* ignore browser animation API quirks */
    }
  }

  stageCanvas.classList.remove('is-assembling', 'is-assembled', 'is-preloading');
  stageCanvas.replaceChildren();
  return nextToken;
}

/**
 * Resolve exact aspect ratio, layout archetype, and promo badge PNG for all 11 XEXYMIX placements.
 */
function resolveXexymixSceneConfig(placement) {
  const id = String((placement && placement.id) || '01').padStart(2, '0');
  let ratioFloat = 0.5625;
  if (placement && typeof placement.resolution === 'string') {
    const match = placement.resolution.match(/(\d+)\s*x\s*(\d+)/i);
    if (match) {
      const w = parseInt(match[1], 10);
      const h = parseInt(match[2], 10);
      if (w > 0 && h > 0) {
        ratioFloat = w / h;
      }
    }
  }

  let layoutMode = 'vertical-tall';
  let promoPath = XEXYMIX_CUTOUT_ASSETS.promoStory;

  if (id === '01') {
    layoutMode = 'vertical-tall';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoStory;
  } else if (id === '02' || id === '03' || id === '04') {
    layoutMode = 'vertical-feed';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoMaster;
  } else if (id === '05' || id === '06') {
    layoutMode = 'square';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoMaster;
  } else if (id === '07' || id === '08') {
    layoutMode = 'wide';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoWide;
  } else if (id === '09') {
    layoutMode = 'display-thumb';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoThumb;
  } else if (id === '10') {
    layoutMode = 'micro-right';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoSmart;
  } else {
    layoutMode = 'micro-flipped';
    promoPath = XEXYMIX_CUTOUT_ASSETS.promoBizboard;
  }

  const assets = {
    modelSrc: resolveAssetPath(XEXYMIX_CUTOUT_ASSETS.modelCutout),
    logoSrc: resolveAssetPath(XEXYMIX_CUTOUT_ASSETS.logo),
    pocketSrc: resolveAssetPath(XEXYMIX_CUTOUT_ASSETS.pocketCard),
    fleeceSrc: resolveAssetPath(XEXYMIX_CUTOUT_ASSETS.fleeceCard),
    promoSrc: resolveAssetPath(promoPath)
  };

  return {
    sceneKey: `xexymix-${id}`,
    layoutMode,
    ratioFloat,
    assets,
    preloadUrls: Object.values(assets)
  };
}

function buildXexymixLayersMarkup(scene) {
  const { modelSrc, logoSrc, pocketSrc, fleeceSrc, promoSrc } = scene.assets;
  return `
    <div class="layer-canvas-bg" aria-hidden="true"></div>
    <div class="layer-product-cutout">
      <img src="${modelSrc}" alt="XEXYMIX Black Label 360N Leggings Model Cutout" decoding="async" />
    </div>
    <div class="layer-typography-group">
      <img src="${logoSrc}" alt="XEXYMIX" class="assembly-brand-logo" decoding="async" />
      <div class="assembly-copy-block">
        <span class="assembly-eyebrow-pill">RX 블랙라벨 시그니처 360N 기모 포켓 레깅스</span>
        <div class="assembly-headline-line">허리 압박은 덜고</div>
        <div class="assembly-headline-line"><span class="assembly-headline-accent">기모의 온기</span>는 더했어요</div>
      </div>
    </div>
    <div class="layer-feature-card">
      <div class="feature-callout-circle-wrap">
        <div class="feature-callout-circle">
          <img src="${pocketSrc}" alt="사이드 삼각 포켓" decoding="async" />
        </div>
        <span class="feature-callout-label">사이드 삼각 포켓</span>
        <span class="feature-callout-connector" aria-hidden="true"></span>
      </div>
      <div class="feature-callout-circle-wrap">
        <div class="feature-callout-circle">
          <img src="${fleeceSrc}" alt="하이 게이지 편직 및 기모 소재" decoding="async" />
        </div>
        <span class="feature-callout-label">기모 보온 소재</span>
        <span class="feature-callout-connector" aria-hidden="true"></span>
      </div>
    </div>
    <div class="layer-badge-cta">
      <img src="${promoSrc}" alt="다시 없을 마지막 혜택! 젝시블프 UP TO 80%" class="assembly-promo-bar-img" decoding="async" />
    </div>
  `;
}

function resolveMeritzSceneConfig(optionId) {
  const isOpt2 = optionId === 'opt2_monumental';
  const assets = {
    logoSrc: resolveAssetPath(MERITZ_CUTOUT_ASSETS.logo),
    heroSrc: resolveAssetPath(isOpt2 ? MERITZ_CUTOUT_ASSETS.heroOption2 : MERITZ_CUTOUT_ASSETS.coin3d),
    iconSproutSrc: resolveAssetPath(MERITZ_CUTOUT_ASSETS.iconSprout),
    iconGrowthSrc: resolveAssetPath(MERITZ_CUTOUT_ASSETS.iconGrowth),
    iconHoneySrc: resolveAssetPath(MERITZ_CUTOUT_ASSETS.iconHoney)
  };
  return {
    sceneKey: isOpt2 ? 'meritz-opt2' : 'meritz-opt1',
    layoutMode: isOpt2 ? 'meritz-opt2' : 'meritz-opt1',
    isOpt2,
    ratioFloat: 1,
    assets,
    preloadUrls: Object.values(assets)
  };
}

function buildMeritzLayersMarkup(scene) {
  const { logoSrc, heroSrc, iconSproutSrc, iconGrowthSrc, iconHoneySrc } = scene.assets;
  const headlineHtml = scene.isOpt2
    ? `
      <div class="meritz-headline-wrap">
        <span class="meritz-eyebrow">초보자도 첫달부터 수익+</span>
        <div class="meritz-subhead">첫달 평균 수익</div>
      </div>
      <div class="meritz-unit-callout">
        <span>만원</span>
        <span class="meritz-unit-bar" aria-hidden="true"></span>
      </div>
    `
    : `
      <div class="meritz-headline-wrap">
        <span class="meritz-eyebrow">초보자도 첫달부터 수익+</span>
        <div class="meritz-subhead">첫달 평균 수익</div>
        <div class="meritz-hero-numeral">150<span class="meritz-hero-unit">만원</span></div>
      </div>
    `;

  return `
    <div class="layer-canvas-bg" aria-hidden="true">
      <div class="meritz-canvas-card"></div>
    </div>
    <div class="layer-product-cutout">
      <img src="${heroSrc}" alt="${scene.isOpt2 ? "Meritz 3D '150' Floating Sculpture" : 'Meritz 3D Gold Coin'}" decoding="async" />
    </div>
    <div class="layer-typography-group">
      <div class="meritz-header-bar">
        <img src="${logoSrc}" alt="Meritz Partners" class="meritz-brand-logo" decoding="async" />
        <div class="meritz-header-chips">
          <span class="meritz-header-chip">경력무관</span>
          <span class="meritz-header-chip">나이 무관</span>
        </div>
      </div>
      ${headlineHtml}
    </div>
    <div class="layer-feature-card">
      <div class="meritz-benefit-card">
        <img src="${iconSproutSrc}" alt="" class="meritz-benefit-icon" decoding="async" />
        <div>
          <div class="meritz-benefit-title">경력무관</div>
          <div class="meritz-benefit-sub">초보자 누구나 시작</div>
        </div>
      </div>
      <div class="meritz-benefit-card">
        <img src="${iconGrowthSrc}" alt="" class="meritz-benefit-icon" decoding="async" />
        <div>
          <div class="meritz-benefit-title">첫달부터 수익+</div>
          <div class="meritz-benefit-sub">체결 즉시 실적 반영</div>
        </div>
      </div>
      <div class="meritz-benefit-card">
        <img src="${iconHoneySrc}" alt="" class="meritz-benefit-icon" decoding="async" />
        <div>
          <div class="meritz-benefit-title">나이 안보는 부업</div>
          <div class="meritz-benefit-sub">원하는 시간 꿀부업</div>
        </div>
      </div>
    </div>
    <div class="layer-badge-cta">
      <div class="meritz-cta-button">꿀부업 시작 바로가기 &gt;</div>
      <div class="meritz-legal-note">*‘24년 8월 ~ ‘25년 7월 수익자의 첫 달 평균 금액 기준, 수익은 보험체결 후 발생, 개인차 있음</div>
    </div>
  `;
}

/**
 * STEP 20 (PHASE 2): Hardened Multi-Layer Remotion-Style Motion Assembly Trigger
 * Enforces all 4 mandatory safeguards:
 *   1. Clean DOM teardown (teardownAssemblyStage + monotonic runToken)
 *   2. Fluid % / cqw coordinates via --stage-ratio + data-layout-mode
 *   3. Replay debounce (180ms) + synchronous reflow flush + rAF start
 *   4. Cutout PNG preload & decode gate before spring translations begin
 */
function triggerLiveAssembly(stageCanvas, config = {}) {
  if (!stageCanvas) return;

  const opts = typeof config === 'object' && config !== null ? config : {};

  /* Safeguard 3: Replay debounce prevents rapid-click storming & visual flicker */
  if (opts.isReplay) {
    const now = performance.now();
    const lastTs = assemblyReplayTimestamps.get(stageCanvas) || 0;
    if (now - lastTs < REPLAY_DEBOUNCE_MS) {
      return;
    }
    assemblyReplayTimestamps.set(stageCanvas, now);
  }

  /* Safeguard 1: Clean teardown of prior layers, timers, and animations */
  const runToken = teardownAssemblyStage(stageCanvas);

  const brand = opts.brand || 'xexymix';
  const scene =
    brand === 'meritz'
      ? resolveMeritzSceneConfig(opts.optionId || 'opt2_monumental')
      : resolveXexymixSceneConfig(opts.placement || { id: '01', resolution: '1440x2560' });

  stageCanvas.style.setProperty('--stage-ratio', String(Number(scene.ratioFloat.toFixed(4))));
  stageCanvas.setAttribute('data-layout-mode', scene.layoutMode);
  stageCanvas.setAttribute('data-scene-key', scene.sceneKey);
  stageCanvas.classList.add('is-preloading');

  stageCanvas.innerHTML =
    brand === 'meritz' ? buildMeritzLayersMarkup(scene) : buildXexymixLayersMarkup(scene);

  const initialDelayMs =
    typeof opts.initialDelayMs === 'number' && opts.initialDelayMs > 0 ? opts.initialDelayMs : 0;
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const effectiveDelay = prefersReducedMotion ? 0 : initialDelayMs;
  const settleMs = prefersReducedMotion ? 60 : REMOTION_SETTLE_DURATION_MS;

  const timerBag = { startTimerId: null, completeTimerId: null, rafId: null };
  assemblyTimers.set(stageCanvas, timerBag);

  /* Safeguard 4: Await cutout PNG preload/decode (never hangs or aborts on delay) */
  preloadSceneAssets(scene.preloadUrls)
    .catch(() => {})
    .then(() => {
      if (assemblyRunTokens.get(stageCanvas) !== runToken || !stageCanvas.isConnected) {
        return;
      }

      const startSpringSequence = () => {
        if (assemblyRunTokens.get(stageCanvas) !== runToken || !stageCanvas.isConnected) {
          return;
        }
        stageCanvas.classList.remove('is-preloading', 'is-assembling', 'is-assembled');
        /* Explicit synchronous reflow flush before re-applying animation class */
        void stageCanvas.offsetWidth;
        timerBag.rafId = window.requestAnimationFrame(() => {
          if (assemblyRunTokens.get(stageCanvas) !== runToken || !stageCanvas.isConnected) {
            return;
          }
          stageCanvas.classList.add('is-assembling');
          timerBag.completeTimerId = window.setTimeout(() => {
            if (assemblyRunTokens.get(stageCanvas) !== runToken) return;
            stageCanvas.classList.remove('is-assembling');
            stageCanvas.classList.add('is-assembled');
            assemblyTimers.delete(stageCanvas);
          }, settleMs);
        });
      };

      if (effectiveDelay > 0) {
        timerBag.startTimerId = window.setTimeout(startSpringSequence, effectiveDelay);
      } else {
        startSpringSequence();
      }
    });
}

if (typeof window !== 'undefined') {
  window.triggerLiveAssembly = triggerLiveAssembly;
  window.teardownAssemblyStage = teardownAssemblyStage;
}

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

  /* Sync Master ZIP download button href & translated label + Live 11-Ratio Assembly launcher */
  const zipBtn = mount.querySelector('#xexymix-master-zip-btn');
  const ctaWrap = mount.querySelector('.keepsake-zip-cta-wrap');
  if (zipBtn) {
    zipBtn.setAttribute('href', resolveAssetPath(SHOWCASE_CONFIG.xexymixZipPath));
    const zipLabelEl = zipBtn.querySelector('[data-i18n="keepsake.btn_download_zip"]');
    if (zipLabelEl) {
      zipLabelEl.textContent = t(locale, 'keepsake.btn_download_zip', 'DOWNLOAD ALL 11 SIZES (.ZIP)');
    }
  }

  if (ctaWrap && zipBtn) {
    let ctaRow = ctaWrap.querySelector('.keepsake-cta-row');
    if (!ctaRow) {
      ctaRow = document.createElement('div');
      ctaRow.className = 'keepsake-cta-row';
      zipBtn.parentNode.insertBefore(ctaRow, zipBtn);
      ctaRow.appendChild(zipBtn);
    }

    let liveBtn = ctaRow.querySelector('#xexymix-live-assembly-btn');
    if (!liveBtn) {
      liveBtn = document.createElement('button');
      liveBtn.type = 'button';
      liveBtn.id = 'xexymix-live-assembly-btn';
      liveBtn.className = 'keepsake-live-assembly-btn';
      liveBtn.setAttribute('data-open-ratio-preview', placements[0] ? placements[0].id : '01');
      liveBtn.innerHTML = `<span data-i18n="assembly.btn_live_preview">${t(locale, 'assembly.btn_live_preview', 'LAUNCH LIVE 11-RATIO ASSEMBLY')}</span>`;
      ctaRow.insertBefore(liveBtn, zipBtn);
    } else {
      const liveLabelEl = liveBtn.querySelector('[data-i18n="assembly.btn_live_preview"]');
      if (liveLabelEl) {
        liveLabelEl.textContent = t(locale, 'assembly.btn_live_preview', 'LAUNCH LIVE 11-RATIO ASSEMBLY');
      }
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

      /* Desktop click on any expanded Keepsake ratio card launches Live Parametric Assembly preview */
      const keepsakeContainer = mount.querySelector('.keepsake-container');
      if (keepsakeContainer) {
        keepsakeContainer.addEventListener('click', (event) => {
          const isCoarse =
            typeof window !== 'undefined' &&
            window.matchMedia &&
            window.matchMedia('(pointer: coarse)').matches;
          if (isCoarse) return;
          const root = keepsakeContainer.querySelector('[data-keepsake-root]');
          if (!root || !root.classList.contains('is-expanded')) return;
          const slot = event.target.closest('.keepsake-card-slot');
          if (!slot) return;
          const placementId = slot.getAttribute('data-placement-id');
          if (placementId && AppState.manifest) {
            openRatioPreviewModal(AppState.manifest, placementId);
          }
        });
      }
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

function closeShowcaseModal(modal) {
  if (!modal) return;
  const activeCanvas = modal.querySelector('#assembly-stage-canvas');
  if (activeCanvas) {
    teardownAssemblyStage(activeCanvas);
  }
  modal.classList.remove('is-open');
  if (AppState.heroStage && typeof AppState.heroStage.resume === 'function') {
    AppState.heroStage.resume();
  }
}

/**
 * Deep-Zoom & Multi-Layer Assembly Modal Host
 */
function ensureDeepZoomModal(manifest) {
  let modal = document.getElementById('meritz-deep-zoom-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'meritz-deep-zoom-modal';
    modal.className = 'cyber-modal-backdrop';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', 'Auto-Banner Multi-Layer Assembly Inspector');
    document.body.appendChild(modal);
  }

  document.addEventListener('click', (event) => {
    const ratioTrigger = event.target.closest('[data-open-ratio-preview]');
    if (ratioTrigger) {
      const placementId = ratioTrigger.getAttribute('data-open-ratio-preview');
      openRatioPreviewModal(manifest, placementId);
      return;
    }
    const trigger = event.target.closest('[data-open-zoom]');
    if (trigger) {
      const optionId = trigger.getAttribute('data-open-zoom');
      openDeepZoomModal(manifest, optionId);
      return;
    }
    if (event.target.matches('#meritz-deep-zoom-modal') || event.target.closest('[data-close-zoom]')) {
      closeShowcaseModal(modal);
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.classList.contains('is-open')) {
      closeShowcaseModal(modal);
    }
  });
}

function openDeepZoomModal(manifest, optionId) {
  const modal = document.getElementById('meritz-deep-zoom-modal');
  if (!modal) return;

  const task2 = manifest.tasks.task2_meritz;
  let activeOpt = task2.options.find((o) => o.option_id === optionId) || task2.options[1];
  const locale = AppState.locale;
  const replayLabel = t(locale, 'assembly.btn_replay', '▶ Xem Lại Lắp Ráp');

  AppState.modalZoomMagnified = false;
  if (AppState.heroStage && typeof AppState.heroStage.pause === 'function') {
    AppState.heroStage.pause();
  }
  prewarmAllCutoutAssets();

  modal.innerHTML = `
    <div class="cyber-modal-dialog">
      <div class="cyber-modal-header">
        <span id="meritz-modal-title">${t(locale, 'task2_meritz.modal_title', 'CLOSE-UP 3D DETAIL VIEWER')} // ${activeOpt.label.toUpperCase()}</span>
        <div class="modal-header-actions">
          <button type="button" id="replay-assembly-btn" class="replay-assembly-btn">
            <span data-i18n="assembly.btn_replay">${replayLabel}</span>
          </button>
          <button type="button" class="cyber-btn" data-close-zoom="true">
            <span>[ ESC // CLOSE ]</span>
          </button>
        </div>
      </div>

      <div class="modal-ratio-strip" role="tablist" aria-label="Switch Creative Option">
        ${task2.options
          .map(
            (o, idx) => `
          <button
            type="button"
            class="modal-ratio-pill ${o.option_id === activeOpt.option_id ? 'is-active' : ''}"
            data-switch-meritz-opt="${o.option_id}"
            role="tab"
            aria-selected="${String(o.option_id === activeOpt.option_id)}"
          >
            <span>OPT 0${idx + 1}</span>
            <span>// ${o.option_id === 'opt2_monumental' ? '3D FLOATING' : 'CLASSIC DR'}</span>
          </button>`
          )
          .join('')}
      </div>

      <div class="cyber-modal-body">
        <div id="deep-zoom-stage" class="deep-zoom-stage has-assembly-canvas supports-loupe" title="Click to toggle 2.35x loupe and move cursor to pan">
          <div id="assembly-stage-canvas" class="assembly-stage-canvas"></div>
        </div>

        <div class="deep-zoom-sidebar">
          <div>
            <span class="zone-eyebrow" data-i18n="task2_meritz.modal_eyebrow">${t(locale, 'task2_meritz.modal_eyebrow', "ACCURACY SPECIFICATIONS // 3D '150' CENTERPIECE")}</span>
            <h3 class="zone-title" id="meritz-modal-heading" style="font-size:22px;margin-bottom:10px;" data-i18n="task2_meritz.modal_heading">${t(locale, 'task2_meritz.modal_heading', 'Matte Finish & Geometric Gold Frame')}</h3>
            <p class="meritz-art-direction" id="meritz-modal-desc" data-i18n="task2_meritz.modal_desc">
              ${t(locale, 'task2_meritz.modal_desc', "Move your cursor across the banner to inspect the natural matte finish on the Meritz Red (#EF3B24) '150' sculpture, crisp gold frame lines, and balanced Korean typography.")}
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
              <span class="cad-spec-val" id="zoom-scale-readout">1.00x FULL FRAME</span>
            </li>
          </ul>

          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            <button type="button" id="toggle-zoom-scale-btn" class="cyber-btn emerald-toggle">
              <span data-i18n="task2_meritz.modal_toggle_zoom">${t(locale, 'task2_meritz.modal_toggle_zoom', 'TOGGLE 2.35x / 1.0x ZOOM')}</span>
            </button>
            <a id="meritz-download-psd-link" href="${resolveAssetPath(activeOpt.psd_path)}" download class="cyber-btn">
              <span data-i18n="task2_meritz.modal_download_psd">${t(locale, 'task2_meritz.modal_download_psd', 'DOWNLOAD LAYERED .PSD')}</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  modal.classList.add('is-open');

  const stage = modal.querySelector('#deep-zoom-stage');
  const canvasEl = modal.querySelector('#assembly-stage-canvas');
  const replayBtn = modal.querySelector('#replay-assembly-btn');
  const toggleBtn = modal.querySelector('#toggle-zoom-scale-btn');
  const readout = modal.querySelector('#zoom-scale-readout');
  const titleBar = modal.querySelector('#meritz-modal-title');
  const psdLink = modal.querySelector('#meritz-download-psd-link');

  if (canvasEl) {
    triggerLiveAssembly(canvasEl, {
      brand: 'meritz',
      optionId: activeOpt.option_id,
      initialDelayMs: ASSEMBLY_MODAL_DELAY_MS
    });
  }

  const syncZoomUi = () => {
    if (stage) {
      stage.classList.toggle('is-magnified', AppState.modalZoomMagnified);
    }
    if (toggleBtn) {
      toggleBtn.classList.toggle('is-active', AppState.modalZoomMagnified);
    }
    if (readout) {
      readout.textContent = AppState.modalZoomMagnified ? '2.35x LOUPE ACTIVE' : '1.00x FULL FRAME';
    }
  };

  if (replayBtn && canvasEl) {
    replayBtn.addEventListener('click', () => {
      AppState.modalZoomMagnified = false;
      syncZoomUi();
      triggerLiveAssembly(canvasEl, {
        brand: 'meritz',
        optionId: activeOpt.option_id,
        initialDelayMs: 0,
        isReplay: true
      });
    });
  }

  const optPills = modal.querySelectorAll('[data-switch-meritz-opt]');
  optPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      const nextOptId = pill.getAttribute('data-switch-meritz-opt');
      const nextOpt = task2.options.find((o) => o.option_id === nextOptId);
      if (!nextOpt || !canvasEl) return;
      activeOpt = nextOpt;
      AppState.modalZoomMagnified = false;
      syncZoomUi();

      optPills.forEach((btn) => {
        const active = btn === pill;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', String(active));
      });

      if (titleBar) {
        titleBar.textContent = `${t(locale, 'task2_meritz.modal_title', 'CLOSE-UP 3D DETAIL VIEWER')} // ${activeOpt.label.toUpperCase()}`;
      }
      if (psdLink) {
        psdLink.setAttribute('href', resolveAssetPath(activeOpt.psd_path));
      }

      triggerLiveAssembly(canvasEl, {
        brand: 'meritz',
        optionId: activeOpt.option_id,
        initialDelayMs: 0
      });
    });
  });

  if (stage && canvasEl) {
    const updateZoomOrigin = (clientX, clientY) => {
      const rect = stage.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      const xPct = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100));
      const yPct = Math.max(0, Math.min(100, ((clientY - rect.top) / rect.height) * 100));
      canvasEl.style.transformOrigin = `${xPct.toFixed(1)}% ${yPct.toFixed(1)}%`;
    };

    stage.addEventListener('mousemove', (e) => {
      if (AppState.modalZoomMagnified) {
        updateZoomOrigin(e.clientX, e.clientY);
      }
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
      syncZoomUi();
    });
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      AppState.modalZoomMagnified = !AppState.modalZoomMagnified;
      syncZoomUi();
    });
  }
}

/**
 * Live 11-Ratio Multi-Layer Remotion Assembly Modal for all XEXYMIX placements
 * Switching any ratio pill cleanly tears down prior layers and re-mounts the target archetype.
 */
function openRatioPreviewModal(manifest, placementId) {
  const modal = document.getElementById('meritz-deep-zoom-modal');
  if (!modal) return;

  const task1 = manifest.tasks.task1_xexymix;
  const placements = task1.placements || [];
  if (!placements.length) return;

  let activePlacement =
    placements.find((p) => String(p.id) === String(placementId)) || placements[0];
  const imgUrl = resolveAssetPath(activePlacement.file);
  const locale = AppState.locale;
  const replayLabel = t(locale, 'assembly.btn_replay', '▶ Xem Lại Lắp Ráp');

  AppState.modalZoomMagnified = false;
  if (AppState.heroStage && typeof AppState.heroStage.pause === 'function') {
    AppState.heroStage.pause();
  }
  prewarmAllCutoutAssets();

  modal.innerHTML = `
    <div class="cyber-modal-dialog">
      <div class="cyber-modal-header">
        <span data-i18n="assembly.modal_ratio_title">${t(locale, 'assembly.modal_ratio_title', 'LIVE PARAMETRIC ASSEMBLY // XEXYMIX 11 RATIOS')}</span>
        <div class="modal-header-actions">
          <button type="button" id="replay-assembly-btn" class="replay-assembly-btn">
            <span data-i18n="assembly.btn_replay">${replayLabel}</span>
          </button>
          <button type="button" class="cyber-btn" data-close-zoom="true">
            <span>[ ESC // CLOSE ]</span>
          </button>
        </div>
      </div>

      <div class="modal-ratio-strip" role="tablist" aria-label="Select Banner Ratio">
        ${placements
          .map(
            (p) => `
          <button
            type="button"
            class="modal-ratio-pill ${p.id === activePlacement.id ? 'is-active' : ''}"
            data-select-ratio-id="${p.id}"
            role="tab"
            aria-selected="${String(p.id === activePlacement.id)}"
          >
            <span>#${p.id}</span>
            <span>${p.ratio}</span>
          </button>`
          )
          .join('')}
      </div>

      <div class="cyber-modal-body">
        <div id="deep-zoom-stage" class="deep-zoom-stage has-assembly-canvas">
          <div id="assembly-stage-canvas" class="assembly-stage-canvas"></div>
        </div>

        <div class="deep-zoom-sidebar">
          <div>
            <span class="zone-eyebrow" id="ratio-sidebar-eyebrow">PLACEMENT #${activePlacement.id} // ${getPlacementCategory(activePlacement)}</span>
            <h3 class="zone-title" id="ratio-sidebar-title" style="font-size:22px;margin-bottom:10px;">${activePlacement.name}</h3>
            <p class="meritz-art-direction" data-i18n="task1_xexymix.description">
              ${t(locale, 'task1_xexymix.description', task1.title)}
            </p>
          </div>

          <ul class="cad-spec-list">
            <li class="cad-spec-item">
              <span class="cad-spec-key" data-i18n="keepsake.label_resolution">${t(locale, 'keepsake.label_resolution', 'DIMENSIONS')}</span>
              <span class="cad-spec-val" id="ratio-spec-res" style="color:var(--accent-cyan);">${activePlacement.resolution} px</span>
            </li>
            <li class="cad-spec-item">
              <span class="cad-spec-key" data-i18n="keepsake.label_ratio">${t(locale, 'keepsake.label_ratio', 'ASPECT RATIO')}</span>
              <span class="cad-spec-val" id="ratio-spec-ratio">${activePlacement.ratio}</span>
            </li>
            <li class="cad-spec-item">
              <span class="cad-spec-key" data-i18n="keepsake.label_stepping">${t(locale, 'keepsake.label_stepping', 'CLEAN GUIDES')}</span>
              <span class="cad-spec-val" style="color:var(--status-emerald);" data-i18n="keepsake.status_passed">${t(locale, 'keepsake.status_passed', 'PASSED')}</span>
            </li>
            <li class="cad-spec-item">
              <span class="cad-spec-key" data-i18n="keepsake.label_watermark">${t(locale, 'keepsake.label_watermark', 'AI WATERMARK')}</span>
              <span class="cad-spec-val" style="color:var(--status-emerald);" data-i18n="keepsake.watermark_compliant">${t(locale, 'keepsake.watermark_compliant', 'NONE (CLEAN)')}</span>
            </li>
          </ul>

          <div style="display:flex;flex-wrap:wrap;gap:10px;">
            <a id="ratio-download-jpg" href="${imgUrl}" download class="cyber-btn emerald-toggle is-active">
              <span data-i18n="task2_meritz.btn_preview_jpg">${t(locale, 'task2_meritz.btn_preview_jpg', 'DOWNLOAD PREVIEW .JPG')}</span>
            </a>
            <a href="${resolveAssetPath(SHOWCASE_CONFIG.xexymixZipPath)}" download class="cyber-btn">
              <span data-i18n="keepsake.btn_download_zip">${t(locale, 'keepsake.btn_download_zip', 'DOWNLOAD ALL 11 SIZES (.ZIP)')}</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  modal.classList.add('is-open');

  const canvasEl = modal.querySelector('#assembly-stage-canvas');
  const replayBtn = modal.querySelector('#replay-assembly-btn');

  if (canvasEl) {
    triggerLiveAssembly(canvasEl, {
      brand: 'xexymix',
      placement: activePlacement,
      initialDelayMs: ASSEMBLY_MODAL_DELAY_MS
    });
  }

  if (replayBtn && canvasEl) {
    replayBtn.addEventListener('click', () => {
      triggerLiveAssembly(canvasEl, {
        brand: 'xexymix',
        placement: activePlacement,
        initialDelayMs: 0,
        isReplay: true
      });
    });
  }

  /* In-place 11-size switcher: clean teardown + dynamic aspect-ratio & layer repositioning */
  const pills = modal.querySelectorAll('[data-select-ratio-id]');
  pills.forEach((pill) => {
    pill.addEventListener('click', () => {
      const nextId = pill.getAttribute('data-select-ratio-id');
      const nextPlacement = placements.find((p) => String(p.id) === String(nextId));
      if (!nextPlacement || !canvasEl) return;
      activePlacement = nextPlacement;

      pills.forEach((btn) => {
        const active = btn === pill;
        btn.classList.toggle('is-active', active);
        btn.setAttribute('aria-selected', String(active));
      });

      const nextUrl = resolveAssetPath(nextPlacement.file);
      const eyebrow = modal.querySelector('#ratio-sidebar-eyebrow');
      const titleEl = modal.querySelector('#ratio-sidebar-title');
      const resEl = modal.querySelector('#ratio-spec-res');
      const ratioEl = modal.querySelector('#ratio-spec-ratio');
      const dlLink = modal.querySelector('#ratio-download-jpg');

      if (eyebrow) {
        eyebrow.textContent = `PLACEMENT #${nextPlacement.id} // ${getPlacementCategory(nextPlacement)}`;
      }
      if (titleEl) {
        titleEl.textContent = nextPlacement.name;
      }
      if (resEl) {
        resEl.textContent = `${nextPlacement.resolution} px`;
      }
      if (ratioEl) {
        ratioEl.textContent = nextPlacement.ratio;
      }
      if (dlLink) {
        dlLink.setAttribute('href', nextUrl);
      }

      triggerLiveAssembly(canvasEl, {
        brand: 'xexymix',
        placement: nextPlacement,
        initialDelayMs: 0
      });
    });
  });
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
    if (AppState.assemblyObserver) {
      AppState.assemblyObserver.disconnect();
      AppState.assemblyObserver = null;
    }
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
