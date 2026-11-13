# Animazioni con ComfyUI (PC di Denis, RTX 3060 12 GB)

Le animazioni dell'interfaccia (intro, personaggi vivi nei menu; niente sfondo in ciclo, Denis 12/11) si generano sul PC di Denis con ComfyUI: la sessione
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
Immagini: orizzontali 16:9, almeno 1280×720 (meglio 1920×1080), PNG o JPG; per l'intro partenza e arrivo con lo stesso
sfondo, la stessa luce e la stessa inquadratura.

## Prompt (in inglese: il modello li capisce meglio)
- **Intro**: `anime fighting game cinematic, two martial artists dash toward each other from the left and the right, Ren (dark spiky hair, teal sleeveless gi, orange sash, bandaged wrists) and Kael (silver-white hair, black and violet outfit), both throw a punch at the same time and their fists collide in the center with a burst of light, sparks and flying debris, dramatic dusk sky over ruins, camera pushes in, high quality anime style, consistent faces and outfits`
- **Personaggio in ciclo**: `anime character standing still, subtle breathing, hair and clothes moving gently in the wind, floating embers, soft aura glow, camera locked, seamless loop, same pose at the start and at the end`
- **Negativo** (per tutte): `blurry, low quality, deformed hands, extra fingers, extra limbs, morphing face, changing outfit, text, watermark, flicker, static image`

## Nel gioco (lo faccio io)
- Taglio, ciclo senza stacchi, compressione (WebM/MP4 leggeri, misurati sul peso della pagina).
- Intro: il video con i miei effetti sopra (lampo, anelli, logo); menu: il video dietro i pulsanti al posto degli strati fermi.
- I video partono muti e in linea (anche su iPhone), si fermano e spariscono durante la lotta; FPS misurati prima e dopo.

## Com'è stata fatta l'intro (12-13/11, nel gioco dal 13/11)
- **Sul PC**: Comfy Desktop (`C:\comfy`), server sulla porta 8188; modelli in `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models`:
  `unet/Wan2.2-I2V-A14B-{High,Low}Noise-Q4_K_M.gguf` (9 GB l'uno), `loras/wan2.2_i2v_lightx2v_4steps_lora_v1_{high,low}_noise`,
  `frame_interpolation/rife_v4.26.safetensors`, `upscale_models/RealESRGAN_x4plus_anime_6B.pth`. Nodi ComfyUI-GGUF (con `gguf`
  installato nel `.venv` di ComfyUI, non nello `standalone-env`).
- **Script** (in `Documenti\voidrise-video`, fuori dal repository): `gen_flf.py <clip> <seme> [fast|full]` = una clip tra due
  fotogrammi chiave (`frames/k*.png`, 928×416); `gen_i2v.py` = da un'immagine sola; `gen_post.py` = Real-ESRGAN anime + RIFE ×2
  (16 → 32 fps); il montaggio e la compressione con PyAV dal Python di ComfyUI.
- **Cosa ha funzionato**: i **fotogrammi chiave disegnati da Denis** (`docs/ref/intro/`) con «primo e ultimo fotogramma»; prima
  bozze a 4 passi (circa 4 minuti l'una, 3-4 semi, tutte mandate a Denis) e poi la scelta. Da un'immagine sola il modello
  inventa male le coreografie a più tempi (pugni che si attraversano, parate confuse). I 20 passi (circa 50 minuti a clip) non
  sono stati migliori delle bozze nel movimento.
- **Scelte di Denis**: niente parata, solo lo scambio di pugni in faccia (Ren col sinistro, Kael col destro); clip `c1` (701)
  + `fin2` (1002), 4,5 s; nel gioco a 960×432, CRF 30 (0,6 MB).

## Per dopo: modelli 3D con ComfyUI (annotato il 12/11, non costruito)
Denis è d'accordo a provarlo più avanti. Hunyuan3D 2 (nei modelli pronti di ComfyUI; versione «mini» per la 3060 da 12 GB)
crea un `.glb` fermo da un'immagine: niente scheletro né animazioni. Uso previsto: oggetti e pezzi delle arene (colonne, archi,
stendardi, rocce, statue) e prove veloci di un personaggio prima di spendere crediti Meshy. I lottatori restano su Meshy.
Idea di Denis (12/11): l'«Anteprima arena» (https://claude.ai/artifact/9i779EszTGaKUBTJu2bTYh, La Grande Cascata con
strati di immagini da `cascata_atlas.jpg`) rifatta con i pezzi in 3D. Ogni elemento dell'immagine (archi, colonne, rocce,
stendardi, statue) ritagliato e trasformato in modello con Hunyuan3D, semplificato per il telefono e messo nella scena
three.js; cielo, montagne lontane e acqua delle cascate restano immagini o video (Hunyuan3D non fa acqua né cielo).
Misurare peso e FPS prima e dopo; la zona della lotta resta libera.
Deciso con Denis (12/11, da fare la sera del 12/11): prima prova sullo strato `docs/ref/arena/cascata_strato_rocce.png`
(rocce e cascata, sfondo trasparente). Rocce → rilievo 3D con la mappa di profondità (Depth Anything in ComfyUI), che tiene
il disegno com'è; cascata → acqua animata sopra (in codice o video in ciclo), con spruzzi e nebbia alla base. Hunyuan3D solo
per gli oggetti singoli (archi, colonne, statue, stendardi). Prima di scaricare: dire a Denis pesi esatti e aspettare l'ok.
Precisazione di Denis (12/11): la cascata dell'Anteprima arena va già bene e resta com'è (lo shader dell'acqua). Da rendere
più reale è **il resto**: rocce, pareti, colline e pezzi dell'arena in 3D (rilievo dalla profondità o Hunyuan3D per gli oggetti).
