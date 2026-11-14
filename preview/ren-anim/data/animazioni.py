#!/usr/bin/env python3
"""Ren's animations for the "Pose di Ren" page (mods/posa.js), made by Claude on Denis's request (14/11/2026):
"creami tantissime animazioni, inventatene almeno 50 [...] basta che siano fatte bene e senza bug o comportamenti del
corpo strane".

Each animation is a list of key poses built from the page's ready positions (the same buttons Denis has), each pose
with its own timing: t frames to reach it (60 a second), h frames held on it, e its ease ('snap': faster and faster
into it, a strike that lands at full speed; 'out': fast, then slowing; none: even, from rest to rest). A pose is the one
before it with some choices changed; guard=True brings everything back to the guard (the place stays unless passo is
given). The first pose of every animation is the guard.

    python3 data/animazioni.py            writes data/animazioni.json (the documents, as the page saves them)

The documents go into the page's database (collection "animazioni", one document per animation: id "c-<name>").
"""
import json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = dict(bA='guardia', mA='pugno', bD='guardia', mD='socchiusa', gA='terra', gD='terra', busto='dritto', alt='normale', passo='qui')
VALUES = {
    'bA': {'guardia', 'avanti', 'alto', 'viso', 'gomito', 'basso'}, 'bD': {'guardia', 'avanti', 'alto', 'viso', 'gomito', 'basso'},
    'mA': {'pugno', 'socchiusa', 'aperta'}, 'mD': {'pugno', 'socchiusa', 'aperta'},
    'gA': {'terra', 'ginocchio', 'calcio', 'basso'}, 'gD': {'terra', 'ginocchio', 'calcio', 'basso'},
    'busto': {'dritto', 'avanti', 'indietro'}, 'alt': {'normale', 'basso', 'alto'}, 'passo': {'indietro', 'qui', 'avanti', 'avanti2'},
}
CATS = ['Colpi', 'Calci', 'Combinazioni', 'Difese', 'Movimenti', 'Speciali']
ANIMS = []


def s(t, note='', e=None, h=0, guard=False, **ch):
    """One key pose: reached in t frames (ease e), held h frames, with these choices changed."""
    return dict(t=t, note=note, e=e, h=h, guard=guard, ch=ch)


def anim(key, name, cat, note, *steps):
    assert cat in CATS, cat
    poses, cur = [dict(GUARD, note='Guardia')], dict(GUARD)
    for st in steps:
        if st['guard']:
            place = cur['passo']
            cur = dict(GUARD); cur['passo'] = place
        for k, v in st['ch'].items():
            assert k in VALUES and v in VALUES[k], (key, k, v)
            cur[k] = v
        p = dict(cur, note=st['note'], t=st['t'])
        if st['h']: p['h'] = st['h']
        if st['e']: p['e'] = st['e']
        poses.append(p)
    assert all(a['passo'] == 'qui' for a in poses[:1]) and 2 <= len(poses) <= 24, key
    ANIMS.append(dict(key=key, name=name, cat=cat, note=note, poses=poses))


G = dict(guard=True)   # (back to the guard)

# ---------------------------------------------------------------------------------------------------- Colpi (strikes)
anim('jab', 'Pugno avanti', 'Colpi', 'Il jab: il pugno torna un attimo davanti al viso e riparte secco.',
     s(5, 'Il pugno davanti torna davanti al viso', bA='viso'),
     s(5, 'Impatto: il pugno esce dritto, la spalla entra', 'snap', 3, bA='avanti'),
     s(12, 'Torna in guardia', 'out', **G))
anim('diretto', 'Diretto dietro', 'Colpi', 'Il pugno della mano dietro: le anche girano e portano la spalla.',
     s(7, 'Impatto: la spalla dietro entra, il pugno dritto, la mano davanti copre il viso', 'snap', 3, bD='avanti', mD='pugno', bA='viso'),
     s(14, 'Torna in guardia', 'out', **G))
anim('palmo', 'Palmo a scatto', 'Colpi', 'La tecnica delle tavole: carica breve, il palmo esce dritto.',
     s(9, 'Carica: la mano si apre davanti al viso, il peso indietro', bA='viso', mA='aperta', busto='indietro'),
     s(5, 'Impatto: il palmo spinge, il busto va avanti', 'snap', 3, bA='avanti', busto='avanti'),
     s(16, 'Torna in guardia', 'out', **G))
anim('palmo_dietro', 'Palmo dietro', 'Colpi', 'Il palmo della mano dietro, con la spalla che entra.',
     s(9, 'Carica: la mano dietro si apre vicino alla testa', bD='viso', mD='aperta', busto='indietro', bA='viso'),
     s(6, 'Impatto: palmo dritto, la spalla dietro avanti', 'snap', 3, bD='avanti', busto='avanti'),
     s(16, 'Torna in guardia', 'out', **G))
anim('doppio_palmo', 'Doppio palmo', 'Colpi', 'Raccoglie le mani e spinge con tutte e due.',
     s(10, 'Raccoglie: le mani aperte davanti al viso, scende', bA='viso', bD='viso', mA='aperta', mD='aperta', alt='basso'),
     s(6, 'Spinta: due palmi dritti, il busto avanti', 'snap', 4, bA='avanti', bD='avanti', busto='avanti', alt='normale'),
     s(18, 'Torna in guardia', 'out', **G))
anim('montante', 'Montante', 'Colpi', 'Dal basso verso l\'alto: le gambe spingono il pugno.',
     s(8, 'Scende sulle gambe, il pugno davanti basso', alt='basso', bA='basso', busto='avanti'),
     s(6, 'Sale: il pugno in alto, le gambe si distendono', 'snap', 3, bA='alto', alt='alto', busto='indietro'),
     s(16, 'Torna in guardia', 'out', **G))
anim('gomitata', 'Gomitata', 'Colpi', 'Il gomito davanti, corto e duro, a distanza ravvicinata.',
     s(7, 'Carica: il braccio si raccoglie davanti al viso', bA='viso'),
     s(5, 'Impatto: il gomito gira in orizzontale', 'snap', 3, bA='gomito', busto='avanti'),
     s(14, 'Torna in guardia', 'out', **G))
anim('gomitata_dietro', 'Gomitata dietro', 'Colpi', 'Il gomito dietro che gira in avanti con le anche.',
     s(7, 'Impatto: il gomito dietro passa davanti al petto, la mano davanti copre', 'snap', 3, bD='gomito', mD='pugno', busto='avanti', bA='viso'),
     s(14, 'Torna in guardia', 'out', **G))
anim('palmo_basso', 'Palmo basso', 'Colpi', 'Scende e colpisce basso con la mano aperta.',
     s(7, 'Scende e spinge in basso col palmo', 'snap', 3, alt='basso', bA='basso', mA='aperta'),
     s(14, 'Torna in guardia', 'out', **G))
anim('pugno_basso', 'Pugno basso', 'Colpi', 'Accucciato, il pugno dietro colpisce basso.',
     s(7, 'Accucciato, il pugno dietro va basso, la mano davanti copre', 'snap', 3, alt='basso', bD='basso', mD='pugno', busto='avanti', bA='viso'),
     s(14, 'Torna in guardia', 'out', **G))
anim('palmo_alto', 'Palmo che sale', 'Colpi', 'Parte dal basso e sale col palmo aperto.',
     s(8, 'Scende, la mano aperta in basso', alt='basso', bA='basso', mA='aperta'),
     s(6, 'Sale col palmo in alto', 'snap', 3, alt='alto', bA='alto'),
     s(16, 'Torna in guardia', 'out', **G))
anim('martello', 'Pugno a martello', 'Colpi', 'Alza il pugno e lo cala dall\'alto.',
     s(9, 'Alza il pugno, si allunga', bA='alto', alt='alto'),
     s(5, 'Lo cala in basso, scende con tutto il corpo', 'snap', 4, bA='basso', alt='basso', busto='avanti'),
     s(16, 'Torna in guardia', 'out', **G))
anim('passo_palmo', 'Passo e palmo', 'Colpi', 'Entra con un passo e colpisce col palmo.',
     s(16, 'Passo avanti, la mano si apre davanti al viso', passo='avanti', bA='viso', mA='aperta'),
     s(5, 'Palmo', 'snap', 3, bA='avanti', busto='avanti'),
     s(12, 'Guardia', 'out', **G),
     s(16, 'Passo indietro', passo='qui'))
anim('passo_diretto', 'Passo e diretto', 'Colpi', 'Un passo dentro e il pugno dietro.',
     s(16, 'Passo avanti', passo='avanti'),
     s(6, 'Diretto, la mano davanti copre', 'snap', 3, bD='avanti', mD='pugno', bA='viso'),
     s(14, 'Guardia', 'out', **G),
     s(16, 'Passo indietro', passo='qui'))
anim('pugno_alto', 'Pugno alto', 'Colpi', 'Il pugno davanti sale dritto sopra la testa.',
     s(6, 'Sale: il pugno davanti in alto, sulle punte', 'snap', 3, bA='alto', alt='alto'),
     s(14, 'Torna in guardia', 'out', **G))

# ---------------------------------------------------------------------------------------------------- Calci (kicks)
anim('frontale', 'Calcio frontale', 'Calci', 'Ginocchio su, calcio di pianta, richiama, appoggia.',
     s(8, 'Ginocchio su, il piede sotto', gA='ginocchio'),
     s(5, 'Calcio: colpisce con la pianta', 'snap', 3, gA='calcio'),
     s(7, 'Richiama la gamba', 'out', gA='ginocchio'),
     s(10, 'Appoggia, guardia', **G))
anim('frontale_dietro', 'Calcio frontale dietro', 'Calci', 'Lo stesso calcio con la gamba dietro: più forte, più lento.',
     s(9, 'Il ginocchio dietro viene avanti e sale', gD='ginocchio'),
     s(6, 'Calcio di pianta', 'snap', 3, gD='calcio'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia, guardia', **G))
anim('ginocchiata', 'Ginocchiata', 'Calci', 'Afferra con le mani e tira giù sul ginocchio.',
     s(7, 'Le mani avanti, aperte, ad afferrare', bA='avanti', bD='avanti', mA='aperta', mD='aperta'),
     s(6, 'Ginocchio in avanti, le mani tirano giù', 'snap', 4, gD='ginocchio', bA='basso', bD='basso', busto='avanti'),
     s(14, 'Torna in guardia', 'out', **G))
anim('calcio_basso', 'Calcio basso', 'Calci', 'Un colpo secco allo stinco con la gamba davanti.',
     s(6, 'Colpisce lo stinco', 'snap', 3, gA='basso'),
     s(12, 'Torna in guardia', 'out', **G))
anim('calcio_basso_dietro', 'Calcio basso dietro', 'Calci', 'La gamba dietro spazza in avanti, bassa.',
     s(7, 'La gamba dietro colpisce basso', 'snap', 3, gD='basso'),
     s(14, 'Torna in guardia', 'out', **G))
anim('calcio_saltato', 'Calcio saltato', 'Calci', 'Carica, salta e calcia in aria, atterra morbido.',
     s(8, 'Carica sulle gambe, le mani alzate', alt='basso', bA='viso', bD='viso', mD='pugno'),
     s(8, 'In aria: calcio avanti, l\'altro ginocchio su', 'out', 4, gA='calcio', gD='ginocchio', alt='normale', bA='guardia', bD='guardia'),
     s(10, 'Atterra piegando le gambe', gA='terra', gD='terra', alt='basso'),
     s(14, 'Guardia', **G))
anim('doppio_calcio', 'Doppio calcio', 'Calci', 'Un calcio per gamba, uno dopo l\'altro.',
     s(7, 'Ginocchio davanti su', gA='ginocchio'),
     s(5, 'Primo calcio', 'snap', 2, gA='calcio'),
     s(8, 'Appoggia', 'out', gA='terra'),
     s(7, 'Ginocchio dietro avanti', gD='ginocchio'),
     s(5, 'Secondo calcio', 'snap', 3, gD='calcio'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Guardia', **G))
anim('pestone', 'Pestone', 'Calci', 'Alza il ginocchio e pesta a terra con forza.',
     s(9, 'Alza il ginocchio davanti', gA='ginocchio', bA='viso'),
     s(4, 'Pesta: scende con tutto il peso', 'snap', 5, gA='terra', alt='basso', bA='basso', busto='avanti'),
     s(14, 'Torna in guardia', 'out', **G))
anim('ginocchiata_volante', 'Ginocchiata volante', 'Calci', 'Salta portando il ginocchio avanti, le mani ad afferrare.',
     s(8, 'Carica sulle gambe', alt='basso'),
     s(8, 'In aria: il ginocchio avanti, le mani afferrano', 'out', 4, gA='ginocchio', gD='ginocchio', alt='normale', bA='avanti', bD='avanti', mA='aperta', mD='aperta'),
     s(10, 'Atterra', gA='terra', gD='terra', alt='basso', bA='guardia', bD='guardia', mA='pugno', mD='socchiusa'),
     s(14, 'Guardia', **G))
anim('passo_calcio', 'Passo e calcio', 'Calci', 'Un passo per accorciare, poi il calcio frontale.',
     s(16, 'Passo avanti', passo='avanti'),
     s(8, 'Ginocchio su', gA='ginocchio'),
     s(5, 'Calcio', 'snap', 3, gA='calcio'),
     s(7, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Appoggia', gA='terra'),
     s(16, 'Passo indietro', passo='qui'))
anim('basso_alto', 'Calcio basso e alto', 'Calci', 'Basso allo stinco, richiama senza appoggiare, alto al petto.',
     s(6, 'Basso', 'snap', 2, gA='basso'),
     s(7, 'Richiama, il piede resta su', 'out', gA='ginocchio'),
     s(5, 'Alto', 'snap', 3, gA='calcio'),
     s(8, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Appoggia, guardia', **G))
anim('calcio_dietro_passo', 'Passo e calcio dietro', 'Calci', 'Entra di un passo e calcia con la gamba dietro.',
     s(16, 'Passo avanti', passo='avanti'),
     s(9, 'Il ginocchio dietro avanti', gD='ginocchio'),
     s(6, 'Calcio', 'snap', 3, gD='calcio'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia', gD='terra'),
     s(16, 'Passo indietro', passo='qui'))

# ---------------------------------------------------------------------------------------------- Combinazioni (combos)
anim('uno_due', 'Uno-due', 'Combinazioni', 'Jab e diretto, la base.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(5, 'Jab', 'snap', 2, bA='avanti'),
     s(6, 'Diretto, il braccio davanti torna', 'snap', 3, bA='viso', bD='avanti', mD='pugno'),
     s(14, 'Guardia', 'out', **G))
anim('uno_due_palmo', 'Uno-due-palmo', 'Combinazioni', 'Jab, diretto e chiude col palmo.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(5, 'Jab', 'snap', 2, bA='avanti'),
     s(6, 'Diretto', 'snap', 2, bA='viso', bD='avanti', mD='pugno'),
     s(6, 'Carica il palmo', bD='guardia', mD='socchiusa', bA='viso', mA='aperta'),
     s(5, 'Palmo', 'snap', 3, bA='avanti', busto='avanti'),
     s(16, 'Guardia', 'out', **G))
anim('palmo_ginocchio', 'Palmo e ginocchiata', 'Combinazioni', 'Il palmo apre la guardia, il ginocchio chiude.',
     s(5, 'Palmo', 'snap', 2, bA='avanti', mA='aperta', busto='avanti'),
     s(7, 'Afferra con le due mani', bA='avanti', bD='avanti', mD='aperta', busto='dritto'),
     s(6, 'Ginocchiata, tira giù', 'snap', 4, gD='ginocchio', bA='basso', bD='basso', busto='avanti'),
     s(14, 'Guardia', 'out', **G))
anim('jab_calcio_basso', 'Jab e calcio basso', 'Combinazioni', 'Distrae in alto, colpisce in basso.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(5, 'Jab', 'snap', 2, bA='avanti'),
     s(6, 'Calcio basso, il braccio torna', 'snap', 3, bA='guardia', gA='basso'),
     s(12, 'Guardia', 'out', **G))
anim('calcio_diretto', 'Calcio e diretto', 'Combinazioni', 'Calcio frontale, appoggia avanti e diretto.',
     s(8, 'Ginocchio su', gA='ginocchio'),
     s(5, 'Calcio', 'snap', 2, gA='calcio'),
     s(8, 'Richiama', 'out', gA='ginocchio'),
     s(9, 'Appoggia', gA='terra'),
     s(6, 'Diretto, la mano davanti copre', 'snap', 3, bD='avanti', mD='pugno', bA='viso'),
     s(14, 'Guardia', 'out', **G))
anim('gomito_palmo', 'Gomito e palmo', 'Combinazioni', 'Gomito corto, poi il palmo dietro.',
     s(5, 'Gomito', 'snap', 2, bA='gomito'),
     s(6, 'Palmo dietro, la mano davanti torna a coprire', 'snap', 3, bA='viso', bD='avanti', mD='aperta'),
     s(16, 'Guardia', 'out', **G))
anim('tre_palmi', 'Tre palmi', 'Combinazioni', 'Davanti, dietro, poi tutti e due.',
     s(5, 'Palmo davanti', 'snap', 2, bA='avanti', mA='aperta'),
     s(6, 'Palmo dietro', 'snap', 2, bA='viso', bD='avanti', mD='aperta'),
     s(7, 'Raccoglie', bA='viso', bD='viso', alt='basso'),
     s(6, 'Doppio palmo', 'snap', 4, bA='avanti', bD='avanti', busto='avanti', alt='normale'),
     s(18, 'Guardia', 'out', **G))
anim('montante_gomito', 'Montante e gomitata', 'Combinazioni', 'Il montante davanti alza la guardia, il gomito dietro chiude.',
     s(8, 'Scende, il pugno davanti basso', alt='basso', bA='basso', busto='avanti'),
     s(6, 'Montante', 'snap', 2, bA='alto', alt='alto', busto='indietro'),
     s(6, 'Gomitata dietro, la mano davanti copre', 'snap', 3, bA='viso', bD='gomito', mD='pugno', alt='normale', busto='avanti'),
     s(14, 'Guardia', 'out', **G))
anim('passo_uno_due', 'Passo, uno-due', 'Combinazioni', 'Entra di un passo, jab e diretto, esce.',
     s(16, 'Passo avanti', passo='avanti'),
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(5, 'Jab', 'snap', 2, bA='avanti'),
     s(6, 'Diretto', 'snap', 3, bA='viso', bD='avanti', mD='pugno'),
     s(12, 'Guardia', 'out', **G),
     s(16, 'Passo indietro', passo='qui'))
anim('basso_alto_palmo', 'Palmo basso e alto', 'Combinazioni', 'Colpisce basso e risale col palmo.',
     s(7, 'Palmo basso', 'snap', 2, alt='basso', bA='basso', mA='aperta'),
     s(6, 'Risale col palmo', 'snap', 3, alt='alto', bA='alto'),
     s(16, 'Guardia', 'out', **G))
anim('raffica', 'Raffica di palmi', 'Combinazioni', 'Quattro palmi veloci, alternati.',
     s(5, 'Uno', 'snap', 1, bA='avanti', mA='aperta', mD='aperta'),
     s(5, 'Due', 'snap', 1, bA='viso', bD='avanti'),
     s(5, 'Tre', 'snap', 1, bA='avanti', bD='viso'),
     s(5, 'Quattro', 'snap', 3, bA='viso', bD='avanti'),
     s(16, 'Guardia', 'out', **G))
anim('combo_finale', 'Combinazione finale', 'Combinazioni', 'Jab, diretto, ginocchiata, calcio, doppio palmo.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(5, 'Jab', 'snap', 2, bA='avanti'),
     s(6, 'Diretto', 'snap', 2, bA='viso', bD='avanti', mD='pugno'),
     s(7, 'Afferra', bA='avanti', bD='avanti', mA='aperta', mD='aperta'),
     s(6, 'Ginocchiata', 'snap', 2, gD='ginocchio', bA='basso', bD='basso', busto='avanti'),
     s(9, 'Appoggia', gD='terra', bA='viso', bD='viso', busto='dritto'),
     s(8, 'Ginocchio davanti su', gA='ginocchio'),
     s(5, 'Calcio', 'snap', 2, gA='calcio'),
     s(8, 'Richiama', 'out', gA='ginocchio'),
     s(9, 'Appoggia e raccoglie', gA='terra', alt='basso'),
     s(6, 'Doppio palmo', 'snap', 5, bA='avanti', bD='avanti', busto='avanti', alt='normale'),
     s(20, 'Guardia', 'out', **G))
anim('jab_gomito', 'Jab e gomitata', 'Combinazioni', 'Il jab misura, il gomito entra.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(5, 'Jab', 'snap', 2, bA='avanti'),
     s(6, 'Gomitata con lo stesso braccio', 'snap', 3, bA='gomito', busto='avanti'),
     s(14, 'Guardia', 'out', **G))
anim('diretto_calcio_basso', 'Diretto e calcio basso', 'Combinazioni', 'Il diretto copre, il calcio dietro spazza basso.',
     s(6, 'Diretto, la mano davanti copre', 'snap', 2, bD='avanti', mD='pugno', bA='viso'),
     s(7, 'Calcio basso dietro, le braccia tornano', 'snap', 3, bD='guardia', mD='socchiusa', bA='guardia', gD='basso'),
     s(14, 'Guardia', 'out', **G))
anim('palmo_calcio', 'Palmo e calcio', 'Combinazioni', 'Il palmo spinge, il calcio frontale segue.',
     s(5, 'Palmo', 'snap', 2, bA='avanti', mA='aperta', busto='avanti'),
     s(8, 'Ginocchio su, il braccio torna', bA='guardia', mA='pugno', busto='dritto', gA='ginocchio'),
     s(5, 'Calcio', 'snap', 3, gA='calcio'),
     s(8, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Guardia', **G))

# ----------------------------------------------------------------------------------------------------- Difese (defence)
anim('parata_alta', 'Parata alta', 'Difese', 'Il braccio dietro sale a coprire la testa.',
     s(5, 'Para in alto', 'snap', 10, bD='alto', mD='pugno'),
     s(12, 'Guardia', 'out', **G))
anim('parata_bassa', 'Parata bassa', 'Difese', 'Il braccio davanti scende a deviare un calcio basso.',
     s(5, 'Para in basso', 'snap', 10, bA='basso', alt='basso'),
     s(12, 'Guardia', 'out', **G))
anim('copertura', 'Copertura', 'Difese', 'Si chiude dietro le mani e assorbe.',
     s(5, 'Mani alla testa, si chiude', 'snap', 16, bA='viso', bD='viso', mD='pugno', alt='basso', busto='avanti'),
     s(12, 'Guardia', 'out', **G))
anim('schivata_indietro', 'Schivata indietro', 'Difese', 'Si piega indietro e il colpo passa.',
     s(6, 'Si piega indietro', 'out', 10, busto='indietro', alt='alto', bA='viso', bD='viso', mD='pugno'),
     s(12, 'Guardia', **G))
anim('schivata_bassa', 'Schivata bassa', 'Difese', 'Si abbassa sotto il colpo, le mani su.',
     s(6, 'Giù sotto il colpo', 'out', 10, alt='basso', busto='avanti', bA='viso', bD='viso', mD='pugno'),
     s(12, 'Guardia', **G))
anim('deviazione', 'Deviazione e palmo', 'Difese', 'La mano davanti devia in alto, il palmo dietro risponde.',
     s(5, 'Devia in alto con la mano aperta', 'snap', 2, bA='alto', mA='aperta'),
     s(6, 'Risponde col palmo dietro', 'snap', 3, bA='viso', bD='avanti', mD='aperta'),
     s(16, 'Guardia', 'out', **G))
anim('parata_calcio', 'Parata e calcio', 'Difese', 'Para in alto e risponde col calcio frontale.',
     s(5, 'Para in alto', 'snap', 6, bD='alto', mD='pugno'),
     s(8, 'Ginocchio su, la parata scende', bD='guardia', mD='socchiusa', gA='ginocchio'),
     s(5, 'Calcio', 'snap', 3, gA='calcio'),
     s(8, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Guardia', **G))
anim('ritirata', 'Passo indietro coperto', 'Difese', 'Esce coperto con un passo indietro e rientra.',
     s(16, 'Passo indietro, le mani alla testa', passo='indietro', bA='viso', bD='viso', mD='pugno'),
     s(8, 'Tiene la copertura', h=6),
     s(12, 'Guardia', **G),
     s(16, 'Rientra con un passo', passo='qui'))
anim('schivata_montante', 'Schivata e montante', 'Difese', 'Va sotto il colpo e risale col montante.',
     s(6, 'Giù sotto il colpo', 'out', 6, alt='basso', busto='avanti', bA='viso', bD='viso', mD='pugno'),
     s(6, 'Risale col montante davanti', 'snap', 3, alt='alto', busto='indietro', bA='alto', bD='viso'),
     s(16, 'Guardia', 'out', **G))

# ------------------------------------------------------------------------------------------------- Movimenti (movement)
anim('passo_avanti', 'Passo avanti', 'Movimenti', 'Un passo radente avanti e uno indietro, la guardia ferma.',
     s(16, 'Passo avanti', h=10, passo='avanti'),
     s(16, 'Passo indietro', passo='qui'))
anim('due_passi', 'Due passi avanti', 'Movimenti', 'Due passi avanti, poi torna.',
     s(16, 'Un passo', passo='avanti'),
     s(16, 'Due passi', h=8, passo='avanti2'),
     s(30, 'Torna indietro', passo='qui'))
anim('passo_indietro', 'Passo indietro', 'Movimenti', 'Un passo indietro e ritorno.',
     s(16, 'Passo indietro', h=10, passo='indietro'),
     s(16, 'Rientra', passo='qui'))
anim('salto', 'Salto sul posto', 'Movimenti', 'Carica, salta raccogliendo le gambe, atterra morbido.',
     s(8, 'Carica sulle gambe', alt='basso', bA='viso', bD='viso', mD='pugno'),
     s(9, 'In aria, le ginocchia su', 'out', 4, gA='ginocchio', gD='ginocchio', alt='normale'),
     s(9, 'Atterra', gA='terra', gD='terra', alt='basso'),
     s(12, 'Guardia', **G))
anim('accovacciata', 'Accovacciata', 'Movimenti', 'Scende basso, resta, risale.',
     s(12, 'Giù basso', h=12, alt='basso', busto='avanti'),
     s(14, 'Risale', **G))
anim('saltello', 'Saltello in guardia', 'Movimenti', 'Il molleggio sulle punte prima di attaccare.',
     s(7, 'Su', alt='alto'),
     s(7, 'Giù', alt='basso'),
     s(7, 'Su', alt='alto'),
     s(8, 'Guardia', **G))
anim('avanzata_coperta', 'Avanzata coperta', 'Movimenti', 'Avanza di due passi dietro le mani, poi torna.',
     s(16, 'Un passo, le mani alla testa', passo='avanti', bA='viso', bD='viso', mD='pugno'),
     s(16, 'Due passi', passo='avanti2'),
     s(12, 'Guardia', **G),
     s(30, 'Torna indietro', passo='qui'))
anim('cambio_ritmo', 'Avanti e indietro', 'Movimenti', 'Entra, esce, rientra: cerca la distanza.',
     s(14, 'Passo avanti', passo='avanti'),
     s(14, 'Passo indietro', passo='qui'),
     s(14, 'Passo indietro ancora', passo='indietro'),
     s(14, 'Rientra', passo='qui'))

# --------------------------------------------------------------------------------------------------------- Speciali
anim('carica', 'Carica di energia', 'Speciali', 'Si concentra in basso ed esplode verso l\'alto.',
     s(14, 'Si concentra: basso, i pugni giù', h=12, alt='basso', bA='basso', bD='basso', mD='pugno', busto='avanti'),
     s(10, 'Esplode: in alto, le mani aperte', 'out', 16, alt='alto', bA='alto', bD='alto', mA='aperta', mD='aperta', busto='indietro'),
     s(18, 'Guardia', **G))
anim('vittoria', 'Vittoria', 'Speciali', 'Il pugno al cielo.',
     s(12, 'Il pugno davanti al cielo', 'out', 30, bA='alto', alt='alto'),
     s(16, 'Guardia', **G))
anim('passo_spezzato', 'Passo spezzato', 'Speciali', 'La firma di Ren: finta indietro, si raccoglie basso, scatta e spinge con due palmi.',
     s(10, 'Finta: mezzo passo indietro, il busto indietro', passo='indietro', busto='indietro'),
     s(10, 'Si raccoglie basso, le mani aperte davanti al viso', busto='avanti', alt='basso', bA='viso', bD='viso', mA='aperta', mD='aperta'),
     s(12, 'Scatta avanti basso', passo='avanti'),
     s(6, 'Doppio palmo', 'snap', 5, bA='avanti', bD='avanti', alt='normale'),
     s(16, 'Guardia', 'out', **G),
     s(16, 'Torna al suo posto', passo='qui'))
anim('finale_volante', 'Finale volante', 'Speciali', 'Calcio saltato, atterra e chiude col doppio palmo.',
     s(8, 'Carica', alt='basso', bA='viso', bD='viso', mD='pugno'),
     s(8, 'Calcio in aria', 'out', 3, gA='calcio', gD='ginocchio', alt='normale', bA='guardia', bD='guardia'),
     s(10, 'Atterra, raccoglie le mani', gA='terra', gD='terra', alt='basso', bA='viso', bD='viso', mA='aperta', mD='aperta'),
     s(6, 'Doppio palmo', 'snap', 5, bA='avanti', bD='avanti', alt='normale', busto='avanti'),
     s(18, 'Guardia', 'out', **G))
anim('respiro', 'Respiro', 'Speciali', 'Apre le mani, scende piano e torna: si ricarica.',
     s(30, 'Le mani aperte, scende piano', h=10, mA='aperta', mD='aperta', bA='basso', bD='basso', alt='basso'),
     s(30, 'Risale', h=10, alt='alto', bA='viso', bD='viso'),
     s(24, 'Guardia', **G))
anim('sfida', 'Sfida', 'Speciali', 'Si drizza, apre la mano davanti e lo aspetta.',
     s(12, 'Si drizza, la mano davanti aperta', 'out', 24, alt='alto', bA='avanti', mA='aperta', busto='indietro'),
     s(14, 'Guardia', **G))


def legend():
    src = open(os.path.join(HERE, '..', 'mods', 'posa.js'), encoding='utf-8').read()
    a = src.index('const PZ_LEGENDA = '); b = src.index(';\n', a)
    return ''.join(x.replace("\\'", "'") for x in re.findall(r"'((?:[^'\\]|\\.)*)'", src[a:b]))


def main():
    keys = [a['key'] for a in ANIMS]
    assert len(keys) == len(set(keys))
    now, leg, docs = int(time.time() * 1000), legend(), []
    for i, a in enumerate(ANIMS):
        docs.append({'id': 'c-' + a['key'], 'doc': {'v': 2, 'name': a['name'], 'cat': a['cat'], 'ord': i, 'note': a['note'], 'frames': 24,
                                                     'updated': now - i, 'legenda': leg, 'poses': a['poses']}})
    out = os.path.join(HERE, 'animazioni.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False, indent=0)
    by = {}
    for a in ANIMS: by[a['cat']] = by.get(a['cat'], 0) + 1
    print('%d animazioni -> %s %s' % (len(ANIMS), out, by))


if __name__ == '__main__':
    main()
