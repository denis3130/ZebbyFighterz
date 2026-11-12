# Messaggio per la sessione di Claude sul PC di Denis (ComfyUI)

Da incollare in una nuova sessione **Locale** di Claude Code sul PC (Windows, RTX 3060 12 GB, ComfyUI Desktop).

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
   - Titolo, Menu, Sfondo: la STESSA immagine come partenza e come arrivo, così il video torna all'inizio e va in ciclo.
4. Prompt (inglese):
   - Intro: anime fighting game cinematic, two martial artists dash toward each other from the left and the right,
     Ren (dark spiky hair, teal sleeveless gi, orange sash, bandaged wrists) and Kael (silver-white hair, black and
     violet outfit), both throw a punch at the same time and their fists collide in the center with a burst of light,
     sparks and flying debris, dramatic dusk sky over ruins, camera pushes in, high quality anime style, consistent
     faces and outfits
   - Personaggio in ciclo: anime character standing still, subtle breathing, hair and clothes moving gently in the
     wind, floating embers, soft aura glow, camera locked, seamless loop, same pose at the start and at the end
   - Sfondo in ciclo: dusk sky over ancient ruins, clouds drifting slowly, floating embers, light rays, camera locked,
     seamless loop
   - Negativo: blurry, low quality, deformed hands, extra fingers, extra limbs, morphing face, changing outfit, text,
     watermark, flicker, static image
5. Per ogni clip: generala, guarda tu i fotogrammi (volti e vestiti che non cambiano, mani giuste), mostrami un foglio
   di fotogrammi e rifalla con un altro seme se non va.
6. Consegna: se puoi usare git sul ramo claude/cool-fermi-fkx4iq, metti gli MP4 in assets/ui/video_src/
   (intro.mp4, titolo.mp4, menu.mp4, sfondo.mp4), fai commit e push; altrimenti salvali in Documenti\voidrise-video
   e dimmelo: li mando io alla chat nel cloud.
Inizia dal punto 1 e dimmi cosa trovi.
```
