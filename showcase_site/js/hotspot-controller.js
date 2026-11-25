/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Pure Manifest-Driven 2D Hotspot Controller (STEP 12)
 * Module: showcase_site/js/hotspot-controller.js
 *
 * Architectural Guarantees:
 *   1. 100% Render-Agnostic: Pure 2D DOM/CSS overlay (z-index: 15) positioned
 *      by percentage coordinates relative to .hero-cad-viewport. Zero WebGL or
 *      canvas render-loop coupling.
 *   2. 100% Manifest-Driven & White-Label: Zero hardcoded campaign data; all
 *      pins, previews, .PSD download links, and i18n keys come from
 *      manifest.hero_hotspots and active locale dictionaries.
 *   3. Hover-Intent & Zero Jitter: 120ms enter debounce + 200ms exit grace
 *      period so cursor glide from '+' pin -> flyout card never flickers.
 * ============================================================================
 */

const HOVER_ENTER_DELAY_MS = 120;
const HOVER_EXIT_GRACE_MS = 200;
const CARD_EDGE_PADDING_PX = 14;
const CARD_PIN_GAP_PX = 12;
const TOP_TELEMETRY_SAFE_PX = 52;

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function lookupLocaleKey(dict, key) {
  if (!dict || !key) return null;
  const parts = String(key).split('.');
  let node = dict;
  for (let i = 0; i < parts.length; i += 1) {
    if (node && Object.prototype.hasOwnProperty.call(node, parts[i])) {
      node = node[parts[i]];
    } else {
      return null;
    }
  }
  return typeof node === 'string' ? node : null;
}

function extractFilename(path) {
  if (!path) return '';
  const clean = String(path).split('?')[0].split('#')[0];
  const segments = clean.split('/');
  return segments[segments.length - 1] || '';
}

export class HotspotOverlayController {
  /**
   * @param {Object} options
   * @param {HTMLElement|string} options.container - Target container (.hero-cad-viewport)
   * @param {Array<Object>} options.hotspots - Manifest-driven hotspot definitions (manifest.hero_hotspots)
   * @param {string} [options.lang] - Active language ('ko' | 'en' | 'vi')
   * @param {Object|null} [options.locale] - Active locale dictionary from AutoBannerI18n
   * @param {number} [options.enterDelayMs] - Hover-intent enter debounce (default 120ms)
   * @param {number} [options.exitGraceMs] - Hover-intent exit grace period (default 200ms)
   */
  constructor(options = {}) {
    this.container =
      typeof options.container === 'string'
        ? document.querySelector(options.container)
        : options.container || null;

    this.hotspots = Array.isArray(options.hotspots) ? options.hotspots : [];
    this.lang = options.lang || 'ko';
    this.locale = options.locale || null;
    this.enterDelayMs =
      typeof options.enterDelayMs === 'number' ? options.enterDelayMs : HOVER_ENTER_DELAY_MS;
    this.exitGraceMs =
      typeof options.exitGraceMs === 'number' ? options.exitGraceMs : HOVER_EXIT_GRACE_MS;

    this.overlayLayer = null;
    this.entries = new Map();
    this.activeId = null;
    this.enterTimer = null;
    this.exitTimer = null;
    this.resizeObserver = null;
    this.isDestroyed = false;

    this._boundDocumentPointerDown = this._handleDocumentPointerDown.bind(this);
    this._boundDocumentKeyDown = this._handleDocumentKeyDown.bind(this);
    this._boundWindowResize = this._repositionActiveCard.bind(this);

    if (this.container) {
      this._mount();
    }
  }

  _resolveLocaleText(i18nKey, fallback = '') {
    const translated = lookupLocaleKey(this.locale, i18nKey);
    return translated !== null ? translated : fallback;
  }

  _getPinAccessibleTitle(cfg) {
    const i18n = cfg.i18n || {};
    if (cfg.type === 'existing_dom_target') {
      return this._resolveLocaleText(i18n.pin_label || i18n.title, cfg.label || cfg.badge || cfg.id);
    }
    return this._resolveLocaleText(i18n.title, (cfg.data && cfg.data.title) || cfg.badge || cfg.id);
  }

  _mount() {
    this.overlayLayer = document.createElement('div');
    this.overlayLayer.className = 'hotspot-overlay-layer';
    this.overlayLayer.setAttribute('data-hotspot-layer', 'true');

    this.hotspots.forEach((cfg) => {
      const entry = this._createHotspotEntry(cfg);
      if (entry) {
        this.entries.set(cfg.id, entry);
      }
    });

    this.container.appendChild(this.overlayLayer);

    document.addEventListener('pointerdown', this._boundDocumentPointerDown);
    document.addEventListener('keydown', this._boundDocumentKeyDown);
    window.addEventListener('resize', this._boundWindowResize, { passive: true });

    if (typeof ResizeObserver !== 'undefined') {
      this.resizeObserver = new ResizeObserver(() => {
        this._repositionActiveCard();
      });
      this.resizeObserver.observe(this.container);
    }
  }

  _createHotspotEntry(cfg) {
    const pinBtn = document.createElement('button');
    pinBtn.type = 'button';
    pinBtn.id = cfg.id;
    pinBtn.className = 'hotspot-pin';
    pinBtn.style.top = cfg.top;
    pinBtn.style.left = cfg.left;
    pinBtn.style.setProperty('--pin-color', cfg.color || '#00E5FF');
    pinBtn.setAttribute('aria-expanded', 'false');
    pinBtn.setAttribute('data-hotspot-pin', cfg.id);

    const ariaPrefix = this._resolveLocaleText('hero_hotspots.pin_aria_prefix', 'Inspect hotspot');
    const accessibleTitle = this._getPinAccessibleTitle(cfg);
    pinBtn.setAttribute('aria-label', `${ariaPrefix}: ${accessibleTitle}`);
    pinBtn.setAttribute('title', accessibleTitle);

    pinBtn.innerHTML = `
      <span class="hotspot-pin-plus" aria-hidden="true">+</span>
      ${cfg.badge ? `<span class="hotspot-pin-badge" aria-hidden="true">${escapeHtml(cfg.badge)}</span>` : ''}
    `;

    this.overlayLayer.appendChild(pinBtn);

    let cardEl = null;
    let isExternalTarget = false;

    if (cfg.type === 'existing_dom_target' && cfg.targetSelector) {
      cardEl = this.container.querySelector(cfg.targetSelector) || document.querySelector(cfg.targetSelector);
      isExternalTarget = true;
      if (cardEl) {
        cardEl.classList.add('hotspot-flyout-card');
        cardEl.setAttribute('aria-hidden', 'true');
        cardEl.setAttribute('data-hotspot-card', cfg.id);
      }
    } else if (cfg.type === 'banner_preview' && cfg.data) {
      cardEl = this._buildBannerPreviewCard(cfg);
      this.overlayLayer.appendChild(cardEl);
    }

    if (!cardEl) {
      return null;
    }

    if (cardEl.id) {
      pinBtn.setAttribute('aria-controls', cardEl.id);
    }

    const entry = {
      id: cfg.id,
      config: cfg,
      pinEl: pinBtn,
      cardEl,
      isExternalTarget,
      listeners: []
    };

    this._bindEntryEvents(entry);
    return entry;
  }

  _buildBannerPreviewCard(cfg) {
    const data = cfg.data || {};
    const i18n = cfg.i18n || {};
    const card = document.createElement('div');
    card.id = `flyout-${cfg.id}`;
    card.className = 'hotspot-flyout-card';
    card.setAttribute('role', 'region');
    card.setAttribute('aria-hidden', 'true');
    card.setAttribute('data-hotspot-card', cfg.id);
    card.style.setProperty('--pin-color', cfg.color || '#00E5FF');

    const optionId = data.option_id || data.optionId || '';
    const tagText = this._resolveLocaleText(i18n.tag, data.tag || '');
    const titleText = this._resolveLocaleText(i18n.title, data.title || '');
    const descText = this._resolveLocaleText(i18n.desc, data.desc || '');
    const zoomLabel = this._resolveLocaleText(i18n.cta_zoom, 'INSPECT DEEP ZOOM');
    const downloadLabel = this._resolveLocaleText(i18n.cta_download, 'DOWNLOAD .PSD');
    const downloadFilename = extractFilename(data.download);

    const tagI18nAttr = i18n.tag ? ` data-i18n="${escapeHtml(i18n.tag)}"` : '';
    const titleI18nAttr = i18n.title ? ` data-i18n="${escapeHtml(i18n.title)}"` : '';
    const descI18nAttr = i18n.desc ? ` data-i18n="${escapeHtml(i18n.desc)}"` : '';
    const zoomI18nAttr = i18n.cta_zoom ? ` data-i18n="${escapeHtml(i18n.cta_zoom)}"` : '';
    const downloadI18nAttr = i18n.cta_download ? ` data-i18n="${escapeHtml(i18n.cta_download)}"` : '';
    const zoomAttr = optionId ? ` data-open-zoom="${escapeHtml(optionId)}"` : '';

    card.innerHTML = `
      <div class="hotspot-card-header">
        <span class="hotspot-card-tag"${tagI18nAttr}>${escapeHtml(tagText)}</span>
        <span class="hotspot-card-badge">PIN // ${escapeHtml(cfg.badge || '01')}</span>
      </div>
      <div class="hotspot-card-thumb flyout-preview-wrapper"${zoomAttr} role="button" tabindex="0" aria-label="${escapeHtml(titleText)}">
        <img class="flyout-card-banner-img" src="${escapeHtml(data.image || '')}" alt="${escapeHtml(titleText)}" loading="lazy" />
      </div>
      <h4 class="hotspot-card-title"${titleI18nAttr}>${escapeHtml(titleText)}</h4>
      <p class="hotspot-card-desc"${descI18nAttr}>${escapeHtml(descText)}</p>
      <div class="hotspot-card-actions">
        ${
          optionId
            ? `<button type="button" class="cyber-btn emerald-toggle is-active" data-open-zoom="${escapeHtml(optionId)}">
                 <span${zoomI18nAttr}>${escapeHtml(zoomLabel)}</span>
               </button>`
            : ''
        }
        ${
          data.download
            ? `<a href="${escapeHtml(data.download)}" download="${escapeHtml(downloadFilename)}" class="cyber-btn">
                 <span${downloadI18nAttr}>${escapeHtml(downloadLabel)}</span>
               </a>`
            : ''
        }
      </div>
    `;

    const previewImg = card.querySelector('.flyout-card-banner-img');
    if (previewImg) {
      previewImg.addEventListener('load', () => {
        if (this.activeId === cfg.id) {
          this._repositionActiveCard();
        }
      });
    }

    return card;
  }

  _addListener(entry, target, eventName, handler) {
    target.addEventListener(eventName, handler);
    entry.listeners.push({ target, eventName, handler });
  }

  _bindEntryEvents(entry) {
    const { id, pinEl, cardEl } = entry;

    /* Desktop hover-intent: 120ms enter debounce, 200ms exit grace */
    this._addListener(entry, pinEl, 'mouseenter', () => {
      this._clearExitTimer();
      if (this.activeId === id) {
        return;
      }
      this._clearEnterTimer();
      this.enterTimer = window.setTimeout(() => {
        this.show(id);
      }, this.enterDelayMs);
    });

    this._addListener(entry, pinEl, 'mouseleave', () => {
      this._clearEnterTimer();
      this._scheduleHide();
    });

    this._addListener(entry, cardEl, 'mouseenter', () => {
      this._clearExitTimer();
      this._clearEnterTimer();
    });

    this._addListener(entry, cardEl, 'mouseleave', () => {
      this._scheduleHide();
    });

    /* Mobile / Touch / Direct Click toggle */
    this._addListener(entry, pinEl, 'click', (event) => {
      event.stopPropagation();
      this._clearEnterTimer();
      this._clearExitTimer();
      if (this.activeId === id) {
        this.hideAll();
      } else {
        this.show(id);
      }
    });

    /* Keyboard focus accessibility */
    this._addListener(entry, pinEl, 'focus', () => {
      this._clearExitTimer();
      this.show(id);
    });

    this._addListener(entry, cardEl, 'focusin', () => {
      this._clearExitTimer();
    });
  }

  _clearEnterTimer() {
    if (this.enterTimer !== null) {
      window.clearTimeout(this.enterTimer);
      this.enterTimer = null;
    }
  }

  _clearExitTimer() {
    if (this.exitTimer !== null) {
      window.clearTimeout(this.exitTimer);
      this.exitTimer = null;
    }
  }

  _scheduleHide() {
    this._clearExitTimer();
    this.exitTimer = window.setTimeout(() => {
      this.hideAll();
    }, this.exitGraceMs);
  }

  _handleDocumentPointerDown(event) {
    if (!this.activeId) return;
    const activeEntry = this.entries.get(this.activeId);
    if (!activeEntry) return;
    const target = event.target;
    if (activeEntry.pinEl.contains(target) || activeEntry.cardEl.contains(target)) {
      return;
    }
    this.hideAll();
  }

  _handleDocumentKeyDown(event) {
    if (event.key === 'Escape' && this.activeId) {
      this.hideAll();
    }
  }

  _repositionActiveCard() {
    if (!this.activeId) return;
    const entry = this.entries.get(this.activeId);
    if (entry) {
      this._positionCard(entry);
    }
  }

  /**
   * Auto-position flyout card adjacent to its anchor pin while respecting
   * .hero-cad-viewport boundaries (flips left/right and above/beside).
   */
  _positionCard(entry) {
    if (!this.container || !entry || !entry.cardEl || !entry.pinEl) return;

    const containerWidth = this.container.clientWidth;
    const containerHeight = this.container.clientHeight;
    if (containerWidth <= 0 || containerHeight <= 0) return;

    const card = entry.cardEl;
    const pad = CARD_EDGE_PADDING_PX;
    const gap = CARD_PIN_GAP_PX;
    const topSafe = Math.min(TOP_TELEMETRY_SAFE_PX, containerHeight * 0.14);

    const pinX = (parseFloat(entry.config.left) / 100) * containerWidth;
    const pinY = (parseFloat(entry.config.top) / 100) * containerHeight;
    const pinRadius = (entry.pinEl.offsetWidth || 32) / 2;

    const cardWidth = Math.min(card.offsetWidth || 360, containerWidth - pad * 2);
    const cardHeight = Math.min(card.offsetHeight || 280, containerHeight - pad * 2);

    let left = pad;
    let top = topSafe;

    if (containerWidth < 640) {
      /* Compact mobile: center horizontally and flip above/below pin */
      left = Math.max(pad, (containerWidth - cardWidth) / 2);
      const spaceAbove = pinY - pinRadius - gap - topSafe;
      const spaceBelow = containerHeight - pad - (pinY + pinRadius + gap);
      if (spaceAbove >= cardHeight || spaceAbove >= spaceBelow) {
        top = Math.max(pad, pinY - pinRadius - gap - cardHeight);
      } else {
        top = Math.min(containerHeight - cardHeight - pad, pinY + pinRadius + gap);
      }
    } else {
      const preferAbove = parseFloat(entry.config.top) >= 65;

      if (preferAbove && pinY - pinRadius - gap - cardHeight >= topSafe) {
        /* Bottom-center pin (e.g. pin-spec at 75%, 50%): open cleanly above pin */
        left = Math.max(pad, Math.min(containerWidth - cardWidth - pad, pinX - cardWidth / 2));
        top = Math.max(topSafe, pinY - pinRadius - gap - cardHeight);
      } else {
        /* Side placement: open right if room, otherwise flip left */
        const fitsRight = pinX + pinRadius + gap + cardWidth <= containerWidth - pad;
        const fitsLeft = pinX - pinRadius - gap - cardWidth >= pad;

        if (fitsRight) {
          left = pinX + pinRadius + gap;
        } else if (fitsLeft) {
          left = pinX - pinRadius - gap - cardWidth;
        } else {
          left = Math.max(pad, Math.min(containerWidth - cardWidth - pad, pinX - cardWidth / 2));
        }

        const idealTop = pinY - cardHeight * 0.42;
        top = Math.max(topSafe, Math.min(containerHeight - cardHeight - pad, idealTop));
      }
    }

    card.style.left = `${Math.round(left)}px`;
    card.style.top = `${Math.round(top)}px`;
    card.style.right = 'auto';
    card.style.bottom = 'auto';
  }

  show(id) {
    if (this.isDestroyed) return;
    const nextEntry = this.entries.get(id);
    if (!nextEntry) return;

    if (this.activeId && this.activeId !== id) {
      this._deactivateEntry(this.entries.get(this.activeId));
    }

    this._positionCard(nextEntry);
    nextEntry.pinEl.classList.add('is-active');
    nextEntry.pinEl.setAttribute('aria-expanded', 'true');
    nextEntry.cardEl.classList.add('is-active');
    nextEntry.cardEl.setAttribute('aria-hidden', 'false');
    this.activeId = id;
  }

  _deactivateEntry(entry) {
    if (!entry) return;
    entry.pinEl.classList.remove('is-active');
    entry.pinEl.setAttribute('aria-expanded', 'false');
    entry.cardEl.classList.remove('is-active');
    entry.cardEl.setAttribute('aria-hidden', 'true');
  }

  hideAll() {
    this._clearEnterTimer();
    this._clearExitTimer();
    if (!this.activeId) return;
    this._deactivateEntry(this.entries.get(this.activeId));
    this.activeId = null;
  }

  /**
   * Synchronize flyout text nodes & pin ARIA attributes in-place across KO / EN / VI
   * without recreating DOM pins or touching WebGL.
   */
  setLocale(locale, lang) {
    if (lang) {
      this.lang = lang;
    }
    if (locale) {
      this.locale = locale;
    }

    const ariaPrefix = this._resolveLocaleText('hero_hotspots.pin_aria_prefix', 'Inspect hotspot');

    this.entries.forEach((entry) => {
      const accessibleTitle = this._getPinAccessibleTitle(entry.config);
      entry.pinEl.setAttribute('aria-label', `${ariaPrefix}: ${accessibleTitle}`);
      entry.pinEl.setAttribute('title', accessibleTitle);

      if (!entry.isExternalTarget && entry.cardEl) {
        entry.cardEl.querySelectorAll('[data-i18n]').forEach((el) => {
          const key = el.getAttribute('data-i18n');
          const translated = lookupLocaleKey(this.locale, key);
          if (translated !== null) {
            el.textContent = translated;
          }
        });

        const thumb = entry.cardEl.querySelector('.hotspot-card-thumb');
        if (thumb) {
          thumb.setAttribute('aria-label', accessibleTitle);
          const img = thumb.querySelector('img');
          if (img) img.setAttribute('alt', accessibleTitle);
        }
      }
    });

    this._repositionActiveCard();
  }

  destroy() {
    if (this.isDestroyed) return;
    this.isDestroyed = true;

    this.hideAll();

    document.removeEventListener('pointerdown', this._boundDocumentPointerDown);
    document.removeEventListener('keydown', this._boundDocumentKeyDown);
    window.removeEventListener('resize', this._boundWindowResize);

    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }

    this.entries.forEach((entry) => {
      entry.listeners.forEach(({ target, eventName, handler }) => {
        target.removeEventListener(eventName, handler);
      });
      entry.listeners = [];
    });
    this.entries.clear();

    if (this.overlayLayer && this.overlayLayer.parentNode) {
      this.overlayLayer.parentNode.removeChild(this.overlayLayer);
    }
    this.overlayLayer = null;
  }
}

export default HotspotOverlayController;
