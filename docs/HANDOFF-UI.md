# Passaggio di consegne — Interfaccia (UI/UX) di Voidrise

- Design: `docs/superpowers/specs/2026-11-11-voidrise-interfaccia-design.md`. Piano U1: `docs/superpowers/plans/2026-11-11-voidrise-interfaccia-u1.md`.
- Riferimenti visivi: `docs/ref/ui/00-…04-*.png` (stile scuro, oro e arancione, caratteri con le grazie).
- Ramo: `claude/cool-fermi-fkx4iq`, partito da `tappa2-ren-meshy` (la linea principale del gioco, Ren di Meshy acceso).

## Misure di partenza (11/11/2026, prima dell'interfaccia nuova)
- Serie completa di `docs/HANDOFF.md` («Build e test»): **21 comandi verdi, 0 errori** (3+29+35+22+23+12+7+15+13+14+19+3+20 prove nella prima serie, poi render/hud/touch/orient/model/perf alle altre misure e `play_check`).
- Chromium headless con SwiftShader, 844x390 (solo di riferimento, non è un telefono):
  - un `tick` nei menu (titolo vecchio): **0,20 ms**; un `tick` in lotta: **2,36 ms**;
  - `perf.test.js`: logica 0,0042 ms per fotogramma, disegno + logica 1,27 ms per fotogramma; KO in 1040 fotogrammi con hitstop contro 988 senza.
- Pagina: `index.html` 9,99 MB, app `play/index.html` 10,6 MB.

## Scelte
- Le pagine costruite (`index.html`, `play/`) entrano nei commit solo quando si pubblica (Task 12): ogni build pesa 10 MB.
