#!/usr/bin/env python3
"""Validator for Nova item files. Usage: python3 validate_items.py <file.json> [--quiet]"""
import json, sys, os, re, math, difflib
import pandas as pd

import os as _os
ROOT = _os.environ.get('NOVA_ROOT', '/home/claude/nova')  # set NOVA_ROOT to the folder containing the six dataset folders
DIRS = {'D1': '1. GSE47363 - mir-542-3p', 'D2': '2. GSE147507 - Covid NBHE', 'D3': '3. GSE150316 - Covid Influenza',
        'D4': '4. GSE26487 - Dexamethasone', 'D5': '5. GSE74000 - Acetaminophen', 'D6': '6. GSE58434 - Vitamin D Calcitriol'}
S1_N = {'D1': 67, 'D2': 67, 'D3': 67, 'D4': 67, 'D5': 66, 'D6': 66}
S1_RRL = {k: {'R0': 7, 'R1': 10, 'R2': (17 if S1_N[k] == 67 else 16), 'R3': 20, 'R4': 13} for k in S1_N}
S1_MAN = {'D1': 17, 'D2': 17, 'D3': 17, 'D4': 17, 'D5': 16, 'D6': 16}
TRAJ_LEN = {'D1': [9, 8, 11, 11, 11], 'D2': [8, 9, 11, 11, 11], 'D3': [9, 8, 11, 11, 11], 'D4': [8, 9, 11, 11, 11],
            'D5': [8, 8, 12, 11, 11], 'D6': [8, 8, 12, 11, 11]}  # first two = MANUAL_CURATED_CANDIDATE
RRL = {'R0', 'R1', 'R2', 'R3', 'R4'}; DIFF = {'EASY', 'MODERATE', 'HARD', 'EXPERT'}
GS = {'MANUAL_CURATED_CANDIDATE', 'LLM_ASSISTED_REVIEW_PENDING'}
QT = {'MCQ', 'TRUE_FALSE', 'SHORT_ANSWER', 'EVIDENCE_INTEGRATION', 'MECHANISTIC_INTERPRETATION'}
LAYERS = {'DEG', 'PATHWAY', 'GO', 'UPSTREAM_REGULATOR', 'MIRNA', 'DISEASE', 'PHENOTYPE', 'LITERATURE', 'OTHER'}
LAYERS3 = LAYERS | {'TARGET_GENE_DIRECTIONALITY', 'CONTRADICTORY_EVIDENCE', 'LIMITING_EVIDENCE', 'ALTERNATIVE_MECHANISMS',
                    'DEGS', 'PATHWAYS', 'UPSTREAM_REGULATORS', 'MIRNAS', 'DISEASE_ASSOCIATIONS', 'PHENOTYPE_ASSOCIATIONS', 'PROVIDED_LITERATURE'}
STATES = {'SUPPORTED', 'PARTIALLY_SUPPORTED', 'INSUFFICIENT_EVIDENCE', 'WEAKENED', 'CONTRADICTED'}
REL = {'SUPPORTS', 'CONTRADICTS', 'QUALIFIES', 'NEUTRAL'}
DEC = {'RETAIN', 'QUALIFY', 'REVISE', 'REJECT', 'INSUFFICIENT_EVIDENCE'}
_cache = {}
errors, warns = [], []

def E(m): errors.append(m)
def W(m): warns.append(m)

def table(dk, f):
    k = (dk, f)
    if k not in _cache:
        p = f"{ROOT}/{DIRS[dk]}/data/{f}"
        if not os.path.exists(p): _cache[k] = None
        else: _cache[k] = pd.read_csv(p, sep='\t')
    return _cache[k]

def close(a, b):
    try:
        a = float(a); b = float(b)
    except Exception:
        return str(a).strip().lower() == str(b).strip().lower()
    if a == b: return True
    if b != 0 and 0 < abs(b) < 1e-2 and a > 0 and b > 0:  # p-value-like: compare in log10
        return abs(math.log10(a) - math.log10(b)) < 0.06 or abs(a - b) / abs(b) < 0.15
    return abs(a - b) <= max(0.011, 0.03 * abs(b)) or (abs(b) >= 1 and abs(a - b) <= 0.051)

def check_facts(dk, where, checks):
    if not isinstance(checks, list): E(f"{where}: checks must be a list"); return
    for c in checks:
        try:
            f, kc, key, col, val = c['file'], c['key_col'], c['key'], c['col'], c['value']
        except Exception:
            E(f"{where}: malformed check {c}"); continue
        f = f.replace('data/', '')
        t = table(dk, f)
        if t is None: E(f"{where}: check file not found {f}"); continue
        if kc not in t.columns or col not in t.columns: E(f"{where}: column missing in {f}: {kc}/{col}"); continue
        rows = t[t[kc].astype(str) == str(key)]
        if len(rows) == 0: E(f"{where}: key not found {f}[{kc}={key}]"); continue
        if not any(close(v, val) for v in rows[col].tolist()):
            E(f"{where}: VALUE MISMATCH {f}[{kc}={key}].{col}: stated {val}, file {rows[col].tolist()[:3]}")

def need(where, obj, keys):
    for k in keys:
        if k not in obj: E(f"{where}: missing key {k}"); continue
        v = obj[k]
        if k in ('checks', 'Depends_On', 'turns', 'steps', 'final'): continue
        if not isinstance(v, str): E(f"{where}: {k} must be string"); continue
        if k.startswith('Option_'): continue
        if not v.strip(): E(f"{where}: {k} empty")

def layers_ok(where, s, allowed):
    toks = [t.strip() for t in s.split(';') if t.strip()]
    bad = [t for t in toks if t not in allowed]
    if bad: E(f"{where}: invalid evidence layer tokens {bad}")
    return toks

def dupcheck(qs, label):
    norm = [re.sub(r'\W+', ' ', q.lower()).strip() for q in qs]
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            r = difflib.SequenceMatcher(None, norm[i], norm[j]).ratio()
            if r > 0.9: E(f"{label}: near-duplicate questions #{i+1} and #{j+1} (ratio {r:.2f})")
            elif r > 0.8: W(f"{label}: similar questions #{i+1} and #{j+1} (ratio {r:.2f})")

S1K = ['Generation_Source', 'Question_Type', 'RRL', 'Difficulty', 'Question', 'Option_A', 'Option_B', 'Option_C', 'Option_D', 'Correct_Answer',
       'Reference_Answer', 'Required_Evidence', 'Evidence_Layers', 'Evidence_Provenance', 'Required_Reasoning_Relations', 'Supporting_Evidence',
       'Contradictory_Evidence', 'Expected_Conclusion', 'Acceptable_Alternative', 'Rationale_for_RRL', 'Rationale_for_Difficulty', 'checks']
S2T = ['Generation_Source', 'Trajectory_Goal', 'Starting_Biological_Question', 'Overall_Difficulty', 'Expected_Final_Interpretation', 'Primary_Mechanism', 'Primary_Uncertainty', 'turns']
S2K = ['Question', 'RRL', 'Difficulty', 'Depends_On', 'Prior_Evidence_Required', 'New_Evidence_Required', 'Evidence_Layers', 'Evidence_Provenance', 'Required_Reasoning',
       'Reference_Answer', 'Supporting_Evidence', 'Contradictory_Evidence', 'Consistency_Constraint', 'Revision_Expected', 'Expected_Revision', 'Challenge_Turn', 'Rationale_for_Difficulty', 'checks']
S3H = ['Generation_Source', 'Initial_Hypothesis', 'Biological_Rationale', 'Primary_Mechanism', 'Evidence_Layers_Available', 'Initial_Evidence_Status', 'Overall_Difficulty',
       'Expected_Final_State', 'Reference_Revised_Hypothesis', 'steps', 'final']
S3K = ['Question', 'RRL', 'Difficulty', 'Depends_On', 'Evidence_Being_Tested', 'Evidence_Layer', 'Evidence_Provenance', 'Reference_Evidence', 'Expected_Reasoning',
       'Evidence_Relationship_to_Hypothesis', 'Hypothesis_State_Before', 'Hypothesis_State_After', 'Revision_Expected', 'Revised_Hypothesis', 'Supporting_Evidence',
       'Contradictory_or_Limiting_Evidence', 'Alternative_Explanation', 'Rationale_for_Difficulty', 'checks']
S3F = ['Reference_Final_Answer', 'Supporting_Evidence_Summary', 'Contradictory_or_Limiting_Evidence_Summary', 'Alternative_Explanation', 'Final_Hypothesis_State', 'Decision',
       'Reference_Revised_Hypothesis', 'Calibration_Requirement', 'Evidence_Provenance_Summary']

def v1(d, dk):
    items = d.get('items', [])
    if len(items) != S1_N[dk]: E(f"S1 count {len(items)} != {S1_N[dk]}")
    cnt = {r: 0 for r in RRL}; man = 0; tf = {'TRUE': 0, 'FALSE': 0}; letters = {}
    for i, it in enumerate(items, 1):
        w = f"item {i}"
        need(w, it, S1K)
        if it.get('Generation_Source') not in GS: E(f"{w}: bad Generation_Source")
        if it.get('Generation_Source') == 'MANUAL_CURATED_CANDIDATE': man += 1
        if it.get('Question_Type') not in QT: E(f"{w}: bad Question_Type")
        if it.get('RRL') not in RRL: E(f"{w}: bad RRL")
        else: cnt[it['RRL']] += 1
        if it.get('Difficulty') not in DIFF: E(f"{w}: bad Difficulty")
        layers_ok(w, it.get('Evidence_Layers', ''), LAYERS)
        qt = it.get('Question_Type')
        opts = [it.get(f'Option_{x}', '') for x in 'ABCD']
        if qt == 'MCQ':
            if any(not o.strip() for o in opts): E(f"{w}: MCQ needs 4 options")
            if len(set(o.strip().lower() for o in opts)) < 4: E(f"{w}: MCQ options not distinct")
            m = re.match(r'^([ABCD]) \| (.+)$', it.get('Correct_Answer', '').strip())
            if not m: E(f"{w}: MCQ Correct_Answer must be 'X | text'")
            else:
                letters[m.group(1)] = letters.get(m.group(1), 0) + 1
                if m.group(2).strip().lower() != it.get(f'Option_{m.group(1)}', '').strip().lower(): E(f"{w}: Correct_Answer text does not match Option_{m.group(1)}")
        else:
            if any(o.strip() for o in opts): E(f"{w}: non-MCQ must have blank options")
        if qt == 'TRUE_FALSE':
            if it.get('Correct_Answer') not in ('TRUE', 'FALSE'): E(f"{w}: TRUE_FALSE answer must be TRUE/FALSE")
            else: tf[it['Correct_Answer']] += 1
        if it.get('RRL') in ('R2', 'R3', 'R4') and '->' not in it.get('Required_Reasoning_Relations', ''): W(f"{w}: R2-R4 reasoning relations lack '->' chain")
        if it.get('RRL') in ('R2', 'R3', 'R4') and len(layers_ok(w, it.get('Evidence_Layers', ''), LAYERS)) < 2: W(f"{w}: R2+ item lists <2 evidence layers")
        check_facts(dk, w, it.get('checks', []))
    for r, n in S1_RRL[dk].items():
        if cnt[r] != n: E(f"S1 RRL {r}: {cnt[r]} != target {n}")
    if man != S1_MAN[dk]: E(f"S1 MANUAL_CURATED_CANDIDATE count {man} != {S1_MAN[dk]}")
    if tf['TRUE'] + tf['FALSE'] and min(tf.values()) == 0: W(f"TRUE/FALSE answers unbalanced {tf}")
    if letters and max(letters.values()) > 0.6 * sum(letters.values()): W(f"MCQ correct letters skewed {letters}")
    dupcheck([it.get('Question', '') for it in items], 'S1')

def v2(d, dk):
    trs = d.get('trajectories', [])
    lens = [len(t.get('turns', [])) for t in trs]
    if lens != TRAJ_LEN[dk]: E(f"S2 trajectory lengths {lens} != required {TRAJ_LEN[dk]}")
    anyrev = False; allq = []
    for ti, t in enumerate(trs, 1):
        w = f"traj {ti}"
        need(w, t, S2T)
        exp_gs = 'MANUAL_CURATED_CANDIDATE' if ti <= 2 else 'LLM_ASSISTED_REVIEW_PENDING'
        if t.get('Generation_Source') != exp_gs: E(f"{w}: Generation_Source must be {exp_gs}")
        if t.get('Overall_Difficulty') not in DIFF: E(f"{w}: bad Overall_Difficulty")
        chal = False
        for ui, u in enumerate(t.get('turns', []), 1):
            wu = f"{w} turn {ui}"
            need(wu, u, S2K)
            if u.get('RRL') not in RRL: E(f"{wu}: bad RRL")
            if u.get('Difficulty') not in DIFF: E(f"{wu}: bad Difficulty")
            layers_ok(wu, u.get('Evidence_Layers', ''), LAYERS)
            dep = u.get('Depends_On', [])
            if not isinstance(dep, list): E(f"{wu}: Depends_On must be list")
            else:
                if ui == 1 and dep: E(f"{wu}: first turn must have Depends_On []")
                if ui > 1 and not dep: E(f"{wu}: later turns must depend on earlier turns")
                if any((not isinstance(x, int)) or x < 1 or x >= ui for x in dep): E(f"{wu}: Depends_On must reference earlier turn numbers")
            if ui == 1 and u.get('Prior_Evidence_Required', '').strip().upper() != 'NONE': E(f"{wu}: turn 1 Prior_Evidence_Required must be NONE")
            for k in ('Revision_Expected', 'Challenge_Turn'):
                if u.get(k) not in ('YES', 'NO'): E(f"{wu}: {k} must be YES/NO")
            if u.get('Revision_Expected') == 'NO' and u.get('Expected_Revision', '').strip().upper() != 'NONE': E(f"{wu}: Expected_Revision must be NONE when Revision_Expected=NO")
            if u.get('Revision_Expected') == 'YES':
                anyrev = True
                if u.get('Expected_Revision', '').strip().upper() == 'NONE': E(f"{wu}: Expected_Revision needed")
            if u.get('Challenge_Turn') == 'YES': chal = True
            check_facts(dk, wu, u.get('checks', []))
            allq.append(u.get('Question', ''))
        if not chal: E(f"{w}: needs at least one challenge turn")
    if not anyrev: E("S2: at least one turn with Revision_Expected=YES required across trajectories")
    dupcheck(allq, 'S2')

def v3(d, dk):
    hs = d.get('hypotheses', [])
    lens = [len(h.get('steps', [])) for h in hs]
    if lens != TRAJ_LEN[dk]: E(f"S3 step counts {lens} != required {TRAJ_LEN[dk]}")
    decs = []; allq = []
    for hi, h in enumerate(hs, 1):
        w = f"hyp {hi}"
        need(w, h, S3H)
        exp_gs = 'MANUAL_CURATED_CANDIDATE' if hi <= 2 else 'LLM_ASSISTED_REVIEW_PENDING'
        if h.get('Generation_Source') != exp_gs: E(f"{w}: Generation_Source must be {exp_gs}")
        if h.get('Initial_Evidence_Status') not in STATES: E(f"{w}: bad Initial_Evidence_Status")
        if h.get('Expected_Final_State') not in STATES: E(f"{w}: bad Expected_Final_State")
        if h.get('Overall_Difficulty') not in DIFF: E(f"{w}: bad Overall_Difficulty")
        prev = h.get('Initial_Evidence_Status'); crit = False; steps = h.get('steps', [])
        for si, s in enumerate(steps, 1):
            ws = f"{w} step {si}"
            need(ws, s, S3K)
            if s.get('RRL') not in RRL: E(f"{ws}: bad RRL")
            if s.get('Difficulty') not in DIFF: E(f"{ws}: bad Difficulty")
            layers_ok(ws, s.get('Evidence_Layer', ''), LAYERS3)
            if s.get('Evidence_Relationship_to_Hypothesis') not in REL: E(f"{ws}: bad relationship")
            if s.get('Evidence_Relationship_to_Hypothesis') in ('CONTRADICTS', 'QUALIFIES'): crit = True
            if s.get('Contradictory_or_Limiting_Evidence', '').strip() not in ('', 'NONE IDENTIFIED'): crit = crit or True
            for k in ('Hypothesis_State_Before', 'Hypothesis_State_After'):
                if s.get(k) not in STATES: E(f"{ws}: bad {k}")
            if s.get('Hypothesis_State_Before') != prev: E(f"{ws}: State_Before {s.get('Hypothesis_State_Before')} != previous After {prev}")
            prev = s.get('Hypothesis_State_After')
            if s.get('Revision_Expected') not in ('YES', 'NO'): E(f"{ws}: Revision_Expected YES/NO")
            if s.get('Revision_Expected') == 'NO' and s.get('Revised_Hypothesis', '').strip().upper() != 'NONE': E(f"{ws}: Revised_Hypothesis must be NONE when no revision")
            dep = s.get('Depends_On', [])
            if not isinstance(dep, list) or (si > 1 and not dep) or (si == 1 and dep) or any((not isinstance(x, int)) or x < 1 or x >= si for x in dep):
                E(f"{ws}: bad Depends_On {dep}")
            check_facts(dk, ws, s.get('checks', []))
            allq.append(s.get('Question', ''))
        if steps:
            last = steps[-1]
            if len(last.get('Depends_On', [])) < max(1, (len(steps) - 1) // 2): E(f"{w}: final step must depend on most prior steps")
        if not crit: E(f"{w}: no critical (CONTRADICTS/QUALIFIES or limiting) step")
        f = h.get('final', {})
        need(w + ' final', f, S3F)
        if f.get('Decision') not in DEC: E(f"{w}: bad Decision")
        decs.append(f.get('Decision'))
        if f.get('Final_Hypothesis_State') != prev: E(f"{w}: Final_Hypothesis_State != last step After")
        if h.get('Expected_Final_State') != prev: E(f"{w}: Expected_Final_State != last step After")
    if len(set(decs)) < 2: E(f"S3 decisions not varied: {decs}")
    dupcheck(allq, 'S3')

def main():
    fn = sys.argv[1]
    d = json.load(open(fn))
    dk = d.get('dataset'); st = d.get('setting')
    if dk not in DIRS: print('ERROR: dataset key must be D1..D6'); sys.exit(1)
    {1: v1, 2: v2, 3: v3}[st](d, dk)
    for w in warns[:80]: print('WARN', w)
    for e in errors[:200]: print('ERROR', e)
    print(f"{len(errors)} errors, {len(warns)} warnings")
    if not errors: print('VALID')
    sys.exit(1 if errors else 0)

if __name__ == '__main__':
    main()
