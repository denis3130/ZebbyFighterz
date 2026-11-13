// The device save (localStorage 'voidrise.save', versioned). SV is the live object the screens read and change;
// saveWrite() stores it. Storage that is missing, full or throws (a sandboxed frame, private mode) only means the
// progress is not kept: the game goes on and says so once per session.
const SAVE = {key: 'voidrise.save', v: 1, old: 'voidrise.prefs', warned: false};
let SV = null;

function saveDefaults() {
  return {v: SAVE.v, name: null, avatar: null, introSeen: false, xp: 0, lastChar: 'ren',
    stats: {played: 0, won: 0, lost: 0, draw: 0, rounds: 0, hits: 0, maxCombo: 0, timeS: 0, byChar: {}},
    settings: {quality: 'auto', fpsCap: 60, showFps: false, music: 70, sfx: 85}};
}
const svIsObj = o => !!o && typeof o === 'object' && !Array.isArray(o);
// s laid over d: nested objects merge key by key, so a save written before a new setting still gets its default.
function svMerge(d, s) {
  for (const k of Object.keys(s)) {
    if (svIsObj(d[k]) && svIsObj(s[k])) svMerge(d[k], s[k]);
    else if (s[k] !== undefined) d[k] = s[k];
  }
  return d;
}
function svRead(key) { try { return JSON.parse(localStorage.getItem(key)); } catch (_) { return null; } }

// Fills SV from the device: nothing saved, unreadable or another version -> the defaults. The FPS preference of the
// first version of the game (voidrise.prefs) is carried over once, when there is no save yet.
function saveLoad() {
  const d = saveDefaults(), s = svRead(SAVE.key);
  if (svIsObj(s) && s.v === SAVE.v) svMerge(d, s);
  else { const p = svRead(SAVE.old); if (svIsObj(p) && p.fps === true) d.settings.showFps = true; }
  return (SV = d);
}
// Stores SV; false when the device refused (the first refusal of the session shows a notice).
function saveWrite() {
  try { localStorage.setItem(SAVE.key, JSON.stringify(SV)); return true; }
  catch (_) {
    if (!SAVE.warned) { SAVE.warned = true; if (typeof uiToast === 'function') uiToast('Impossibile salvare i progressi su questo dispositivo', 'err'); }
    return false;
  }
}
