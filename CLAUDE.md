# Voidrise Fighters — istruzioni per Claude

Rispondi sempre a Denis **in italiano**, con messaggi brevi e chiari (spesso usa il telefono).

- Picchiaduro anime 2.5D originale in **Three.js r128**, JavaScript vanilla. PC, telefono (**solo orizzontale**) e controller. Obiettivo: Steam e store dei telefoni.
- Design approvato: `docs/superpowers/specs/2026-11-06-voidrise-tappa1-design.md`. Riferimento visivo: `docs/ref/riferimento-stile.png`.
- Logica di combattimento deterministica a 60 passi fissi (serve per l'online futuro); la grafica legge lo stato e non lo cambia.
- Tutti i numeri di bilanciamento in `src/a0_cfg.js` (oggetto `CFG`).

## Regole di lavoro di Denis
- Giochi completi e curati: niente emoji al posto della grafica, niente combattimenti fatti solo di numeri.
- Tappe piccole e verificabili: dopo ogni tappa una versione giocabile.
- Ogni funzione va su touch, mouse e tastiera, e controller.
- Game feel: hitstop, lampo, leggero tremolio, colpiti che si schiacciano, contatori che rimbalzano, pulsanti che si schiacciano.
- Gli effetti non allungano le lotte: misura prima e dopo. Misura gli FPS prima e dopo (obiettivo 60 su telefono medio).
- Contenuti originali: ispirati al genere, senza copiare nomi, personaggi o grafica di altri giochi.
- Meshy: prima di spendere crediti mostra a Denis saldo e costo stimato, e procedi solo con il suo ok.
- Consegna: 2-3 righe su cosa è cambiato, FPS e come provarlo; idee "per dopo" annotate senza costruirle; chiudi con un solo passo successivo concreto.
