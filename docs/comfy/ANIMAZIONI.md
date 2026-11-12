# Animazioni con ComfyUI (PC di Denis, RTX 3060 12 GB)

Le animazioni dell'interfaccia (intro, personaggi vivi nei menu, sfondi) si generano sul PC di Denis con ComfyUI: la sessione
di Claude nel cloud non ha una scheda video. Claude prepara immagini di partenza, prompt e impostazioni; Denis avvia e manda
i video; Claude li taglia, li mette in ciclo, li comprime e li monta nel gioco.
Le immagini di partenza sono **solo** quelle che manda Denis (si salvano in `docs/ref/ui/` come i riferimenti).

## Il modello: Wan 2.2 14B, «primo e ultimo fotogramma» (FLF2V)
Gli si danno l'immagine di partenza e quella d'arrivo e crea il movimento in mezzo:
- **intro**: partenza = Ren e Kael lontani, arrivo = i pugni che si scontrano → si vedono avvicinarsi e colpirsi davvero;
- **cicli** (menu, sfondi): la **stessa immagine** come partenza e come arrivo → il video torna al punto di partenza e si ripete
  senza stacchi (l'ultimo fotogramma, uguale al primo, lo tolgo io).

## Passi sul PC
1. Aggiorna ComfyUI (Desktop o portable) all'ultima versione (i flussi Wan 2.2 nativi chiedono almeno la 0.3.46).
2. ComfyUI → *Workflow* → *Browse Templates* (libreria dei modelli) → cerca **«Wan2.2 14B FLF2V»** e aprilo.
   Se mancano dei modelli ComfyUI li elenca col pulsante per scaricarli: scaricali tutti (sono decine di GB).
3. **Se la 3060 va in «out of memory» o è lentissima**, usa la versione leggera GGUF:
   - *Manager* → *Install Custom Nodes* → **ComfyUI-GGUF** → riavvia ComfyUI;
   - scarica da Hugging Face i due file **Wan2.2-I2V-A14B** in formato GGUF **Q4_K_M** (uno *HighNoise*, uno *LowNoise*)
     nella cartella dei modelli che il nodo legge (`ComfyUI/models/unet`);
   - nel flusso sostituisci i due nodi *Load Diffusion Model* con due *Unet Loader (GGUF)* e scegli i due file;
   - per andare molto più veloce: il LoRA a 4 passi per Wan 2.2 I2V (*lightx2v* / *Lightning*), con *steps* 4 e *cfg* 1.
4. Impostazioni per la 3060: **832×480**, **81 fotogrammi** (5 s a 16 fps), seme fisso. Prima una prova a 480p: se è bella,
   la versione finale si rifà più grande oppure la ingrandisco io (lo stesso ingranditore anime delle immagini).
5. Carica le immagini nei due *Load Image* (start = primo fotogramma, end = ultimo), incolla il prompt, *Queue*.
   Il video esce in `ComfyUI/output/`.
6. Mandami l'MP4 (anche 2-3 tentativi con semi diversi: scelgo il migliore e ti mostro i fotogrammi prima di montarlo).

## Le clip
| Clip | Partenza | Arrivo | Durata |
|---|---|---|---|
| Intro: il pugno | Ren e Kael lontani ai due lati, si guardano, pronti a scattare | i pugni che si scontrano al centro (come il riferimento 00) | 5 s |
| Intro: l'esplosione (facoltativa) | i pugni che si scontrano | lo stesso, dopo il lampo (o solo partenza, senza arrivo) | 3-5 s |
| Titolo vivo | i due volti ai lati con le rovine | la stessa immagine | 4-5 s in ciclo |
| Menu vivo | Ren a destra nelle rovine | la stessa immagine | 4-5 s in ciclo |
| Sfondo | rovine e cielo senza personaggi | la stessa immagine | 5 s in ciclo |
Immagini: orizzontali 16:9, almeno 1280×720 (meglio 1920×1080), PNG o JPG; per l'intro partenza e arrivo con lo stesso
sfondo, la stessa luce e la stessa inquadratura.

## Prompt (in inglese: il modello li capisce meglio)
- **Intro**: `anime fighting game cinematic, two martial artists dash toward each other from the left and the right, Ren (dark spiky hair, teal sleeveless gi, orange sash, bandaged wrists) and Kael (silver-white hair, black and violet outfit), both throw a punch at the same time and their fists collide in the center with a burst of light, sparks and flying debris, dramatic dusk sky over ruins, camera pushes in, high quality anime style, consistent faces and outfits`
- **Personaggio in ciclo**: `anime character standing still, subtle breathing, hair and clothes moving gently in the wind, floating embers, soft aura glow, camera locked, seamless loop, same pose at the start and at the end`
- **Sfondo in ciclo**: `dusk sky over ancient ruins, clouds drifting slowly, floating embers, light rays, camera locked, seamless loop`
- **Negativo** (per tutte): `blurry, low quality, deformed hands, extra fingers, extra limbs, morphing face, changing outfit, text, watermark, flicker, static image`

## Nel gioco (lo faccio io)
- Taglio, ciclo senza stacchi, compressione (WebM/MP4 leggeri, misurati sul peso della pagina).
- Intro: il video con i miei effetti sopra (lampo, anelli, logo); menu: il video dietro i pulsanti al posto degli strati fermi.
- I video partono muti e in linea (anche su iPhone), si fermano e spariscono durante la lotta; FPS misurati prima e dopo.
