# Mani e polsi di Kael rifatti: mano di Ren, guanto vero, anello vero (17/11/2026)

## Perché
Denis, sull'anteprima di Kael (versione 21): "non mi piace ancora il modello 3d in generale, la testa ecc va anche bene
ma il resto no", poi "a me non piacciono soprattutto le mani", "ora il polso", e sulle 4 zone cerchiate del polso:
"è ancora fatto male". Su mani e polsi ci sono già stati più di dieci giri di ritocchi (`docs/meshy/KAEL.md`, da "Mani di
Ren" a "Zone cerchiate in guardia"): i ritocchi a quello che c'è non bastano, serve cambiare come sono fatti.

Cosa non va adesso (confronto con Ren e coi fogli, 17/11):
- **mani**: dita a blocchi con le facce piatte (il pollice aperto sembra una matita a sei lati), dita marroni più scure
  del braccio, guanto prugna senza forma che copre il dorso come un calzino e le dita ammucchiate sopra (pugno piccolo e
  finto). Sono le mani di Ren, ma su Kael non gli somigliano: la pittura ricampionata nella mappa del busto, la luce e il
  guanto dipinto sulla pelle le cambiano;
- **polso** (le 4 zone cerchiate da Denis): il guanto si stringe come un collo di bottiglia e il bracciale si allarga
  subito dopo (il pugno sembra su un bastone); l'anello viola da un lato quasi non si vede; nel pugno dall'anello esce
  un lembo e dentro il polso ci sono macchie nere e pezzi strappati.

## Strade considerate (scelta di Denis: la 2)
1. Ritocchi a mani e polsi di adesso (gratis, veloce): dita lisce, polso riempito, anello pulito. Scartata: è quello che
   si fa da dieci giri.
2. **Mano e polso di Ren interi, con guanto e anello veri sopra** (gratis, più lavoro). **Scelta.**
3. Mani nuove da Meshy (circa 30 crediti, saldo 970): scartata, risultato incerto (sul busto Meshy ha fatto pollici in
   più e dita attaccate).

## Obiettivi
- La pelle delle mani di Kael si vede **come quella di Ren** su Ren: stessa forma, stessa pittura, stessa luce, stesso
  contorno, nelle stesse pose. Misura: le due mani accanto dagli stessi lati, la pelle con gli stessi colori.
- Il **mezzo guanto è un pezzo vero** sopra la pelle (un guscio sottile), non un colore dipinto: dorso e palmo fino alle
  nocche, base del pollice dentro, dita e pollice scoperti come nel foglio del busto; il bordo una riga d'inchiostro
  netta; il guscio ha il suo volume e la sua sagoma.
- **Al polso un anello viola vero**, in rilievo, che fa tutto il giro come nel disegno e copre l'attacco tra bracciale e
  guanto: niente collo, niente lembo, niente macchie o pezzi strappati, da ogni lato e in ogni mossa.
- I colori restano quelli dei fogli del busto (guanto e bracciale prugna scuro, anello viola).

## Fuori dal lavoro
- Testa, occhi e sopracciglia (non si toccano), busto, braccia sopra il polso, gambe, fascia.
- Ren: non cambia niente.
- Niente Meshy, niente agenti sul corpo (regole di Denis per Kael).
- La punta viola dietro il pugno destro (l'ala della spalla del vestito): domanda a parte per Denis.

## Da non fare (sarebbe un fallimento anche se funziona)
- Una mano che di nuovo non sembra quella di Ren.
- Un guanto che sembra dipinto o che sfarfalla sulla pelle sotto (pelle che buca il guscio).
- Il pugno che si apre o si deforma, l'anello che si stacca dal polso quando il polso piega.
- Pubblicare senza l'ok di Denis sulle immagini.

## Come (deciso)
- Le mani diventano **parti a sé** del pacchetto di Kael, come la testa e il busto (`mdPartData` in `src/e_model.js`),
  invece di essere dentro il busto:
  - **mani**: i triangoli delle mani di Ren presi dal suo pacchetto con le sue coordinate di pittura, la sua pittura
    (ritagliata attorno alle mani, non ricampionata), le sue normali per la luce, il suo materiale; messe e scalate sulle
    ossa delle mani di Kael come adesso (`HAND_MUL` 0,9, la posa dei pugni di Ren);
  - **guanto**: un guscio di qualche millimetro sopra la pelle della mano nella zona del guanto di adesso (dorso, palmo
    fino alle nocche, base del pollice), con i pesi della pelle sotto, la luce del gioco e una riga d'inchiostro sul
    bordo; verso il polso si allarga fino a entrare nell'anello (via il collo);
  - **anello**: un tubo corto e un po' bombato attorno al polso, alto come la banda viola del foglio, più largo sia del
    bracciale sia del guanto, attaccato all'avambraccio e in parte alla mano, così copre l'attacco anche col polso
    piegato.
- Nel busto si nascondono mani, guanti dipinti e la fine del polsino di Meshy oltre il bracciale (dove ci sono il lembo e
  le macchie).

## Scelte mie (da correggere se Denis non è d'accordo)
- La mano di Ren è quella che il gioco disegna col suo look (`CFG.looks.ren`: pittura `viewer_assets/ren/ren_painted.jpg`,
  ossa delle dita del look), senza la sua fascia del polso.
- Pugno con la posa di Ren com'è, pollice compreso (Denis, 12/11: "taglia i pugni di ren e attaccali a kael"); la base
  del pollice sta dentro il guanto vero. Se il "cuneo" della base del pollice torna a vedersi, si ripiega il pollice come
  nella versione 21 (`thumb_fist`) e lo si dice a Denis.
- Solo l'anteprima di Kael (`viewer_kael.html`): Kael nel gioco resta il lottatore provvisorio.

## Lasciato a chi costruisce
- Spessori e distanze esatti (guscio, anello), come misurarli e le soglie dei controlli.
- Come ritagliare la pittura di Ren e come portare le sue normali.
- I pesi dell'anello tra avambraccio e mano.

## Come si prova
- Mani di Kael e di Ren accanto, dagli stessi 8 lati per mano, a pugno e aperte, nelle stesse mosse (guardia, pugni,
  calci, accovacciato, speciale e presa a mani aperte, colpito, a terra).
- Polso da vicino dagli stessi lati e nelle stesse mosse: niente collo, lembo, macchie, buchi, pelle che buca il guanto.
- `bash mk.sh`, i 22 test, `tests/viewer_check.py --page=viewer_kael.html` con le prove nuove (parti presenti, numeri
  finiti, guanto sopra la pelle); triangoli e tempo per fotogramma prima e dopo.
- Immagini a Denis; si pubblica l'anteprima di Kael solo col suo ok.
