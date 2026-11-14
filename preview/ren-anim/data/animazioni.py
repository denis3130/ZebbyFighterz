#!/usr/bin/env python3
"""Ren's animations for the "Pose di Ren" page (mods/posa.js), made by Claude on Denis's requests (14/11/2026):
"creami tantissime animazioni, inventatene almeno 50 [...] basta che siano fatte bene e senza bug o comportamenti del
corpo strane"; then "aggiungi anche tante combo [...] inventati anche qualche figata, come combo speciali, mosse
speciali ecc".

Each animation is a list of key poses built from the page's ready positions (the same buttons Denis has), each pose
with its own timing: t frames to reach it (60 a second), h frames held on it, e its ease ('snap': faster and faster
into it, a strike that lands at full speed; 'out': fast, then slowing; none: even, from rest to rest). A pose is the one
before it with some choices changed; guard=True brings everything back to the guard (the place and the turns stay).
The first pose of every animation is the guard.

Beyond the buttons (the special moves): giro and capriola, the whole body turned about itself (on the foot that stays
down) and flipped (forward; < 0 backward), in degrees counted on (they stay until changed); vola, a higher jump (m);
x, his place in metres (instead of passo; it stays until changed); scatto, reached in one low dash; fx, an effect on
reaching the pose (colpo, forte: an impact; energia: energy gathering in the hands; onda: a wave sent forward) at the
limb hit (mA, mD hands, eA, eD elbows, gA, gD knees, pA, pD feet, due: both hands); scia, a trail behind that limb.
vola, scatto, fx, hit and scia are the pose's own (not carried on). A strike reached with 'snap' and no fx given gets
an impact at its limb (a kick a trail too), the last strike of a combination a heavy one; fx=None: none.

    python3 data/animazioni.py            writes data/animazioni.json (the documents, as the page saves them)

The documents go into the page's database (collection "animazioni", one document per animation: id "c-<name>").
"""
import json, os, re, time

HERE = os.path.dirname(os.path.abspath(__file__))
GUARD = dict(bA='guardia', mA='pugno', bD='guardia', mD='socchiusa', gA='terra', gD='terra', busto='dritto', alt='normale', passo='qui')
LEGS = {'terra', 'ginocchio', 'calcio', 'alto', 'basso', 'dietro'}
VALUES = {
    'bA': {'guardia', 'avanti', 'alto', 'viso', 'gomito', 'basso'}, 'bD': {'guardia', 'avanti', 'alto', 'viso', 'gomito', 'basso'},
    'mA': {'pugno', 'socchiusa', 'aperta'}, 'mD': {'pugno', 'socchiusa', 'aperta'}, 'gA': LEGS, 'gD': LEGS,
    'busto': {'dritto', 'avanti', 'indietro'}, 'alt': {'normale', 'basso', 'alto'}, 'passo': {'indietro', 'qui', 'avanti', 'avanti2'},
}
NUM = {'giro': (-1080, 1080), 'capriola': (-1080, 1080), 'vola': (0, 1), 'x': (-3, 3)}
FX, HIT = {'colpo', 'forte', 'energia', 'onda'}, {'mA', 'mD', 'eA', 'eD', 'gA', 'gD', 'pA', 'pD', 'due'}
KEEP = ('passo', 'x', 'giro', 'capriola')   # (carried through a return to the guard)
OWN = ('vola', 'scatto', 'fx', 'hit', 'scia')   # (the pose's own)
CATS = ['Colpi', 'Calci', 'Combinazioni', 'Difese', 'Movimenti', 'Speciali']
ANIMS = []


def s(t, note='', e=None, h=0, guard=False, **ch):
    """One key pose: reached in t frames (ease e), held h frames, with these choices changed."""
    return dict(t=t, note=note, e=e, h=h, guard=guard, ch=ch)


def strike(a, b):
    """The limb a change from pose a to pose b strikes with, and whether it is a kick (None: no strike)."""
    for d in 'AD':
        g0, g1, other = a['g' + d], b['g' + d], b['g' + ('D' if d == 'A' else 'A')]
        if g1 != g0 and g1 in ('calcio', 'alto', 'basso', 'dietro'): return 'p' + d, True
        if g1 != g0 and g1 == 'ginocchio' and g0 == 'terra': return 'g' + d, False   # (a knee)
        if g1 != g0 and g1 == 'terra' and g0 in ('ginocchio', 'alto') and other == 'terra' and a['g' + ('D' if d == 'A' else 'A')] == 'terra': return 'p' + d, False   # (a stamp, an axe)
    arm = {d: a['b' + d] != b['b' + d] and b['b' + d] in ('avanti', 'alto', 'basso', 'gomito') for d in 'AD'}
    if arm['A'] and arm['D']: return 'due', False
    for d in 'DA':
        if arm[d]: return ('e' if b['b' + d] == 'gomito' else 'm') + d, False
    return None


def anim(key, name, cat, note, *steps):
    assert cat in CATS, cat
    poses, cur, auto = [dict(GUARD, note='Guardia')], dict(GUARD), []
    for st in steps:
        prev = dict(cur)
        if st['guard']:
            keep = {k: cur[k] for k in KEEP if k in cur}
            cur = dict(GUARD); cur.update(keep)
        for k in OWN: cur.pop(k, None)
        for k, v in st['ch'].items():
            if k in VALUES: assert v in VALUES[k], (key, k, v)
            elif k in NUM: assert isinstance(v, (int, float)) and NUM[k][0] <= v <= NUM[k][1], (key, k, v)
            elif k == 'fx': assert v is None or v in FX, (key, v)
            elif k == 'hit': assert v in HIT, (key, v)
            elif k in ('scatto', 'scia'): assert v is True, (key, k)
            else: raise AssertionError((key, k))
            if v is not None: cur[k] = v
        if 'fx' not in st['ch'] and st['e'] == 'snap' and cat not in ('Difese', 'Movimenti'):
            hit = strike(prev, cur)
            if hit: cur['fx'], cur['hit'] = 'colpo', hit[0]; cur.update({'scia': True} if hit[1] else {}); auto.append(len(poses))
        p = dict(cur, note=st['note'], t=st['t'])
        if st['h']: p['h'] = st['h']
        if st['e']: p['e'] = st['e']
        poses.append(p)
    # the last strike of a combination (or of more than one) lands heavy
    if auto and (cat in ('Combinazioni', 'Speciali') or len(auto) > 1) and not any(p.get('fx') == 'forte' for p in poses): poses[auto[-1]]['fx'] = 'forte'
    assert poses[0]['passo'] == 'qui' and 2 <= len(poses) <= 24, key
    last = poses[-1]
    assert last.get('giro', 0) % 360 == 0 and last.get('capriola', 0) % 360 == 0, key   # (back round to the guard: no turn on the way)
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
     s(5, 'Lo cala in basso, scende con tutto il corpo', 'snap', 4, bA='basso', alt='basso', busto='avanti', fx='forte', hit='mA'),
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
     s(8, 'In aria: calcio avanti, l\'altro ginocchio su', 'out', 4, gA='calcio', gD='ginocchio', alt='normale', bA='guardia', bD='guardia', fx='forte', hit='pA', scia=True),
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
     s(4, 'Pesta: scende con tutto il peso', 'snap', 5, gA='terra', alt='basso', bA='basso', busto='avanti', fx='forte', hit='pA'),
     s(14, 'Torna in guardia', 'out', **G))
anim('ginocchiata_volante', 'Ginocchiata volante', 'Calci', 'Salta portando il ginocchio avanti, le mani ad afferrare.',
     s(8, 'Carica sulle gambe', alt='basso'),
     s(8, 'In aria: il ginocchio avanti, le mani afferrano', 'out', 4, gA='ginocchio', gD='ginocchio', alt='normale', bA='avanti', bD='avanti', mA='aperta', mD='aperta', fx='forte', hit='gD'),
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

# (round 2: the head kicks, the kick behind, the axe, the flurry)
anim('calcio_alto', 'Calcio alto', 'Calci', 'La gamba dietro sale fino alla testa, il busto si inclina indietro.',
     s(9, 'Il ginocchio dietro sale e gira', gD='ginocchio'),
     s(6, 'Calcio alla testa', 'snap', 3, gD='alto'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia, guardia', **G))
anim('calcio_alto_avanti', 'Calcio alto davanti', 'Calci', 'Veloce, con la gamba davanti: dal ginocchio dritto alla testa.',
     s(8, 'Ginocchio davanti su', gA='ginocchio'),
     s(5, 'Calcio alla testa', 'snap', 3, gA='alto'),
     s(7, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Appoggia, guardia', **G))
anim('calcio_indietro', "Calcio all'indietro", 'Calci', "Per chi gli arriva alle spalle: il busto avanti, il tallone dritto indietro.",
     s(7, 'Il busto avanti, guarda dietro', busto='avanti'),
     s(7, 'Calcio indietro di tallone', 'snap', 4, gD='dietro'),
     s(12, 'Richiama e appoggia', 'out', **G))
anim('calcio_ascia', "Calcio ad ascia", 'Calci', "La gamba davanti sale dritta e cala di tallone come un'ascia.",
     s(11, 'La gamba davanti sale dritta, alta', gA='alto', bA='viso'),
     s(5, "Cala come un'ascia", 'snap', 6, gA='terra', alt='basso', busto='avanti', bA='guardia', fx='forte', hit='pA', scia=True),
     s(14, 'Guardia', 'out', **G))
anim('raffica_calci', 'Raffica di calci', 'Calci', 'Tre calci con la gamba davanti senza appoggiarla: basso, medio, alto.',
     s(7, 'Ginocchio davanti su', gA='ginocchio'),
     s(4, 'Basso, allo stinco', 'snap', 1, gA='basso'),
     s(5, 'Richiama', 'out', gA='ginocchio'),
     s(4, 'Medio, al corpo', 'snap', 1, gA='calcio'),
     s(5, 'Richiama', 'out', gA='ginocchio'),
     s(5, 'Alto, alla testa', 'snap', 4, gA='alto'),
     s(7, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Appoggia, guardia', **G))

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

# (round 2)
anim('jab_jab_diretto', 'Jab, jab, diretto', 'Combinazioni', 'Due jab veloci per misurare, il diretto per chiudere.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(4, 'Jab', 'snap', 1, bA='avanti'),
     s(4, 'Torna', 'out', bA='viso'),
     s(4, 'Jab', 'snap', 1, bA='avanti'),
     s(6, 'Diretto: le anche girano', 'snap', 4, bA='viso', bD='avanti', mD='pugno'),
     s(14, 'Guardia', 'out', **G))
anim('uno_due_alto', 'Uno-due e calcio alto', 'Combinazioni', 'Jab e diretto tengono su la guardia, il calcio alto arriva sopra.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(4, 'Jab', 'snap', 1, bA='avanti'),
     s(6, 'Diretto', 'snap', 2, bA='viso', bD='avanti', mD='pugno'),
     s(8, 'Le mani tornano, il ginocchio dietro sale', bA='guardia', bD='guardia', mD='socchiusa', gD='ginocchio'),
     s(6, 'Calcio alto', 'snap', 3, gD='alto'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia, guardia', **G))
anim('palmo_gomito_ginocchio', 'Palmo, gomito, ginocchio', 'Combinazioni', 'Sempre più vicino: il palmo apre, il gomito entra, il ginocchio chiude.',
     s(5, 'Il palmo davanti si raccoglie', bA='viso', mA='aperta'),
     s(5, 'Palmo', 'snap', 2, bA='avanti'),
     s(6, 'Gomito dietro', 'snap', 2, bA='viso', bD='gomito'),
     s(6, 'Afferra', bA='avanti', bD='avanti', mA='aperta', mD='aperta'),
     s(6, 'Ginocchiata, tira giù', 'snap', 3, gD='ginocchio', bA='basso', bD='basso', busto='avanti'),
     s(10, 'Appoggia', gD='terra', busto='dritto', bA='viso', bD='viso'),
     s(12, 'Guardia', **G))
anim('basso_diretto_alto', 'Calcio basso, diretto, calcio alto', 'Combinazioni', 'Basso, in mezzo, alto: non sa più dove coprirsi.',
     s(7, 'Calcio basso davanti', 'snap', 2, gA='basso'),
     s(7, 'Appoggia', 'out', gA='terra'),
     s(6, 'Diretto', 'snap', 2, bA='viso', bD='avanti', mD='pugno'),
     s(8, 'Il ginocchio dietro sale', bA='guardia', bD='guardia', mD='socchiusa', gD='ginocchio'),
     s(6, 'Calcio alto', 'snap', 3, gD='alto'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia, guardia', **G))
anim('doppio_gomito', 'Doppio gomito', 'Combinazioni', 'Da vicinissimo: gomito davanti, gomito dietro.',
     s(5, 'Gomito davanti', 'snap', 2, bA='gomito'),
     s(6, 'Gomito dietro', 'snap', 4, bA='viso', bD='gomito'),
     s(14, 'Guardia', 'out', **G))
anim('montante_alto', 'Montante e calcio alto', 'Combinazioni', 'Il montante gli alza il mento, il calcio alto lo trova.',
     s(8, 'Scende, il pugno davanti basso', alt='basso', bA='basso', busto='avanti'),
     s(6, 'Montante', 'snap', 2, alt='normale', bA='alto', busto='dritto'),
     s(8, 'Il ginocchio dietro sale', bA='guardia', gD='ginocchio'),
     s(6, 'Calcio alto', 'snap', 3, gD='alto'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia, guardia', **G))
anim('quattro_colpi', 'Quattro colpi', 'Combinazioni', 'Jab, diretto, gomito, ginocchio: entra un colpo alla volta.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(4, 'Jab', 'snap', 1, bA='avanti'),
     s(6, 'Diretto', 'snap', 1, bA='viso', bD='avanti', mD='pugno'),
     s(6, 'Gomito davanti', 'snap', 1, bA='gomito', bD='viso'),
     s(6, 'Afferra', bA='avanti', bD='avanti', mA='aperta', mD='aperta'),
     s(6, 'Ginocchiata', 'snap', 3, gD='ginocchio', bA='basso', bD='basso', busto='avanti'),
     s(10, 'Appoggia', gD='terra', busto='dritto', bA='viso', bD='viso'),
     s(12, 'Guardia', **G))
anim('uno_due_girato', 'Uno-due e calcio girato', 'Combinazioni', 'Jab, diretto, poi gira sul piede davanti e calcia di tallone.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(4, 'Jab', 'snap', 1, bA='avanti'),
     s(6, 'Diretto', 'snap', 2, bA='viso', bD='avanti', mD='pugno'),
     s(9, 'Gira sul piede davanti, la schiena verso di lui', bA='guardia', bD='guardia', mD='socchiusa', gD='ginocchio', giro=-180),
     s(6, 'Calcio girato: il tallone dritto', 'snap', 4, gD='dietro'),
     s(10, 'Richiama e finisce il giro', gD='ginocchio', giro=-360),
     s(10, 'Appoggia, guardia', **G))
anim('palmo_tornado', 'Palmo e tornado', 'Combinazioni', 'Il palmo lo spinge indietro, il calcio tornado lo raggiunge in volo.',
     s(5, 'Il palmo davanti si raccoglie', bA='viso', mA='aperta'),
     s(5, 'Palmo', 'snap', 2, bA='avanti'),
     s(8, 'Si carica basso', bA='guardia', mA='pugno', alt='basso'),
     s(9, 'Salta girando', 'out', gA='ginocchio', gD='ginocchio', alt='normale', vola=.25, giro=-180),
     s(6, 'Calcio in volo a fine giro', 'snap', 3, gD='calcio', giro=-360),
     s(10, 'Atterra morbido', gA='terra', gD='terra', alt='basso'),
     s(12, 'Guardia', **G))
anim('finta_alto', 'Finta bassa, calcio alto', 'Combinazioni', 'Accenna il calcio basso, lo fa abbassare, e calcia alto.',
     s(6, 'Finta: il ginocchio davanti accenna', gA='ginocchio', bA='viso'),
     s(6, 'Lo rimette giù', 'out', gA='terra', bA='guardia'),
     s(7, 'Il ginocchio dietro sale', gD='ginocchio'),
     s(6, 'Calcio alto', 'snap', 3, gD='alto'),
     s(8, 'Richiama', 'out', gD='ginocchio'),
     s(12, 'Appoggia, guardia', **G))
anim('pioggia_pugni', 'Pioggia di pugni', 'Combinazioni', 'Sei pugni a raffica, uno per mano, e il montante che chiude.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(4, 'Uno', 'snap', 0, bA='avanti', bD='viso', mD='pugno'),
     s(4, 'Due', 'snap', 0, bA='viso', bD='avanti'),
     s(4, 'Tre', 'snap', 0, bA='avanti', bD='viso'),
     s(4, 'Quattro', 'snap', 0, bA='viso', bD='avanti'),
     s(4, 'Cinque', 'snap', 0, bA='avanti', bD='viso'),
     s(4, 'Sei', 'snap', 0, bA='viso', bD='avanti'),
     s(6, 'Scende, il pugno davanti basso', bA='basso', bD='viso', alt='basso'),
     s(6, 'Montante', 'snap', 5, bA='alto', alt='normale'),
     s(16, 'Guardia', 'out', **G))
anim('ginocchio_martello', 'Ginocchiata volante e martello', 'Combinazioni', 'Salta col ginocchio, ricade calando i due pugni.',
     s(8, 'Carica sulle gambe', alt='basso', bA='viso', bD='viso', mD='pugno'),
     s(8, 'Ginocchiata in volo, i pugni su', 'out', 2, gA='ginocchio', gD='ginocchio', alt='normale', bA='alto', bD='alto', fx='colpo', hit='gD'),
     s(8, 'Ricade calando i due pugni', 'snap', 5, gA='terra', gD='terra', alt='basso', bA='basso', bD='basso', busto='avanti'),
     s(14, 'Guardia', 'out', **G))
anim('jab_alto', 'Jab e calcio alto', 'Combinazioni', 'Il jab gli chiude gli occhi, la gamba davanti sale alla testa.',
     s(4, 'Il pugno davanti si raccoglie', bA='viso'),
     s(4, 'Jab', 'snap', 1, bA='avanti'),
     s(7, 'Il ginocchio davanti sale', bA='guardia', gA='ginocchio'),
     s(5, 'Calcio alto', 'snap', 3, gA='alto'),
     s(7, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Appoggia, guardia', **G))
anim('combo_aerea', 'Combo aerea', 'Combinazioni', 'Montante che lancia, ginocchio e calcio in volo, atterra coi due palmi.',
     s(8, 'Scende, il pugno davanti basso', alt='basso', bA='basso', busto='avanti'),
     s(6, 'Montante che lancia', 'snap', 2, alt='normale', bA='alto', busto='dritto'),
     s(8, 'Salta: il ginocchio', 'out', gA='ginocchio', gD='ginocchio', bA='guardia', vola=.2, fx='colpo', hit='gD'),
     s(5, 'Calcio in volo', 'snap', 2, gA='calcio', vola=.2),
     s(6, 'Raccoglie in aria', gA='ginocchio', bA='viso', bD='viso', vola=.1),
     s(8, 'Atterra coi due palmi', 'snap', 5, gA='terra', gD='terra', alt='basso', bA='avanti', bD='avanti', mA='aperta', mD='aperta', busto='avanti'),
     s(14, 'Guardia', 'out', **G))
anim('diretto_volante', 'Diretto e ginocchiata volante', 'Combinazioni', 'Il diretto lo ferma, il ginocchio volante lo chiude.',
     s(6, 'Diretto', 'snap', 2, bA='viso', bD='avanti', mD='pugno'),
     s(8, 'Si carica', bA='guardia', bD='guardia', mD='socchiusa', alt='basso'),
     s(8, 'Ginocchiata volante, le mani afferrano', 'out', 3, gA='ginocchio', gD='ginocchio', alt='normale', bA='avanti', bD='avanti', mA='aperta', mD='aperta', fx='forte', hit='gD'),
     s(10, 'Atterra', gA='terra', gD='terra', alt='basso', bA='guardia', bD='guardia', mA='pugno', mD='socchiusa'),
     s(14, 'Guardia', **G))

# ----------------------------------------------------------------------------------------------------- Difese (defence)
anim('parata_alta', 'Parata alta', 'Difese', 'Il braccio dietro sale a coprire la testa.',
     s(5, 'Para in alto', 'snap', 10, bD='alto', mD='pugno', fx='colpo', hit='eD'),
     s(12, 'Guardia', 'out', **G))
anim('parata_bassa', 'Parata bassa', 'Difese', 'Il braccio davanti scende a deviare un calcio basso.',
     s(5, 'Para in basso', 'snap', 10, bA='basso', alt='basso', fx='colpo', hit='eA'),
     s(12, 'Guardia', 'out', **G))
anim('copertura', 'Copertura', 'Difese', 'Si chiude dietro le mani e assorbe.',
     s(5, 'Mani alla testa, si chiude', 'snap', 16, bA='viso', bD='viso', mD='pugno', alt='basso', busto='avanti', fx='colpo', hit='due'),
     s(12, 'Guardia', 'out', **G))
anim('schivata_indietro', 'Schivata indietro', 'Difese', 'Si piega indietro e il colpo passa.',
     s(6, 'Si piega indietro', 'out', 10, busto='indietro', alt='alto', bA='viso', bD='viso', mD='pugno'),
     s(12, 'Guardia', **G))
anim('schivata_bassa', 'Schivata bassa', 'Difese', 'Si abbassa sotto il colpo, le mani su.',
     s(6, 'Giù sotto il colpo', 'out', 10, alt='basso', busto='avanti', bA='viso', bD='viso', mD='pugno'),
     s(12, 'Guardia', **G))
anim('deviazione', 'Deviazione e palmo', 'Difese', 'La mano davanti devia in alto, il palmo dietro risponde.',
     s(5, 'Devia in alto con la mano aperta', 'snap', 2, bA='alto', mA='aperta', fx='colpo', hit='eA'),
     s(6, 'Risponde col palmo dietro', 'snap', 3, bA='viso', bD='avanti', mD='aperta', fx='forte', hit='mD'),
     s(16, 'Guardia', 'out', **G))
anim('parata_calcio', 'Parata e calcio', 'Difese', 'Para in alto e risponde col calcio frontale.',
     s(5, 'Para in alto', 'snap', 6, bD='alto', mD='pugno', fx='colpo', hit='eD'),
     s(8, 'Ginocchio su, la parata scende', bD='guardia', mD='socchiusa', gA='ginocchio'),
     s(5, 'Calcio', 'snap', 3, gA='calcio', fx='forte', hit='pA', scia=True),
     s(8, 'Richiama', 'out', gA='ginocchio'),
     s(10, 'Guardia', **G))
anim('ritirata', 'Passo indietro coperto', 'Difese', 'Esce coperto con un passo indietro e rientra.',
     s(16, 'Passo indietro, le mani alla testa', passo='indietro', bA='viso', bD='viso', mD='pugno'),
     s(8, 'Tiene la copertura', h=6),
     s(12, 'Guardia', **G),
     s(16, 'Rientra con un passo', passo='qui'))
anim('schivata_montante', 'Schivata e montante', 'Difese', 'Va sotto il colpo e risale col montante.',
     s(6, 'Giù sotto il colpo', 'out', 6, alt='basso', busto='avanti', bA='viso', bD='viso', mD='pugno'),
     s(6, 'Risale col montante davanti', 'snap', 3, alt='alto', busto='indietro', bA='alto', bD='viso', fx='forte', hit='mA', scia=True),
     s(16, 'Guardia', 'out', **G))

# (round 2)
anim('para_girato', 'Para e calcio girato', 'Difese', 'Para in alto e risponde girando: il calcio di tallone.',
     s(5, 'Para in alto', 'snap', 6, bD='alto', mD='pugno', fx='colpo', hit='eD'),
     s(9, 'Gira sul piede davanti', bD='guardia', mD='socchiusa', gD='ginocchio', giro=-180),
     s(6, 'Calcio girato', 'snap', 4, gD='dietro', fx='forte', hit='pD', scia=True),
     s(10, 'Richiama e finisce il giro', gD='ginocchio', giro=-360),
     s(10, 'Appoggia, guardia', **G))
anim('capriola_indietro', "Capriola all'indietro", 'Difese', "Esce dal pericolo con una capriola all'indietro e torna.",
     s(8, 'Si carica, le braccia giù', alt='basso', bA='basso', bD='basso', mA='aperta', mD='aperta'),
     s(10, 'Salta indietro, le braccia su', 'out', gA='ginocchio', gD='ginocchio', alt='normale', bA='alto', bD='alto', vola=.45, capriola=-200, x=-.25),
     s(8, 'Gira in aria', bA='viso', bD='viso', vola=.3, capriola=-360, x=-.45),
     s(8, 'Atterra', gA='terra', gD='terra', alt='basso', x=-.6),
     s(14, 'Guardia', **G),
     s(18, 'Torna al suo posto', x=0))

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

# (round 2)
anim('scatto_avanti', 'Scatto avanti', 'Movimenti', 'Un balzo radente in avanti, poi torna camminando.',
     s(8, 'Si abbassa', alt='basso', busto='avanti'),
     s(9, 'Scatta avanti, radente', 'out', 6, x=.6, scatto=True, alt='normale', busto='dritto'),
     s(18, 'Torna indietro', x=0))
anim('scatto_indietro', 'Scatto indietro', 'Movimenti', 'Un balzo radente indietro, poi rientra.',
     s(8, 'Si raccoglie', alt='basso', bA='viso', bD='viso'),
     s(9, 'Scatta indietro, radente', 'out', 6, x=-.6, scatto=True, alt='normale'),
     s(12, 'Guardia', **G),
     s(18, 'Rientra', x=0))
anim('salto_avanti', 'Salto in avanti', 'Movimenti', 'Carica e salta in avanti raccogliendo le gambe.',
     s(8, 'Carica', alt='basso', bA='viso', bD='viso'),
     s(10, 'In volo avanti', 'out', gA='ginocchio', gD='ginocchio', alt='normale', vola=.15, x=.3),
     s(9, 'Atterra', gA='terra', gD='terra', alt='basso', x=.6),
     s(12, 'Guardia', **G),
     s(18, 'Torna al suo posto', x=0))
anim('giro', 'Giro su se stesso', 'Movimenti', 'Un giro intero sulla punta del piede davanti, il ginocchio dietro su.',
     s(24, 'Gira sulla punta del piede davanti', gD='ginocchio', bA='viso', bD='viso', giro=-360),
     s(10, 'Appoggia, guardia', **G))

# --------------------------------------------------------------------------------------------------------- Speciali
anim('carica', 'Carica di energia', 'Speciali', 'Si concentra in basso ed esplode verso l\'alto.',
     s(14, 'Si concentra: basso, i pugni giù', h=12, alt='basso', bA='basso', bD='basso', mD='pugno', busto='avanti', fx='energia', hit='due'),
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
     s(8, 'Calcio in aria', 'out', 3, gA='calcio', gD='ginocchio', alt='normale', bA='guardia', bD='guardia', fx='colpo', hit='pA', scia=True),
     s(10, 'Atterra, raccoglie le mani', gA='terra', gD='terra', alt='basso', bA='viso', bD='viso', mA='aperta', mD='aperta'),
     s(6, 'Doppio palmo', 'snap', 5, bA='avanti', bD='avanti', alt='normale', busto='avanti'),
     s(18, 'Guardia', 'out', **G))
anim('respiro', 'Respiro', 'Speciali', 'Apre le mani, scende piano e torna: si ricarica.',
     s(30, 'Le mani aperte, scende piano', h=10, mA='aperta', mD='aperta', bA='basso', bD='basso', alt='basso', fx='energia', hit='due'),
     s(30, 'Risale', h=10, alt='alto', bA='viso', bD='viso'),
     s(24, 'Guardia', **G))
anim('sfida', 'Sfida', 'Speciali', 'Si drizza, apre la mano davanti e lo aspetta.',
     s(12, 'Si drizza, la mano davanti aperta', 'out', 24, alt='alto', bA='avanti', mA='aperta', busto='indietro'),
     s(14, 'Guardia', **G))

# (round 2: the special moves, with their effects)
anim('calcio_girato', 'Calcio girato', 'Speciali', 'Gira sul piede davanti dandogli la schiena e lo colpisce di tallone.',
     s(9, 'Gira sul piede davanti: la schiena verso di lui', gD='ginocchio', giro=-180),
     s(6, 'Calcio girato: il tallone dritto al corpo', 'snap', 4, gD='dietro', fx='forte', hit='pD', scia=True),
     s(10, 'Richiama e finisce il giro', gD='ginocchio', giro=-360),
     s(10, 'Appoggia, guardia', **G))
anim('tornado', 'Calcio tornado', 'Speciali', 'Salta girando su se stesso e calcia in volo a fine giro.',
     s(8, 'Si carica basso', alt='basso'),
     s(9, 'Salta girando', 'out', gA='ginocchio', gD='ginocchio', alt='normale', vola=.25, giro=-180),
     s(6, 'Calcio in volo a fine giro', 'snap', 3, gD='calcio', giro=-360, fx='forte', hit='pD', scia=True),
     s(10, 'Atterra morbido', gA='terra', gD='terra', alt='basso'),
     s(12, 'Guardia', **G))
anim('capriola_ascia', "Capriola d'ascia", 'Speciali', "Capriola in avanti in volo, esce con la gamba alta e la cala come un'ascia atterrando.",
     s(8, 'Si carica, le mani al viso', alt='basso', bA='viso', bD='viso'),
     s(10, 'Salta e si arrotola in avanti', 'out', gA='ginocchio', gD='ginocchio', alt='normale', vola=.45, capriola=200, x=.3),
     s(7, 'Esce dalla capriola: la gamba davanti in alto', gA='alto', capriola=360, vola=.3, x=.45),
     s(6, "Cala come un'ascia e atterra", 'snap', 5, gA='terra', gD='terra', alt='basso', x=.6, fx='forte', hit='pA', scia=True),
     s(14, 'Guardia', **G),
     s(18, 'Torna al suo posto', x=0))
anim('mille_palmi', 'Mille palmi', 'Speciali', 'Una raffica di palmi alternati, poi il doppio palmo che lo spinge via.',
     *[s(4, ('Palmo davanti' if i % 2 == 0 else 'Palmo dietro'), 'snap', 1, bA=('avanti' if i % 2 == 0 else 'viso'), bD=('viso' if i % 2 == 0 else 'avanti'),
         mA='aperta', mD='aperta', fx='colpo', hit=('mA' if i % 2 == 0 else 'mD')) for i in range(6)],
     s(7, 'Raccoglie le mani', bA='viso', bD='viso', alt='basso'),
     s(6, 'Doppio palmo finale', 'snap', 6, bA='avanti', bD='avanti', alt='normale', busto='avanti', fx='forte', hit='due', scia=True),
     s(18, 'Guardia', 'out', **G))
anim('onda_vuoto', 'Onda del vuoto', 'Speciali', "Raccoglie l'energia tra le mani e la spinge avanti in un'onda.",
     s(16, "Raccoglie l'energia tra le mani", h=10, alt='basso', bA='basso', bD='basso', mA='aperta', mD='aperta', busto='indietro', fx='energia', hit='due'),
     s(6, 'La spinge avanti', 'snap', 12, bA='avanti', bD='avanti', alt='normale', busto='avanti', fx='onda', hit='due'),
     s(18, 'Guardia', 'out', **G))
anim('pugno_fantasma', 'Pugno fantasma', 'Speciali', 'Carica il pugno dietro, sparisce in uno scatto e colpisce da vicino.',
     s(10, 'Carica il pugno dietro', bA='viso', bD='viso', mD='pugno', fx='energia', hit='mD'),
     s(10, 'Scatta e colpisce', 'snap', 5, x=.9, scatto=True, bD='avanti', busto='avanti', fx='forte', hit='mD', scia=True),
     s(14, 'Guardia', 'out', **G),
     s(18, 'Torna al suo posto', x=0))
anim('ascesa', 'Ascesa', 'Speciali', "Si raccoglie basso e sale in volo col montante, l'energia nel pugno.",
     s(10, 'Si abbassa, il pugno davanti carico', alt='basso', bA='basso', busto='avanti', fx='energia', hit='mA'),
     s(8, 'Sale in volo col montante', 'snap', 4, gA='ginocchio', gD='dietro', alt='normale', vola=.4, bA='alto', bD='viso', busto='indietro', fx='forte', hit='mA', scia=True),
     s(12, 'Ricade', gA='terra', gD='terra', alt='basso', bA='viso', busto='dritto'),
     s(14, 'Guardia', **G))
anim('martello_cielo', 'Martello del cielo', 'Speciali', 'Salta coi pugni al cielo e ricade calandoli insieme.',
     s(8, 'Si carica', alt='basso', bA='viso', bD='viso', mD='pugno'),
     s(10, 'Salta, i pugni al cielo', 'out', gA='ginocchio', gD='ginocchio', alt='normale', vola=.4, x=.3, bA='alto', bD='alto'),
     s(7, 'Cala i due pugni e atterra', 'snap', 6, gA='terra', gD='terra', alt='basso', x=.45, bA='basso', bD='basso', busto='avanti', fx='forte', hit='due'),
     s(14, 'Guardia', **G),
     s(16, 'Torna al suo posto', x=0))
anim('pugno_rotante', 'Pugno rotante', 'Speciali', 'Gira su se stesso e il pugno dietro arriva con tutto il giro.',
     s(8, 'Gira sul piede davanti, il braccio dietro carica', gD='ginocchio', giro=-180, bA='viso', bD='alto', mD='pugno'),
     s(6, 'Chiude il giro col pugno', 'snap', 4, giro=-360, bD='avanti', fx='forte', hit='mD', scia=True),
     s(10, 'Appoggia, guardia', **G))
anim('voidrise', 'Colpo Voidrise', 'Speciali', "La mossa finale di Ren: energia, scatto coi palmi, calcio alto, capriola d'ascia e l'onda.",
     s(16, "Raccoglie l'energia", h=6, alt='basso', bA='basso', bD='basso', mA='aperta', mD='aperta', busto='indietro', fx='energia', hit='due'),
     s(8, 'Scatta coi due palmi', 'snap', 3, x=.6, scatto=True, bA='avanti', bD='avanti', alt='normale', busto='avanti', fx='forte', hit='due', scia=True),
     s(8, 'Il ginocchio dietro sale', bA='guardia', bD='guardia', mA='pugno', mD='socchiusa', busto='dritto', gD='ginocchio'),
     s(6, 'Calcio alto che lo alza', 'snap', 3, gD='alto', fx='forte', hit='pD', scia=True),
     s(8, 'Appoggia e si carica', gD='terra', alt='basso', bA='viso', bD='viso'),
     s(10, 'Capriola in avanti', 'out', gA='ginocchio', gD='ginocchio', alt='normale', vola=.45, capriola=200, x=.9),
     s(7, 'La gamba davanti in alto', gA='alto', capriola=360, vola=.3, x=1.05),
     s(6, 'Ascia e atterra', 'snap', 4, gA='terra', gD='terra', alt='basso', x=1.2, fx='forte', hit='pA', scia=True),
     s(12, "Raccoglie l'energia", h=4, bA='basso', bD='basso', mA='aperta', mD='aperta', busto='indietro', fx='energia', hit='due'),
     s(6, "L'onda finale", 'snap', 14, bA='avanti', bD='avanti', alt='normale', busto='avanti', fx='onda', hit='due'),
     s(18, 'Guardia', 'out', **G),
     s(40, 'Torna al suo posto', x=0))
anim('danza_vuoto', 'Danza del vuoto', 'Speciali', "Palmo, calcio girato e l'onda: una combinazione speciale senza pause.",
     s(5, 'Il palmo davanti si raccoglie', bA='viso', mA='aperta'),
     s(5, 'Palmo', 'snap', 2, bA='avanti', fx='colpo', hit='mA'),
     s(9, 'Gira sul piede davanti', bA='guardia', mA='pugno', gD='ginocchio', giro=-180),
     s(6, 'Calcio girato', 'snap', 3, gD='dietro', fx='forte', hit='pD', scia=True),
     s(10, 'Finisce il giro', gD='ginocchio', giro=-360),
     s(10, "Appoggia e raccoglie l'energia", gD='terra', alt='basso', bA='basso', bD='basso', mA='aperta', mD='aperta', fx='energia', hit='due'),
     s(6, "L'onda", 'snap', 12, bA='avanti', bD='avanti', alt='normale', busto='avanti', fx='onda', hit='due'),
     s(16, 'Guardia', 'out', **G))
anim('capriola_vittoria', 'Capriola di vittoria', 'Speciali', "Una capriola all'indietro sul posto, poi il pugno al cielo.",
     s(8, 'Si carica', alt='basso', bA='basso', bD='basso'),
     s(10, "Salta all'indietro, le braccia su", 'out', gA='ginocchio', gD='ginocchio', alt='normale', bA='alto', bD='alto', vola=.45, capriola=-200),
     s(8, 'Chiude la capriola', bA='viso', bD='viso', capriola=-360, vola=.25),
     s(8, 'Atterra', gA='terra', gD='terra', alt='basso'),
     s(12, 'Il pugno al cielo', 'out', 30, alt='alto', bA='alto', bD='guardia'),
     s(16, 'Guardia', **G))


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
