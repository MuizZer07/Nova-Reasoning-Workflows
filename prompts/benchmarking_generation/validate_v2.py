#!/usr/bin/env python3
"""Nova v2 validator. Usage: python3 validate_v2.py <items_v2/DK_Sn.json>
Runs all v1 checks plus v2 rules (banned naive questions, reasoning-category tags, diversity caps,
cross-setting duplicate checks within the same dataset)."""
import json, sys, re, os, difflib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validate_items as V

CATS = ['DEG_PROGRAM', 'PATHWAY_IDENTIFICATION', 'PATHWAY_DIRECTIONALITY', 'GO_PROCESS', 'UPSTREAM_REGULATOR', 'MIRNA_REGULATION',
        'CHEMICAL_CONNECTIVITY', 'CELL_COMPOSITION', 'DISEASE_PHENOTYPE', 'CROSS_LAYER_CONSISTENCY', 'MECHANISTIC_CHAIN',
        'FEEDBACK_COUNTERREGULATION', 'PUBLICATION_CONCORDANCE', 'ALTERNATIVE_MECHANISM', 'PERTURBATION_PREDICTION',
        'EVIDENCE_CALIBRATION', 'TRANSCRIPTIONAL_VS_POSTTRANSCRIPTIONAL']
BANNED = [
    (r'\bthreshold', 'asks about thresholds'), (r'\bcut-?off', 'asks about cut-offs'),
    (r'\blog ?2? ?fc\b|\blogfc\b|log2?\s*fold[- ]change\s+(value|of)', 'asks for a logFC value'),
    (r'\bp-?values?\b|\badj(usted)?[ .]?p\b|\badjpv\b|\bq-?values?\b|\bfdr\b|\bbonferroni\b|\bz-?scores?\b', 'asks about p/FDR/z statistics'),
    (r'\bhow many\b|\bnumber of\b|\bcount of\b|\bwhat fraction\b|\bwhat proportion\b|\bpercentage\b', 'asks for a count'),
    (r'\bwhich (contrast|comparison)\b|\bwhat (contrast|comparison)\b|\bcontrast identity\b|\bwhich (cell system|model system) was\b', 'asks to identify the contrast'),
    (r'\bmetadata\b|experiment_info|\.tsv\b|\bcolumn\b|\bplaceholder\b|\bcapped\b|\bfile\b', 'asks about files/metadata'),
    (r'^(what|which|how)\b[^?]*\b(platform|microarray|sequencing depth|replicates?|sample size|time ?points?|dose|concentration)\b', 'asks about study design'),
]
errs, warns = [], []

def tag_checks(where, o):
    c = o.get('Reasoning_Category'); e = o.get('Primary_Entity')
    if c not in CATS: errs.append(f'{where}: Reasoning_Category must be one of CATS (got {c})')
    if not isinstance(e, str) or not e.strip(): errs.append(f'{where}: Primary_Entity missing')
    q = o.get('Question', '')
    for pat, why in BANNED:
        if re.search(pat, q, re.I): errs.append(f'{where}: BANNED naive question pattern ({why}): "{q[:110]}"')
    return c, (e or '').strip().lower()

def norm(q): return re.sub(r'\W+', ' ', q.lower()).strip()

def questions(d, s):
    if s == 1: return [(f'S1 item {i}', it) for i, it in enumerate(d['items'], 1)]
    if s == 2: return [(f'S2 traj {t} turn {u}', x) for t, tr in enumerate(d['trajectories'], 1) for u, x in enumerate(tr['turns'], 1)]
    return [(f'S3 hyp {h} step {u}', x) for h, hy in enumerate(d['hypotheses'], 1) for u, x in enumerate(hy['steps'], 1)]

def main():
    fn = sys.argv[1]; d = json.load(open(fn)); dk, st = d['dataset'], d['setting']
    # base v1 rules
    {1: V.v1, 2: V.v2, 3: V.v3}[st](d, dk)
    errs.extend(V.errors); warns.extend(V.warns)
    qs = questions(d, st)
    cats = collections.Counter(); combos = collections.Counter()
    for w, o in qs:
        c, e = tag_checks(w, o); cats[c] += 1; combos[(c, e)] += 1
    if st == 1:
        for (c, e), n in combos.items():
            if n > 1: errs.append(f'S1: {n} items share the same Reasoning_Category+Primary_Entity ({c}, {e}) -> same question type repeated')
        if len([c for c in cats if c in CATS]) < 14: errs.append(f'S1: only {len(cats)} reasoning categories used; need >= 14 of {len(CATS)}')
        for c, n in cats.items():
            if n > 8: errs.append(f'S1: category {c} used {n} times (max 8)')
        # R0 must be named-entity retrieval
        for i, it in enumerate(d['items'], 1):
            if it['RRL'] == 'R0' and it.get('Reasoning_Category') not in ('PATHWAY_IDENTIFICATION', 'UPSTREAM_REGULATOR', 'MIRNA_REGULATION', 'GO_PROCESS', 'DEG_PROGRAM', 'DISEASE_PHENOTYPE', 'CELL_COMPOSITION', 'CHEMICAL_CONNECTIVITY'):
                errs.append(f'S1 item {i}: R0 items must retrieve a named biological entity (pathway/regulator/miRNA/GO/gene program/disease/cell type)')
            if it['Question_Type'] == 'TRUE_FALSE' and re.search(r'\bis (significantly )?(differentially expressed|up-?regulated|down-?regulated|DE)\b', it['Question'], re.I) and it['RRL'] in ('R0', 'R1'):
                errs.append(f'S1 item {i}: naive single-gene DE-status TRUE/FALSE question')
    else:
        units = d['trajectories'] if st == 2 else d['hypotheses']
        key = 'turns' if st == 2 else 'steps'
        for i, u in enumerate(units, 1):
            k = len(set(x.get('Reasoning_Category') for x in u[key]))
            if k < 4: errs.append(f'S{st} unit {i}: only {k} distinct reasoning categories (need >= 4)')
        if len(cats) < 12: errs.append(f'S{st}: only {len(cats)} categories across dataset (need >= 12)')
    # cross-setting duplicates within dataset
    base = os.path.dirname(os.path.abspath(fn)); allq = [(f'S{st}:{w}', norm(o['Question'])) for w, o in qs]
    for s2 in (1, 2, 3):
        if s2 == st: continue
        p = f'{base}/{dk}_S{s2}.json'
        if os.path.exists(p):
            allq += [(f'S{s2}:{w}', norm(o['Question'])) for w, o in questions(json.load(open(p)), s2)]
    own = [x for x in allq if x[0].startswith(f'S{st}:')]
    for a, x in own:
        for b, y in allq:
            if a >= b and b.startswith(f'S{st}:'): continue
            if a == b or abs(len(x) - len(y)) > 0.35 * max(len(x), len(y)): continue
            sm = difflib.SequenceMatcher(None, x, y)
            if sm.quick_ratio() > 0.8 and sm.ratio() > 0.75: errs.append(f'near-duplicate ({sm.ratio():.2f}): {a} ~ {b}')
    for w in warns[:60]: print('WARN', w)
    for e in errs[:250]: print('ERROR', e)
    print(f'{len(errs)} errors, {len(warns)} warnings'); print('VALID' if not errs else 'INVALID')
    sys.exit(1 if errs else 0)

if __name__ == '__main__':
    main()
