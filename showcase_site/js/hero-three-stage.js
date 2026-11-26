/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Pure CAD Anatomy in High-Security Bank Vault
 * Module: showcase_site/js/hero-three-stage.js
 * Aesthetic: Pure 1px Vector CAD Engineering Diagram (White & Red Only, Zero Gold)
 *   - Assembly 1: High-Security Bank Vault Outer Frame (#FFFFFF), Rotary Combination Dial
 *                 (36-degree index ticks, frame * 0.04) & 4 Sliding Deadbolt Pistons
 *   - Assembly 2: Numeral '150' Pure Line-Art Ribbed Skeleton (#FF1744 / #E2E8F0, thresholdAngle: 36)
 *   - Assembly 3: Localized Meritz Partners 3D Telemetry Callout Badges (#00E5FF / #FFFFFF)
 *   - Locked 3D Isometric Pitch (rotateXDeg = 28), 100% Transparent Background
 *   - Dynamic Exploded View Math (dispersionAmount clamped [0.0, 0.12])
 * ============================================================================
 */

const THREE_CDN_URLS = Object.freeze([
  'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js',
  'https://unpkg.com/three@0.160.0/build/three.module.js'
]);

const CAD_COLORS = Object.freeze({
  CRIMSON_PRIMARY: 0xff1744,   // Technical Laser Crimson Red (Numeral '150' Outlines)
  CRIMSON_SECONDARY: 0xff2e4f, // Technical Laser Crimson Red (Rear Contours)
  ELECTRIC_COBALT: 0x5322ff,   // Electric Cobalt (Vault Wireframe Cage & Structural Trim)
  TITANIUM_WHITE: 0xffffff,    // Cold Titanium Technical White (Vault Chassis & Dial)
  TITANIUM_STEEL: 0xe2e8f0,    // Cold Titanium Technical White (Internal Ribs & Armor)
  ACID_VOLT: 0xedff57,         // Acid Lime / Volt (Telemetry Accents & Sensor Pins)
  LASER_CYAN: 0x00e5ff         // Secondary Sensor Reference
});

const STAGE_CONSTANTS = Object.freeze({
  FOV_DEG: 42,
  NEAR: 0.1,
  FAR: 1000,
  CAMERA_Z: 4.8,
  LOCKED_ROTATE_X_DEG: 28,
  MAX_YAW_DEG: 18,
  SLERP_DAMPING: 0.05,
  MONOLITH_FLOAT_AMPLITUDE: 0.032,
  DISPERSION_MIN: 0.0,
  DISPERSION_MAX: 0.12,
  // Converts CAD millimeter-scale exploded offsets (220 / 200 / 180) into normalized stage units
  EXPLODE_UNIT_SCALE: 0.004,
  EDGE_THRESHOLD_ANGLE: 36,
  IDLE_SETTLE_MS: 3000,
  IDLE_QUAT_EPSILON: 0.0006,
  IDLE_FRAME_INTERVAL_MS: 66 // ~15 FPS low-power ambient drift after 3s idle
});

let cachedThreePromise = null;

/**
 * Dynamically load Three.js r160 ES module from CDN with secondary fallback.
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
  const rIn = 0.16;
  hole.absarc(cx, yTop, rIn, Math.PI, 0, true);
  hole.lineTo(cx + rIn, yBot);
  hole.absarc(cx, yBot, rIn, 0, Math.PI, true);
  hole.lineTo(cx - rIn, yTop);
  s.holes.push(hole);

  return s;
}

/**
 * Helper: build a THREE.LineSegments from a flat array of [x1,y1,z1, x2,y2,z2, ...]
 */
function createSegmentsFromArray(THREE, coords, material) {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(coords, 3));
  return new THREE.LineSegments(geo, material);
}

/**
 * Helper: create a 2D closed contour polyline at a given Z plane from a THREE.Shape
 */
function createContourLineSegments(THREE, shape, zOffset, curveSegments, material, offsetX = 0, offsetY = 0) {
  const coords = [];
  const extracted = shape.extractPoints(curveSegments);

  const pushLoop = (pts) => {
    if (!pts || pts.length < 2) return;
    for (let i = 0; i < pts.length; i += 1) {
      const a = pts[i];
      const b = pts[(i + 1) % pts.length];
      coords.push(
        a.x - offsetX, a.y - offsetY, zOffset,
        b.x - offsetX, b.y - offsetY, zOffset
      );
    }
  };

  pushLoop(extracted.shape);
  if (Array.isArray(extracted.holes)) {
    for (const holePts of extracted.holes) {
      pushLoop(holePts);
    }
  }

  return createSegmentsFromArray(THREE, coords, material);
}

/**
 * Helper: compute horizontal scanline intersections with a 2D polygon (plus holes)
 * to place equidistant 1px aircraft-wing-style transverse reinforcing ribs cleanly inside a digit.
 */
function computeScanlineSegments(outerPts, holePolys, y) {
  const xs = [];
  const intersectPoly = (pts) => {
    const n = pts.length;
    for (let i = 0; i < n; i += 1) {
      const a = pts[i];
      const b = pts[(i + 1) % n];
      if ((a.y <= y && b.y > y) || (b.y <= y && a.y > y)) {
        const t = (y - a.y) / (b.y - a.y);
        xs.push(a.x + t * (b.x - a.x));
      }
    }
  };

  intersectPoly(outerPts);
  for (const hole of holePolys) {
    intersectPoly(hole);
  }

  xs.sort((a, b) => a - b);
  const spans = [];
  for (let i = 0; i + 1 < xs.length; i += 2) {
    const xStart = xs[i];
    const xEnd = xs[i + 1];
    if (xEnd - xStart > 0.03) {
      spans.push([xStart, xEnd]);
    }
  }
  return spans;
}

/**
 * Assembly 2 helper: Build internal transverse CAD reinforcing ribs (#E2E8F0)
 * spaced like structural aircraft stringers, plus perimeter table for laser tick sweep.
 */
function buildRibbedSkeletonAndPerimeter(THREE, shape, depth, offsetX, offsetY, steelMat) {
  const extracted = shape.extractPoints(32);
  const outerPts = extracted.shape.map((p) => ({ x: p.x - offsetX, y: p.y - offsetY }));
  const holePolys = (extracted.holes || []).map((h) =>
    h.map((p) => ({ x: p.x - offsetX, y: p.y - offsetY }))
  );

  const halfD = depth * 0.5;
  const coords = [];
  const ribCount = 11;
  const yMin = 0.06;
  const yMax = 0.98;

  for (let r = 0; r < ribCount; r += 1) {
    const y = yMin + (r / (ribCount - 1)) * (yMax - yMin);
    const spans = computeScanlineSegments(outerPts, holePolys, y);

    for (const [x0, x1] of spans) {
      const inset = Math.min(0.014, (x1 - x0) * 0.12);
      const a = x0 + inset;
      const b = x1 - inset;
      if (b <= a) continue;

      // Front & rear transverse structural ribs
      coords.push(a, y, halfD * 0.72, b, y, halfD * 0.72);
      coords.push(a, y, -halfD * 0.72, b, y, -halfD * 0.72);

      // Cross-depth aircraft-stringer diagonal truss struts
      const midX = (a + b) * 0.5;
      coords.push(a, y, halfD * 0.72, midX, y, -halfD * 0.72);
      coords.push(midX, y, -halfD * 0.72, b, y, halfD * 0.72);
    }
  }

  const ribLines = createSegmentsFromArray(THREE, coords, steelMat);

  // Cumulative arc-length perimeter table for deterministic cyan laser tick sweep
  const perimeterPts = [];
  const cumLen = [0];
  let totalLen = 0;
  for (let i = 0; i < outerPts.length; i += 1) {
    const curr = outerPts[i];
    const next = outerPts[(i + 1) % outerPts.length];
    perimeterPts.push(curr);
    totalLen += Math.hypot(next.x - curr.x, next.y - curr.y);
    cumLen.push(totalLen);
  }

  return {
    ribLines,
    perimeter: {
      points: perimeterPts,
      cumLen,
      totalLen: Math.max(totalLen, 0.001)
    }
  };
}

/**
 * Sample a point along a closed 2D perimeter at arc-length distance `dist`
 */
function samplePerimeterAt(perimeter, dist) {
  const { points, cumLen, totalLen } = perimeter;
  const d = ((dist % totalLen) + totalLen) % totalLen;
  let idx = 0;
  for (let i = 0; i < points.length; i += 1) {
    if (d >= cumLen[i] && d <= cumLen[i + 1]) {
      idx = i;
      break;
    }
  }
  const a = points[idx];
  const b = points[(idx + 1) % points.length];
  const segLen = Math.max(cumLen[idx + 1] - cumLen[idx], 1e-6);
  const t = (d - cumLen[idx]) / segLen;
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t
  };
}

/**
 * Assembly 1 helper: Build CAD Rotary Combination Dial (circular disc with 36-degree index ticks)
 */
function createRotaryCombinationDial(THREE, whiteMat, steelMat, cyanMat) {
  const dialGroup = new THREE.Group();
  const rOuter = 0.21;
  const rMid = 0.165;
  const rInner = 0.068;
  const zDepth = 0.045;
  const ringSegs = 40;

  const whiteCoords = [];
  const steelCoords = [];
  const cyanCoords = [];

  // Outer & inner concentric rings (front + rear bezel)
  for (let i = 0; i < ringSegs; i += 1) {
    const a1 = (i / ringSegs) * Math.PI * 2;
    const a2 = ((i + 1) / ringSegs) * Math.PI * 2;
    const c1 = Math.cos(a1);
    const s1 = Math.sin(a1);
    const c2 = Math.cos(a2);
    const s2 = Math.sin(a2);

    // Front outer ring
    whiteCoords.push(c1 * rOuter, s1 * rOuter, zDepth, c2 * rOuter, s2 * rOuter, zDepth);
    // Rear outer ring
    steelCoords.push(c1 * rOuter, s1 * rOuter, 0, c2 * rOuter, s2 * rOuter, 0);
    // Inner hub ring
    whiteCoords.push(c1 * rInner, s1 * rInner, zDepth, c2 * rInner, s2 * rInner, zDepth);
  }

  // 36-degree index ticks (10 major index divisions around 360 deg) + minor 12-deg ticks
  for (let deg = 0; deg < 360; deg += 12) {
    const rad = (deg * Math.PI) / 180;
    const isMajor = deg % 36 === 0;
    const rStart = isMajor ? rMid - 0.032 : rMid;
    const rEnd = rOuter;
    const target = isMajor ? whiteCoords : steelCoords;
    target.push(
      Math.cos(rad) * rStart, Math.sin(rad) * rStart, zDepth,
      Math.cos(rad) * rEnd, Math.sin(rad) * rEnd, zDepth
    );
    if (isMajor) {
      // Knurled drum depth tie
      steelCoords.push(
        Math.cos(rad) * rOuter, Math.sin(rad) * rOuter, zDepth,
        Math.cos(rad) * rOuter, Math.sin(rad) * rOuter, 0
      );
    }
  }

  // 3 heavy-duty vault handle spokes
  for (let s = 0; s < 3; s += 1) {
    const a = (s / 3) * Math.PI * 2;
    whiteCoords.push(
      Math.cos(a) * rInner, Math.sin(a) * rInner, zDepth,
      Math.cos(a) * (rMid - 0.035), Math.sin(a) * (rMid - 0.035), zDepth
    );
  }

  // Cyan index pointer & center sensor reticle
  cyanCoords.push(
    0, rOuter + 0.015, zDepth, 0, rOuter + 0.055, zDepth,
    -0.025, 0, zDepth, 0.025, 0, zDepth,
    0, -0.025, zDepth, 0, 0.025, zDepth
  );

  dialGroup.add(createSegmentsFromArray(THREE, whiteCoords, whiteMat));
  dialGroup.add(createSegmentsFromArray(THREE, steelCoords, steelMat));
  dialGroup.add(createSegmentsFromArray(THREE, cyanCoords, cyanMat));
  return dialGroup;
}

/**
 * Assembly 1 helper: Build a heavy-duty horizontal sliding Deadbolt Piston (#FFFFFF / #E2E8F0 + #00E5FF pin)
 */
function createDeadboltPiston(THREE, sideSign, whiteMat, steelMat, cyanMat) {
  const boltGroup = new THREE.Group();
  const len = 0.34;
  const h = 0.075;
  const d = 0.075;

  // Main bolt shaft wireframe box
  const shaftGeo = new THREE.BoxGeometry(len, h, d);
  const shaftEdges = new THREE.EdgesGeometry(shaftGeo, 1);
  boltGroup.add(new THREE.LineSegments(shaftEdges, whiteMat));
  shaftGeo.dispose();

  // Locking collar & machined hydraulic grooves
  const collarX = -sideSign * (len * 0.32);
  const collarGeo = new THREE.BoxGeometry(0.06, h * 1.45, d * 1.45);
  const collarEdges = new THREE.EdgesGeometry(collarGeo, 1);
  const collarMesh = new THREE.LineSegments(collarEdges, steelMat);
  collarMesh.position.x = collarX;
  boltGroup.add(collarMesh);
  collarGeo.dispose();

  // Sensor micro-node at bolt tip
  const tipX = sideSign * (len * 0.5 + 0.025);
  const r = 0.018;
  const cyanCoords = [
    tipX, r, 0, tipX + r, 0, 0,
    tipX + r, 0, 0, tipX, -r, 0,
    tipX, -r, 0, tipX - r, 0, 0,
    tipX - r, 0, 0, tipX, r, 0
  ];
  boltGroup.add(createSegmentsFromArray(THREE, cyanCoords, cyanMat));

  return boltGroup;
}

/**
 * Assembly 3: Create a crisp 1px CAD telemetry callout badge (Sprite + leader line + diamond node)
 * Supports Korean + English JetBrains Mono / sans technical typography with zero overlap.
 */
function createTelemetryCalloutPin(THREE, anchorPos, labelPos, text, cyanMat, whiteMat) {
  const group = new THREE.Group();

  const r = 0.026;
  const [ax, ay, az] = anchorPos;
  const [lx, ly, lz] = labelPos;
  const elbowX = ax + (lx - ax) * 0.52;
  const elbowY = ly;

  const leaderCoords = [
    // Cyan diamond sensor node
    ax, ay + r, az, ax + r, ay, az,
    ax + r, ay, az, ax, ay - r, az,
    ax, ay - r, az, ax - r, ay, az,
    ax - r, ay, az, ax, ay + r, az,
    // Crisp CAD elbow leader line
    ax, ay, az, elbowX, elbowY, lz,
    elbowX, elbowY, lz, lx, ly, lz
  ];
  group.add(createSegmentsFromArray(THREE, leaderCoords, cyanMat));

  // White technical registration tick at elbow
  const tickCoords = [
    elbowX - 0.024, elbowY, lz, elbowX + 0.024, elbowY, lz
  ];
  group.add(createSegmentsFromArray(THREE, tickCoords, whiteMat));

  // Transparent 1px vector-style technical label sprite (680x96 for crisp Korean/KRW legibility)
  const canvas = document.createElement('canvas');
  canvas.width = 680;
  canvas.height = 96;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1px hairline CAD border (Electric Cobalt + Acid Lime corner brackets, zero opaque fill)
    ctx.strokeStyle = 'rgba(83, 34, 255, 0.82)';
    ctx.lineWidth = 2;
    ctx.strokeRect(4, 14, canvas.width - 8, canvas.height - 28);

    ctx.strokeStyle = 'rgba(237, 255, 87, 0.98)';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(4, 32); ctx.lineTo(4, 14); ctx.lineTo(26, 14);
    ctx.moveTo(canvas.width - 26, canvas.height - 14);
    ctx.lineTo(canvas.width - 4, canvas.height - 14);
    ctx.lineTo(canvas.width - 4, canvas.height - 32);
    ctx.stroke();

    // Monospace + Korean fallback typography
    ctx.font = '600 25px "JetBrains Mono", "Pretendard", "Apple SD Gothic Neo", ui-monospace, monospace';
    ctx.fillStyle = '#FFFFFF';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'center';
    ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 1);
  }

  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  const spriteMat = new THREE.SpriteMaterial({
    map: tex,
    transparent: true,
    depthWrite: false
  });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(1.18, 0.166, 1);

  const alignRight = lx >= ax ? 1 : -1;
  sprite.position.set(lx + alignRight * 0.6, ly, lz);
  group.add(sprite);

  return group;
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
   * @param {number} [options.dispersionAmount] - Optional initial exploded view dispersion [0.0, 0.12]
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

    this.stageRig = null;
    this.monolithGroup = null;

    // Bank Vault & Exploded-View Assembly Handles
    this.vaultDoorGroup = null;
    this.vaultRearPlateGroup = null;
    this.vaultChassisGroup = null;
    this.rotaryDial = null;
    this.deadbolts = [];
    this.laserSweeps = [];
    this.calloutPins = [];

    // Deterministic animation & exploded view state
    this.frame = 0;
    this.dispersionAmount =
      typeof options.dispersionAmount === 'number'
        ? Math.max(STAGE_CONSTANTS.DISPERSION_MIN, Math.min(STAGE_CONSTANTS.DISPERSION_MAX, options.dispersionAmount))
        : 0.0;
    this.targetDispersionAmount = this.dispersionAmount;
    this.rotateXDeg = STAGE_CONSTANTS.LOCKED_ROTATE_X_DEG;

    // Reusable math objects (zero per-frame allocations)
    this.targetEuler = null;
    this.targetQuaternion = null;
    this.currentEuler = null;

    // Runtime state
    this.isInitialized = false;
    this.isDestroyed = false;
    this.isVisible = true;
    this.isTabVisible = true;
    this.isExternallyPaused = false;
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
   * Public API: update exploded-view dispersion amount (clamped strictly to [0.0, 0.12]).
   */
  setDispersion(amount) {
    const val = Number(amount);
    if (!Number.isFinite(val)) return;
    this.targetDispersionAmount = Math.max(
      STAGE_CONSTANTS.DISPERSION_MIN,
      Math.min(STAGE_CONSTANTS.DISPERSION_MAX, val)
    );
    this.lastInteractionTs = performance.now();
  }

  /**
   * Async initialization: loads Three.js r160, builds pure CAD Vault + '150' scene, binds observers.
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

    // 1. Scene & Camera (100% transparent background)
    this.scene = new THREE.Scene();
    this.scene.background = null;

    this.camera = new THREE.PerspectiveCamera(
      STAGE_CONSTANTS.FOV_DEG,
      width / height,
      STAGE_CONSTANTS.NEAR,
      STAGE_CONSTANTS.FAR
    );
    this._applyCameraProjection(width, height);
    this.camera.lookAt(0, 0, 0);

    // 2. Renderer (Pure vector line-art, transparent canvas, zero shadow maps)
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    this.renderer.shadowMap.enabled = false;
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.setPixelRatio(dpr);
    this.renderer.setSize(width, height, false);
    this._lastWidth = width;
    this._lastHeight = height;
    this._lastDpr = dpr;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    // 100% transparent container background
    this.container.style.backgroundColor = 'transparent';

    const domEl = this.renderer.domElement;
    domEl.style.width = '100%';
    domEl.style.height = '100%';
    domEl.style.display = 'block';
    domEl.style.backgroundColor = 'transparent';
    domEl.setAttribute('aria-label', "Interactive 3D Pure CAD Anatomy '150' in High-Security Bank Vault");

    this.container.innerHTML = '';
    this.container.appendChild(domEl);

    // 3. Pre-allocated Quaternion / Euler math objects (locked 28 deg isometric pitch)
    const lockedPitchRad = THREE.MathUtils.degToRad(this.rotateXDeg);
    this.targetEuler = new THREE.Euler(lockedPitchRad, 0, 0, 'YXZ');
    this.targetQuaternion = new THREE.Quaternion().setFromEuler(this.targetEuler);
    this.currentEuler = new THREE.Euler(lockedPitchRad, 0, 0, 'YXZ');

    // 4. Build Stage Rig, Bank Vault Outer Frame, Numeral '150' Skeleton & Telemetry Badges
    this.stageRig = new THREE.Group();
    this.stageRig.quaternion.copy(this.targetQuaternion);
    this.scene.add(this.stageRig);

    this._buildHighSecurityBankVault();
    this._buildNumeral150CadAnatomy();
    this._applyExplodedDispersion();

    // 5. Bind Interaction, ResizeObserver, IntersectionObserver & Tab Visibility
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

  /**
   * ASSEMBLY 1: Minimalist High-Security Bank Vault Outer Frame (Pure 12-Edge Box + 8 Corner Brackets)
   * - Zero interior diagonal cross-lines, zero X-bracing, completely hollow transparent faces
   * - Subdued white vault cage (opacity: 0.4, depthWrite: false) so red '150' remains dominant
   * - Rotary Combination Dial (top-right, 36-deg ticks, frame * 0.04) & 4 Sliding Deadbolt Pistons
   */
  _buildHighSecurityBankVault() {
    const THREE = this.THREE;

    const vaultCageMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.ELECTRIC_COBALT,
      transparent: true,
      opacity: 0.72,
      depthWrite: false
    });

    const bracketMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.ELECTRIC_COBALT,
      transparent: true,
      opacity: 0.85,
      depthWrite: false
    });

    const steelMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.TITANIUM_STEEL,
      transparent: true,
      opacity: 0.42,
      depthWrite: false
    });

    const cyanMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.ACID_VOLT,
      transparent: true,
      opacity: 0.95,
      depthWrite: false
    });

    const w = 2.74;
    const h = 1.54;
    const d = 0.94;
    const hw = w * 0.5;
    const hh = h * 0.5;
    const hd = d * 0.5;

    // 1. Pure Minimalist 12-Edge Wireframe Box (BoxGeometry + EdgesGeometry, zero interior clutter)
    this.vaultChassisGroup = new THREE.Group();
    const boxGeo = new THREE.BoxGeometry(w, h, d);
    const boxEdges = new THREE.EdgesGeometry(boxGeo, 1);
    this.vaultChassisGroup.add(new THREE.LineSegments(boxEdges, vaultCageMat));
    boxGeo.dispose();
    this.stageRig.add(this.vaultChassisGroup);

    // Helper: 1px L-shaped chamfered reinforced corner brackets at the 4 corners of a Z-plane
    const buildPlaneCornerBrackets = (zDir) => {
      const arm = 0.14;
      const zArm = 0.11;
      const pad = 0.018;
      const coords = [];
      for (const sx of [-1, 1]) {
        for (const sy of [-1, 1]) {
          const cx = sx * (hw + pad);
          const cy = sy * (hh + pad);
          // L-bracket along X and Y + short Z-return lip
          coords.push(
            cx, cy, 0, cx - sx * arm, cy, 0,
            cx, cy, 0, cx, cy - sy * arm, 0,
            cx, cy, 0, cx, cy, -zDir * zArm
          );
        }
      }
      return createSegmentsFromArray(THREE, coords, bracketMat);
    };

    // 2. Vault Front Reinforced Corner Brackets & Rotary Combination Dial (slides +Z * 220 * dispersionAmount)
    this.vaultDoorGroup = new THREE.Group();
    this.vaultDoorGroup.position.z = hd;
    this.vaultDoorGroup.add(buildPlaneCornerBrackets(1));

    // CAD Rotary Combination Dial positioned at top-right corner of vault front plane
    this.rotaryDial = createRotaryCombinationDial(THREE, bracketMat, steelMat, cyanMat);
    this.rotaryDial.position.set(hw - 0.34, hh - 0.32, 0.02);
    this.vaultDoorGroup.add(this.rotaryDial);

    this.stageRig.add(this.vaultDoorGroup);

    // 3. Vault Rear Reinforced Corner Brackets (slides -Z * 200 * dispersionAmount, center completely hollow)
    this.vaultRearPlateGroup = new THREE.Group();
    this.vaultRearPlateGroup.position.z = -hd;
    this.vaultRearPlateGroup.add(buildPlaneCornerBrackets(-1));
    this.stageRig.add(this.vaultRearPlateGroup);

    // 4. Four Heavy-Duty Horizontal Sliding Deadbolt Pistons at the corners (retract ±X * 180 * dispersionAmount)
    const boltY = hh - 0.24;
    const boltX = hw + 0.04;
    const boltSpecs = [
      { x: -boltX, y: boltY, sideSign: -1 },
      { x: -boltX, y: -boltY, sideSign: -1 },
      { x: boltX, y: boltY, sideSign: 1 },
      { x: boltX, y: -boltY, sideSign: 1 }
    ];

    this.deadbolts = boltSpecs.map((spec) => {
      const bolt = createDeadboltPiston(THREE, spec.sideSign, bracketMat, steelMat, cyanMat);
      bolt.position.set(spec.x, spec.y, 0.08);
      this.stageRig.add(bolt);
      return {
        obj: bolt,
        baseX: spec.x,
        sideSign: spec.sideSign
      };
    });
  }

  /**
   * ASSEMBLY 2 & 3: Numeral '150' Pure Line-Art Ribbed Skeleton (#FF1744 / #E2E8F0)
   * + Localized Meritz Partners 3D Telemetry Callout Badges
   */
  _buildNumeral150CadAnatomy() {
    const THREE = this.THREE;

    const depth = 0.34;
    const halfDepth = depth * 0.5;
    const extrudeSettings = {
      depth,
      bevelEnabled: false,
      curveSegments: 28
    };

    // Pure 1px CAD LineBasicMaterials (Bold dominant Red #FF1744 outlines, White ribs, Cyan accents)
    const crimsonFrontMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.CRIMSON_PRIMARY,
      transparent: false,
      opacity: 1.0
    });

    const crimsonRearMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.CRIMSON_SECONDARY,
      transparent: true,
      opacity: 0.72
    });

    const crimsonEdgeMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.CRIMSON_PRIMARY,
      transparent: false,
      opacity: 1.0
    });

    const whiteRibMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.TITANIUM_STEEL,
      transparent: true,
      opacity: 0.58
    });

    const whiteMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.TITANIUM_WHITE,
      transparent: true,
      opacity: 0.85
    });

    const cyanAccentMat = new THREE.LineBasicMaterial({
      color: CAD_COLORS.ACID_VOLT,
      transparent: true,
      opacity: 0.96
    });

    const glyphSpecs = [
      { id: '1', shape: createDigitOneShape(THREE), gapAfter: 0.16 },
      { id: '5', shape: createDigitFiveShape(THREE), gapAfter: 0.15 },
      { id: '0', shape: createDigitZeroShape(THREE), gapAfter: 0.0 }
    ];

    this.monolithGroup = new THREE.Group();
    const digitGroups = [];
    const digitBounds = {};
    let cursorX = 0;

    for (const spec of glyphSpecs) {
      const tempGeo = new THREE.ExtrudeGeometry(spec.shape, extrudeSettings);
      tempGeo.computeBoundingBox();
      const box = tempGeo.boundingBox;
      const offsetX = box.min.x;
      const offsetY = box.min.y;
      const glyphWidth = box.max.x - box.min.x;
      const glyphHeight = box.max.y - box.min.y;

      tempGeo.translate(-offsetX, -offsetY, -halfDepth);

      const digitGroup = new THREE.Group();
      digitGroup.position.x = cursorX;

      // Crisp 1px laser red contour rails filtered at thresholdAngle: 36
      const edgesGeo = new THREE.EdgesGeometry(tempGeo, STAGE_CONSTANTS.EDGE_THRESHOLD_ANGLE);
      digitGroup.add(new THREE.LineSegments(edgesGeo, crimsonEdgeMat));
      tempGeo.dispose();

      // Front & rear crisp contour polylines
      digitGroup.add(
        createContourLineSegments(THREE, spec.shape, halfDepth + 0.004, 28, crimsonFrontMat, offsetX, offsetY)
      );
      digitGroup.add(
        createContourLineSegments(THREE, spec.shape, -halfDepth - 0.004, 28, crimsonRearMat, offsetX, offsetY)
      );

      // Internal transverse CAD reinforcing ribs (Cold Titanium White #E2E8F0)
      const { ribLines, perimeter } = buildRibbedSkeletonAndPerimeter(
        THREE, spec.shape, depth, offsetX, offsetY, whiteRibMat
      );
      digitGroup.add(ribLines);

      // Deterministic Cyan laser tick sweep along contour
      const sweepGeo = new THREE.BufferGeometry();
      sweepGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(6 * 3), 3));
      const sweepLine = new THREE.LineSegments(sweepGeo, cyanAccentMat);
      digitGroup.add(sweepLine);
      this.laserSweeps.push({
        line: sweepLine,
        perimeter,
        z: halfDepth + 0.012
      });

      this.monolithGroup.add(digitGroup);
      digitGroups.push(digitGroup);
      digitBounds[spec.id] = { x: cursorX, width: glyphWidth, height: glyphHeight };

      cursorX += glyphWidth + spec.gapAfter;
    }

    // Center the complete '150' assembly around exact optical origin (0, 0, 0)
    const totalBox = new THREE.Box3().setFromObject(this.monolithGroup);
    const center = new THREE.Vector3();
    totalBox.getCenter(center);
    for (const digitGroup of digitGroups) {
      digitGroup.position.x -= center.x;
      digitGroup.position.y -= center.y;
    }

    // ------------------------------------------------------------------
    // ASSEMBLY 3: Localized Project Telemetry Badges (Non-overlapping)
    // ------------------------------------------------------------------
    const b1 = digitBounds['1'];
    const b5 = digitBounds['5'];
    const b0 = digitBounds['0'];

    const pinA = createTelemetryCalloutPin(
      THREE,
      [b1.x + b1.width * 0.72 - center.x, b1.height - center.y, halfDepth],
      [b1.x - 0.12 - center.x, b1.height + 0.34 - center.y, halfDepth + 0.05],
      'MERITZ PARTNERS // 첫달 평균 수익',
      cyanAccentMat,
      whiteMat
    );

    const pinB = createTelemetryCalloutPin(
      THREE,
      [b5.x + b5.width * 0.25 - center.x, b5.height * 0.52 - center.y, halfDepth],
      [b5.x + b5.width * 0.18 - center.x, -0.34 - center.y, halfDepth + 0.05],
      'TARGET REVENUE // 150만원 [KRW]',
      cyanAccentMat,
      whiteMat
    );

    const pinC = createTelemetryCalloutPin(
      THREE,
      [b0.x + b0.width * 0.5 - center.x, b0.height * 0.5 - center.y, halfDepth],
      [b0.x + b0.width + 0.18 - center.x, b0.height + 0.34 - center.y, halfDepth + 0.05],
      'VAULT SECURITY // PASS: OPTION-02.PSD',
      cyanAccentMat,
      whiteMat
    );

    this.monolithGroup.add(pinA, pinB, pinC);
    this.calloutPins.push(pinA, pinB, pinC);

    this.monolithGroup.scale.setScalar(0.92);
    this.stageRig.add(this.monolithGroup);
  }

  /**
   * Dynamic Exploded View Math (`dispersionAmount` clamped [0.0, 0.12]):
   * - Vault Outer Door Frame & Rotary Dial: +Z * 220 * dispersionAmount
   * - Sliding Deadbolts: ±X * 180 * dispersionAmount
   * - Numeral '150' Red Core: remains floating at center origin
   * - Vault Rear Armor Plate: -Z * 200 * dispersionAmount
   */
  _applyExplodedDispersion() {
    const d = Math.max(
      STAGE_CONSTANTS.DISPERSION_MIN,
      Math.min(STAGE_CONSTANTS.DISPERSION_MAX, this.dispersionAmount)
    );
    const doorOffsetZ = 220 * d * STAGE_CONSTANTS.EXPLODE_UNIT_SCALE;
    const rearOffsetZ = 200 * d * STAGE_CONSTANTS.EXPLODE_UNIT_SCALE;
    const boltOffsetX = 180 * d * STAGE_CONSTANTS.EXPLODE_UNIT_SCALE;

    const baseHalfDepth = 0.94 * 0.5;

    if (this.vaultDoorGroup) {
      this.vaultDoorGroup.position.z = baseHalfDepth + doorOffsetZ;
    }

    if (this.vaultRearPlateGroup) {
      this.vaultRearPlateGroup.position.z = -baseHalfDepth - rearOffsetZ;
    }

    for (let i = 0; i < this.deadbolts.length; i += 1) {
      const bolt = this.deadbolts[i];
      bolt.obj.position.x = bolt.baseX + bolt.sideSign * boltOffsetX;
    }
  }

  /**
   * Deterministic per-frame updates for Rotary Combination Dial & contour laser sweeps.
   */
  _updateCadMechanisms() {
    const frame = this.frame;

    // Assembly 1: Rotary Combination Dial spinning slowly at frame * 0.04
    if (this.rotaryDial) {
      this.rotaryDial.rotation.z = -frame * 0.04;
    }

    // Assembly 2: Deterministic Cyan laser tick sweep along '1', '5', '0' contours
    for (let i = 0; i < this.laserSweeps.length; i += 1) {
      const sweep = this.laserSweeps[i];
      const { perimeter, line, z } = sweep;
      const dist = (frame * 2.0 * 0.01) % perimeter.totalLen;
      const tailDist = dist - 0.11;
      const pHead = samplePerimeterAt(perimeter, dist);
      const pTail = samplePerimeterAt(perimeter, tailDist);

      const posAttr = line.geometry.getAttribute('position');
      const arr = posAttr.array;
      const c = 0.022;

      arr[0] = pTail.x; arr[1] = pTail.y; arr[2] = z;
      arr[3] = pHead.x; arr[4] = pHead.y; arr[5] = z;
      arr[6] = pHead.x - c; arr[7] = pHead.y; arr[8] = z;
      arr[9] = pHead.x + c; arr[10] = pHead.y; arr[11] = z;
      arr[12] = pHead.x; arr[13] = pHead.y - c; arr[14] = z;
      arr[15] = pHead.x; arr[16] = pHead.y + c; arr[17] = z;

      posAttr.needsUpdate = true;
    }
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

    // Lock rotateXDeg = 28; allow smooth horizontal yaw + vault exploded dispersion on hover
    const maxYawRad = this.THREE.MathUtils.degToRad(STAGE_CONSTANTS.MAX_YAW_DEG);
    this.targetYawRad = this.THREE.MathUtils.clamp(normX * maxYawRad, -maxYawRad, maxYawRad);
    const radial = Math.min(1, Math.hypot(normX, normY));
    this.targetDispersionAmount = radial * STAGE_CONSTANTS.DISPERSION_MAX;

    this.isPointerActive = true;
    this.lastInteractionTs = performance.now();

    if (this.isVisible && this.isTabVisible && !this.rafId && !this.isReducedMotion) {
      this.lastFrameTs = performance.now();
      this._startLoop();
    }
  }

  _handlePointerLeave() {
    this.targetYawRad = 0;
    this.targetDispersionAmount = 0.0;
    this.isPointerActive = false;
    this.lastInteractionTs = performance.now();
  }

  _applyCameraProjection(width, height) {
    if (!this.camera || width <= 0 || height <= 0) return;
    const aspect = width / height;
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

  pause() {
    if (this.isDestroyed || this.isExternallyPaused) return;
    this.isExternallyPaused = true;
    this._stopLoop();
  }

  resume() {
    if (this.isDestroyed || !this.isExternallyPaused) return;
    this.isExternallyPaused = false;
    if (this.isVisible && this.isTabVisible && !this.isReducedMotion) {
      this.lastFrameTs = performance.now();
      this._startLoop();
    }
  }

  _startLoop() {
    if (this.isDestroyed || this.isExternallyPaused || this.rafId !== null) return;
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
    const pitchDeg = this.rotateXDeg;
    const yawDeg = this.THREE.MathUtils.radToDeg(this.currentEuler.y);
    this.options.onRotationUpdate({ pitchDeg, yawDeg, mode });
  }

  _tick(now) {
    if (this.isDestroyed || this.isExternallyPaused || !this.isVisible || !this.isTabVisible) {
      this.rafId = null;
      return;
    }

    this.rafId = window.requestAnimationFrame(this._animate);

    // Locked 3D Isometric Pitch: rotateXDeg = 28
    const lockedPitchRad = this.THREE.MathUtils.degToRad(this.rotateXDeg);
    this.targetEuler.set(lockedPitchRad, this.targetYawRad, 0, 'YXZ');
    this.targetQuaternion.setFromEuler(this.targetEuler);

    const quatDelta = this.stageRig.quaternion.angleTo(this.targetQuaternion);
    const isIdleSettled =
      !this.isPointerActive &&
      now - this.lastInteractionTs > STAGE_CONSTANTS.IDLE_SETTLE_MS &&
      quatDelta < STAGE_CONSTANTS.IDLE_QUAT_EPSILON;

    if (isIdleSettled && now - this.lastRenderTs < STAGE_CONSTANTS.IDLE_FRAME_INTERVAL_MS) {
      return;
    }

    const dt = Math.min(0.05, Math.max(0.001, (now - this.lastFrameTs) / 1000));
    this.lastFrameTs = now;
    this.lastRenderTs = now;
    this.elapsedSec += dt;
    this.frame += dt * 60;

    // 1. Smooth Quaternion slerp (damping 0.05 normalized to 60 FPS)
    const slerpAlpha = 1 - Math.pow(1 - STAGE_CONSTANTS.SLERP_DAMPING, dt * 60);
    this.stageRig.quaternion.slerp(this.targetQuaternion, slerpAlpha);

    // 2. Smoothly approach target dispersionAmount (clamped [0.0, 0.12])
    this.dispersionAmount += (this.targetDispersionAmount - this.dispersionAmount) * slerpAlpha;
    this._applyExplodedDispersion();

    // 3. Deterministic CAD mechanisms (rotary dial & contour laser sweeps)
    this._updateCadMechanisms();

    // 4. Numeral '150' red core remains floating at center origin (±0.032)
    if (this.monolithGroup) {
      this.monolithGroup.position.y =
        Math.sin(this.elapsedSec * 1.4) * STAGE_CONSTANTS.MONOLITH_FLOAT_AMPLITUDE;
    }

    // 5. Render frame
    this.renderer.render(this.scene, this.camera);

    // 6. Throttled HUD telemetry update (~15Hz max)
    if (now - this.lastTelemetryPushTs > 66) {
      this.lastTelemetryPushTs = now;
      this._emitTelemetry(isIdleSettled ? 'IDLE_THROTTLED' : 'ACTIVE');
    }
  }

  /**
   * Public clean disposal: cancels rAF, disconnects observers, removes listeners,
   * disposes all geometries, materials, textures, and WebGLRenderer.
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
        if (mat.map && typeof mat.map.dispose === 'function' && !disposedTex.has(mat.map)) {
          disposedTex.add(mat.map);
          mat.map.dispose();
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

      this.scene.clear();
      this.scene = null;
    }

    if (this.renderer) {
      if (this.renderer.domElement && this.renderer.domElement.parentNode === this.container) {
        this.container.removeChild(this.renderer.domElement);
      }
      this.renderer.dispose();
      this.renderer = null;
    }

    this.vaultDoorGroup = null;
    this.vaultRearPlateGroup = null;
    this.vaultChassisGroup = null;
    this.rotaryDial = null;
    this.deadbolts = [];
    this.laserSweeps = [];
    this.calloutPins = [];
    this.monolithGroup = null;
    this.stageRig = null;
    this.camera = null;
    this.isInitialized = false;
  }
}

export default HeroThreeStage;
