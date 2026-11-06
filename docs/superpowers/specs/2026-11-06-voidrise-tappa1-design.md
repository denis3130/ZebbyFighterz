# Voidrise Fighters — Design (visione generale + Tappa 1 "Basi del combattimento")

Data: 6/11/2026 · Approvato a voce da Denis in chat, da rileggere qui.
Immagini di riferimento in `docs/ref/`: `riferimento-stile.png` (stile generale, menu, interfaccia), `sfondo-cascata.png` (arena della Tappa 1), `sfondo-rovine.png` (seconda arena, per dopo), `personaggi/ren.png` e `personaggi/kael.png` (i primi 2 lottatori per Meshy).

## 1. Visione

Picchiaduro anime 2.5D **originale**, ispirato al genere dei picchiaduro a squadre (stile FighterZ) senza copiarne nomi, personaggi, mosse o grafica.

- **Obiettivo**: gioco da vendere su **Steam** e negli **store dei telefoni** (Google Play, App Store).
- **Modalità**: contro il computer (arcade, allenamento) e **2 giocatori in locale**. L'**online** arriva dopo: per questo la logica è deterministica fin dal primo giorno.
- **Roster "multiverso"**: combattenti anime, dark fantasy e cyber, con **personaggi sbloccabili**. Tutti resi con lo stesso stile (contorno nero, ombre a fasce, aure luminose) così il gioco resta coerente.
- **Personaggi**: modelli **Meshy** con scheletro e animazioni Meshy. Primi 2: **Ren** (capelli neri, gilet verde acqua, fascia arancione, braccia bendate) e **Kael** (capelli bianchi, abiti viola e neri, mezzi guanti). Immagini in `docs/ref/personaggi/`. Da controllare per prime in Meshy: pantaloni larghi e fasce lunghe durante i calci. Prima di spendere crediti: saldo + costo stimato + ok di Denis.
- **Formato scontri**: si parte **1 contro 1**, il codice è pronto per le **squadre 3v3** (cambio personaggio e assist) da aggiungere dopo.
- **Tecnologia**: **Three.js r128**, JavaScript vanilla, moduli in `src/` uniti in un solo HTML (come Stormblade). Poi pacchetti con **Electron** (Steam) e **Capacitor** (telefoni).

## 2. Stile (dal riferimento)

- Anime brillante: colori saturi, contorno nero, cel-shading a 2-3 fasce, effetti energetici azzurri (Ren) e viola (Kael).
- **Arena 1 "La Grande Cascata"** (`docs/ref/sfondo-cascata.png`): una sola grande cascata al centro tra due rupi verdi, cielo azzurro, a sinistra colonna con stendardo rosso, a destra lanterna di pietra, pavimento di lastre di pietra largo e piatto. Scelta perché il centro è pulito e i lottatori si leggono bene.
- **Arena 2 "Rovine dell'acquedotto"** (`docs/ref/sfondo-rovine.png`): per dopo.
- **Interfaccia di combattimento**: ritratto + nome agli angoli alti, barre della vita gialle oblique, timer al centro in un riquadro a punta, contatore combo grande ("4 COLPI"), in basso barra dell'energia a segmenti azzurri con il livello accanto.
- **Menu principale**: logo "VOIDRISE FIGHTERS", voci Gioca / Personaggi / Allenamento / Impostazioni su pulsanti obliqui (attivo arancione, gli altri scuri).
- Limite onesto: il riferimento è un'illustrazione 2D; il gioco in 3D cel-shading gli somiglierà in colori, contorni, effetti e interfaccia, non sarà identico al disegno.

## 3. Le tappe

1. **Basi del combattimento** (questo documento): 1v1 con 2 lottatori provvisori, giocabile in 2.
2. I **2 personaggi Meshy** (Ren e Kael) con animazioni e mosse proprie.
3. **Super**, aure, telecamera cinematografica, effetti speciali.
4. **Avversario del computer**, modalità arcade e allenamento completo.
5. **Menu completi**, selezione personaggi, sblocchi, salvataggi, audio.
6. **Squadre 3v3**, poi pacchetti Steam/telefoni, poi **online** (rollback).

Dopo ogni tappa: versione giocabile pubblicata come pagina Claude.

## 4. Tappa 1 — Architettura

- **Struttura**: `src/` con moduli uniti da `mk.sh` + `build.py` in `index.html` (giocabile) e `game_w.html` (test, espone `window.__VF`). Tutti i numeri di bilanciamento in `src/a0_cfg.js` (oggetto `CFG`). `three.min.js` r128 nel repository per i test.
- **Logica (simulazione)**: passo fisso a **60 al secondo**, solo numeri interi o arrotondati in modo stabile, nessun `Math.random` libero (generatore con seme), nessun uso del tempo reale. Stato completo della partita copiabile (serve per l'online e per i test). Con gli stessi comandi produce sempre lo stesso risultato.
- **Grafica**: legge lo stato della logica e lo disegna (modelli, animazioni, effetti, telecamera, interfaccia). Non cambia mai lo stato. Sostituire i lottatori provvisori con i modelli Meshy non tocca la logica.
- **Comandi**: tastiera, controller e tasti touch producono per ogni giocatore lo stesso "pacchetto comandi" per fotogramma (direzione + tasti premuti). La logica vede solo quello.
- **Pronto per 3v3**: la partita contiene per ogni lato una lista di lottatori (per ora di 1), con un "lottatore attivo".

## 5. Tappa 1 — Combattimento

**Movimento**
- Camminata avanti/indietro, accovacciarsi, salto (verticale, avanti, indietro).
- **Scatto a terra**: tasto Scatto, oppure doppio tocco avanti (tastiera/controller). Scatto indietro con indietro + Scatto.
- I lottatori si girano sempre verso l'avversario; non si attraversano; restano dentro l'arena.
- Rimandati a dopo: scatto in volo, scatto "a razzo", doppio salto.

**Attacchi: 3 tasti**
- **Pugno** e **Calcio**: tocco breve = colpo normale (parte al rilascio), tenuto ~0,2 s (valore in `CFG`) = **colpo forte**, con lampo di carica visibile.
- Ogni colpo cambia se in piedi, accovacciato o in salto.
- **Combo**: tocchi ripetuti dello stesso tasto concatenano i colpi; da normale si può passare a forte e da pugno a calcio entro una finestra di tempo.
- **Lancio in aria**: basso + Calcio forte; si può inseguire con un salto e colpire in aria.
- **Speciale**: colpo energetico a distanza (un solo proiettile alla volta per lottatore). Nella Tappa 3 lo stesso tasto servirà per le super.
- **Presa**: Pugno + Calcio insieme da vicino; batte la guardia.

**Difesa**
- **Guardia**: tasto Guardia, oppure tenere indietro (tastiera/controller). In piedi para i colpi alti e medi, accovacciati para i bassi; i colpi in salto vanno parati in piedi.
- La parata subisce una piccola spinta indietro, nessun danno (tranne lo Speciale: piccolo danno).
- Dopo essere finiti a terra: rialzo automatico, con capriola avanti/indietro se si tiene una direzione.

**Regole del colpo**
- Ogni mossa ha in `CFG`: fotogrammi di preparazione / attivi / recupero, zona che colpisce, danno, stordimento, spinta, tipo (alto / medio / basso / presa / proiettile).
- Ogni lottatore ha zone che possono essere colpite (corpo, testa).
- **Danno che cala nelle combo**: ogni colpo successivo fa una percentuale minore; nessuna combo infinita (limite di stordimento in combo).

**Partita**
- Barra della vita, barra dell'energia (si riempie colpendo ed essendo colpiti; usata dalla Tappa 3), timer 99 s, **al meglio di 3 round**, scritte di inizio/fine round ("ROUND 1", "COMBATTI!", "K.O.", "TEMPO!").

**Game feel**
- Hitstop sui colpi (più lungo sui forti), lampo bianco sul colpito, scintille, leggero tremolio dello schermo sui forti, il colpito si schiaccia, contatore combo che rimbalza, barra della vita persa che cala piano, pulsanti touch che si schiacciano.
- Gli effetti non allungano la partita: si misura la durata media di un round prima e dopo.

## 6. Tappa 1 — Schermo e comandi

- **Arena "La Grande Cascata"**: l'immagine usata come **fondale dipinto** (compressa in JPG, ~300-500 KB), leggermente schiarita e con meno contrasto perché i lottatori risaltino. La linea del pavimento dell'immagine è la linea dei piedi.
  - **L'acqua scorre**: sulla zona della cascata (maschera) uno shader fa scorrere la texture verso il basso con un leggero tremolio e schiuma alla base. Costo minimo (un solo piano).
  - **Foglie** che volano davanti (poche particelle) e leggero spostamento del fondale quando la telecamera si muove, per dare profondità.
  - Il colpo energetico di Ren è più bianco e luminoso dell'acqua, così non si confonde con la cascata.
- **Telecamera** di lato che segue il centro dei due lottatori e si allontana un poco quando si separano (zoom limitato perché il fondale resti credibile).
- **Lottatori provvisori**: costruiti in codice, stile cel-shading con contorno, uno verde acqua/arancione (richiama Ren) e uno viola/bianco (richiama Kael).
- **Interfaccia**: come al punto 2, con ritratti provvisori.
- **Schermata iniziale** essenziale nello stile del menu del riferimento: "1 Giocatore (allenamento)" e "2 Giocatori". In allenamento l'avversario è fermo o si muove a caso (scelta nel menu di pausa).
- **Telefono (solo orizzontale)**: levetta a sinistra; a destra tasti grandi **Pugno**, **Calcio**, **Speciale** e sotto **Scatto** e **Guardia**, come nel riferimento. Se il telefono è in verticale, schermata "gira il telefono".
- **Tastiera**: G1 = WASD + J (Pugno), K (Calcio), L (Speciale), U (Scatto), I (Guardia). G2 = frecce + tastierino 1/2/3, 4 (Scatto), 5 (Guardia).
- **Controller**: fino a 2 (Gamepad API); levetta/croce, X/Quadrato = Pugno, A/Croce = Calcio, B/Cerchio = Speciale, dorsale destro = Scatto, dorsale sinistro = Guardia. Il primo controller va al G1 se non c'è tastiera in uso.
- **Pausa**: Esc / Start / tasto a schermo; riprendi, ricomincia, torna al menu.

## 7. Tappa 1 — Test e consegna

Test automatici con Playwright (come Stormblade, `python3 tests/run.py ...`):
- **Determinismo**: stessa sequenza di comandi due volte → stato finale identico.
- Tocco = colpo normale, tenuto = colpo forte.
- Combo: il danno cala; la combo finisce entro il limite.
- Guardia alta/bassa, presa batte guardia, Speciale e proiettile unico.
- Fine round per K.O. e per tempo; fine partita al meglio di 3.
- Touch su viewport da telefono in orizzontale; schermata "gira il telefono" in verticale.
- Due giocatori da tastiera nello stesso momento.
- Nessun errore in console.
- **FPS**: misurati con un round automatico; obiettivo 60 su telefono di fascia media.

**Consegna**: pagina Claude giocabile con `index.html`; 2-3 righe su cosa è cambiato, FPS e come provarlo.

## 8. Fuori dalla Tappa 1 (per dopo)

Modelli Meshy, super e aure, scatto in volo/a razzo, doppio salto, avversario intelligente, selezione personaggi, sblocchi, salvataggi, musica e suoni completi, 3v3 con assist, Electron/Capacitor, online rollback.
