/**
 * ============================================================================
 * AUTO-BANNER // ENGINE — Standalone Interactive Keepsake Folder Module
 * Reusable Component: Hover Peek -> Click Fan-Out -> 3D Flip Card Telemetry
 * ============================================================================
 */
(function (global) {
  'use strict';

  const DEFAULT_I18N = Object.freeze({
    en: {
      folder_title: '11-Ratio Archival Suite',
      folder_hint_open: '[ CLICK TO FAN OUT 11 RATIOS ]',
      folder_hint_close: '[ COLLAPSE ARCHIVE ]',
      flip_hint: 'HOVER ANY CARD TO FLIP & INSPECT TELEMETRY',
      items_count_suffix: 'RATIOS',
      label_resolution: 'RESOLUTION',
      label_ratio: 'ASPECT RATIO',
      label_weight: 'FILE WEIGHT',
      label_stepping: 'ORTHOGONAL',
      label_watermark: 'AI WATERMARK',
      status_passed: 'PASSED',
      watermark_compliant: '0% COMPLIANT',
      footer_verified: 'VERIFIED'
    },
    ko: {
      folder_title: '11종 규격 아카이브 폴더',
      folder_hint_open: '[ 클릭하여 11종 규격 펼치기 ]',
      folder_hint_close: '[ 폴더 접기 ]',
      flip_hint: '카드에 마우스를 올려 기술 사양 확인',
      items_count_suffix: '종 규격',
      label_resolution: '해상도',
      label_ratio: '종횡비',
      label_weight: '파일 용량',
      label_stepping: '직교 스태핑',
      label_watermark: 'AI 워터마크',
      status_passed: '통과 (PASSED)',
      watermark_compliant: '0% 준수',
      footer_verified: '검증 완료'
    },
    vi: {
      folder_title: 'Thư Mục Lưu Trữ 11 Tỷ Lệ',
      folder_hint_open: '[ NHẤN ĐỂ XÒE 11 TỶ LỆ ]',
      folder_hint_close: '[ THU GỌN THƯ MỤC ]',
      flip_hint: 'RÊ CHUỘT VÀO THẺ ĐỂ LẬT XEM THÔNG SỐ',
      items_count_suffix: 'TỶ LỆ',
      label_resolution: 'ĐỘ PHÂN GIẢI',
      label_ratio: 'TỶ LỆ KHUNG',
      label_weight: 'DUNG LƯỢNG',
      label_stepping: 'BƯỚC TRỰC GIAO',
      label_watermark: 'WATERMARK AI',
      status_passed: 'ĐẠT (PASSED)',
      watermark_compliant: '0% TUÂN THỦ',
      footer_verified: 'ĐÃ KIỂM ĐỊNH'
    }
  });

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function derivePlatform(item) {
    if (item && item.platform) {
      return String(item.platform).toUpperCase();
    }
    const name = String((item && item.name) || '').toLowerCase();
    if (name.includes('meta') || name.includes('instagram') || name.includes('facebook')) return 'META';
    if (name.includes('kakao')) return 'KAKAO';
    if (name.includes('google')) return 'GOOGLE';
    if (name.includes('naver')) return 'NAVER';
    return 'DISPLAY';
  }

  function formatResolution(res) {
    if (!res) return '—';
    return String(res).replace(/x/i, ' × ') + ' px';
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

  class KeepsakeFolder {
    /**
     * @param {Object} config
     * @param {string|HTMLElement} config.containerSelector
     * @param {Array<Object>} config.items
     * @param {string} [config.tabLabel]
     * @param {Function} [config.resolveAssetPath]
     * @param {string} [config.lang]
     * @param {Object} [config.locale]
     */
    constructor(config = {}) {
      this.config = {
        containerSelector: config.containerSelector || '#zone-xexymix .keepsake-container',
        items: Array.isArray(config.items) ? config.items : [],
        tabLabel: config.tabLabel || 'ARCHIVE // XEXYMIX_11_RATIOS',
        resolveAssetPath:
          typeof config.resolveAssetPath === 'function'
            ? config.resolveAssetPath
            : (p) => (p && !p.startsWith('http') && !p.startsWith('./') && !p.startsWith('../') ? `./${p.replace(/^\/+/, '')}` : p || ''),
        lang: config.lang || 'ko',
        locale: config.locale || null
      };

      this.container =
        typeof this.config.containerSelector === 'string'
          ? document.querySelector(this.config.containerSelector)
          : this.config.containerSelector;

      this.isExpanded = false;
      this.rootEl = null;
      this.coverEl = null;
      this.deckEl = null;
      this.cardSlots = [];
      this.resizeObserver = null;
      this._boundHandleResize = this.computeLayout.bind(this);

      if (this.container) {
        this.render();
        this.bindEvents();
        this.computeLayout();
      }
    }

    t(subKey) {
      const fullKey = `keepsake.${subKey}`;
      const fromLocale = lookupLocaleKey(this.config.locale, fullKey);
      if (fromLocale !== null) return fromLocale;

      const lang = DEFAULT_I18N[this.config.lang] ? this.config.lang : 'en';
      return DEFAULT_I18N[lang][subKey] || DEFAULT_I18N.en[subKey] || subKey;
    }

    render() {
      const items = this.config.items;
      const total = items.length;
      const tabLabel = escapeHtml(this.config.tabLabel);

      const cardsMarkup = items
        .map((item, idx) => {
          const imgSrc = escapeHtml(this.config.resolveAssetPath(item.file));
          const platform = derivePlatform(item);
          const idLabel = item.id ? `#${escapeHtml(item.id)}` : `#${String(idx + 1).padStart(2, '0')}`;
          const name = escapeHtml(item.name || `Placement ${idx + 1}`);
          const ratio = escapeHtml(item.ratio || '—');
          const resolution = escapeHtml(formatResolution(item.resolution));
          const fileWeight = escapeHtml(item.fileWeight || '<800KB');

          /* Subtle top-5 peek fan offsets when hovering the collapsed folder */
          const peekSpread = idx < 5 ? (idx - 2) : 0;
          const peekX = idx < 5 ? `${peekSpread * 12}px` : '0px';
          const peekRot = idx < 5 ? `${peekSpread * 2.2}deg` : '0deg';

          return `
            <article
              class="keepsake-card-slot"
              data-card-index="${idx}"
              data-placement-id="${escapeHtml(item.id || idx + 1)}"
              tabindex="0"
              aria-label="${name} (${ratio}, ${resolution})"
              style="--card-index:${idx}; --peek-x:${peekX}; --peek-rot:${peekRot};"
            >
              <div class="keepsake-card-flipper">
                <!-- Front Face: 100% clean banner on dark titanium (#0D0D14), zero laser overlays -->
                <div class="keepsake-card-front">
                  <img
                    src="${imgSrc}"
                    alt="${name} — ${resolution}"
                    class="keepsake-card-img"
                    loading="lazy"
                    decoding="async"
                  />
                </div>

                <!-- Back Face: Pure JetBrains Mono technical telemetry -->
                <div class="keepsake-card-back">
                  <div class="keepsake-back-header">
                    <span class="keepsake-platform-badge" data-platform="${escapeHtml(platform)}">${escapeHtml(platform)}</span>
                    <span class="keepsake-card-id">${idLabel}</span>
                  </div>

                  <h3 class="keepsake-back-title">${name}</h3>

                  <ul class="keepsake-spec-list">
                    <li class="keepsake-spec-row">
                      <span class="keepsake-spec-key" data-i18n="keepsake.label_resolution">${escapeHtml(this.t('label_resolution'))}</span>
                      <span class="keepsake-spec-val is-cyan">${resolution}</span>
                    </li>
                    <li class="keepsake-spec-row">
                      <span class="keepsake-spec-key" data-i18n="keepsake.label_ratio">${escapeHtml(this.t('label_ratio'))}</span>
                      <span class="keepsake-spec-val">${ratio}</span>
                    </li>
                    <li class="keepsake-spec-row">
                      <span class="keepsake-spec-key" data-i18n="keepsake.label_weight">${escapeHtml(this.t('label_weight'))}</span>
                      <span class="keepsake-spec-val">${fileWeight}</span>
                    </li>
                    <li class="keepsake-spec-row">
                      <span class="keepsake-spec-key" data-i18n="keepsake.label_stepping">${escapeHtml(this.t('label_stepping'))}</span>
                      <span class="keepsake-spec-val is-emerald" data-i18n="keepsake.status_passed">${escapeHtml(this.t('status_passed'))}</span>
                    </li>
                    <li class="keepsake-spec-row">
                      <span class="keepsake-spec-key" data-i18n="keepsake.label_watermark">${escapeHtml(this.t('label_watermark'))}</span>
                      <span class="keepsake-spec-val is-emerald" data-i18n="keepsake.watermark_compliant">${escapeHtml(this.t('watermark_compliant'))}</span>
                    </li>
                  </ul>

                  <div class="keepsake-back-footer">
                    <span>sRGB // QA</span>
                    <span class="keepsake-verified-pill" data-i18n="keepsake.footer_verified">${escapeHtml(this.t('footer_verified'))}</span>
                  </div>
                </div>
              </div>
            </article>
          `;
        })
        .join('');

      this.container.innerHTML = `
        <div class="keepsake-folder ${this.isExpanded ? 'is-expanded' : ''}" data-keepsake-root>
          <div class="keepsake-folder-stage">
            <!-- Folder Backplate (Lower Pocket Cradle) -->
            <div class="keepsake-folder-back" aria-hidden="true"></div>

            <!-- Interactive Stacked / Fanned Card Deck -->
            <div class="keepsake-deck" data-keepsake-deck>
              ${cardsMarkup}
            </div>

            <!-- Clickable Folder Front Cover / Docked Header Bar -->
            <button
              type="button"
              class="keepsake-folder-cover"
              data-keepsake-cover
              aria-expanded="${String(this.isExpanded)}"
            >
              <div class="keepsake-cover-top">
                <span class="keepsake-cover-badge">
                  <span class="keepsake-tab-dot" aria-hidden="true"></span>
                  <span>${tabLabel}</span>
                </span>
                <span class="keepsake-cover-count">
                  <span>${total}</span>
                  <span data-i18n="keepsake.items_count_suffix">${escapeHtml(this.t('items_count_suffix'))}</span>
                </span>
              </div>

              <div class="keepsake-cover-body">
                <div class="keepsake-cover-title" data-i18n="keepsake.folder_title">${escapeHtml(this.t('folder_title'))}</div>
                <div class="keepsake-cover-hint" data-i18n="keepsake.folder_hint_open">${escapeHtml(this.t('folder_hint_open'))}</div>
              </div>

              <div class="keepsake-cover-footer">
                <span>4:5 ARCHIVE STACK</span>
                <span>sRGB &lt;= 800KB // 0% AI</span>
              </div>

              <span class="keepsake-cover-flip-hint" data-i18n="keepsake.flip_hint">${escapeHtml(this.t('flip_hint'))}</span>
              <span class="keepsake-cover-action-pill" data-i18n="keepsake.folder_hint_close">${escapeHtml(this.t('folder_hint_close'))}</span>
            </button>
          </div>
        </div>
      `;

      this.rootEl = this.container.querySelector('[data-keepsake-root]');
      this.coverEl = this.container.querySelector('[data-keepsake-cover]');
      this.deckEl = this.container.querySelector('[data-keepsake-deck]');
      this.cardSlots = Array.from(this.container.querySelectorAll('.keepsake-card-slot'));
    }

    bindEvents() {
      if (this.coverEl) {
        this.coverEl.addEventListener('click', () => this.toggle());
      }

      /* Support touch tap & keyboard Enter/Space flip on cards when expanded */
      this.cardSlots.forEach((slot) => {
        slot.addEventListener('click', (event) => {
          if (!this.isExpanded) return;
          event.stopPropagation();
          const isCoarse =
            typeof window !== 'undefined' &&
            window.matchMedia &&
            window.matchMedia('(pointer: coarse)').matches;
          if (isCoarse) {
            slot.classList.toggle('is-flipped');
          }
        });

        slot.addEventListener('keydown', (event) => {
          if (!this.isExpanded) return;
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            slot.classList.toggle('is-flipped');
          }
        });
      });

      if (typeof ResizeObserver !== 'undefined' && this.container) {
        this.resizeObserver = new ResizeObserver(() => {
          this.computeLayout();
        });
        this.resizeObserver.observe(this.container);
      } else if (typeof window !== 'undefined') {
        window.addEventListener('resize', this._boundHandleResize);
      }
    }

    toggle() {
      if (this.isExpanded) {
        this.collapse();
      } else {
        this.expand();
      }
    }

    expand() {
      if (!this.rootEl || this.isExpanded) return;
      this.isExpanded = true;
      this.computeLayout();
      this.rootEl.classList.add('is-expanded');
      if (this.coverEl) {
        this.coverEl.setAttribute('aria-expanded', 'true');
      }
    }

    collapse() {
      if (!this.rootEl || !this.isExpanded) return;
      this.isExpanded = false;
      this.cardSlots.forEach((slot) => slot.classList.remove('is-flipped'));
      this.rootEl.classList.remove('is-expanded');
      if (this.coverEl) {
        this.coverEl.setAttribute('aria-expanded', 'false');
      }
    }

    /**
     * Compute responsive fan-out arc coordinates for all cards without overlap
     */
    computeLayout() {
      if (!this.rootEl || !this.cardSlots.length) return;

      const stageWidth = this.container.clientWidth || 1040;
      const computedStyle = window.getComputedStyle(this.rootEl);
      const cardW = parseFloat(computedStyle.getPropertyValue('--keepsake-card-w')) || 240;
      const cardH = parseFloat(computedStyle.getPropertyValue('--keepsake-card-h')) || 300;

      const gapX = stageWidth < 600 ? 16 : 24;
      const gapY = stageWidth < 600 ? 22 : 30;
      const maxCols = Math.max(1, Math.min(4, Math.floor((stageWidth + gapX) / (cardW + gapX))));
      const total = this.cardSlots.length;
      const totalRows = Math.ceil(total / maxCols);

      /* Slot baseline is top: 52px; offset 44px clears the 64px docked expanded header */
      const topOffset = 44;

      this.cardSlots.forEach((slot, idx) => {
        const row = Math.floor(idx / maxCols);
        const col = idx % maxCols;
        const itemsInRow = row === totalRows - 1 ? total - row * maxCols : maxCols;
        const rowWidth = itemsInRow * cardW + (itemsInRow - 1) * gapX;

        /* Offset relative to center of container */
        const fanX = -rowWidth / 2 + col * (cardW + gapX) + cardW / 2;

        /* Gentle parabolic arc across each row (disabled on single-column mobile) */
        const normPos = itemsInRow > 1 ? (col / (itemsInRow - 1)) * 2 - 1 : 0;
        const arcDrop = itemsInRow > 1 ? Math.round(normPos * normPos * 14) : 0;
        const fanRot = itemsInRow > 1 ? Number((normPos * 2.2).toFixed(2)) : 0;
        const fanY = topOffset + row * (cardH + gapY) + arcDrop;

        slot.style.setProperty('--fan-x', `${Math.round(fanX)}px`);
        slot.style.setProperty('--fan-y', `${Math.round(fanY)}px`);
        slot.style.setProperty('--fan-rot', `${fanRot}deg`);
      });

      const expandedHeight = 52 + topOffset + totalRows * cardH + (totalRows - 1) * gapY + 34;
      this.rootEl.style.setProperty('--keepsake-expanded-height', `${Math.round(expandedHeight)}px`);
    }

    /**
     * Update all translatable labels in-place without resetting expanded state
     */
    setLocale(localeDict, lang) {
      this.config.locale = localeDict || this.config.locale;
      if (lang) this.config.lang = lang;
      if (!this.container) return;

      this.container.querySelectorAll('[data-i18n^="keepsake."]').forEach((el) => {
        const key = el.getAttribute('data-i18n');
        const subKey = key.replace(/^keepsake\./, '');
        el.textContent = this.t(subKey);
      });
    }

    destroy() {
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
        this.resizeObserver = null;
      }
      if (typeof window !== 'undefined') {
        window.removeEventListener('resize', this._boundHandleResize);
      }
      if (this.container) {
        this.container.innerHTML = '';
      }
    }
  }

  global.KeepsakeFolder = KeepsakeFolder;
})(window);
