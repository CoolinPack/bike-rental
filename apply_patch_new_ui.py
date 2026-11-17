import re
from pathlib import Path

ROOT = Path(__file__).parent / "frontend" / "src"

# =============================================================
# 1. theme.css — новый UI + алиасы для старых классов
# =============================================================
ui_css = r'''
/* ============================================================
   Bike Rental — UI (extracted from ui.css + aliases)
   ============================================================ */
:root {
  --bg: var(--tg-theme-secondary-bg-color, #f5f6f8);
  --card: var(--tg-theme-bg-color, #fff);
  --tx: var(--tg-theme-text-color, #101828);
  --hint: var(--tg-theme-hint-color, #667085);
  --ac: var(--tg-theme-button-color, #1d4ed8);
  --act: var(--tg-theme-button-text-color, #fff);
  --line: rgba(128, 128, 128, 0.22);
  --ok: #067647;
  --warn: #b54708;
  --bad: #b42318;
  --okb: color-mix(in srgb, var(--ok) 13%, transparent);
  --warnb: color-mix(in srgb, var(--warn) 14%, transparent);
  --badb: color-mix(in srgb, var(--bad) 13%, transparent);
  --dk: #1b2130;
  color-scheme: light;
  box-sizing: border-box;
  padding-top: env(safe-area-inset-top, 0px);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: var(--tg-theme-secondary-bg-color, #0c0f14);
    --card: var(--tg-theme-bg-color, #151a22);
    --tx: var(--tg-theme-text-color, #eaecf0);
    --hint: var(--tg-theme-hint-color, #98a2b3);
    --ac: var(--tg-theme-button-color, #6c95ff);
    --act: var(--tg-theme-button-text-color, #0c0f14);
    --ok: #47cd89;
    --warn: #fdb022;
    --bad: #f97066;
    --dk: #232a3a;
    color-scheme: dark;
  }
}

html { scroll-padding-top: env(safe-area-inset-top, 0px); }
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--tx);
  font: 15px/1.4 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    sans-serif;
  font-variant-numeric: tabular-nums;
  -webkit-font-smoothing: antialiased;
  overscroll-behavior: none;
}
#root { min-height: 100%; }

button { font: inherit; color: inherit; }

/* App container */
.app {
  max-width: 440px;
  margin: 0 auto;
  padding: 14px 16px 100px;
  min-height: 100vh;
}
.app.wide { max-width: 1040px; padding: 18px 16px 60px; }

/* h1 in pages */
h1 {
  margin: 2px 0 0;
  font-size: 22px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.cap {
  color: var(--hint);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.mut { color: var(--hint); font-size: 13px; }
.row { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.col { display: flex; flex-direction: column; gap: 8px; }

/* Segmented control */
.switch,
.seg {
  display: flex;
  background: var(--line);
  border-radius: 10px;
  padding: 3px;
  gap: 2px;
  margin-bottom: 14px;
}
.switch button,
.seg button {
  all: unset;
  flex: 1;
  text-align: center;
  padding: 8px 4px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 13.5px;
  cursor: pointer;
  transition: 0.2s;
  color: var(--hint);
}
.switch .on,
.seg .on {
  background: var(--card);
  color: var(--tx);
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.12);
}

/* Search bar */
.sb { display: flex; gap: 8px; margin: 14px 0 10px; }
.sw { position: relative; flex: 1; }
.sw input { padding-left: 38px; }
.ib {
  all: unset;
  cursor: pointer;
  width: 46px;
  height: 46px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: var(--card);
  display: grid;
  place-items: center;
  position: relative;
  transition: 0.15s;
}
.ib:hover { border-color: var(--hint); }
.ib:active { transform: scale(0.95); }
.ib.p { background: var(--ac); border-color: var(--ac); color: var(--act); }

/* Chips */
.filters {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 2px 0 10px;
}
.chip {
  all: unset;
  cursor: pointer;
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  transition: 0.15s;
}
.chip.on,
.chip.active {
  background: var(--tx);
  color: var(--bg);
  border-color: var(--tx);
}

/* Cards */
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  margin-bottom: 12px;
}

/* Buttons */
.btn {
  all: unset;
  box-sizing: border-box;
  display: block;
  width: 100%;
  text-align: center;
  cursor: pointer;
  padding: 13px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 15px;
  background: var(--ac);
  color: var(--act);
  transition: opacity 0.15s, transform 0.15s;
}
.btn:hover { opacity: 0.9; }
.btn:active { transform: scale(0.98); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.sm {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: auto;
  padding: 8px 13px;
  font-size: 13.5px;
}
.btn.gh,
.btn-secondary {
  background: transparent;
  color: var(--tx);
  border: 1px solid var(--line);
}
.btn.ok { background: var(--ok); color: #fff; }
.btn.bad,
.btn-danger {
  background: transparent;
  color: var(--bad);
  border: 1px solid var(--line);
}

/* Form fields */
.field { display: block; margin-bottom: 12px; }
.field > span {
  display: block;
  font-size: 12.5px;
  color: var(--hint);
  margin: 0 0 5px 2px;
  font-weight: 500;
}
.label {
  display: block;
  font-size: 12.5px;
  color: var(--hint);
  margin: 0 0 5px 2px;
  font-weight: 500;
}
input,
select,
textarea,
.input {
  width: 100%;
  padding: 11px 12px;
  font-size: 16px;
  border-radius: 10px;
  color: var(--tx);
  border: 1px solid var(--line);
  background: var(--card);
  outline: none;
  transition: 0.15s;
  font-family: inherit;
}
input:focus,
select:focus,
textarea:focus,
.input:focus {
  border-color: var(--ac);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--ac) 20%, transparent);
}

/* Grid / two columns */
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

/* Metrics */
.metrics {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 12px 0;
}
.m { border: 1px solid var(--line); border-radius: 12px; padding: 10px 12px; background: var(--card); }
.m .l { color: var(--hint); font-size: 12px; }
.m .v { font-weight: 700; font-size: 16.5px; margin-top: 2px; }
.pos { color: var(--ok); }

/* KPIs */
.kpis {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin: 18px 0 12px;
}
@media (min-width: 760px) { .kpis { grid-template-columns: repeat(4, 1fr); } }
.k {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  transition: border-color 0.2s, transform 0.2s;
}
.k:hover { border-color: var(--hint); transform: translateY(-2px); }
.k .top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--hint);
  font-size: 12.5px;
}
.k .v {
  font-size: 23px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-top: 8px;
}
.k .s { color: var(--hint); font-size: 12.5px; margin-top: 2px; }

/* List items */
.li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 0;
  border-bottom: 1px solid var(--line);
}
.li:last-child { border: 0; }
.li .g { flex: 1; min-width: 0; }
.li .t { font-weight: 600; }
.li .s { color: var(--hint); font-size: 13px; }

/* Status pills */
.tg {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  background: var(--card);
  color: var(--tx);
}
.tg::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.tg.ok { color: var(--ok); background: var(--okb); }
.tg.warn { color: var(--warn); background: var(--warnb); }
.tg.bad { color: var(--bad); background: var(--badb); }

/* Bike grid & card */
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.bike-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.pc,
.bike-card {
  all: unset;
  display: block;
  cursor: pointer;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s;
  text-align: left;
  font: inherit;
  color: var(--tx);
}
.pc:hover,
.bike-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(16, 24, 40, 0.1);
}
.pc:active,
.bike-card:active { transform: scale(0.98); }

.ph,
.bike-card-image,
.bike-card-image-empty {
  position: relative;
  aspect-ratio: 4 / 3;
  display: grid;
  place-items: center;
  background: var(--line);
  color: var(--hint);
  overflow: hidden;
  width: 100%;
  height: auto;
  object-fit: contain;
  display: block;
}
.bike-card-image {
  object-fit: contain;
  background: #111;
}
.bike-card-image-empty {
  display: grid;
  font-size: 28px;
  font-weight: 600;
}

.pc .b,
.bike-card-body {
  padding: 10px 12px 12px;
}
.pc .n,
.bike-card-title {
  font-weight: 600;
  font-size: 14.5px;
  line-height: 1.25;
  margin: 0;
}
.pc .s,
.bike-card-meta {
  color: var(--hint);
  font-size: 12.5px;
  margin-top: 2px;
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}
.pr,
.bike-card-price {
  font-weight: 700;
  margin-top: 6px;
  font-size: 14px;
}
.bike-card-price span { color: var(--hint); font-weight: 400; font-size: 11px; }

/* Badges (aliases) */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
}
.badge-available,
.badge-active { background: var(--okb); color: var(--ok); }
.badge-rented,
.badge-pending { background: var(--warnb); color: var(--warn); }
.badge-maintenance,
.badge-cancelled,
.badge-rejected { background: var(--badb); color: var(--bad); }
.badge-completed { background: var(--okb); color: var(--ok); }
.badge-license { background: var(--badb); color: var(--bad); }
.badge-nolicense { background: var(--okb); color: var(--ok); }

/* Bottom tab bar */
.tab-bar,
.tabbar {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 0;
  z-index: 30;
  width: min(440px, 100%);
  display: flex;
  padding: 6px 8px calc(6px + env(safe-area-inset-bottom, 0px));
  background: var(--card);
  border-top: 1px solid var(--line);
  backdrop-filter: none;
}
.tab-bar-inner {
  display: flex;
  width: 100%;
}
.tab-item,
.tabbar button {
  all: unset;
  flex: 1;
  text-align: center;
  cursor: pointer;
  padding: 6px 0;
  color: var(--hint);
  font-size: 11.5px;
  font-weight: 600;
  position: relative;
  transition: color 0.2s;
  text-decoration: none;
}
.tab-icon,
.tabbar .ic {
  display: block;
  margin: 0 auto 3px;
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
  font-size: 20px;
}
.tab-item.active,
.tabbar .on { color: var(--ac); }
.tab-item.active .tab-icon,
.tabbar .on .ic { transform: translateY(-2px); }

/* App header */
.app-header {
  max-width: 440px;
  margin: 0 auto;
  padding: 12px 16px 0;
  font-size: 13px;
  color: var(--hint);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.app-header > span { color: var(--hint); }

/* Pages */
.page {
  padding: 16px 16px 96px;
  min-height: 100vh;
  max-width: 440px;
  margin: 0 auto;
  width: 100%;
}
.page-title {
  font-size: 22px;
  font-weight: 650;
  margin: 2px 0 16px;
  letter-spacing: -0.02em;
}
.section-title {
  font-size: 16px;
  font-weight: 650;
  margin: 18px 2px 8px;
  color: var(--tx);
}
.empty {
  text-align: center;
  padding: 36px 10px;
  color: var(--hint);
}

/* Modals */
.sheet-backdrop,
.ov {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(10, 14, 25, 0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  animation: fade 0.2s both;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.sheet {
  width: 100%;
  max-width: 440px;
  max-height: 92dvh;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  background: var(--bg);
  border-radius: 20px 20px 0 0;
  padding: 8px 16px calc(24px + env(safe-area-inset-bottom, 0px));
  animation: up 0.28s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  margin: 0 auto;
}
.sheet-handle,
.grab {
  width: 40px;
  height: 4px;
  border-radius: 9px;
  background: var(--line);
  margin: 4px auto 12px;
}
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes up { from { transform: translateY(100%); } to { transform: none; } }

/* Radio option (used in filters/forms) */
.option-list { display: flex; flex-direction: column; gap: 6px; }
.option-radio {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--card);
  border: 1px solid var(--line);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  min-height: 40px;
}
.option-radio.checked {
  background: color-mix(in srgb, var(--ac) 12%, transparent);
  border-color: var(--ac);
}
.option-radio-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--hint);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.option-radio.checked .option-radio-dot { border-color: var(--ac); }
.option-radio-dot-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ac);
}
.option-radio-label { font-size: 14px; color: var(--tx); }

/* Price input: hide arrows */
.price-input,
input[type="number"] {
  -moz-appearance: textfield;
  appearance: textfield;
}
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

/* Photo gallery */
.media-single-view {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 12px;
  overflow: hidden;
  background: var(--line);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 16px;
  cursor: pointer;
}
.media-single-view img,
.media-single-view video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  user-select: none;
}
.media-single-view-main-badge,
.media-single-view-set-main {
  position: absolute;
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  backdrop-filter: blur(6px);
  border: none;
}
.media-single-view-main-badge { top: 8px; left: 8px; pointer-events: none; }
.media-single-view-set-main { top: 8px; right: 8px; cursor: pointer; }
.media-single-view-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  border: none;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
}
.media-single-view-arrow.left { left: 8px; }
.media-single-view-arrow.right { right: 8px; }
.media-single-view-thumbs {
  display: flex;
  gap: 6px;
  padding: 8px 16px 4px;
  overflow-x: auto;
  scrollbar-width: none;
}
.media-single-view-thumbs::-webkit-scrollbar { display: none; }
.media-thumb {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  overflow: hidden;
  background: var(--line);
  border: 2px solid transparent;
  cursor: pointer;
  position: relative;
  padding: 0;
}
.media-thumb.active { border-color: var(--ac); }
.media-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.media-thumb-video {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  font-size: 14px;
  pointer-events: none;
}
.media-thumb-main {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: color-mix(in srgb, var(--ac) 85%, transparent);
  color: #fff;
  font-size: 8px;
  font-weight: 700;
  text-align: center;
  padding: 1px 0;
}

/* ImageViewer / GalleryModal */
.image-viewer,
.gallery-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.95);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fade 0.2s both;
}
.image-viewer img,
.gallery-modal-slide img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  user-select: none;
}
.image-viewer-close,
.gallery-modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 22px;
  border: none;
  cursor: pointer;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
}
.gallery-modal-track {
  flex: 1;
  display: flex;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
}
.gallery-modal-track::-webkit-scrollbar { display: none; }
.gallery-modal-slide {
  flex: 0 0 100%;
  scroll-snap-align: start;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  box-sizing: border-box;
}
.gallery-modal-slide video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.gallery-modal-counter,
.gallery-modal-dots {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 6px;
  z-index: 2;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  border-radius: 14px;
  color: #fff;
  font-size: 12px;
}
.gallery-modal-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.35);
  border: none;
  cursor: pointer;
  padding: 0;
  transition: background 0.15s, width 0.15s;
}
.gallery-modal-dot.active {
  background: #fff;
  width: 18px;
  border-radius: 3px;
}

/* Thin scrollbars everywhere */
html, body, * {
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--tx) 15%, transparent) transparent;
}
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--tx) 15%, transparent);
  border-radius: 2px;
}
::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--tx) 35%, transparent);
}

/* Toggle switch (used in admin park form) */
.switch-toggle {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 30px;
  flex-shrink: 0;
}
.switch-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}
.switch-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: var(--line);
  transition: 0.2s;
  border-radius: 30px;
}
.switch-slider::before {
  position: absolute;
  content: "";
  height: 26px;
  width: 26px;
  left: 2px;
  bottom: 2px;
  background-color: #fff;
  transition: 0.2s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
.switch-toggle input:checked + .switch-slider {
  background-color: var(--ok);
}
.switch-toggle input:checked + .switch-slider::before {
  transform: translateX(20px);
}

/* Media grid (form) */
.media-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.media-grid-item {
  position: relative;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  overflow: hidden;
  background: var(--line);
  cursor: pointer;
}
.media-grid-item img,
.media-grid-item video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}
.media-grid-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.65);
  color: #fff;
  padding: 2px 6px;
  border-radius: 5px;
  font-size: 10px;
  font-weight: 500;
}
.media-grid-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 14px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
}
.media-grid-add {
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  border: 1px dashed var(--line);
  background: var(--card);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: var(--hint);
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
}

/* Hide old stuff */
.media-gallery { margin-bottom: 16px; }
.media-blur, .media-sharp, .media-video, .media-strip, .media-strip-item,
.media-strip-play, .media-strip-video, .media-dots, .media-dot {
  /* legacy: новая UI использует .media-single-view */
}
'''

css_path = ROOT / "styles" / "theme.css"
css_path.write_text(ui_css.strip() + "\n", encoding="utf-8")
print("✅ theme.css: новый UI (без кракозябр)")

# =============================================================
# 2. SVG-иконки для таб-бара
# =============================================================
icons = r'''
// SVG-иконки 20×20 для таб-бара и интерфейса.
// Стиль — stroke, как в новой UI (.ic).
export function IconCatalog() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-6 9 6v11a2 2 0 0 1-2 2h-4v-7h-6v7H5a2 2 0 0 1-2-2z" />
    </svg>
  );
}

export function IconHistory() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 1 0 3-6.7" />
      <path d="M3 4v5h5" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

export function IconGarage() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21V8l9-5 9 5v13" />
      <path d="M9 21v-6h6v6" />
    </svg>
  );
}

export function IconExpenses() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="6" width="18" height="13" rx="2" />
      <path d="M3 10h18" />
      <path d="M7 15h4" />
    </svg>
  );
}

export function IconRequests() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M10 21a2 2 0 0 0 4 0" />
    </svg>
  );
}

export function IconAnalytics() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <path d="M7 15l4-4 3 3 5-5" />
    </svg>
  );
}

export function IconProfile() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
    </svg>
  );
}

export function IconSummary() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  );
}

export function IconParks() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 21h18" />
      <path d="M5 21V7l7-4 7 4v14" />
      <path d="M9 21v-4h6v4" />
      <path d="M9 11h.01M15 11h.01" />
    </svg>
  );
}

export function IconPayments() {
  return (
    <svg className="tab-icon" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="6" width="20" height="13" rx="2" />
      <path d="M2 10h20" />
      <path d="M7 15h4" />
    </svg>
  );
}
'''

(ROOT / "components" / "icons.tsx").write_text(
    icons.strip() + "\n", encoding="utf-8"
)
print("✅ components/icons.tsx создан")

# =============================================================
# 3. App.tsx — SVG-иконки вместо эмодзи в таб-баре
# =============================================================
app_path = ROOT / "App.tsx"
text = app_path.read_text(encoding="utf-8")

# Импорты иконок
if "IconCatalog" not in text:
    text = text.replace(
        'import { Layout } from "./components/Layout";',
        '''import { Layout } from "./components/Layout";
import {
  IconCatalog,
  IconHistory,
  IconGarage,
  IconExpenses,
  IconRequests,
  IconAnalytics,
  IconProfile,
  IconSummary,
  IconParks,
  IconPayments,
} from "./components/icons";''',
        1,
    )

# Client tabs
text = text.replace(
    '''              tabs={[
                { to: "/catalog", label: "Каталог", icon: "🏍" },
                { to: "/history", label: "История", icon: "📜" },
              ]}''',
    '''              tabs={[
                { to: "/catalog", label: "Каталог", icon: <IconCatalog /> },
                { to: "/history", label: "История", icon: <IconHistory /> },
              ]}''',
    1,
)

# Owner tabs
text = text.replace(
    '''              tabs={[
                { to: "/garage", label: "Гараж", icon: "🔧" },
                { to: "/expenses", label: "Расходы", icon: "💸" },
                { to: "/requests", label: "Заявки", icon: "🔔" },
                { to: "/analytics", label: "Аналитика", icon: "📊" },
                { to: "/profile", label: "Профиль", icon: "👤" },
              ]}''',
    '''              tabs={[
                { to: "/garage", label: "Гараж", icon: <IconGarage /> },
                { to: "/expenses", label: "Расходы", icon: <IconExpenses /> },
                { to: "/requests", label: "Заявки", icon: <IconRequests /> },
                { to: "/analytics", label: "Аналитика", icon: <IconAnalytics /> },
                { to: "/profile", label: "Профиль", icon: <IconProfile /> },
              ]}''',
    1,
)

# Super admin tabs
text = text.replace(
    '''              tabs={[
                { to: "/summary", label: "Сводка", icon: "📊" },
                { to: "/parks", label: "Парки", icon: "🏢" },
                { to: "/payments", label: "Оплаты", icon: "💳" },
              ]}''',
    '''              tabs={[
                { to: "/summary", label: "Сводка", icon: <IconSummary /> },
                { to: "/parks", label: "Парки", icon: <IconParks /> },
                { to: "/payments", label: "Оплаты", icon: <IconPayments /> },
              ]}''',
    1,
)

app_path.write_text(text, encoding="utf-8")
print("✅ App.tsx: SVG-иконки в таб-баре")

# =============================================================
# 4. Убираем эмодзи из всех .tsx
# =============================================================
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "\uFE0F"
    "]+",
    flags=re.UNICODE,
)

removed_count = 0
for tsx in ROOT.rglob("*.tsx"):
    if "icons.tsx" in tsx.name:
        continue
    try:
        content = tsx.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    new_content, n = EMOJI_PATTERN.subn("", content)
    if n > 0:
        # Убираем двойные пробелы, которые могли остаться
        new_content = re.sub(r"  +", " ", new_content)
        # Убираем пустые строки, которые стали
        tsx.write_text(new_content, encoding="utf-8")
        print(f"  ✅ {tsx.relative_to(ROOT)}: убрано {n} эмодзи")
        removed_count += n

print(f"✅ Всего удалено эмодзи: {removed_count}")
print("\nГотово. Перезапусти Vite (Ctrl+C → npm run dev) и браузер Ctrl+Shift+R.")