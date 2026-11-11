// Shared interface components (spec §2): one of each, reused by every screen so the whole interface looks and behaves
// the same. Each returns its element; a focusable one has [data-focus] and el.uiAct(device, target) for the navigation.
// Styles in u_style.css. A locked element does nothing but say why («In arrivo» or its own note).
const UI_ICON = {
  lock: '<svg viewBox="0 0 24 24" class="uico"><rect x="5" y="11" width="14" height="10" rx="1.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
  back: '<svg viewBox="0 0 24 24" class="uico"><path d="M15 5l-7 7 7 7"/></svg>',
  left: '<svg viewBox="0 0 24 24" class="uico"><path d="M14.5 6l-6 6 6 6"/></svg>',
  right: '<svg viewBox="0 0 24 24" class="uico"><path d="M9.5 6l6 6-6 6"/></svg>',
  soon: '<svg viewBox="0 0 24 24" class="uico"><path d="M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9"/></svg>',
  warn: '<svg viewBox="0 0 24 24" class="uico"><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/></svg>',
};
function uiEl(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html !== undefined) e.innerHTML = html; return e; }
const uiEsc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
// Makes el focusable with an action; locked = the action is replaced by the notice.
function uiFocusable(el, act, locked, note) {
  el.setAttribute('data-focus', '');
  el.setAttribute('role', 'button');
  if (locked) { el.classList.add('lock'); el.uiAct = () => uiToast(note || 'In arrivo', 'soon'); }
  else el.uiAct = act || (() => {});
  return el;
}

// «VOIDRISE» in spaced capitals with a thin gold crescent cutting behind it (size 's' in a corner, 'l' on the title).
function cLogo(size) {
  return uiEl('div', 'ulogo ' + (size || 's'), '<svg class="ulogoArc" viewBox="0 0 100 100" aria-hidden="true"><path d="M70 8a44 44 0 1 1-52 64"/></svg>' +
    '<span class="ulogoTx">VOIDRISE</span><i class="ulogoCut"></i>');
}
// Section title: orange bar on the left, title, italic subtitle, a fading line with an orange brush stroke under it.
function cHead(title, sub) {
  return uiEl('div', 'uhead', '<b class="uheadT">' + uiEsc(title) + '</b>' + (sub ? '<i class="uheadS">' + uiEsc(sub) + '</i>' : '') + '<span class="uheadL"></span>');
}
// Slanted button. kind 'line' (default, the pause and list buttons), 'main' (the big bronze one with gold lines either
// side: returns the row, the button inside is the focusable part), 'small' (keys of a grid). o.id / o.txId: ids of the
// button and of its label.
function cBtn(o) {
  const b = uiEl('div', 'ub ' + (o.kind || 'line'), (o.locked ? UI_ICON.lock : '') + '<span' + (o.txId ? ' id="' + o.txId + '"' : '') + '>' + uiEsc(o.label) + '</span>');
  if (o.id) b.id = o.id;
  if (o.act0) b.dataset.act = o.act0;
  uiFocusable(b, o.act, o.locked, o.note);
  if (o.kind !== 'main') return b;
  const row = uiEl('div', 'umw'); row.appendChild(b); return row;
}
// Menu entry: big serif text; with the focus it grows, turns light gold, gets the orange bar and a brush stroke behind.
function cItem(o) { const e = uiFocusable(uiEl('div', 'uitem', (o.locked ? UI_ICON.lock : '') + '<span>' + uiEsc(o.label) + '</span>'), o.act, o.locked, o.note); if (o.act0) e.dataset.act = o.act0; return e; }
// Card with a picture: italic label at the bottom; with the focus an orange frame, a glow and the picture zooms a little.
function cCard(o) {
  const c = uiEl('div', 'ucard', '<i class="ucardImg"' + (o.img ? ' style="background-image:url(' + o.img + ')"' : '') + '></i>' +
    (o.badge ? '<em class="ucardBadge">' + uiEsc(o.badge) + '</em>' : '') + '<span class="ucardTx">' + (o.locked ? UI_ICON.lock : '') + uiEsc(o.label) + '</span>');
  return uiFocusable(c, o.act, o.locked, o.note);
}
// Tabs: each tab is focusable; Q / E, PageUp / PageDown, LB / RB move between them (el.uiTab(d)).
function cTabs(labels, i, onPick) {
  const box = uiEl('div', 'utabs');
  box.setAttribute('data-tabs', '');
  const set = k => { i = k; [...box.children].forEach((t, j) => t.classList.toggle('on', j === k)); onPick(k); };
  labels.forEach((l, k) => box.appendChild(uiFocusable(uiEl('div', 'utab' + (k === i ? ' on' : ''), uiEsc(l)), () => set(k))));
  box.uiTab = d => { const k = Math.max(0, Math.min(labels.length - 1, i + d)); if (k !== i) set(k); };
  return box;
}
// ‹ label: value ›. Left / right with the focus change the value (no wrap); a tap on an arrow too; confirm = next value.
function cStepper(o) {
  let i = o.i;
  const fmt = o.fmt || String;
  const el = uiEl('div', 'ustep', '<i class="ustepA" data-d="-1">' + UI_ICON.left + '</i><span class="ustepT">' + uiEsc(o.label) + ': <b></b></span><i class="ustepA" data-d="1">' + UI_ICON.right + '</i>');
  const val = el.querySelector('b');
  const draw = () => { val.textContent = fmt(o.values[i]); el.querySelector('[data-d="-1"]').classList.toggle('off', i === 0); el.querySelector('[data-d="1"]').classList.toggle('off', i === o.values.length - 1); };
  const step = d => { const k = Math.max(0, Math.min(o.values.length - 1, i + d)); if (k === i) return; i = k; draw(); val.classList.remove('bump'); void val.offsetWidth; val.classList.add('bump'); o.onChange(o.values[i]); };
  uiFocusable(el, (dev, t) => { const a = t && t.closest && t.closest('[data-d]'); step(a ? +a.dataset.d : (i === o.values.length - 1 ? -i : 1)); });
  el.uiDir = dir => { if (dir !== 'left' && dir !== 'right') return false; step(dir === 'left' ? -1 : 1); return true; };
  draw();
  return el;
}
// Stat bar: label and max slanted notches, n of them lit.
function cStatBar(label, n, max) {
  let h = '<span class="ustatL">' + uiEsc(label) + '</span><span class="ustatB">';
  for (let k = 0; k < max; k++) h += '<i' + (k < n ? ' class="on"' : '') + '></i>';
  return uiEl('div', 'ustat', h + '</span>');
}
function cProgress(frac) {
  const e = uiEl('div', 'uprog', '<i></i>');
  e.uiSet = f => { e.firstChild.style.transform = 'scaleX(' + Math.max(0, Math.min(1, f)) + ')'; };
  e.uiSet(frac || 0);
  return e;
}
// The player's chip, top right: round portrait, name, level.
function uiFace(c) { return ASSETS['ui/face_' + c + '.webp'] || ''; }   // (only Denis's interface references: the faces of the VS screen)
function cChip() {
  const e = uiEl('div', 'uchip');
  const lv = progLevel(SV ? SV.xp : 0).lvl;
  e.innerHTML = '<i class="uchipFace" style="background-image:url(' + uiFace((SV && SV.lastChar) || 'ren') + ')"></i><span class="uchipN">' +
    uiEsc((SV && SV.name) || 'Giocatore') + '</span><span class="uchipL">Liv. ' + lv + '</span>';
  return e;
}
// «‹ Indietro», top left: the same as Esc / B.
function cBack() { return uiFocusable(uiEl('div', 'uback', UI_ICON.back + '<span>Indietro</span>'), () => menuBack()); }

// One notice at a time, top centre, gone after CFG.ui.t.toast ms. kind: 'info' | 'soon' (a feature still to come) | 'err'.
const UI_TOAST = {timer: 0};
function uiToast(text, kind) {
  let t = document.getElementById('uiToast');
  if (!t) { t = uiEl('div', 'utoast'); t.id = 'uiToast'; document.getElementById('ui').appendChild(t); }
  t.className = 'utoast ' + (kind || 'info');
  t.innerHTML = (kind === 'soon' ? UI_ICON.soon : kind === 'err' ? UI_ICON.warn : '') + '<span>' + uiEsc(text) + '</span>';
  t.classList.remove('on'); void t.offsetWidth; t.classList.add('on');
  clearTimeout(UI_TOAST.timer);
  UI_TOAST.timer = setTimeout(() => t.classList.remove('on'), CFG.ui.t.toast);
}
// A yes / no question over the screen. The focus stays inside (on «no» first, the safe answer); Esc / B = no; the
// focus goes back where it was. Resolves true for yes.
function uiConfirm(o) {
  return new Promise(resolve => {
    const prev = NAV.focus, over = document.getElementById('uiOver');
    const dlg = uiEl('div', 'udlg', '<div class="udlgBox"><b class="udlgT">' + uiEsc(o.title) + '</b>' + (o.text ? '<p class="udlgP">' + uiEsc(o.text) + '</p>' : '') + '<div class="udlgBtns"></div></div>');
    dlg.id = 'uiDlg';
    const close = v => { if (!dlg.parentNode) return; dlg.remove(); navFocus(prev && prev.isConnected ? prev : null); resolve(v); };
    const no = cBtn({label: o.no || 'Annulla', act: () => close(false), act0: 'no'}), yes = cBtn({label: o.yes || 'Conferma', act: () => close(true), act0: 'yes'});
    dlg.querySelector('.udlgBtns').append(no, yes);
    dlg.uiBack = () => close(false);
    over.appendChild(dlg);
    NAV.busyUntil = performance.now() + CFG.ui.t.tapGuard;
    navFocus(no);
  });
}
