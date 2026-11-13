# Pose di Ren: editor di pose chiave (13/11/2026)

## Perché
Denis: "mi puoi fare un'anteprima del personaggio dove posso muoverlo come voglio toccando per esempio le gambe o le
braccia per fare nuove animazioni? così capisci meglio cosa intendo". Serve a lui per mostrare a Claude le animazioni
che ha in mente, senza lunghe descrizioni e senza rifare le cose molte volte.

## Approcci considerati
- **A, scelto da Denis**: solo pose chiave, come le sue tavole (posa 1, 2, 3...), un "Riproduci" che le mostra in
  fila a velocità fissa; i tempi li dice a parole (note). Semplice da usare sul telefono.
- B: una linea del tempo con i fotogrammi di ogni posa. Più preciso sui tempi, più complicato da toccare sul telefono.

## Cosa fa
- Lo stesso Ren della pagina delle tecniche (kit.js): stessa guardia, stesso risolutore (gambe e braccia per IK,
  piedi in appoggio fermi). La guardia è la prima posa di ogni animazione nuova.
- Punti da trascinare: testa (il punto davanti al viso, dove guarda), busto (piega), bacino (sposta e abbassa),
  mani, gomiti (da che parte si piega il braccio), piedi (sposta e alza), tutto il corpo. Si muovono nel piano di
  fronte alla camera; per la profondità si gira la vista (Lato, 3/4, Fronte o trascinando).
- Per mano: Pugno / Socchiusa / Aperta, Palmo giù / di lato / su, Polso avanti / dritto / indietro. Per piede:
  tallone giù / su / punta, punta in aria tesa / normale / a martello, gira. Busto, bacino e testa: gira.
- Pose numerate in alto, + Posa (copia quella corrente), Elimina, Riproduci (24 fotogrammi da una posa all'altra,
  tenuta sull'ultima, poi torna alla prima), Annulla, Guardia, Note (nome, note per Claude, nota della posa,
  animazioni salvate, nuova animazione, copia dei dati).
- Tocco, mouse, tastiera e controller per tutto (tasti e controller nel suggerimento in basso).
- Salvataggio automatico nel database della pagina (raccolta `animazioni`, un documento per animazione, con la
  legenda dei numeri dentro), e su questo dispositivo quando il database non c'è.

## Scelte di Claude
- Mani nel riferimento del busto (il busto che gira o si piega porta le braccia con sé); gomito come "lato verso
  cui si piega" (mai un punto: così muovere la mano dopo non lo ribalta); rotazione del palmo e piega del polso
  misurate sull'avambraccio, quindi sempre definite.
- Zoom con due dita: si avvicina alla parte scelta, non al viso.
- Grafica sola: lo stato del combattimento non cambia; costo per fotogramma +0,02 ms rispetto alla guardia.

## Per dopo (non costruito)
- Linea del tempo con i fotogrammi (approccio B), se le note non bastano.
- Ginocchia trascinabili, inclinazione della testa, specchiare una posa.
- Eliminare un'animazione salvata.
