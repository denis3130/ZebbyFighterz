# Messaggio per la sessione di Claude sul PC di Denis (ComfyUI)

La sessione **Locale** di Claude Code sul PC (Windows, RTX 3060 12 GB, ComfyUI Desktop) fa tutto da sola: genera le
animazioni con ComfyUI **e** le monta nel gioco. Basta incollarle questa riga:

```
Ciao, sono Denis (rispondimi in italiano, brevi). Clona il repository GitHub denis3130/ZebbyFighterz, ramo
claude/cool-fermi-fkx4iq, leggi docs/comfy/PROMPT-SESSIONE-PC.md e fai tutto quello che c'è scritto, dall'inizio alla fine.
```

Quello che segue è il lavoro completo per quella sessione: prima le animazioni (il blocco qui sotto), poi il montaggio
nel gioco (la sezione «Montaggio nel gioco»).

```
Ciao, sono Denis. Rispondimi sempre in italiano, con messaggi brevi.
Progetto: Voidrise Fighters, picchiaduro anime 2.5D (repository GitHub denis3130/ZebbyFighterz). Una sessione di Claude
nel cloud fa l'interfaccia sul ramo claude/cool-fermi-fkx4iq; tu, qui sul mio PC, generi con ComfyUI le animazioni
dell'interfaccia, che poi lei monta nel gioco. Se riesci a leggere quel ramo (git clone o la cartella del progetto),
leggi docs/comfy/ANIMAZIONI.md, docs/HANDOFF-UI.md e CLAUDE.md; l'essenziale comunque è qui sotto.

Regole: immagini di partenza SOLO quelle che ti do io; non cambiare la forma dei personaggi; prima di scaricare
qualcosa dimmi cosa e quanto pesa e aspetta il mio ok; non toccare il codice del gioco.

1. Trova ComfyUI Desktop (di solito Documenti\ComfyUI) e la sua API locale (porta 8000 o 8188); controlla la scheda
   con nvidia-smi.
2. Modello: Wan 2.2 14B «primo e ultimo fotogramma» (nella libreria di ComfyUI «Wan2.2 14B FLF2V»). Con 12 GB usa
   la via leggera: nodi ComfyUI-GGUF, i due file Wan2.2-I2V-A14B GGUF Q4_K_M (HighNoise e LowNoise) e il LoRA a 4
   passi (lightx2v / Lightning), steps 4, cfg 1. Impostazioni di prova: 832x480, 81 fotogrammi (5 s a 16 fps), seme fisso.
3. Le clip (immagini orizzontali 16:9 che ti do io):
   - Intro: partenza = Ren e Kael lontani ai lati, pronti a scattare; arrivo = i pugni che si scontrano al centro.
   - Titolo, Menu: la STESSA immagine come partenza e come arrivo, così il video torna all'inizio e va in ciclo.
4. Prompt (inglese):
   - Intro: anime fighting game cinematic, two martial artists dash toward each other from the left and the right,
     Ren (dark spiky hair, teal sleeveless gi, orange sash, bandaged wrists) and Kael (silver-white hair, black and
     violet outfit), both throw a punch at the same time and their fists collide in the center with a burst of light,
     sparks and flying debris, dramatic dusk sky over ruins, camera pushes in, high quality anime style, consistent
     faces and outfits
   - Personaggio in ciclo: anime character standing still, subtle breathing, hair and clothes moving gently in the
     wind, floating embers, soft aura glow, camera locked, seamless loop, same pose at the start and at the end
   - Negativo: blurry, low quality, deformed hands, extra fingers, extra limbs, morphing face, changing outfit, text,
     watermark, flicker, static image
5. Per ogni clip: generala, guarda tu i fotogrammi (volti e vestiti che non cambiano, mani giuste), mostrami un foglio
   di fotogrammi e rifalla con un altro seme se non va.
6. Consegna: se puoi usare git sul ramo claude/cool-fermi-fkx4iq, metti gli MP4 in assets/ui/video_src/
   (intro.mp4, titolo.mp4, menu.mp4), fai commit e push; altrimenti salvali in Documenti\voidrise-video
   e dimmelo: li mando io alla chat nel cloud.
Inizia dal punto 1 e dimmi cosa trovi.
```

## Montaggio nel gioco (dopo che Denis ha approvato le clip)
Leggi prima `CLAUDE.md` e `docs/HANDOFF-UI.md` (regole, architettura dell'interfaccia, prove). In breve:
- **Regole fisse**: niente animazioni CSS infinite (rallentano la lotta): il movimento dei menu è in JavaScript, solo mentre
  un menu è aperto; immagini e video solo da quelli di Denis; game feel e 60 FPS su un telefono medio; misura FPS prima e dopo.
- **Comprimi** le clip con ffmpeg (su Windows: `winget install ffmpeg`): H.264 MP4 `-crf 28-32 -preset slow -an
  -movflags +faststart`, 960x540 o 832x480, cicli senza l'ultimo fotogramma (uguale al primo). Pesa ogni file: la pagina
  `index.html` contiene tutto in un solo file (ora circa 12 MB) e la pagina Claude accetta al massimo 16 MB.
- **Dove vanno**: `assets/ui/video/` + supporto in `build.py` (i file di `assets/` diventano `ASSETS[...]` in base64).
  - Intro (`src/u4_intro.js`): il video dell'intro nello stage, sotto i due canvas degli effetti; tieni lampo, anelli e logo
    allineati al momento del pugno nel video (un numero in `CFG.ui.intro`, in `src/a1_ui_cfg.js`); «Salta» e la fine
    verso il titolo restano come sono.
  - Titolo, menu (`src/u3_layers.js`, `#uiLayers`): un livello `<video muted playsinline loop autoplay>` per scena,
    con un fotogramma fisso come riserva; **in pausa e nascosto** durante la lotta e la pausa (`menuSync` in `src/h_menu.js`
    già spegne `#uiLayers`) e quando la pagina è nascosta.
- **Prove**: `bash mk.sh` (deve dire SYNTAX_OK); la serie dell'interfaccia e del gioco elencata in `docs/HANDOFF-UI.md`
  (serve `pip install playwright` e Chrome/Chromium); aggiungi prove per i video (partono nei menu, fermi in lotta, nessuna
  animazione infinita); FPS prima e dopo con `python3 tests/run.py tests/ui_fps.test.js --viewport 844x390`.
- **Consegna**: commit e push sul ramo `claude/cool-fermi-fkx4iq`, aggiorna `docs/HANDOFF-UI.md`, poi a Denis 2-3 righe:
  cosa è cambiato, FPS, come provarlo. Per giocarla: apri `index.html` dopo `bash mk.sh`. La pubblicazione sulla pagina
  Claude «Voidrise Interfaccia» (https://claude.ai/artifact/PSAtwRuNWi6XUCg5uj2zR6) si fa con lo strumento Artifact: se
  non ce l'hai, Denis la chiede alla chat nel cloud.
