#!/usr/bin/env python3
"""Stage 1 data extractor for the Chaos Daemons Army Builder.

Reads chaos-daemons-reference.md (+ the three uploaded .txt files) and emits
the JSON data the app consumes:  data/units/<id>.json, data/abilities.json,
data/enhancements.json, data/army.json.

Roster scope: units whose Keywords list contains "Daemon" (per user decision).
"""
import json, os, re, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF  = os.path.join(ROOT, 'chaos-daemons-reference.md')
UNIT_DIR = os.path.join(ROOT, 'data', 'units')
os.makedirs(UNIT_DIR, exist_ok=True)
for _f in os.listdir(UNIT_DIR):          # start clean so dropped units don't linger
    if _f.endswith('.json'):
        os.remove(os.path.join(UNIT_DIR, _f))

def norm(s):
    """Normalise curly quotes etc. to plain ASCII-ish for matching."""
    return (s.replace('’', "'").replace('‘', "'")
             .replace('“', '"').replace('”', '"')
             .replace('–', '-').replace('—', '-')
             .replace('‑', '-').replace('\xa0', ' '))

def slug(s):
    s = norm(s).lower().strip()
    s = re.sub(r"['’]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')

# ── Standard 10th-ed rules text for common weapon/core abilities ──────────────
# Keyed by the *base* keyword (parameter stripped). Used to fill ability bodies.
BASE_RULES = {
    'lethal hits': ('Weapon Ability', 'Each unmodified <strong>Hit roll of 6</strong> automatically wounds the target.'),
    'sustained hits': ('Weapon Ability', 'Each <strong>Critical Hit</strong> scores a number of additional hits as denoted by the value (X).'),
    'devastating wounds': ('Weapon Ability', 'Each <strong>Critical Wound</strong> inflicts mortal wounds equal to the weapon’s Damage, instead of the normal damage.'),
    'precision': ('Weapon Ability', 'Attacks targeting a unit with an attached Character can be allocated to that Character model.'),
    'torrent': ('Weapon Ability', 'Weapons with [TORRENT] in their profile are known as Torrent weapons. Each time an attack is made with such a weapon, that attack automatically hits the target.'),
    'ignores cover': ('Weapon Ability', 'The target cannot have the Benefit of Cover against this weapon’s attacks.'),
    'rapid fire': ('Weapon Ability', 'When targeting a unit within half range, increase the Attacks characteristic by the value (X).'),
    'assault': ('Weapon Ability', 'This weapon can be shot even if the bearer’s unit Advanced this turn.'),
    'heavy': ('Weapon Ability', 'If the bearer’s unit Remained Stationary this turn, add 1 to Hit rolls with this weapon.'),
    'pistol': ('Weapon Ability', 'This weapon can be shot while the bearer is within Engagement Range of enemy units.'),
    'blast': ('Weapon Ability', 'Add 1 to the Attacks for every 5 models in the target unit. Cannot target units in Engagement Range.'),
    'melta': ('Weapon Ability', 'When targeting a unit within half range, increase the Damage characteristic by the value (X).'),
    'anti': ('Weapon Ability', 'Wound rolls of the listed value or better against the keyworded target are Critical Wounds.'),
    'hazardous': ('Weapon Ability', 'After firing, roll one D6 per Hazardous weapon used; on a 1 the bearer suffers 3 mortal wounds (or is destroyed if a single model).'),
    'psychic': ('Weapon Ability', 'This is a Psychic Attack.'),
    'lance': ('Weapon Ability', 'Add 1 to Wound rolls if the bearer made a Charge move this turn.'),
    'twin-linked': ('Weapon Ability', 'You can re-roll the Wound roll for attacks made with this weapon.'),
    'extra attacks': ('Weapon Ability', 'Attacks are made in addition to those from the bearer’s other melee weapons.'),
    'indirect fire': ('Weapon Ability', 'Can target and be used to make attacks against units not visible to the bearer.'),
    'one shot': ('Weapon Ability', 'This weapon can only be shot once per battle.'),
    'deep strike': ('Core Ability', 'This unit can be placed in Reserves and arrive anywhere more than 9" from enemy models.'),
    'deadly demise': ('Core Ability', 'When destroyed, roll one D6 (per the value); on a 6 each unit within 6" suffers mortal wounds.'),
    'scouts': ('Core Ability', 'This unit can make a Normal move of up to the listed distance before the first turn begins.'),
    'leader': ('Core Ability', 'During the Declare Battle Formations step, this Character can be attached to a unit it can lead.'),
    'fights first': ('Core Ability', 'This unit fights in the Fight phase before units that do not have this ability.'),
    'feel no pain': ('Core Ability', 'Each time a model would lose a wound, roll a D6; on the listed value or better, that wound is not lost.'),
    'stealth': ('Core Ability', 'Subtract 1 from Hit rolls for ranged attacks targeting this unit.'),
    'firing deck': ('Core Ability', 'Embarked models can shoot as if part of this Transport (up to the listed number of weapons).'),
    'infiltrators': ('Core Ability', 'Can be set up anywhere more than 9" horizontally from enemy models during deployment.'),
}

FACTION_RULES = {
    'the shadow of chaos': ('Faction Rule', 'See the army rule <strong>The Shadow of Chaos</strong> — Daemonic Manifestation and Daemonic Terror.'),
    'dark pacts': ('Faction Rule', 'This unit can invoke <strong>Dark Pacts</strong> as described in Codex: Chaos Space Marines.'),
}

abilities = {}   # id -> {name,type,description}

# Abilities to drop from every unit (redundant: army rule / universal keyword).
EXCLUDE_ABILITY_NAMES = {'the shadow of chaos', 'daemonic allegiance'}

def base_key(disp):
    """Strip trailing parameters to find the base rule keyword."""
    d = re.sub(r'\b(d?\d+\+?|d\d+(\+\d+)?|\d+)\b.*$', '', disp.lower()).strip()
    d = d.rstrip('+').strip()
    return d

def add_ability(disp, kind='Weapon Ability'):
    disp = norm(disp).strip()
    if not disp or disp.lower() in EXCLUDE_ABILITY_NAMES:
        return None
    aid = slug(disp)
    if aid in abilities:
        return aid
    name = disp[:1].upper() + disp[1:]
    desc = ''
    bk = base_key(disp)
    if bk in BASE_RULES:
        kind, desc = BASE_RULES[bk]
    elif disp.lower() in FACTION_RULES:
        kind, desc = FACTION_RULES[disp.lower()]
    if not desc:
        # try first word match (e.g. "anti-character 3+")
        first = disp.lower().split('-')[0].split(' ')[0]
        if first in BASE_RULES:
            kind, desc = BASE_RULES[first]
    if not desc:
        desc = '<em>Rules text not provided in source data.</em>'
    abilities[aid] = {'name': name, 'type': kind, 'description': desc}
    return aid

def add_named_ability(name, desc, kind='Ability'):
    name = norm(name).strip()
    if name.lower() in EXCLUDE_ABILITY_NAMES:
        return None
    aid = slug(name)
    desc = norm(desc).strip()
    if aid in abilities:
        # keep first; if different text, suffix
        if abilities[aid]['description'] != desc:
            i = 2
            while f'{aid}-{i}' in abilities:
                i += 1
            aid = f'{aid}-{i}'
        else:
            return aid
    abilities[aid] = {'name': name, 'type': kind, 'description': desc or '<em>See datasheet.</em>'}
    return aid

# ── Parse stat tables / weapon tables ────────────────────────────────────────
def parse_table(block):
    rows = [l for l in block.splitlines() if l.strip().startswith('|')]
    if len(rows) < 2:
        return []
    def cells(r):
        return [c.strip() for c in r.strip().strip('|').split('|')]
    header = cells(rows[0])
    out = []
    for r in rows[2:]:
        out.append(cells(r))
    return header, out

def parse_stats(block):
    header, rows = parse_table(block)
    profiles = []
    for r in rows:
        if len(r) < 8:
            continue
        name, m, t, sv, w, ld, oc, inv = r[:8]
        st = {'m': m, 't': try_int(t), 'sv': sv, 'w': try_int(w), 'ld': ld, 'oc': try_int(oc)}
        profiles.append((name, st, inv))
    return profiles

def try_int(v):
    v = v.strip()
    return int(v) if re.fullmatch(r'\d+', v) else v

def parse_weapons(block):
    header, rows = parse_table(block)
    out = []
    for r in rows:
        if len(r) < 8:
            continue
        name, rng, a, skill, s, ap, d, ab = r[:8]
        if not name:
            continue
        w = {'name': norm(name)}
        is_melee = rng.strip().lower() == 'melee'
        if not is_melee:
            w['range'] = rng
        w['a'] = a
        if is_melee:
            w['ws'] = skill or '-'
        else:
            w['bs'] = skill or '-'
        w['s'] = s; w['ap'] = ap; w['d'] = d
        abids = []
        for piece in re.split(r',', ab):
            piece = piece.strip()
            if piece:
                aid = add_ability(piece)
                if aid:
                    abids.append(aid)
        w['abilities'] = abids
        w['inheritedAbilities'] = []
        out.append((is_melee, w))
    return out

def parse_comp(comp):
    """Return (default, base, mx). Handles ranges & multi-part comps."""
    comp = norm(comp)
    nums = []
    # collect leading ranges of each ;-separated clause
    for part in comp.split(';'):
        m = re.match(r'\s*(\d+)\s*-\s*(\d+)', part)
        if m:
            nums.append((int(m.group(1)), int(m.group(2))))
        else:
            m = re.match(r'\s*(\d+)', part)
            if m:
                nums.append((int(m.group(1)), int(m.group(1))))
    if not nums:
        return 1, 1, None
    base = sum(n[0] for n in nums)
    mx = sum(n[1] for n in nums)
    return base, base, (mx if mx != base else None)

# ── Points file ───────────────────────────────────────────────────────────────
def parse_points():
    pts = {}
    lines = [l.rstrip() for l in open(os.path.join(ROOT, 'ChaosDaemonsPoints.txt'), encoding='utf-8')]
    cur = None
    for l in lines:
        if not l.strip():
            continue
        m = re.match(r'\s*(\d+)\s+models?\s+(\d+)\s*pts', l, re.I)
        if m and cur:
            pts[cur].append((int(m.group(1)), int(m.group(2))))
        elif not re.match(r'\s*\d+\s+model', l, re.I):
            cur = slug(l)
            pts[cur] = []
    return pts

POINTS = parse_points()
# Manual overrides: Tranceweaver's value was truncated in the source upload.
POINTS['tranceweaver'] = [(1, 60)]

# ── BS/WS skill values (ESTIMATED from 10th-ed knowledge) ─────────────────────
# The Wahapedia export dropped the Skill column for every weapon (0/436 present).
# Filled per unit and applied to all that unit's weapons: ws->melee, bs->ranged.
# BS is NOT applied to Torrent weapons (they auto-hit). Mount weapons are
# corrected via SUB_WS substring overrides. Flagged with unit.skillEstimated.
SKILLS = {
    # uid: (ws, bs)  — use None where a unit has no relevant profile
    'beasts-of-nurgle': ('4+', None), 'belakor': ('2+', '2+'),
    'bloodcrushers': ('3+', None), 'bloodletters': ('3+', None),
    'bloodmaster': ('2+', None), 'bloodthirster': ('2+', '2+'),
    'blue-horrors': ('5+', '5+'), 'burning-chariot': ('4+', '4+'),
    'changecaster': ('4+', '3+'), 'daemon-prince-of-chaos': ('2+', '3+'),
    'daemon-prince-of-chaos-with-wings': ('2+', '3+'), 'daemonettes': ('3+', None),
    'epidemius': ('4+', None), 'exalted-flamer': ('4+', '3+'),
    'fateskimmer': ('4+', '3+'), 'fiends': ('3+', None),
    'flamers': ('4+', None), 'flesh-hounds': ('3+', None),
    'fluxmaster': ('4+', '3+'), 'great-unclean-one': ('3+', '4+'),
    'hellflayers': ('3+', '3+'), 'horticulous-slimux': ('3+', None),
    'infernal-enrapturess': ('3+', '3+'), 'kairos-fateweaver': ('4+', '2+'),
    'karanak': ('4+', None), 'keeper-of-secrets': ('2+', '3+'),
    'lord-of-change': ('3+', '2+'), 'nurglings': ('5+', None),
    'pink-horrors': ('4+', '4+'), 'plague-drones': ('4+', '4+'),
    'plaguebearers': ('4+', None), 'poxbringer': ('4+', None),
    'rendmaster-on-blood-throne': ('2+', None), 'rotigus': ('3+', None),
    'screamers': ('4+', None), 'seekers': ('3+', None),
    'shalaxi-helbane': ('2+', '2+'), 'skarbrand': ('2+', None),
    'skull-cannon': ('4+', '4+'), 'skullmaster': ('2+', None),
    'skulltaker': ('2+', None), 'sloppity-bilepiper': ('4+', None),
    'soul-grinder': ('3+', '3+'), 'spoilpox-scrivener': ('4+', None),
    'syllesske': ('2+', '3+'), 'the-blue-scribes': ('4+', None),
    'the-changeling': ('4+', None), 'the-masque-of-slaanesh': ('2+', None),
    'tormentbringer': ('3+', '3+'), 'tranceweaver': ('3+', None),
}
# mount weapons hit worse than their rider — override to 4+ when rider is better
SUB_WS = ['bladed horn', 'juggernaut', 'bladed wheels', 'mulch', 'steed', 'tongue']

def apply_skills(unit):
    sk = SKILLS.get(unit['id'])
    if not sk:
        return
    ws, bs = sk
    touched = False
    for w in unit['weapons']['melee']:
        if w.get('ws', '-') in ('', '-'):
            val = ws
            if ws and int(ws[0]) < 4 and any(t in w['name'].lower() for t in SUB_WS):
                val = '4+'
            if val:
                w['ws'] = val; touched = True
    for w in unit['weapons']['ranged']:
        if 'torrent' in w.get('abilities', []):
            continue  # auto-hits; BS not used
        if bs and w.get('bs', '-') in ('', '-'):
            w['bs'] = bs; touched = True
    if touched:
        unit['skillEstimated'] = True

# ── Main datasheet parse ─────────────────────────────────────────────────────
text = norm(open(REF, encoding='utf-8').read())
ds = text.split('## UNIT DATASHEETS', 1)[1]

# map each datasheet name -> the most recent "### CATEGORY" header above it
CATEGORY = {}
_cur_cat = ''
for _line in ds.splitlines():
    hm = re.match(r'### (.+)', _line)
    if hm:
        _cur_cat = hm.group(1).strip().upper()
    um = re.match(r'#### (.+)', _line)
    if um:
        CATEGORY[um.group(1).strip()] = _cur_cat

blocks = re.split(r'\n#### ', ds)

units = {}
seen = set()
for b in blocks[1:]:
    name = b.split('\n', 1)[0].strip()
    kwm = re.search(r'\*\*Keywords:\*\*(.*)', b)
    if not kwm:
        continue
    raw_kws = [k.strip() for k in kwm.group(1).split(',') if k.strip()]
    kws_lower = [k.lower() for k in raw_kws]
    if 'daemon' not in kws_lower:
        continue
    uid = slug(name)
    if uid in seen:      # skip the duplicate Karanak (keep first/fuller one)
        continue
    seen.add(uid)
    # dedup keywords preserving order, uppercase for display per schema
    kw_seen = set(); keywords = []
    for k in raw_kws:
        ku = k.upper()
        if ku not in kw_seen:
            kw_seen.add(ku); keywords.append(ku)

    unit = {'id': uid, 'name': name, 'keywords': keywords}

    # type labels from notable keywords
    type_labels = [k for k in raw_kws if k.lower() in
                   ('infantry', 'monster', 'vehicle', 'mounted', 'cavalry', 'beast',
                    'character', 'swarm', 'fortification', 'towering', 'titanic')]
    unit['type'] = [t.title() for t in type_labels] or ['Infantry']
    unit['isLeader'] = False
    unit['isEpicHero'] = any(k.lower() == 'epic hero' for k in raw_kws)
    unit['isBattleline'] = CATEGORY.get(name) == 'BATTLELINE'

    # stats
    stm = re.search(r'\|\s*Name\s*\|.*?\n\|[-| ]+\|\n((?:\|.*\n?)+)', b)
    profiles = parse_stats('| Name |\n|---|\n' + (stm.group(1) if stm else ''))
    if profiles:
        if len(profiles) == 1:
            _, st, inv = profiles[0]
            unit['stats'] = st
            if inv and inv != '-':
                unit['invulnerableSave'] = inv
        else:
            unit['stats'] = profiles[0][1]
            unit['modelProfiles'] = [{'name': n, 'count': 1, 'stats': s} for n, s, _ in profiles]
            invs = [i for _, _, i in profiles if i and i != '-']
            if invs:
                unit['invulnerableSave'] = invs[0]

    # composition
    cm = re.search(r'\*\*Unit Composition:\*\*(.*)', b)
    comp = cm.group(1).strip() if cm else ''
    base, default, mx = parse_comp(comp)
    unit['modelBreakdown'] = comp
    unit['models'] = default
    unit['baseModels'] = base
    if mx:
        unit['maxModels'] = mx

    # points (merge brackets)
    pb = POINTS.get(uid)
    if pb:
        pb.sort()
        unit['points'] = pb[0][1]
        unit['baseModels'] = pb[0][0]
        unit['models'] = pb[0][0]
        if len(pb) > 1:
            unit['maxModels'] = pb[-1][0]
            # explicit pricing brackets — these units are priced per bracket
            # size (e.g. 3 or 6 models), not linearly per model.
            unit['modelBrackets'] = [{'models': m, 'points': p} for m, p in pb]
    else:
        # No points entry -> Forgeworld / extra unit; ignored per user decision.
        continue

    # weapons
    weapons = {'ranged': [], 'melee': []}
    for tag, key in (('Ranged Weapons', 'ranged'), ('Melee Weapons', 'melee')):
        wm = re.search(r'\*\*' + tag + r':\*\*\s*\n(\|.*?)(?=\n\*\*|\n---|\Z)', b, re.S)
        if wm:
            for is_melee, w in parse_weapons(wm.group(1)):
                w['count'] = unit['models']
                weapons['melee' if is_melee else 'ranged'].append(w)
    unit['weapons'] = weapons

    # core abilities
    core_ids = []
    cmcore = re.search(r'\*\*Core:\*\*(.*)', b)
    if cmcore:
        for c in cmcore.group(1).split(','):
            c = c.strip()
            if c:
                aid = add_ability(c, 'Core Ability')
                core_ids.append(aid)
                if c.lower().startswith('leader'):
                    unit['isLeader'] = True
    unit['coreAbilities'] = [a for a in core_ids if a]

    # faction
    fac_ids = []
    fm = re.search(r'\*\*Faction:\*\*(.*)', b)
    if fm:
        for c in fm.group(1).split(','):
            c = c.strip()
            if c:
                fac_ids.append(add_ability(c, 'Faction Rule'))

    # named unit abilities: lines like **Name:** desc  and bullets - **Name:** desc
    unit_ab_ids = []
    wargear_ids = []
    in_wargear = False
    for line in b.splitlines():
        if re.match(r'\*Wargear Abilities:\*', line):
            in_wargear = True
            continue
        m = re.match(r'\s*-?\s*\*\*([^:*]+):\*\*\s*(.*)', line)
        if not m:
            continue
        nm, desc = m.group(1).strip(), m.group(2).strip()
        if nm in ('Keywords', 'Unit Composition', 'Core', 'Faction',
                  'Ranged Weapons', 'Melee Weapons', 'Wargear Abilities'):
            continue
        aid = add_named_ability(nm, desc, 'Wargear' if in_wargear else 'Ability')
        (wargear_ids if in_wargear else unit_ab_ids).append(aid)

    unit['abilities'] = [a for a in fac_ids + unit_ab_ids if a]
    unit['wargear'] = [a for a in wargear_ids if a]

    # leader/attachment placeholders (Stage 5 refinement)
    unit['canLead'] = []
    unit['canBeLeadBy'] = []

    apply_skills(unit)   # fill estimated BS/WS (source export omitted them)
    units[uid] = unit

# ── Write unit files ─────────────────────────────────────────────────────────
for uid, u in units.items():
    with open(os.path.join(UNIT_DIR, uid + '.json'), 'w', encoding='utf-8') as f:
        json.dump(u, f, ensure_ascii=False, indent=2)

# ── abilities.json ───────────────────────────────────────────────────────────
with open(os.path.join(ROOT, 'data', 'abilities.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(sorted(abilities.items())), f, ensure_ascii=False, indent=2)

# ── Report ───────────────────────────────────────────────────────────────────
no_pts = [u for u in units if units[u]['points'] == 0]
print(f'units: {len(units)}')
print(f'abilities: {len(abilities)}')
print(f'units without points ({len(no_pts)}): ' + ', '.join(sorted(no_pts)))
print('points keys unmatched: ' + ', '.join(sorted(set(POINTS) - set(units))))
