#!/usr/bin/env python3
"""Builds the "Ren animazioni nuove" preview page.

  python3 build.py --assets ASSETS.js --out OUT.html [--mods body.js,trail.js,...] [--base base/viewer_code.html]

base/viewer_code.html is the original "Anteprima 3D di Ren" page without its one huge line of embedded assets
(const ASSETS={...}; ~9.7 MB: get it from the published page, it is the line right after "(()=>{").
The build patches the viewer's hook points (PATCHES), puts scaffold.js and the chosen mods/*.js before the
viewer's boot, and puts the assets line back. Every patch must match exactly once: the build fails otherwise.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

PATCHES = [
    # --- page ---
    ("<title>Anteprima 3D di Ren</title>", "<title>Ren animazioni nuove</title>"),
    ('<div id="name">REN<small>Anteprima 3D, senza giocare</small></div>',
     '<div id="name">REN<small>Animazioni nuove · confronta con le vecchie</small></div>'),
    ('    <div class="opt"><button id="spin"><span>Gira</span></button></div>',
     '    <div class="opt">Animazioni <button id="aNew"><span>Nuove</span></button><button id="aOld"><span>Vecchie</span></button></div>\n'
     '    <div class="opt" id="rnOpts"></div>\n'
     '    <div class="opt"><button id="spin"><span>Gira</span></button></div>\n'
     '    <div class="opt" id="fps"></div>'),
    ("Trascina per girare Ren, pizzica o usa la rotella per avvicinarti, doppio tocco per tornare al centro.",
     "Trascina per girare, pizzica o usa la rotella per avvicinarti, doppio tocco per tornare al centro."
     "<span class=kb> Tastiera: 1-0 mosse, N nuove/vecchie, M manichino, L allungo, spazio velocità. "
     "Controller: dorsali = mossa, A nuove/vecchie, B velocità, X manichino, Y allungo.</span>"),
    ("@media (prefers-reduced-motion:reduce){button{transition:none}}",
     "@media (prefers-reduced-motion:reduce){button{transition:none}}\n@media (pointer:coarse){#hint .kb{display:none}"
     "#moves{flex-wrap:nowrap;overflow-x:auto;touch-action:pan-x;scrollbar-width:none;padding:2px 0}#moves::-webkit-scrollbar{display:none}#moves button{flex:0 0 auto}}"),
    # --- a move's clip time: the layer's own, when it has one ---
    ("function mdMoveT(t, m, af, hit) {\n",
     "function mdMoveT(t, m, af, hit) {\n  if (RN.on && RN.moveT) return RN.moveT(t, m, af, hit);\n"),
    # --- viewer: boot, play, step, loop ---
    ("  vwPlay(0); vwPaint('draw'); vwLight('toon'); vwSpeed(1);\n",
     "  rnBoot();\n  vwPlay(0); vwPaint('draw'); vwLight('toon'); vwSpeed(1);\n"),
    ("  Object.assign(VW.F, {x: 0, y: 0, vy: 0, air: false, hit: 0}); vwNext();\n",
     "  Object.assign(VW.F, {x: 0, y: 0, vy: 0, air: false, hit: 0}); vwNext(); rnReset();\n"),
    ("function vwStep() {\n", "function vwStep0() {\n"),
    # (the jump's attack: the plan's own move, not always the air kick)
    ("if (mode === 'jumpAtk') { F.act = 'air'; VW.atkIn = 8; }", "if (mode === 'jumpAtk') { VW.atk = act; F.act = 'air'; VW.atkIn = 8; }"),
    ("{ F.act = 'jk'; F.af = 0; VW.name = VW_NAMES.jk; }", "{ F.act = VW.atk || 'jk'; F.af = 0; VW.name = VW_NAMES[F.act] || F.act; }"),
    # (the energy shot for its whole length: startup and recovery, as in the sim)
    ("  ['Speciale', ['spec']],", "  ['Speciale', [['spec', CFG.spec.spawn + CFG.spec.rec]]],"),
    ("  const it = VW.it, F = VW.F;\n  mdSync(it, 0, VW.S);\n",
     "  const it = VW.it, S = rnDrawState(), F = fighterOf(S, 0);\n  rnSync(it, 0, S);\n"),
    ("c = VW.camera, d = VW.fit * VW.zoom;", "c = VW.camera, d = VW.fit * VW.zoom * VW.wide;"),
    ("  c.position.set(0, cy + .1, d); c.lookAt(0, cy, 0);\n  VW.renderer.render(VW.scene, c);\n  const m = CFG.moves[F.act],",
     "  c.position.set(VW.aimX, cy + .1, d); c.lookAt(VW.aimX, cy, 0);\n  for (const f of RN.hooks.draw) if (RN.on) f(VW, dt, c);\n"
     "  VW.renderer.render(VW.scene, c);\n  rnFps(now);\n  { const F = VW.F;\n  const m = CFG.moves[F.act],"),
    ("  if (now2.innerHTML !== txt) now2.innerHTML = txt;\n", "  if (now2.innerHTML !== txt) now2.innerHTML = txt; }\n"),
]

TICK = "VW.tick = n => { for (let k = 0; k < n; k++) { vwStep(); mdSync(VW.it, 0, VW.S); } };"
NEW_TICK = ("VW.tick = n => { for (let k = 0; k < n; k++) { vwStep(); rnSync(VW.it, 0, rnDrawState(0)); } };"
            "   // tests: n frames now, each drawn\nVW.RN = RN;\n"
            "window.__X = {CFG, BTN, THREE, ASSETS, RN, VW_PLAYS, F3_YAW, F3_DEG, MD, MD_SASH, mdData, mdPoseOf, mdEval, mdSample, mdWorld, mdLegIK, mdApply, mdRest,\n"
            "  mdSync, mdMix, mdRoot, mdMoveT, mdKey, mdLayer, mdHipsTurn, mdBoneTurn, mdSash, rnSync, rnDrawState, vwPlay, vwStep, vwNext, fighterOf};   // tests")
BOOT_MARK = "(()=>{\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True, help="file with the single line: const ASSETS={...};")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mods", default="", help="comma separated module files (relative to mods/ or absolute), in order")
    ap.add_argument("--base", default=os.path.join(HERE, "base", "viewer_code.html"))
    a = ap.parse_args()
    code = open(a.base, encoding="utf-8").read()
    for old, new in PATCHES:
        n = code.count(old)
        if n != 1:
            sys.exit("build.py: patch matches %d times (must be 1): %r" % (n, old[:70]))
        code = code.replace(old, new)
    parts = [open(os.path.join(HERE, "scaffold.js"), encoding="utf-8").read()]
    for m in [m.strip() for m in a.mods.split(",") if m.strip()]:
        path = m if os.path.isabs(m) else os.path.join(HERE, "mods", m)
        parts.append("// ===== " + os.path.basename(path) + " =====\n" + open(path, encoding="utf-8").read())
    if code.count(TICK) != 1 or code.count(BOOT_MARK) != 1:
        sys.exit("build.py: the viewer's VW.tick line or its first line was not found")
    code = code.replace(TICK, "\n".join(parts) + "\n" + NEW_TICK)
    assets = open(a.assets, encoding="utf-8").read().rstrip("\n")
    if not assets.startswith("const ASSETS="):
        sys.exit("build.py: the assets file must be the single line starting with const ASSETS=")
    code = code.replace(BOOT_MARK, BOOT_MARK + assets + "\n")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(code)
    print("built %s (%.1f MB, %d modules)" % (a.out, len(code) / 1e6, len(parts) - 1))


if __name__ == "__main__":
    main()
