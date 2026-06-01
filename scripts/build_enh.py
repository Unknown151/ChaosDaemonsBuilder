#!/usr/bin/env python3
"""Build data/enhancements.json and a default data/army.json (Blood Legion)."""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def norm(s):
    return (s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
             .replace('–', '-').replace('—', '-').replace('‑', '-').replace('\xa0', ' '))

def slug(s):
    s = norm(s).lower().strip()
    s = re.sub(r"'", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')

DET_ID = {
    'blood legion': 'blood-legion',
    'daemonic incursion': 'daemonic-incursion',
    'legion of excess': 'legion-of-excess',
    'plague legion': 'plague-legion',
    'scintillating legion': 'scintillating-legion',
    'shadow legion': 'shadow-legion',
}

# ── points + detachment grouping ──────────────────────────────────────────────
enh = {}
cur = None
for line in open(os.path.join(ROOT, 'ChaosDaemonsEnhancementPoints.txt'), encoding='utf-8'):
    line = norm(line.strip())
    if not line or line.upper() == 'DETACHMENT ENHANCEMENTS':
        continue
    m = re.match(r'-(.+)-$', line)
    if m:
        cur = DET_ID.get(m.group(1).strip().lower())
        continue
    pm = re.match(r'(.+?)\s+(\d+)\s*pts$', line)
    if pm and cur:
        name = pm.group(1).strip()
        pts = int(pm.group(2))
        eid = slug(name)
        enh[eid] = {
            'name': name,
            'type': f'Enhancement ({pts} pts)',
            'points': pts,
            'detachment': cur,
            'description': '<em>Rules text not provided in source data.</em>',
        }

# ── Blood Legion full descriptions ────────────────────────────────────────────
bl = norm(open(os.path.join(ROOT, 'ChaosDaemonsEnhancementsBloodLegion.txt'), encoding='utf-8').read())
# Split on **NAME** headers
parts = re.split(r'\*\*([^*]+)\*\*', bl)
# parts: ['', NAME1, body1, NAME2, body2, ...]
for i in range(1, len(parts) - 1, 2):
    raw_name = parts[i].strip()
    body = parts[i + 1].strip()
    # strip "(AURA)" etc. from the matching name
    clean = re.sub(r'\s*\(.*?\)\s*$', '', raw_name).strip()
    eid = slug(clean)
    if eid not in enh:
        continue
    # collapse whitespace/newlines
    body = re.sub(r'\s*\n\s*', ' ', body).strip()
    # pull restriction ("... model only.")
    restr = None
    rm = re.search(r'((?:Legiones Daemonica )?Khorne[^.]*?(?:model|unit)s? only)\.', body, re.I)
    if rm:
        restr = rm.group(1).strip()
    # rebuild description with aura tag if present
    aura = ''
    am = re.search(r'\((AURA|PSYCHIC)\)', raw_name, re.I)
    if am:
        aura = f'<strong>[{am.group(1).upper()}]</strong> '
    enh[eid]['description'] = aura + body
    if restr:
        enh[eid]['restriction'] = restr

with open(os.path.join(ROOT, 'data', 'enhancements.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(sorted(enh.items())), f, ensure_ascii=False, indent=2)

# ── default army.json (small Blood Legion sample) ─────────────────────────────
units_dir = os.path.join(ROOT, 'data', 'units')
have = lambda u: os.path.exists(os.path.join(units_dir, u + '.json'))
sample = [u for u in ['bloodthirster', 'bloodmaster', 'bloodletters', 'bloodcrushers', 'flesh-hounds'] if have(u)]
army = {
    'name': 'Blood Legion Patrol',
    'detachment': 'blood-legion',
    'pointsLimit': 1000,
    'units': [{'unitId': u} for u in sample],
}
with open(os.path.join(ROOT, 'data', 'army.json'), 'w', encoding='utf-8') as f:
    json.dump(army, f, ensure_ascii=False, indent=2)

print(f'enhancements: {len(enh)}')
print('blood-legion enh:', [e for e in enh if enh[e]['detachment'] == 'blood-legion'])
print('with full descriptions:', [e for e in enh if 'not provided' not in enh[e]['description']])
print('army sample:', sample)
