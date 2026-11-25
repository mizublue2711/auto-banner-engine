/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Decoupled Three.js Hero Stage (STEP 09)
 * Module: showcase_site/js/hero-three-stage.js
 * Aesthetic: Meritz Option 2 Monumental 3D Zero-Gravity
 *   - Matte Vermillion Red '150' Monolith (#EF3B24, roughness 0.88)
 *   - Champagne Gold Wireframe Gem Cage (#C5A059, metalness 0.85, roughness 0.25)
 *   - 5 Layered Zero-Gravity Gold Coins (#D4AF37, shared CylinderGeometry)
 * Optics & GPU Guardrails:
 *   - PerspectiveCamera (FOV 42deg, z = 4.8) + ResizeObserver aspect sync
 *   - Quaternion.slerp (damping 0.05) clamped strictly to ±12° pitch / ±18° yaw
 *   - Zero Realtime ShadowMap (procedural radial contact shadow plane)
 *   - IntersectionObserver pause + 3s idle throttling + full destroy() disposal
 * ============================================================================
 */

const THREE_CDN_URLS = Object.freeze([
  'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js',
  'https://unpkg.com/three@0.160.0/build/three.module.js'
]);

const STAGE_CONSTANTS = Object.freeze({
  FOV_DEG: 42,
  NEAR: 0.1,
  FAR: 1000,
  CAMERA_Z: 4.8,
  MAX_PITCH_DEG: 12,
  MAX_YAW_DEG: 18,
  SLERP_DAMPING: 0.05,
  CAGE_ROTATION_PER_FRAME: 0.003,
  MONOLITH_FLOAT_AMPLITUDE: 0.04,
  IDLE_SETTLE_MS: 3000,
  IDLE_QUAT_EPSILON: 0.0006,
  IDLE_FRAME_INTERVAL_MS: 66 // ~15 FPS low-power ambient drift after 3s idle
});

let cachedThreePromise = null;

/**
 * Dynamically load Three.js r160 ES module from CDN with secondary fallback.
 * Keeping this dynamic ensures app.js never crashes if offline/CDN is blocked.
 */
async function loadThreeModule() {
  if (cachedThreePromise) return cachedThreePromise;

  cachedThreePromise = (async () => {
    let lastError = null;
    for (const url of THREE_CDN_URLS) {
      try {
        const mod = await import(/* @vite-ignore */ url);
        if (mod && mod.WebGLRenderer) {
          return mod;
        }
      } catch (err) {
        lastError = err;
      }
    }
    cachedThreePromise = null;
    throw lastError || new Error('Failed to load three@0.160.0 from CDN.');
  })();

  return cachedThreePromise;
}

/**
 * Build 2D THREE.Shape for bold geometric numeral '1' (height = 1.04)
 */
function createDigitOneShape(THREE) {
  const s = new THREE.Shape();
  s.moveTo(0.22, 0.0);
  s.lineTo(0.48, 0.0);
  s.lineTo(0.48, 1.04);
  s.lineTo(0.25, 1.04);
  s.lineTo(0.0, 0.85);
  s.lineTo(0.0, 0.65);
  s.lineTo(0.22, 0.78);
  s.closePath();
  return s;
}

/**
 * Build 2D THREE.Shape for bold geometric numeral '5' (height = 1.04)
 */
function createDigitFiveShape(THREE) {
  const s = new THREE.Shape();
  s.moveTo(0.0, 0.27);
  s.bezierCurveTo(0.02, 0.08, 0.16, 0.0, 0.33, 0.0);
  s.bezierCurveTo(0.54, 0.0, 0.66, 0.14, 0.66, 0.335);
  s.bezierCurveTo(0.66, 0.54, 0.53, 0.67, 0.34, 0.67);
  s.lineTo(0.25, 0.67);
  s.lineTo(0.26, 0.83);
  s.lineTo(0.61, 0.83);
  s.lineTo(0.61, 1.04);
  s.lineTo(0.07, 1.04);
  s.lineTo(0.04, 0.47);
  s.lineTo(0.24, 0.47);
  s.bezierCurveTo(0.38, 0.47, 0.45, 0.42, 0.45, 0.335);
  s.bezierCurveTo(0.45, 0.25, 0.39, 0.2, 0.32, 0.2);
  s.bezierCurveTo(0.25, 0.2, 0.21, 0.23, 0.2, 0.28);
  s.closePath();
  return s;
}

/**
 * Build 2D THREE.Shape for bold geometric stadium numeral '0' (height = 1.04)
 */
function createDigitZeroShape(THREE) {
  const s = new THREE.Shape();
  const cx = 0.35;
  const rOut = 0.35;
  const yBot = 0.35;
  const yTop = 0.69;

  s.absarc(cx, yBot, rOut, Math.PI, Math.PI * 2, false);
  s.lineTo(cx + rOut, yTop);
  s.absarc(cx, yTop, rOut, 0, Math.PI, false);
  s.lineTo(cx - rOut, yBot);

  const hole = new THREE.Path();
  const rIn = 0.14;
  hole.absarc(cx, yTop, rIn, Math.PI, 0, true);
  hole.lineTo(cx + rIn, yBot);
  hole.absarc(cx, yBot, rIn, 0, Math.PI, true);
  hole.lineTo(cx - rIn, yTop);
  s.holes.push(hole);

  return s;
}

/**
 * Generate a subtle procedural micro-matte roughness/grain CanvasTexture
 * Keeps roughness strictly within [0.85, 0.95] to prevent glossy plastic highlights.
 */
function createMatteGrainTexture(THREE) {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const imgData = ctx.createImageData(size, size);
    const data = imgData.data;
    // Deterministic PRNG for consistent grain across runs
    let seed = 1502026;
    for (let i = 0; i < data.length; i += 4) {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      const n = (seed >>> 24) / 255;
      // Map to grayscale 218..244 (~0.85..0.96 roughness multiplier)
      const val = Math.round(218 + n * 26);
      data[i] = val;
      data[i + 1] = val;
      data[i + 2] = val;
      data[i + 3] = 255;
    }
    ctx.putImageData(imgData, 0, 0);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(3, 3);
  texture.needsUpdate = true;
  return texture;
}

/**
 * Generate soft radial alpha gradient CanvasTexture for contact shadow plane
 * (replaces expensive real-time shadow maps).
 */
function createContactShadowTexture(THREE) {
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const half = size / 2;
    const grad = ctx.createRadialGradient(half, half, 4, half, half, half);
    grad.addColorStop(0.0, 'rgba(0, 0, 0, 0.62)');
    grad.addColorStop(0.45, 'rgba(0, 0, 0, 0.28)');
    grad.addColorStop(0.78, 'rgba(0, 0, 0, 0.06)');
    grad.addColorStop(1.0, 'rgba(0, 0, 0, 0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

/**
 * Synthesize a lightweight zero-asset studio PMREM environment map so high-metalness
 * Champagne Gold cage (0.85) and Gold Coins (0.90) reflect realistic warm/cyan highlights.
 */
function createStudioEnvironment(THREE, renderer) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();

  const envScene = new THREE.Scene();
  envScene.background = new THREE.Color(0x0b0b12);

  const panelGeo = new THREE.PlaneGeometry(1, 1);

  const panels = [
    // Overhead warm key softbox
    { color: 0xfff5e6, intensity: 3.4, pos: [4, 6, 4], scale: [6, 6, 1] },
    // Right warm champagne bounce
    { color: 0xffd9a0, intensity: 2.2, pos: [7, 1, 2], scale: [5, 4, 1] },
    // Left cool cyan rim panel (echoes Cybernetic Brutalism HUD)
    { color: 0x00e5ff, intensity: 2.0, pos: [-7, 3, -3], scale: [5, 5, 1] },
    // Front subtle fill strip
    { color: 0xffffff, intensity: 1.5, pos: [0, 2, 7], scale: [7, 2.2, 1] },
    // Lower warm bounce for coin undersides
    { color: 0xffe4bd, intensity: 1.1, pos: [0, -6, 3], scale: [8, 6, 1] }
  ];

  const tempMats = [];
  for (const p of panels) {
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(p.color).multiplyScalar(p.intensity),
      side: THREE.DoubleSide
    });
    tempMats.push(mat);
    const mesh = new THREE.Mesh(panelGeo, mat);
    mesh.position.set(p.pos[0], p.pos[1], p.pos[2]);
    mesh.scale.set(p.scale[0], p.scale[1], p.scale[2]);
    mesh.lookAt(0, 0, 0);
    envScene.add(mesh);
  }

  const envRenderTarget = pmrem.fromScene(envScene, 0.04);

  // Clean up temporary virtual studio resources immediately
  panelGeo.dispose();
  for (const m of tempMats) {
    m.dispose();
  }
  pmrem.dispose();

  return envRenderTarget;
}

export class HeroThreeStage {
  /**
   * Static WebGL availability check (safe for SSR / headless / restricted GPUs).
   */
  static isWebGLAvailable() {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return false;
    }
    try {
      const canvas = document.createElement('canvas');
      const gl =
        canvas.getContext('webgl2', { failIfMajorPerformanceCaveat: false }) ||
        canvas.getContext('webgl', { failIfMajorPerformanceCaveat: false }) ||
        canvas.getContext('experimental-webgl');
      if (!gl) return false;
      const loseExt = gl.getExtension('WEBGL_lose_context');
      if (loseExt) loseExt.loseContext();
      return true;
    } catch (_) {
      return false;
    }
  }

  /**
   * @param {HTMLElement} container - Target DOM element (#hero-three-container)
   * @param {Object} [options]
   * @param {Function} [options.onRotationUpdate] - Callback({ pitchDeg, yawDeg, mode })
   * @param {Function} [options.onContextLost] - Callback invoked on unrecoverable WebGL loss
   */
  constructor(container, options = {}) {
    if (!container) {
      throw new Error('HeroThreeStage requires a valid container HTMLElement.');
    }
    this.container = container;
    this.options = options;

    this.THREE = null;
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.envRenderTarget = null;

    this.stageRig = null;
    this.gemCage = null;
    this.monolithGroup = null;
    this.coins = [];
    this.contactShadow = null;

    // Reusable math objects (zero per-frame allocations)
    this.targetEuler = null;
    this.targetQuaternion = null;
    this.currentEuler = null;

    // Runtime state
    this.isInitialized = false;
    this.isDestroyed = false;
    this.isVisible = true;
    this.isTabVisible = true;
    this.isPointerActive = false;
    this.isReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.isCoarsePointer =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(pointer: coarse)').matches;

    this.rafId = null;
    this.lastFrameTs = 0;
    this.lastRenderTs = 0;
    this.elapsedSec = 0;
    this.lastInteractionTs = performance.now();
    this.targetPitchRad = 0;
    this.targetYawRad = 0;
    this.lastTelemetryPushTs = 0;
    this._lastWidth = 0;
    this._lastHeight = 0;
    this._lastDpr = 0;

    // Observers & bound handlers
    this.intersectionObserver = null;
    this.resizeObserver = null;
    this._onPointerMove = this._handlePointerMove.bind(this);
    this._onPointerLeave = this._handlePointerLeave.bind(this);
    this._onWindowResize = this._handleResize.bind(this);
    this._onVisibilityChange = this._handleVisibilityChange.bind(this);
    this._onContextLost = this._handleContextLost.bind(this);
    this._animate = this._tick.bind(this);
  }

  /**
   * Async initialization: loads Three.js r160, builds scene, binds observers, starts render loop.
   */
  async init() {
    if (this.isDestroyed) return false;
    if (this.isInitialized) return true;

    if (!HeroThreeStage.isWebGLAvailable()) {
      throw new Error('WebGL is not supported in this browser environment.');
    }

    const THREE = await loadThreeModule();
    if (this.isDestroyed) return false;
    this.THREE = THREE;

    const { width, height } = this._measureContainer();

    // 1. Scene & Camera (Anti-Flattening PerspectiveCamera FOV 42, z = 4.8)
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(
      STAGE_CONSTANTS.FOV_DEG,
      width / height,
      STAGE_CONSTANTS.NEAR,
      STAGE_CONSTANTS.FAR
    );
    this._applyCameraProjection(width, height);
    this.camera.lookAt(0, 0, 0);

    // 2. Renderer (No Realtime ShadowMap, capped DPR <= 2, sRGB + ACESFilmic)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    this.renderer.shadowMap.enabled = false;
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(width, height, false);
    this._lastWidth = width;
    this._lastHeight = height;
    this._lastDpr = dpr;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.12;

    const domEl = this.renderer.domElement;
    domEl.style.width = '100%';
    domEl.style.height = '100%';
    domEl.style.display = 'block';
    domEl.setAttribute('aria-label', "Interactive 3D Meritz '150' Monolith & Gem Cage Stage");

    this.container.innerHTML = '';
    this.container.appendChild(domEl);

    // 3. Procedural PMREM Studio Environment for Champagne Gold & Coins
    this.envRenderTarget = createStudioEnvironment(THREE, this.renderer);
    this.scene.environment = this.envRenderTarget.texture;

    // 4. Pre-allocated Quaternion / Euler math objects
    this.targetEuler = new THREE.Euler(0, 0, 0, 'YXZ');
    this.targetQuaternion = new THREE.Quaternion();
    this.currentEuler = new THREE.Euler(0, 0, 0, 'YXZ');

    // 5. Build Lighting, Stage Rig, Gem Cage, '150' Monolith, 5 Coins & Contact Shadow
    this._setupLighting();
    this.stageRig = new THREE.Group();
    this.scene.add(this.stageRig);

    this._buildWireframeGemCage();
    this._buildNumeral150Monolith();
    this._buildZeroGravityCoins();
    this._buildContactShadow();

    // 6. Bind Interaction, ResizeObserver, IntersectionObserver & Tab Visibility
    this._bindEvents();
    this._setupObservers();

    this.isInitialized = true;
    this.lastInteractionTs = performance.now();
    this.lastFrameTs = performance.now();
    this.lastRenderTs = performance.now();

    // Render initial frame immediately and sync once more after flex layout settles
    this.renderer.render(this.scene, this.camera);
    this._emitTelemetry('ACTIVE');
    window.requestAnimationFrame(() => this._handleResize());

    if (!this.isReducedMotion) {
      this._startLoop();
    }

    return true;
  }

  _measureContainer() {
    const rect = this.container.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width || this.container.clientWidth || 640));
    const height = Math.max(1, Math.round(rect.height || this.container.clientHeight || 440));
    return { width, height };
  }

  _setupLighting() {
    const THREE = this.THREE;

    // Key Light: DirectionalLight (#FFFFFF, 1.2) at (3, 4, 4) to carve crisp bevels
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(3, 4, 4);
    this.scene.add(keyLight);

    // Fill Light: DirectionalLight (#FFE8D6, 0.4) at (-3, -1, 2) for warm shadows
    const fillLight = new THREE.DirectionalLight(0xffe8d6, 0.4);
    fillLight.position.set(-3, -1, 2);
    this.scene.add(fillLight);

    // Primary Rim Light: DirectionalLight (#00E5FF, 1.2) angled top-back-left for crisp bevel separation
    const rimLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
    rimLight.position.set(-4, 3.5, -3.5);
    this.scene.add(rimLight);

    // Secondary Warm Rim Light: DirectionalLight (#FFE082, 0.9) angled top-back-right for Champagne Gold crystal edge pop
    const warmRimLight = new THREE.DirectionalLight(0xffe082, 0.9);
    warmRimLight.position.set(4, 3.5, -3.5);
    this.scene.add(warmRimLight);

    // Ambient Light: AmbientLight (#14141E, 0.8) to preserve Meritz Brand Red purity
    const ambientLight = new THREE.AmbientLight(0x14141e, 0.8);
    this.scene.add(ambientLight);
  }

  _buildWireframeGemCage() {
    const THREE = this.THREE;
    const cageGeo = new THREE.IcosahedronGeometry(1.6, 1);
    const cageMat = new THREE.MeshStandardMaterial({
      color: 0xc5a059, // Champagne Gold
      metalness: 0.85,
      roughness: 0.25,
      wireframe: true,
      envMapIntensity: 1.05
    });

    this.gemCage = new THREE.Mesh(cageGeo, cageMat);
    // Proportioned horizontally to frame the '150' monolith cleanly without clipping
    this.gemCage.scale.set(1.14, 0.86, 0.88);
    this.gemCage.rotation.set(0.18, 0.35, 0.06);
    this.stageRig.add(this.gemCage);
  }

  _buildNumeral150Monolith() {
    const THREE = this.THREE;

    const extrudeSettings = {
      depth: 0.34,
      bevelEnabled: true,
      bevelThickness: 0.08,
      bevelSize: 0.04,
      bevelSegments: 4,
      curveSegments: 24
    };

    // Frosted Satin Cyber-Glass — velvety non-glossy ruby glass revealing wireframe gem cage behind
    const monolithMat = new THREE.MeshPhysicalMaterial({
      color: 0xff2640,                 // Vibrant ruby red that won't turn muddy against the black background
      emissive: 0x1c0206,              // Subtle internal luminescence to keep the frosted core luminous
      transmission: 0.94,              // High transmission to reveal the wireframe gem cage and inner coins
      opacity: 0.74,                   // Allows crisp 1px wireframe lines behind to show through frosted glass
      transparent: true,
      roughness: 0.35,                 // Soft sandblasted / frosted glass satin finish (not shiny, not flat)
      metalness: 0.02,
      ior: 1.46,                       // Frosted glass / optical acrylic refraction index
      thickness: 0.3,                  // Light optical thickness for high clarity and transmission
      specularIntensity: 0.7,          // Soft diffuse highlight catching the 3D bevel edges
      specularColor: 0xff99aa,         // Warm tinted specular sheen (no harsh stark white glare)
      clearcoat: 0.0,                  // Completely remove glossy lacquer reflection
      clearcoatRoughness: 0.0,
      attenuationColor: 0xff1a3c,      // Rich crimson volumetric tint
      attenuationDistance: 1.2
    });

    const glyphSpecs = [
      { shape: createDigitOneShape(THREE), gapAfter: 0.13 },
      { shape: createDigitFiveShape(THREE), gapAfter: 0.12 },
      { shape: createDigitZeroShape(THREE), gapAfter: 0.0 }
    ];

    this.monolithGroup = new THREE.Group();
    const meshes = [];
    let cursorX = 0;

    for (const spec of glyphSpecs) {
      const geo = new THREE.ExtrudeGeometry(spec.shape, extrudeSettings);
      geo.computeBoundingBox();
      const box = geo.boundingBox;
      const glyphWidth = box.max.x - box.min.x;

      // Shift geometry so its min.x starts at 0 and center in Z
      geo.translate(-box.min.x, -box.min.y, -extrudeSettings.depth * 0.5);

      const mesh = new THREE.Mesh(geo, monolithMat);
      mesh.position.x = cursorX;
      this.monolithGroup.add(mesh);
      meshes.push(mesh);

      cursorX += glyphWidth + spec.gapAfter;
    }

    // Center the complete '150' monolith around exact optical origin (0, 0, 0)
    const totalBox = new THREE.Box3().setFromObject(this.monolithGroup);
    const center = new THREE.Vector3();
    totalBox.getCenter(center);
    for (const mesh of meshes) {
      mesh.position.x -= center.x;
      mesh.position.y -= center.y;
    }

    // Slightly scale so '150' commands strong presence well inside the gem cage
    this.monolithGroup.scale.setScalar(0.92);
    this.stageRig.add(this.monolithGroup);
  }

  _buildZeroGravityCoins() {
    const THREE = this.THREE;

    // Shared single CylinderGeometry across all 5 coins for minimal GPU memory
    const sharedCoinGeo = new THREE.CylinderGeometry(0.32, 0.32, 0.04, 32);

    const standardGoldMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.9,
      roughness: 0.2,
      envMapIntensity: 1.15
    });

    // Subtle soft-focus treatment for the closest foreground coin (cinematic depth feel)
    const foregroundGoldMat = new THREE.MeshStandardMaterial({
      color: 0xd4af37,
      metalness: 0.86,
      roughness: 0.32,
      transparent: true,
      opacity: 0.9,
      envMapIntensity: 1.0
    });

    // 1 foreground coin, 2 midground coins, 2 background micro-coins
    const coinConfigs = [
      // Foreground (close to camera, bottom-left)
      {
        pos: [-1.42, -0.92, 1.78],
        rot: [1.22, 0.38, -0.25],
        scale: 1.06,
        floatAmp: 0.075,
        floatSpeed: 1.15,
        phase: 0.2,
        rotSpeed: [0.18, 0.32, 0.14],
        mat: foregroundGoldMat
      },
      // Midground 1 (top-right)
      {
        pos: [1.56, 0.9, 0.36],
        rot: [1.38, -0.45, 0.22],
        scale: 0.95,
        floatAmp: 0.085,
        floatSpeed: 1.35,
        phase: 1.6,
        rotSpeed: [0.15, -0.42, 0.2],
        mat: standardGoldMat
      },
      // Midground 2 (bottom-right)
      {
        pos: [1.36, -0.98, 0.56],
        rot: [1.18, -0.62, -0.35],
        scale: 0.86,
        floatAmp: 0.068,
        floatSpeed: 1.5,
        phase: 3.1,
        rotSpeed: [-0.22, 0.36, 0.16],
        mat: standardGoldMat
      },
      // Background micro-coin 1 (upper-left mid-back)
      {
        pos: [-1.62, 0.98, -1.02],
        rot: [1.45, 0.52, 0.3],
        scale: 0.62,
        floatAmp: 0.095,
        floatSpeed: 0.95,
        phase: 4.4,
        rotSpeed: [0.24, 0.28, -0.18],
        mat: standardGoldMat
      },
      // Background micro-coin 2 (top-center-left deep-back)
      {
        pos: [-0.62, 1.32, -1.62],
        rot: [1.05, 0.24, 0.48],
        scale: 0.48,
        floatAmp: 0.1,
        floatSpeed: 0.85,
        phase: 5.5,
        rotSpeed: [-0.16, -0.34, 0.22],
        mat: standardGoldMat
      }
    ];

    this.coins = coinConfigs.map((cfg) => {
      const mesh = new THREE.Mesh(sharedCoinGeo, cfg.mat);
      mesh.position.set(cfg.pos[0], cfg.pos[1], cfg.pos[2]);
      mesh.rotation.set(cfg.rot[0], cfg.rot[1], cfg.rot[2]);
      mesh.scale.setScalar(cfg.scale);
      this.stageRig.add(mesh);

      return {
        mesh,
        baseY: cfg.pos[1],
        floatAmp: cfg.floatAmp,
        floatSpeed: cfg.floatSpeed,
        phase: cfg.phase,
        rotSpeed: cfg.rotSpeed
      };
    });
  }

  _buildContactShadow() {
    const THREE = this.THREE;
    const shadowTex = createContactShadowTexture(THREE);
    const shadowGeo = new THREE.PlaneGeometry(3.8, 2.3);
    const shadowMat = new THREE.MeshBasicMaterial({
      map: shadowTex,
      transparent: true,
      depthWrite: false,
      opacity: 0.78
    });

    this.contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
    this.contactShadow.rotation.x = -Math.PI / 2;
    this.contactShadow.position.set(0, -1.52, 0);
    this.scene.add(this.contactShadow);
  }

  _bindEvents() {
    if (!this.isCoarsePointer) {
      this.container.addEventListener('pointermove', this._onPointerMove, { passive: true });
      this.container.addEventListener('pointerleave', this._onPointerLeave, { passive: true });
    }
    window.addEventListener('resize', this._onWindowResize, { passive: true });
    document.addEventListener('visibilitychange', this._onVisibilityChange);
    if (this.renderer && this.renderer.domElement) {
      this.renderer.domElement.addEventListener('webglcontextlost', this._onContextLost, false);
    }
  }

  _setupObservers() {
    if (typeof IntersectionObserver !== 'undefined') {
      this.intersectionObserver = new IntersectionObserver(
        (entries) => {
          const entry = entries[0];
          if (!entry) return;
          const nextVisible = entry.isIntersecting;
          if (nextVisible === this.isVisible) return;
          this.isVisible = nextVisible;
          if (this.isVisible && this.isTabVisible) {
            this.lastFrameTs = performance.now();
            this._startLoop();
          } else {
            this._stopLoop();
          }
        },
        { threshold: 0.05 }
      );
      this.intersectionObserver.observe(this.container);
    }

    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        this._handleResize();
      });
      this.resizeObserver.observe(this.container);
    }
  }

  _handlePointerMove(event) {
    if (this.isDestroyed || !this.THREE) return;
    const rect = this.container.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const normX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const normY = ((event.clientY - rect.top) / rect.height) * 2 - 1;

    const maxPitchRad = this.THREE.MathUtils.degToRad(STAGE_CONSTANTS.MAX_PITCH_DEG);
    const maxYawRad = this.THREE.MathUtils.degToRad(STAGE_CONSTANTS.MAX_YAW_DEG);

    this.targetPitchRad = this.THREE.MathUtils.clamp(normY * maxPitchRad, -maxPitchRad, maxPitchRad);
    this.targetYawRad = this.THREE.MathUtils.clamp(normX * maxYawRad, -maxYawRad, maxYawRad);
    this.isPointerActive = true;
    this.lastInteractionTs = performance.now();

    if (this.isVisible && this.isTabVisible && !this.rafId && !this.isReducedMotion) {
      this.lastFrameTs = performance.now();
      this._startLoop();
    }
  }

  _handlePointerLeave() {
    this.targetPitchRad = 0;
    this.targetYawRad = 0;
    this.isPointerActive = false;
    this.lastInteractionTs = performance.now();
  }

  _applyCameraProjection(width, height) {
    if (!this.camera || width <= 0 || height <= 0) return;
    const aspect = width / height;
    // Keep exact CAMERA_Z on full-width/landscape viewports; gently pull back on narrow portrait screens so geometry never clips
    const targetZ =
      aspect < 1.15
        ? STAGE_CONSTANTS.CAMERA_Z * Math.min(1.5, 1.15 / Math.max(aspect, 0.5))
        : STAGE_CONSTANTS.CAMERA_Z;
    this.camera.aspect = aspect;
    this.camera.position.set(0, 0, targetZ);
    this.camera.updateProjectionMatrix();
  }

  resize() {
    this._handleResize();
  }

  _handleResize() {
    if (this.isDestroyed || !this.camera || !this.renderer) return;
    const rect = this.container.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const width = Math.round(rect.width);
    const height = Math.round(rect.height);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    if (width === this._lastWidth && height === this._lastHeight && dpr === this._lastDpr) {
      return;
    }

    this._lastWidth = width;
    this._lastHeight = height;
    this._lastDpr = dpr;

    this._applyCameraProjection(width, height);
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(width, height, false);

    this.lastInteractionTs = performance.now();
    this.renderer.render(this.scene, this.camera);
  }

  _handleVisibilityChange() {
    this.isTabVisible = document.visibilityState !== 'hidden';
    if (this.isTabVisible && this.isVisible && !this.isReducedMotion) {
      this.lastFrameTs = performance.now();
      this._startLoop();
    } else {
      this._stopLoop();
    }
  }

  _handleContextLost(event) {
    event.preventDefault();
    this._stopLoop();
    if (typeof this.options.onContextLost === 'function') {
      this.options.onContextLost();
    }
  }

  _startLoop() {
    if (this.isDestroyed || this.rafId !== null) return;
    this.rafId = window.requestAnimationFrame(this._animate);
  }

  _stopLoop() {
    if (this.rafId !== null) {
      window.cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }

  _emitTelemetry(mode) {
    if (typeof this.options.onRotationUpdate !== 'function' || !this.stageRig || !this.THREE) {
      return;
    }
    this.currentEuler.setFromQuaternion(this.stageRig.quaternion, 'YXZ');
    const pitchDeg = this.THREE.MathUtils.radToDeg(this.currentEuler.x);
    const yawDeg = this.THREE.MathUtils.radToDeg(this.currentEuler.y);
    this.options.onRotationUpdate({ pitchDeg, yawDeg, mode });
  }

  _tick(now) {
    if (this.isDestroyed || !this.isVisible || !this.isTabVisible) {
      this.rafId = null;
      return;
    }

    this.rafId = window.requestAnimationFrame(this._animate);

    // Compute target quaternion from clamped pitch/yaw
    this.targetEuler.set(this.targetPitchRad, this.targetYawRad, 0, 'YXZ');
    this.targetQuaternion.setFromEuler(this.targetEuler);

    const quatDelta = this.stageRig.quaternion.angleTo(this.targetQuaternion);
    const isIdleSettled =
      !this.isPointerActive &&
      now - this.lastInteractionTs > STAGE_CONSTANTS.IDLE_SETTLE_MS &&
      quatDelta < STAGE_CONSTANTS.IDLE_QUAT_EPSILON;

    // GPU Idle Throttling: reduce render cadence after 3s of no interaction once settled
    if (isIdleSettled && now - this.lastRenderTs < STAGE_CONSTANTS.IDLE_FRAME_INTERVAL_MS) {
      return;
    }

    const dt = Math.min(0.05, Math.max(0.001, (now - this.lastFrameTs) / 1000));
    this.lastFrameTs = now;
    this.lastRenderTs = now;
    this.elapsedSec += dt;

    // 1. Smooth Quaternion slerp (damping 0.05 normalized to 60 FPS)
    const slerpAlpha = 1 - Math.pow(1 - STAGE_CONSTANTS.SLERP_DAMPING, dt * 60);
    this.stageRig.quaternion.slerp(this.targetQuaternion, slerpAlpha);

    // 2. Wireframe Gem Cage continuous ambient rotation (0.003 rad/frame at 60 FPS)
    if (this.gemCage) {
      this.gemCage.rotation.y += STAGE_CONSTANTS.CAGE_ROTATION_PER_FRAME * (dt * 60);
    }

    // 3. '150' Monolith gentle harmonic vertical floating (±0.04)
    if (this.monolithGroup) {
      this.monolithGroup.position.y =
        Math.sin(this.elapsedSec * 1.4) * STAGE_CONSTANTS.MONOLITH_FLOAT_AMPLITUDE;
    }

    // 4. 5 Zero-Gravity Gold Coins independent harmonic float & micro-rotation
    for (let i = 0; i < this.coins.length; i += 1) {
      const c = this.coins[i];
      c.mesh.position.y =
        c.baseY + Math.sin(this.elapsedSec * c.floatSpeed + c.phase) * c.floatAmp;
      c.mesh.rotation.x += c.rotSpeed[0] * dt;
      c.mesh.rotation.y += c.rotSpeed[1] * dt;
      c.mesh.rotation.z += c.rotSpeed[2] * dt;
    }

    // 5. Render frame
    this.renderer.render(this.scene, this.camera);

    // 6. Throttled HUD telemetry update (~15Hz max to avoid DOM thrashing)
    if (now - this.lastTelemetryPushTs > 66) {
      this.lastTelemetryPushTs = now;
      this._emitTelemetry(isIdleSettled ? 'IDLE_THROTTLED' : 'ACTIVE');
    }
  }

  /**
   * Public clean disposal: cancels rAF, disconnects observers, removes listeners,
   * disposes all geometries, materials, textures, PMREM target, and WebGLRenderer.
   */
  destroy() {
    if (this.isDestroyed) return;
    this.isDestroyed = true;

    this._stopLoop();

    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
      this.intersectionObserver = null;
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }

    this.container.removeEventListener('pointermove', this._onPointerMove);
    this.container.removeEventListener('pointerleave', this._onPointerLeave);
    window.removeEventListener('resize', this._onWindowResize);
    document.removeEventListener('visibilitychange', this._onVisibilityChange);

    if (this.renderer && this.renderer.domElement) {
      this.renderer.domElement.removeEventListener('webglcontextlost', this._onContextLost);
    }

    if (this.scene) {
      const disposedGeos = new Set();
      const disposedMats = new Set();
      const disposedTex = new Set();

      const disposeMaterial = (mat) => {
        if (!mat || disposedMats.has(mat)) return;
        disposedMats.add(mat);
        const texKeys = ['map', 'bumpMap', 'roughnessMap', 'metalnessMap', 'normalMap', 'alphaMap', 'envMap'];
        for (const key of texKeys) {
          const tex = mat[key];
          if (tex && typeof tex.dispose === 'function' && !disposedTex.has(tex)) {
            disposedTex.add(tex);
            tex.dispose();
          }
        }
        if (typeof mat.dispose === 'function') {
          mat.dispose();
        }
      };

      this.scene.traverse((obj) => {
        if (obj.geometry && !disposedGeos.has(obj.geometry)) {
          disposedGeos.add(obj.geometry);
          obj.geometry.dispose();
        }
        if (Array.isArray(obj.material)) {
          obj.material.forEach(disposeMaterial);
        } else if (obj.material) {
          disposeMaterial(obj.material);
        }
      });

      this.scene.environment = null;
      this.scene.clear();
      this.scene = null;
    }

    if (this.envRenderTarget) {
      this.envRenderTarget.dispose();
      this.envRenderTarget = null;
    }

    if (this.renderer) {
      if (this.renderer.domElement && this.renderer.domElement.parentNode === this.container) {
        this.container.removeChild(this.renderer.domElement);
      }
      this.renderer.dispose();
      this.renderer = null;
    }

    this.coins = [];
    this.gemCage = null;
    this.monolithGroup = null;
    this.stageRig = null;
    this.contactShadow = null;
    this.camera = null;
    this.isInitialized = false;
  }
}

export default HeroThreeStage;
