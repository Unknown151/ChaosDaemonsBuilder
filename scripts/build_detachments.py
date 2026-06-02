#!/usr/bin/env python3
"""Build data/detachments.json (rules + stratagems) and data/units-manifest.json."""
import json, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def norm(s):
    return (s.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
             .replace('–', '-').replace('—', '-').replace('‑', '-').replace('\xa0', ' '))

def slug(s):
    s = norm(s).lower().strip()
    s = re.sub(r"'", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')

# god / faction keyword each detachment keys off (for stratagem targeting later)
GOD = {
    'blood-legion': 'KHORNE', 'daemonic-incursion': None, 'dread-carnival': 'SLAANESH',
    'infernal-onslaught': 'KHORNE', 'legion-of-excess': 'SLAANESH',
    'pandaemoniac-inferno': 'TZEENTCH', 'plague-legion': 'NURGLE',
    'rotten-and-rusted': 'NURGLE', 'scintillating-legion': 'TZEENTCH',
    'shadow-legion': None,
}

# Rule text the Wahapedia export dropped — appended to the detachment rule.
RULE_ADDENDA = {
    'blood-legion': (
        'In addition, each time an enemy unit (excluding AIRCRAFT) ends a Normal '
        'or Advance move within 6" of one or more LEGIONES DAEMONICA KHORNE units '
        'from your army, one of those LEGIONES DAEMONICA KHORNE units can make a '
        'Surge move towards that enemy unit. To do so, roll one D6: models in your '
        'unit move a number of inches up to this result, but your unit must end '
        'that move as close as possible to that enemy unit. When doing so, those '
        'models can be moved within Engagement Range of that enemy unit. A unit '
        'cannot make a Surge move while it is within Engagement Range of one or '
        'more enemy units.'
    ),
}

text = norm(open(os.path.join(ROOT, 'chaos-daemons-reference.md'), encoding='utf-8').read())
section = text.split('## DETACHMENTS', 1)[1].split('## UNIT DATASHEETS', 1)[0]
blocks = re.split(r'\n### ', section)

dets = {}
for b in blocks[1:]:
    name = b.split('\n', 1)[0].strip()
    did = slug(name)
    rule_m = re.search(r'\*\*Detachment Rule:\s*([^*]+)\*\*\s*(.*?)(?=\n\*\*Stratagems:\*\*|\Z)', b, re.S)
    rule_name = rule_m.group(1).strip() if rule_m else ''
    rule_text = re.sub(r'\s*\n\s*', ' ', rule_m.group(2).strip()) if rule_m else ''
    if did in RULE_ADDENDA:
        rule_text = (rule_text + ' ' + RULE_ADDENDA[did]).strip()

    strat_part = b.split('**Stratagems:**', 1)[1] if '**Stratagems:**' in b else ''
    strat_blocks = re.split(r'\n\*\*([A-Z][^*]+?)\*\*\s*\((\d+CP)\)\s*[-–—]\s*(.*)', strat_part)
    stratagems = []
    # re.split with 3 groups -> [pre, name, cp, cat, body, name, cp, cat, body, ...]
    for i in range(1, len(strat_blocks) - 3, 4):
        sname = strat_blocks[i].strip()
        cp = strat_blocks[i + 1].strip()
        cat = strat_blocks[i + 2].strip()
        body = strat_blocks[i + 3]
        def field(key):
            m = re.search(key + r':\s*(.*?)(?=\n[A-Z]{2,}:|\nDesigner|\nExample|\Z)', body, re.S)
            return re.sub(r'\s*\n\s*', ' ', m.group(1).strip()) if m else ''
        stratagems.append({
            'id': slug(sname),
            'name': sname,
            'cp': cp,
            'category': cat,
            'when': field('WHEN'),
            'target': field('TARGET'),
            'effect': field('EFFECT'),
            'restrictions': field('RESTRICTIONS'),
        })

    dets[did] = {
        'id': did,
        'name': name,
        'god': GOD.get(did),
        'ruleId': slug(rule_name) or did + '-rule',
        'ruleName': rule_name,
        'ruleType': f'Detachment Rule - {rule_name}',
        'ruleDescription': rule_text,
        'stratagems': stratagems,
    }

with open(os.path.join(ROOT, 'data', 'detachments.json'), 'w', encoding='utf-8') as f:
    json.dump(dets, f, ensure_ascii=False, indent=2)

# unit manifest (browser can't list a directory)
ids = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'data', 'units', '*.json')))
with open(os.path.join(ROOT, 'data', 'units-manifest.json'), 'w', encoding='utf-8') as f:
    json.dump(ids, f, indent=2)

print(f'detachments: {len(dets)}')
for d in dets.values():
    print(f"  {d['id']:24s} rule={d['ruleName']!r:34s} stratagems={len(d['stratagems'])}")
print(f'manifest units: {len(ids)}')
