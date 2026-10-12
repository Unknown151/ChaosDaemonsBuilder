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

# ── Standard 11th-ed rules summaries for common weapon/core abilities ─────────
# Keyed by the *base* keyword (parameter stripped). Used to fill ability bodies.
# Short summaries of the 11th edition core rules (section 24) — see the core
# rules for the full wording.
BASE_RULES = {
    'lethal hits': ('Weapon Ability', 'Each <strong>Critical Hit</strong> made with this weapon can be treated as an automatic wound (your choice). No Wound roll is made for it, so it cannot become a Critical Wound.'),
    'sustained hits': ('Weapon Ability', 'Each <strong>Critical Hit</strong> made with this weapon scores X additional hits on the target.'),
    'devastating wounds': ('Weapon Ability', 'Each <strong>Critical Wound</strong> ends that attack and deals mortal wounds equal to the weapon’s Damage instead, applied after any normal damage. Each Critical Wound can damage only one model — excess mortal wounds are lost.'),
    'precision': ('Weapon Ability', 'If the target unit contains a visible CHARACTER, you can choose for these attacks to be allocated to that CHARACTER first.'),
    'torrent': ('Weapon Ability', 'Attacks made with this weapon automatically hit. A [TORRENT] weapon cannot also have [INDIRECT FIRE] or [PRECISION].'),
    'ignores cover': ('Weapon Ability', 'The target cannot have the Benefit of Cover against this weapon’s attacks — including cover granted by rules such as Stealth.'),
    'rapid fire': ('Weapon Ability', 'Gain X additional attack dice when the target is within half this weapon’s range.'),
    'assault': ('Weapon Ability', 'A unit with one or more [ASSAULT] weapons can shoot using assault shooting (core rules 10.05).'),
    'heavy': ('Weapon Ability', 'In your Shooting phase, add 1 to Hit rolls if the bearer’s unit is unengaged, was not set up this turn, and none of its models moved more than 3" this turn.'),
    'pistol': ('Weapon Ability', 'Identical to [CLOSE-QUARTERS]: the bearer’s unit can shoot using close-quarters shooting (core rules 10.06). When shooting any other way, a model that is not a MONSTER or VEHICLE fires either these weapons or its other ranged weapons, not both.'),
    'blast': ('Weapon Ability', 'Gain 1 additional attack dice for every five models in the target unit (rounding down). [BLAST X] adds X per five models instead.'),
    'melta': ('Weapon Ability', 'Add X to this weapon’s Damage when the target is within half range.'),
    'anti': ('Weapon Ability', '[ANTI-X Y+]: against a target with keyword X, an unmodified Wound roll of Y+ is a Critical Wound.'),
    'hazardous': ('Weapon Ability', 'After the unit has resolved its attacks, make one hazard roll for each [HAZARDOUS] weapon it used. Hazard roll: on a D6 result of 1-2 the unit suffers 1 mortal wound (3 if every model in it is a MONSTER or VEHICLE).'),
    'psychic': ('Weapon Ability', 'Each time an attack is made with a [PSYCHIC] weapon, you can ignore any or all modifiers to that attack’s BS or WS characteristic and any or all modifiers to the hit roll. Attacks made with [PSYCHIC] weapons are known as psychic attacks (this can be important for the triggering of other rules).'),
    'lance': ('Weapon Ability', 'Add 1 to Wound rolls if the attacking model’s unit made a Charge move this turn.'),
    'twin-linked': ('Weapon Ability', 'You can re-roll the Wound roll for attacks made with this weapon.'),
    'extra attacks': ('Weapon Ability', 'The bearer attacks with all of its [EXTRA ATTACKS] weapons in addition to one of its other melee weapons.'),
    'indirect fire': ('Weapon Ability', 'A unit with one or more [INDIRECT FIRE] weapons can shoot using indirect shooting (core rules 10.07).'),
    'one shot': ('Weapon Ability', 'This weapon can only be selected to make attacks once per battle.'),
    'deep strike': ('Core Ability', 'When this unit makes an ingress move, it can be set up anywhere on the battlefield that is more than 8" horizontally from all enemy units — if every model in the unit has this ability.'),
    'deadly demise': ('Core Ability', 'When this model is destroyed, roll one D6: on a 6, each unit within 6" suffers X mortal wounds (roll separately for each unit if X is random).'),
    'scouts': ('Core Ability', 'Before the battle, if every model in the unit has this ability: a unit wholly within your deployment zone can make a scout move of up to X", ending more than 8" from all enemy units. A unit in Strategic Reserves can instead be set up wholly within your deployment zone.'),
    'leader': ('Core Ability', 'When mustering your army, this unit can be attached to one Bodyguard unit it is able to lead. A Bodyguard unit can have one Leader and one Support unit attached.'),
    'fights first': ('Core Ability', 'While every model in the unit has this ability, it is a Fights First unit and fights in the Fights First step of the Fight phase.'),
    'feel no pain': ('Core Ability', 'Each time a model with this ability would lose a wound, roll one D6: on X+, that wound is not lost.'),
    'stealth': ('Core Ability', 'If every model in a unit has this ability, each time a ranged attack targets that unit, that unit has the <strong onclick="showModal(\'benefit-of-cover\')" style="cursor:pointer;text-decoration:underline">Benefit of Cover</strong> against that attack (13.08).'),
    'benefit of cover': ('Core Ability', 'Each time a ranged attack targets a unit that has the Benefit of Cover against it, worsen the BS characteristic of that attack by 1.'),
    'lone operative': ('Core Ability', 'Unless it is part of an attached unit, this unit is only visible to enemy models within 12", and [INDIRECT FIRE] weapons can only target it from within 12".'),
    'firing deck': ('Core Ability', 'Embarked models can shoot as if part of this Transport (up to the listed number of weapons).'),
    'infiltrators': ('Core Ability', 'During deployment, if every model in the unit has this ability, it can be set up anywhere more than 8" horizontally from the enemy deployment zone and all enemy units.'),
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

# ── Authoritative per-unit overrides (data/overrides.json) ────────────────────
# Hand-maintained corrections from official datasheets the user provides.
# Deep-merged over the parsed unit; "verified": true clears the BS/WS estimate flag.
_ov_path = os.path.join(ROOT, 'data', 'overrides.json')
OVERRIDES = json.load(open(_ov_path, encoding='utf-8')) if os.path.exists(_ov_path) else {}

# Point updates from the user's live pricing reference (supersedes the original
# points file; adds 1st-2nd vs 3rd+ same-unit tiered pricing where it applies).
_pts_ov_path = os.path.join(ROOT, 'data', 'points-overrides.json')
POINTS_OVERRIDES = json.load(open(_pts_ov_path, encoding='utf-8')) if os.path.exists(_pts_ov_path) else {}

def apply_points_override(unit):
    ov = POINTS_OVERRIDES.get(unit['id'])
    if not ov:
        return
    for k, v in ov.items():
        unit[k] = v

def apply_override(unit):
    ov = OVERRIDES.get(unit['id'])
    if not ov:
        return
    for k, v in ov.items():
        if k == 'verified':
            if v:
                unit.pop('skillEstimated', None)
                unit['verified'] = True
        elif k == 'weaponSkills':
            # per-weapon BS/WS fixes: WS applies to melee profiles, BS to ranged
            # (some weapons share a name across both, e.g. lashes of torment)
            for cat, key in (('melee', 'ws'), ('ranged', 'bs')):
                for w in unit['weapons'][cat]:
                    fix = v.get(w['name'])
                    if fix and key in fix:
                        w[key] = fix[key]
        else:
            unit[k] = v

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
    'karanak': ('2+', None), 'keeper-of-secrets': ('2+', '3+'),
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
    # dedup keywords preserving order, uppercase for display per schema.
    # Drop 'SHADOW LEGION' — a detachment name wrongly injected by the export.
    kw_seen = set(); keywords = []
    for k in raw_kws:
        ku = k.upper()
        if ku == 'SHADOW LEGION':
            continue
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
    apply_override(unit) # authoritative corrections from official datasheets
    apply_points_override(unit) # live points reference (supersedes points file)
    units[uid] = unit

# ── Write unit files ─────────────────────────────────────────────────────────
for uid, u in units.items():
    with open(os.path.join(UNIT_DIR, uid + '.json'), 'w', encoding='utf-8') as f:
        json.dump(u, f, ensure_ascii=False, indent=2)

# ── abilities.json ───────────────────────────────────────────────────────────
# Curated short summaries (overview text on the ability tiles). Anything not
# listed falls back to an auto-generated first-clause snippet.
ABILITY_SHORT = {
    'psychic': 'Ignore BS/WS & hit-roll modifiers; counts as a psychic attack',
    'stealth': 'Ranged attacks targeting this unit have the Benefit of Cover',
    'benefit-of-cover': 'Ranged attacks targeting the unit have -1 BS',
    # core
    'deep-strike': 'Ingress move: set up >8" from all enemy units',
    'leader': 'Can attach to a Bodyguard unit',
    'fights-first': 'Fights first in the Fight phase',
    'scouts-6': 'Pre-battle move up to 6"',
    'scouts-9': 'Pre-battle move up to 9"',
    'infiltrators': 'Deploy anywhere >8" from the enemy zone and units',
    'lone-operative': 'Only visible to enemy models within 12"',
    # weapon
    'lethal-hits': 'Critical Hits can automatically wound',
    'devastating-wounds': 'Critical Wounds deal mortal wounds equal to Damage',
    'hazardous': 'Hazard roll after attacking: 1-2 → mortal wound(s)',
    'assault': 'Unit can shoot using assault shooting',
    'pistol': 'Close-quarters weapon — can shoot while engaged',
    'blast': '+1 attack dice per five models in the target',
    'precision': 'Can be allocated to a visible Character first',
    'deadly-demise-d6': 'On death, roll D6; 6 → D6 MW to units within 6"',
    'deadly-demise-d3': 'On death, roll D6; 6 → D3 MW to units within 6"',
    'deadly-demise-1': 'On death, roll D6; 6 → 1 MW to units within 6"',
    # Blood Legion / verified units
    'brass-stampede': 'After a Charge: D6 per model, each 4+ → D3 MW',
    'bane-of-cowards': 'Enemies that Fall Back nearby take Desperate Escape tests',
    'lord-of-decapitations': "Led unit's melee gains [Devastating Wounds]",
    'skulls-for-khorne': 'Re-roll Hit & Wound vs Characters; +1CP on a kill',
    'pack-leader': 'Led unit can re-roll Advance & Charge',
    'prey-of-the-blood-god': 'Mark prey: re-roll Wounds against it in melee',
    'blood-throne': 'Mark a target: friendly Khorne get +1 S/AP/D vs it',
    'champion-slayer': 'Re-roll Wounds vs Characters/Monsters; heal D6 on a kill',
    'skulls-of-the-fallen': 'After shooting, a unit hit takes a Battle-shock test',
    'daemon-lord-of-khorne-aura': 'Aura: nearby Khorne get +1 to melee Hit rolls',
    'relentless-carnage': 'End of Fight: 8D6, each 4+ → 1 MW to a unit in range',
    'greater-daemon-of-khorne-aura': 'Aura: nearby Khorne are within your Shadow of Chaos',
    'rage-embodied-aura': 'Aura: nearby Khorne get +1 Attack to melee weapons',
    'murderlust': 'Can declare a charge in a turn it Advanced',
    'malefic-destruction': 'Once per battle: +3 Attacks to hellforged weapons',
    'harbinger-of-death': 'Each fight, pick a keyword for hellforged weapons',
    'supreme-commander': 'This model must be your Warlord',
    'the-dark-master-aura': 'Aura: 6" around is within your Shadow of Chaos',
    'shadow-form': 'Each battle round, pick one Shadow Form ability',
    'daemon-prince-of-khorne': 'Khorne: +2 S to hellforged weapons',
    'daemon-prince-of-tzeentch': 'Tzeentch: +3 Attacks to infernal cannon',
    'daemon-prince-of-nurgle': 'Nurgle: +1 Toughness',
    'daemon-prince-of-slaanesh': 'Slaanesh: +2" Move',
    'daemonic-icon': "Unit's Leadership becomes 6+",
    'instrument-of-chaos': '+1 to Charge rolls',
    'grotesque-regeneration': 'Heals all lost wounds at end of each phase',
}

def make_short(desc):
    t = re.sub(r'<[^>]+>', '', norm(desc or '')).strip()
    if not t or 'not provided' in t.lower():
        return ''
    sent = re.split(r'(?<=[.:])\s+', t)[0].rstrip(' .:')
    if len(sent) > 78:
        sent = sent[:75].rsplit(' ', 1)[0] + '…'
    return sent

# glossary entries not attached to any datasheet but linked from other rules
GLOSSARY = {
    'benefit-of-cover': 'benefit of cover',
}
for _gid, _bk in GLOSSARY.items():
    if _gid not in abilities and _bk in BASE_RULES:
        _kind, _desc = BASE_RULES[_bk]
        abilities[_gid] = {'name': 'Benefit of Cover', 'type': _kind, 'description': _desc}

# ── authoritative ability overrides (data/ability-overrides.json) ─────────────
# Datasheet abilities whose rules changed since the reference export, or whose
# text the export truncated. Fields are merged over the parsed entry, new ids
# are added, and a null value drops an entry that is no longer used.
_ab_ov_path = os.path.join(ROOT, 'data', 'ability-overrides.json')
if os.path.exists(_ab_ov_path):
    for _aid, _fields in json.load(open(_ab_ov_path, encoding='utf-8')).items():
        if _fields is None:
            abilities.pop(_aid, None)
        else:
            abilities.setdefault(_aid, {'name': _aid, 'type': 'Ability', 'description': ''}).update(_fields)

for _aid, _a in abilities.items():
    _a['short'] = _a.get('short') or ABILITY_SHORT.get(_aid) or make_short(_a.get('description'))

with open(os.path.join(ROOT, 'data', 'abilities.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(sorted(abilities.items())), f, ensure_ascii=False, indent=2)

# ── Build version stamp (cache-busting) ──────────────────────────────────────
import time as _time
with open(os.path.join(ROOT, 'data', 'version.json'), 'w', encoding='utf-8') as f:
    json.dump({'v': _time.strftime('%Y%m%d%H%M%S')}, f)

# ── Report ───────────────────────────────────────────────────────────────────
no_pts = [u for u in units if units[u]['points'] == 0]
print(f'units: {len(units)}')
print(f'abilities: {len(abilities)}')
print(f'units without points ({len(no_pts)}): ' + ', '.join(sorted(no_pts)))
print('points keys unmatched: ' + ', '.join(sorted(set(POINTS) - set(units))))
