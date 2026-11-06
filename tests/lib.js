// tests/lib.js — tiny in-page test API. Tests in one file run in order and share page state.
window.T = (() => {
  const tests = [];
  class Fail extends Error {}
  const fmt = v => { try { const s = JSON.stringify(v); return s === undefined ? String(v) : s; } catch (_) { return String(v); } };
  const pre = msg => (msg ? msg + ': ' : '');
  return {
    test(name, fn) { tests.push({name, fn}); },
    eq(a, b, msg) { if (a !== b) throw new Fail(pre(msg) + 'expected ' + fmt(b) + ', got ' + fmt(a)); },
    ok(v, msg) { if (!v) throw new Fail(msg || 'expected truthy, got ' + fmt(v)); },
    near(a, b, eps, msg) { if (!(Math.abs(a - b) <= eps)) throw new Fail(pre(msg) + 'expected ' + b + ' ±' + eps + ', got ' + a); },
    // printed by run.py as "INFO msg"
    info(msg) { (window.TINFO = window.TINFO || []).push(String(msg)); },
    // runs simStep n times with the given inputs (a: player 0, b: player 1)
    feed(S, n, a = 0, b = 0) { for (let i = 0; i < n; i++) __VF.simStep(S, a, b); },
    // deterministic Math.random (mulberry32): a failing run can be replayed with the same seed (run.py --seed N)
    seed(s) { let a = s >>> 0; Math.random = () => { a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; },
    SEED: 1,
    // synchronous on purpose: no await between tests, so the real-time frame loop never runs in between
    async run() {
      this.seed(this.SEED);
      const out = [];
      for (const t of tests) {
        try { t.fn(); out.push({name: t.name, ok: true}); }
        catch (e) { out.push({name: t.name, ok: false, msg: e instanceof Fail ? e.message : String(e && e.stack || e)}); }
      }
      return out;
    },
  };
})();

// Shared helpers of the fight-logic suites (sim, attack, guard, round): B = buttons,
// N(opts) = new versus sim (seed 1, Ren vs Kael, opts override), F(S, i) = active fighter of side i.
const B = __VF.BTN;
function N(opts) { return __VF.simCreate(Object.assign({seed: 1, mode: 'versus', chars: ['ren', 'kael']}, opts)); }
function F(S, i) { return __VF.fighterOf(S, i); }
