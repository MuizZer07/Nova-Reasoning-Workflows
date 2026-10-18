#!/usr/bin/env python3
"""Robustness analysis for the 15% subset runs (R1-R4).

Reads data/results/robustness_subset/D*/15%_<model>_<wording>.xlsx, where
<model> is GLM or Haiku and <wording> is original or rephrased, and writes

  numbers/robust_macros.tex     \\newcommand macros (prefix \\Rob...) for the text
  numbers/tab_robust_runs.tex   mean credit by workflow and run
  figures/fig_robust.pdf           credit by run, and paired rephrasing/model effects

Metric definitions and timeout handling are shared with nova_results.py.

Usage (from the paper directory):  python scripts/robustness_results.py
"""
import glob
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)  # repository root; scripts live in <repo>/scripts
sys.path.insert(0, HERE)
import nova_results as nr  # noqa: E402

SAMPLE_DIR = os.path.join(PAPER, "data", "results", "robustness_subset")
RUNS = [("R1", "glm", "original"), ("R2", "glm", "rephrased"),
        ("R3", "haiku", "original"), ("R4", "haiku", "rephrased")]
RUN_LABEL = {"R1": "R1: GLM-5.2, original", "R2": "R2: GLM-5.2, rephrased",
             "R3": "R3: Haiku 4.5, original", "R4": "R4: Haiku 4.5, rephrased"}
N_BOOT = 2000
RNG = np.random.default_rng(20261006)


def load_runs():
    files = {}
    for f in glob.glob(os.path.join(SAMPLE_DIR, "D*", "*.xlsx")):
        m = re.search(r"15%_(glm|haiku)_(original|rephrased)\.xlsx$", os.path.basename(f), re.I)
        if m:
            files.setdefault((m.group(1).lower(), m.group(2).lower()), []).append(f)
    out = {}
    for run, model, wording in RUNS:
        fs = sorted(files.get((model, wording), []))
        if not fs:
            sys.exit(f"missing files for {model} {wording}")
        s1, s2, s3, info = nr.load(fs)
        steps = s3[s3.Is_Final != 1]
        items = pd.concat([s1.assign(Setting="S1"), s2.assign(Setting="S2"), s3.assign(Setting="S3")],
                          ignore_index=True)
        out[run] = dict(s1=s1, s2=s2, s3=s3, items=items, info=info, files=fs)
    return out


def paired(R, a, b, completed_only=False):
    """Item-level pairs between runs a and b (same items and workflows)."""
    cols = ["Dataset_ID", "Item", "Workflow", "Cluster", "Setting", "Credit", "Timeout", "RRL"]
    x = R[a]["items"][cols]
    y = R[b]["items"][cols]
    m = x.merge(y, on=["Dataset_ID", "Item", "Workflow"], suffixes=("_a", "_b"))
    if completed_only:
        m = m[(m.Timeout_a == 0) & (m.Timeout_b == 0)]
    return m


def boot_diff(m):
    """Mean (b - a) credit difference with a cluster bootstrap CI.

    Clusters are questions, conversations, or hypotheses (each dataset has only
    one conversation and one hypothesis in the subset), resampled within setting.
    """
    d = (m.Credit_b - m.Credit_a).to_numpy()
    keys = list(zip(m.Setting_a, m.Dataset_ID, m.Cluster_a))
    uniq = list(dict.fromkeys(keys))
    idx = {k: i for i, k in enumerate(uniq)}
    code = np.array([idx[k] for k in keys])
    sums = np.bincount(code, weights=d, minlength=len(uniq))
    cnts = np.bincount(code, minlength=len(uniq))
    st = np.array([k[0] for k in uniq])
    strata = [np.where(st == v)[0] for v in pd.unique(st)]
    ds_c = np.array([k[1] for k in uniq])
    dsets = pd.unique(ds_c)

    def mac_mean(i):                     # macro mean over datasets of the (resampled) difference
        vals = [sums[i][ds_c[i] == d_].sum() / max(cnts[i][ds_c[i] == d_].sum(), 1) for d_ in dsets
                if (ds_c[i] == d_).any()]
        return np.mean(vals)
    reps = []
    for _ in range(N_BOOT):
        i = np.concatenate([RNG.choice(s, size=len(s), replace=True) for s in strata])
        reps.append(mac_mean(i))
    try:
        p = stats.wilcoxon(m.Credit_b, m.Credit_a).pvalue if np.any(d != 0) else 1.0
    except ValueError:
        p = 1.0
    return 100 * mac_mean(np.arange(len(uniq))), 100 * np.percentile(reps, 2.5), 100 * np.percentile(reps, 97.5), p, len(m)


def weighted_kappa(a, b, levels=(0.0, 0.5, 1.0)):
    """Quadratic-weighted Cohen's kappa for ordinal credit."""
    k = len(levels)
    pos = {v: i for i, v in enumerate(levels)}
    O = np.zeros((k, k))
    for x, y in zip(a, b):
        O[pos[x], pos[y]] += 1
    W = np.array([[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)])
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / (W * E).sum()


def run_ci(items):
    """Mean credit with cluster bootstrap CI, pooled over workflows."""
    g = items.groupby(["Setting", "Dataset_ID", "Cluster"]).Credit.agg(["sum", "count"]).reset_index()
    strata = [np.where(g.Setting.to_numpy() == v)[0] for v in g.Setting.unique()]
    s, n = g["sum"].to_numpy(), g["count"].to_numpy()
    reps = []
    for _ in range(N_BOOT):
        i = np.concatenate([RNG.choice(st, size=len(st), replace=True) for st in strata])
        reps.append(s[i].sum() / n[i].sum())
    return nr.macro1(items, "Credit"), 100 * np.percentile(reps, 2.5), 100 * np.percentile(reps, 97.5)


def figure_effects():
    """Paired wording and model effects for the RQ4 figure of the RECOMB paper (judge_comparison.py),
    reproducing main()'s bootstrap stream so the intervals match the robustness macros exactly."""
    R = load_runs()
    for run, _, _ in RUNS:
        run_ci(R[run]["items"])                       # same RNG draws as in main()
    eff = {}
    for name, a, b in [("RephGLM", "R1", "R2"), ("RephHaiku", "R3", "R4"),
                       ("ModelOrig", "R1", "R3"), ("ModelReph", "R2", "R4")]:
        for comp in (False, True):
            r = boot_diff(paired(R, a, b, completed_only=comp))
            if not comp:
                eff[name] = r
    return eff


def main():
    R = load_runs()
    gen = nr.numbers_dir()
    img = os.path.join(PAPER, "figures")
    L = ["% Auto-generated by scripts/robustness_results.py -- do not edit by hand."]

    def mac(name, val):
        v = str(val)
        if len(v) > 1 and v[0] in "+-" and (v[1].isdigit() or v[1] == "."):
            v = v.replace("-", "$-$", 1)
        L.append(f"\\newcommand{{\\{name}}}{{{v}}}")

    f1, fp = nr.f1, nr.fp_tex
    sgn = lambda x: f"{x:+.1f}"  # noqa: E731
    base = R["R1"]
    per_wf = len(base["items"]) // 4
    mac("RobNItems", per_wf)
    mac("RobNSOne", len(base["s1"]) // 4)
    mac("RobNSTwo", len(base["s2"]) // 4)
    mac("RobNSThree", len(base["items"][base["items"].Setting == "S3"]) // 4)
    mac("RobNTraj", base["s2"].drop_duplicates(["Dataset_ID", "Trajectory_ID"]).shape[0])
    mac("RobNHyp", base["s3"].drop_duplicates(["Dataset_ID", "Hypothesis_ID"]).shape[0])
    mac("RobNDatasets", base["info"].Dataset_ID.nunique())
    mac("RobNAnswers", f"{sum(len(R[r]['s1']) + len(R[r]['s2']) + len(R[r]['s3']) for r in R):,}".replace(",", "{,}"))
    mac("RobPctOfBenchmark", f"{100 * per_wf / 1000:.0f}")
    judges = sorted({str(j) for r in R for j in R[r]["info"].get("Judge_Model", pd.Series(dtype=str)).dropna()})
    mac("RobJudge", ", ".join(judges).replace("_", "\\_") or "--")
    rph = sorted({str(j) for r in ("R2", "R4") for j in R[r]["info"].get("Rephrase_Model", pd.Series(dtype=str)).dropna()})
    mac("RobRephraseModel", ", ".join(x.split("/")[-1] for x in rph).replace("_", "\\_") or "--")

    # ---- per-run results
    M, CI, TO = {}, {}, {}
    for run, _, _ in RUNS:
        r = R[run]
        M[run] = nr.setting_metrics(r["s1"], r["s2"], r["s3"])
        CI[run] = run_ci(r["items"])
        allr = pd.concat([r["s1"], r["s2"], r["s3"]])
        TO[run] = (int(allr.Timeout.sum()), 100 * allr.Timeout.mean())
        tag = {"R1": "ROne", "R2": "RTwo", "R3": "RThree", "R4": "RFour"}[run]
        mac(f"Rob{tag}Credit", f1(CI[run][0]))
        mac(f"Rob{tag}Lo", f1(CI[run][1]))
        mac(f"Rob{tag}Hi", f1(CI[run][2]))
        wf_credit = nr.macro(r["items"], "Credit").reindex(nr.WF_ORDER)
        for wf in nr.WF_ORDER:
            mac(f"Rob{tag}{nr.WF_MACRO[wf]}", f1(wf_credit[wf]))
        mac(f"Rob{tag}Best", nr.WF_LABEL[wf_credit.idxmax()])
        mac(f"Rob{tag}Spread", f1(wf_credit.max() - wf_credit.min()))
        w = nr.wide(r["items"], "Credit")
        chi, p = nr.friedman(w)
        mac(f"Rob{tag}FriedP", fp(p))
        mac(f"Rob{tag}SOne", f1(M[run].S1_Acc.mean()))
        mac(f"Rob{tag}STwo", f1(M[run].S2_Acc.mean()))
        mac(f"Rob{tag}SThreeStep", f1(M[run].S3_Step.mean()))
        mac(f"Rob{tag}Decl", f1(M[run].S3_Decl.mean()))
        mac(f"Rob{tag}Latency", f1(allr.Response_Time_s.median()))
        mac(f"Rob{tag}Tokens", f"{allr.Total_Tokens.mean() / 1000:.0f}k")
        cost = pd.to_numeric(allr.get("Est_Cost_USD"), errors="coerce")
        mac(f"Rob{tag}Cost", f"{cost.mean():.3f}" if cost.notna().any() and cost.sum() > 0 else "--")

    spreads = [nr.macro(R[r]["items"], "Credit") for r in R]
    spreads = [x.max() - x.min() for x in spreads]
    mac("RobMinSpread", f1(min(spreads)))
    mac("RobMaxSpread", f1(max(spreads)))

    # ---- paired effects
    effects = {}
    for name, a, b in [("RephGLM", "R1", "R2"), ("RephHaiku", "R3", "R4"),
                       ("ModelOrig", "R1", "R3"), ("ModelReph", "R2", "R4")]:
        for comp, tag in ((False, ""), (True, "Done")):
            m = paired(R, a, b, completed_only=comp)
            diff, lo, hi, p, n = boot_diff(m)
            effects[name + tag] = (diff, lo, hi, p, n)
            mac(f"Rob{name}{tag}Diff", sgn(diff))
            mac(f"Rob{name}{tag}Lo", sgn(lo))
            mac(f"Rob{name}{tag}Hi", sgn(hi))
            mac(f"Rob{name}{tag}P", fp(p))
            mac(f"Rob{name}{tag}N", n)
            if not comp:
                mac(f"Rob{name}Same", f1(nr.macro1(m.assign(sm=(m.Credit_a == m.Credit_b).astype(float)), "sm")))
                mac(f"Rob{name}Kappa", f"{weighted_kappa(m.Credit_a, m.Credit_b):.2f}")
                mac(f"Rob{name}MaxAbs", f1(max(abs(lo), abs(hi))))
    # rephrasing effect per setting
    for name, a, b in [("RephGLM", "R1", "R2"), ("RephHaiku", "R3", "R4")]:
        m = paired(R, a, b)
        for st, key in (("S1", "SOne"), ("S2", "STwo"), ("S3", "SThree")):
            d, lo, hi, p, n = boot_diff(m[m.Setting_a == st])
            mac(f"Rob{name}{key}Diff", sgn(d))
            mac(f"Rob{name}{key}Lo", sgn(lo))
            mac(f"Rob{name}{key}Hi", sgn(hi))
    # rephrasing effect per workflow (for the figure)
    wf_eff = {}
    for name, a, b in [("RephGLM", "R1", "R2"), ("RephHaiku", "R3", "R4")]:
        m = paired(R, a, b, completed_only=True)
        wf_eff[name] = (nr.macro(m.assign(d=m.Credit_b - m.Credit_a), "d")
                        .reindex(nr.WF_ORDER))

    # ---- completed-by-both model comparison by workflow
    m = paired(R, "R1", "R3", completed_only=True)
    byw = pd.DataFrame({c: nr.macro(m, c) for c in ("Credit_a", "Credit_b")}).reindex(nr.WF_ORDER)
    for wf in nr.WF_ORDER:
        mac(f"RobDoneGLM{nr.WF_MACRO[wf]}", f1(byw.loc[wf, "Credit_a"]))
        mac(f"RobDoneHaiku{nr.WF_MACRO[wf]}", f1(byw.loc[wf, "Credit_b"]))
    mac("RobDoneGLM", f1(nr.macro1(m, "Credit_a")))
    mac("RobDoneHaiku", f1(nr.macro1(m, "Credit_b")))

    # ---- hypothesis decisions per model (both wordings)
    for model, runs in (("GLM", ("R1", "R2")), ("Haiku", ("R3", "R4"))):
        fin = pd.concat([R[r]["s3"][R[r]["s3"].Is_Final == 1].assign(Run=r) for r in runs])
        n = len(fin)
        mac(f"Rob{model}NDec", n)
        mac(f"Rob{model}DecAcc", f1(nr.macro1(fin, "Decision_Match")))
        pred = fin.Extracted_Decision.fillna("NONE")
        over = ((pred == "REJECT") & (fin.Expected_Decision != "REJECT")).sum()
        mac(f"Rob{model}NOverReject", int(over))
        mac(f"Rob{model}NPredReject", int((pred == "REJECT").sum()))
        mac(f"Rob{model}NRefReject", int((fin.Expected_Decision == "REJECT").sum()))
        mac(f"Rob{model}NPredInsuff", int((pred == "INSUFFICIENT_EVIDENCE").sum()))
        mac(f"Rob{model}NNone", int((pred == "NONE").sum()))
        mac(f"Rob{model}Cal", f1(nr.macro1(fin, "Calibration_OK")))
        a = R[runs[0]]["s3"]
        b = R[runs[1]]["s3"]
        fa = a[a.Is_Final == 1][["Dataset_ID", "Hypothesis_ID", "Workflow", "Extracted_Decision"]]
        fb = b[b.Is_Final == 1][["Dataset_ID", "Hypothesis_ID", "Workflow", "Extracted_Decision"]]
        mm = fa.merge(fb, on=["Dataset_ID", "Hypothesis_ID", "Workflow"])
        same = (mm.Extracted_Decision_x.fillna("NONE") == mm.Extracted_Decision_y.fillna("NONE")).mean()
        mac(f"Rob{model}DecStable", f1(100 * same))
        mac(f"Rob{model}NDecPairs", len(mm))

    # ---- low vs high reasoning level spread per model (original wording)
    for model, run in (("GLM", "R1"), ("Haiku", "R3")):
        it = R[run]["items"]
        it = it[it.Timeout == 0]
        lo = nr.macro(it[it.RRL.isin(["R0", "R1"])], "Credit")
        hi = nr.macro(it[it.RRL.isin(["R3", "R4"])], "Credit")
        mac(f"Rob{model}SpreadLow", f1(lo.max() - lo.min()))
        mac(f"Rob{model}SpreadHigh", f1(hi.max() - hi.min()))
        mac(f"Rob{model}HighMin", f1(hi.min()))
        mac(f"Rob{model}HighMax", f1(hi.max()))


    # ---- patterns: where do workflows differ? (both wordings pooled per model)
    SH = {"Nova Instant": "Inst.", "Nova Thinking": "Think.", "Nova Deep Thinking": "Deep",
          "Nova Auto": "Auto"}
    MODELS = (("GLM", ("R1", "R2")), ("Haiku", ("R3", "R4")))

    def pool(runs, part):
        return pd.concat([R[r][part].assign(Item=R[r][part]["Item"] + "|" + r) for r in runs])

    def nlayers(v):
        n = str(v).count(";") + 1
        return "3+ layers" if n >= 3 else ("2 layers" if n == 2 else "1 layer")

    def grp(part, col, fn=None):
        def f(runs):
            d = pool(runs, part)
            if fn is not None:
                d = d.assign(**{col: fn(d)})
            return d
        return f, col

    closed = {"MCQ": "Closed-form", "TRUE_FALSE": "Closed-form"}
    patterns_spec = [
        ("By setting", None),
        ("Single-turn questions", (grp("items", "Setting"), "S1")),
        ("Conversation turns", (grp("items", "Setting"), "S2")),
        ("Hypothesis steps", (grp("items", "Setting"), "S3")),
        ("Single-turn, by question form", None),
        ("Closed-form (MCQ, true/false)", (grp("s1", "Form", lambda d: d.Question_Type.map(closed).fillna(d.Question_Type)), "Closed-form")),
        ("Evidence integration", (grp("s1", "Form", lambda d: d.Question_Type.map(closed).fillna(d.Question_Type)), "EVIDENCE_INTEGRATION")),
        ("Short answer", (grp("s1", "Form", lambda d: d.Question_Type.map(closed).fillna(d.Question_Type)), "SHORT_ANSWER")),
        ("Mechanistic interpretation", (grp("s1", "Form", lambda d: d.Question_Type.map(closed).fillna(d.Question_Type)), "MECHANISTIC_INTERPRETATION")),
        ("Single-turn, by evidence breadth", None),
        ("One evidence layer", (grp("s1", "Layers", lambda d: d.Evidence_Layers.map(nlayers)), "1 layer")),
        ("Two layers", (grp("s1", "Layers", lambda d: d.Evidence_Layers.map(nlayers)), "2 layers")),
        ("Three or more layers", (grp("s1", "Layers", lambda d: d.Evidence_Layers.map(nlayers)), "3+ layers")),
        ("Conversation, by turn type", None),
        ("Standard turns", (grp("s2", "TT", lambda d: np.where(d.Challenge_Turn == 1, "challenge", "standard")), "standard")),
        ("Challenge turns", (grp("s2", "TT", lambda d: np.where(d.Challenge_Turn == 1, "challenge", "standard")), "challenge")),
    ]
    P = [r"\setlength{\tabcolsep}{5pt}",
         r"\begin{tabular}{@{}lr@{\hspace{12pt}}rl@{\hspace{12pt}}rl@{}}", r"\toprule",
         r"& & \multicolumn{2}{c}{\textbf{GLM-5.2}} & \multicolumn{2}{c}{\textbf{Haiku 4.5}} \\",
         r"\cmidrule(lr){3-4}\cmidrule(l){5-6}",
         r"\textbf{Items} & \textbf{$n$} & \textbf{Gap} & \textbf{Best / worst} & \textbf{Gap} & \textbf{Best / worst} \\",
         r"\midrule"]
    pat_vals = {}
    for label, spec in patterns_spec:
        if spec is None:
            P.append(r"\multicolumn{6}{@{}l}{\textit{" + label + r"}} \\")
            continue
        (fn, col), val = spec
        cells, n_items = [], None
        for model, runs in MODELS:
            d = fn(runs)
            d = d[d[col] == val]
            means = nr.macro(d, "Credit").reindex(nr.WF_ORDER)
            n_items = len(d[d.Workflow == "Nova Instant"]) // len(runs)
            gap = means.max() - means.min()
            pat_vals[(label, model)] = (gap, means)
            cells.append(f"{f1(gap)} & {SH[means.idxmax()]} {f1(means.max())} / {SH[means.idxmin()]} {f1(means.min())}")
        P.append(r"\quad " + label + f" & {n_items} & " + " & ".join(cells) + r" \\")
    P += [r"\bottomrule", r"\end{tabular}"]
    with open(os.path.join(gen, "tab_robust_patterns.tex"), "w") as fh:
        fh.write("% Auto-generated by scripts/robustness_results.py\n" + "\n".join(P) + "\n")

    def pv(label, model, wf=None):
        gap, means = pat_vals[(label, model)]
        return gap if wf is None else means[wf]
    for lab, key in (("Single-turn questions", "SOne"), ("Conversation turns", "STwo"), ("Hypothesis steps", "SThree"),
                     ("Closed-form (MCQ, true/false)", "Closed"), ("Mechanistic interpretation", "Mech"),
                     ("Three or more layers", "Three"), ("One evidence layer", "OneLayer"),
                     ("Challenge turns", "Chal"), ("Short answer", "Short"), ("Evidence integration", "Integ")):
        for model, _ in MODELS:
            mac(f"RobGap{key}{model}", f1(pv(lab, model)))
            for wf in nr.WF_ORDER:
                mac(f"RobPat{key}{model}{nr.WF_MACRO[wf]}", f1(pv(lab, model, wf)))
    # omnibus test per setting and model (both wordings pooled)
    for model, runs in MODELS:
        it = pool(runs, "items")
        for st, key in (("S1", "SOne"), ("S2", "STwo"), ("S3", "SThree")):
            chi, p = nr.friedman(nr.wide(it[it.Setting == st], "Credit"))
            mac(f"RobFried{key}{model}", fp(p))
    # evidence-relation accuracy in hypothesis steps, all models and workflows
    st_all = pd.concat([R[r]["s3"][R[r]["s3"].Is_Final != 1] for r in R])
    rel = nr.macro(st_all, "Relationship_Match", ["Expected_Relationship", "Workflow"])
    for relname, key in (("CONTRADICTS", "Contra"), ("QUALIFIES", "Qual"), ("NEUTRAL", "Neutral"), ("SUPPORTS", "Supp")):
        v = rel.loc[relname]
        mac(f"RobRel{key}Min", f"{v.min():.0f}")
        mac(f"RobRel{key}Max", f"{v.max():.0f}")
    # latency by model (median per answer, original wording)
    for model, run in (("GLM", "R1"), ("Haiku", "R3")):
        a_ = pd.concat([R[run]["s1"], R[run]["s2"], R[run]["s3"]])
        mac(f"RobLat{model}", f"{a_.Response_Time_s.median():.0f}")


    # ---- claim 1: cost and credit by workflow (both wordings pooled)
    import warnings
    warnings.filterwarnings("ignore")
    import statsmodels.formula.api as smf
    for model, runs in MODELS:
        a_ = pd.concat([pd.concat([R[r]["s1"], R[r]["s2"], R[r]["s3"]]) for r in runs])
        tok = a_.groupby("Workflow").Total_Tokens.mean()
        calls = a_.groupby("Workflow").Tool_Call_Count.mean()
        cred = nr.macro(pool(runs, "items"), "Credit")
        for wf in nr.WF_ORDER:
            mac(f"RobCred{model}{nr.WF_MACRO[wf]}", f1(cred[wf]))
        mac(f"RobTokRatio{model}", f"{tok['Nova Deep Thinking'] / tok['Nova Instant']:.1f}")
        mac(f"RobCallRatio{model}", f"{calls['Nova Deep Thinking'] / calls['Nova Instant']:.1f}")
        mac(f"RobTokRatioDeepThink{model}", f"{tok['Nova Deep Thinking'] / tok['Nova Thinking']:.1f}")
    # ---- claim 2: workflow x task interaction and task-matched policy
    for model, runs in MODELS:
        it = pool(runs, "items")
        form = pool(runs, "s1").set_index("Item").Question_Type.to_dict()
        it["Task"] = np.where(it.Setting == "S1",
                              it.Item.map(form).replace({"MCQ": "Closed", "TRUE_FALSE": "Closed"}), it.Setting)
        it["grp"] = it.Dataset_ID + "|" + it.Item
        for task, key in (("Setting", "Setting"), ("Task", "Task")):
            f0 = smf.mixedlm(f"Credit ~ C(Workflow) + C({task})", it, groups=it.grp).fit(reml=False)
            f1_ = smf.mixedlm(f"Credit ~ C(Workflow) * C({task})", it, groups=it.grp).fit(reml=False)
            lr = 2 * (f1_.llf - f0.llf)
            dfd = len(f1_.params) - len(f0.params)
            mac(f"RobInter{key}{model}P", fp(stats.chi2.sf(lr, dfd)))
            mac(f"RobInter{key}{model}Chi", f"{lr:.1f}")
            mac(f"RobInter{key}{model}Df", dfd)
        tab_ = nr.macro(it, "Credit", ["Task", "Workflow"], scale=1.0).unstack()
        n_ = it[it.Workflow == "Nova Instant"].groupby("Task").size()
        always = {wf: 100 * (tab_[wf] * n_).sum() / n_.sum() for wf in nr.WF_ORDER}
        matched = 100 * (tab_.max(1) * n_).sum() / n_.sum()
        mac(f"RobMatched{model}", f1(matched))
        mac(f"RobAlwaysDeep{model}", f1(always["Nova Deep Thinking"]))
        mac(f"RobBestFixed{model}", f1(max(always.values())))
        mac(f"RobBestFixedWF{model}", nr.WF_LABEL[max(always, key=always.get)])
        mac(f"RobMatchedGain{model}", f1(matched - always["Nova Deep Thinking"]))
    # ---- claim 3: does single-turn accuracy predict longitudinal metrics?
    urows = []
    for run in R:
        for ds_ in R[run]["items"].Dataset_ID.unique():
            sub = lambda d: d[d.Dataset_ID == ds_]  # noqa: E731
            Mu = nr.setting_metrics(sub(R[run]["s1"]), sub(R[run]["s2"]), sub(R[run]["s3"]))
            for wf in nr.WF_ORDER:
                urows.append({k: Mu.loc[wf, k] for k in ("S1_Acc", "S2_Acc", "S2_Cons", "S3_Rel", "S3_State", "S3_Dec", "S3_Cal")})
    U = pd.DataFrame(urows)
    rhos = []
    for c in ("S2_Acc", "S2_Cons", "S3_Rel", "S3_State", "S3_Dec", "S3_Cal"):
        d_ = U[["S1_Acc", c]].dropna()
        rhos.append(stats.spearmanr(d_.S1_Acc, d_[c])[0])
    mac("RobPredMaxRho", f"{max(abs(r_) for r_ in rhos):.2f}")
    mac("RobPredN", len(U))
    mac("RobSOneRangeLo", f"{U.S1_Acc.groupby(np.arange(len(U)) // 1).mean().quantile(0) if False else min(M[r].S1_Acc.min() for r in M):.0f}")
    mac("RobSOneRangeHi", f"{max(M[r].S1_Acc.max() for r in M):.0f}")
    mac("RobStateLo", f"{min(M[r].S3_State.min() for r in M):.0f}")
    mac("RobStateHi", f"{max(M[r].S3_State.max() for r in M):.0f}")
    mac("RobCalLo", f"{min(M[r].S3_Cal.min() for r in M):.0f}")
    mac("RobCalHi", f"{max(M[r].S3_Cal.max() for r in M):.0f}")
    # ---- claim 4: interpretation of retrieved evidence
    st_all["Model"] = np.where(st_all.Run_ID.isin(set(pd.concat([R["R1"]["s3"], R["R2"]["s3"]]).Run_ID)), "GLM", "Haiku")
    mac("RobStepTool", f1(nr.macro1(st_all, "Tool_Match")))
    okt = st_all[st_all.Tool_Match == 1]
    relok = nr.macro(okt, "Relationship_Match", "Expected_Relationship")
    for relname, key in (("CONTRADICTS", "Contra"), ("QUALIFIES", "Qual"), ("NEUTRAL", "Neutral"), ("SUPPORTS", "Supp")):
        mac(f"RobRelTool{key}", f"{relok[relname]:.0f}")
    cm = sum(pd.crosstab(g.Expected_Relationship, g.Extracted_Relationship.fillna("NONE"), normalize="index")
             for _, g in st_all.groupby("Dataset_ID")) * 100 / st_all.Dataset_ID.nunique()
    for relname, key in (("QUALIFIES", "Qual"), ("NEUTRAL", "Neutral"), ("SUPPORTS", "Supp")):
        mac(f"RobAsContra{key}", f"{cm.loc[relname, 'CONTRADICTS']:.0f}")
    wfrel = nr.macro(st_all, "Relationship_Match", ["Model", "Workflow"]).unstack()
    mac("RobRelWfRange", f1((wfrel.max(1) - wfrel.min(1)).max()))
    mac("RobStepCreditWrongRel", f1(nr.macro1(st_all[st_all.Relationship_Match == 0], "Credit")))
    mac("RobStepCreditRightRel", f1(nr.macro1(st_all[st_all.Relationship_Match == 1], "Credit")))

    with open(os.path.join(gen, "robust_macros.tex"), "w") as fh:
        fh.write("\n".join(L) + "\n")

    # ---- table
    hdr = " & ".join(r"\textbf{" + nr.WF_SHORT[w] + "}" for w in nr.WF_ORDER)
    T = [r"\setlength{\tabcolsep}{5pt}", r"\begin{tabular}{@{}lccccc@{}}", r"\toprule",
         r"\textbf{Run} & " + hdr + r" & \textbf{All [95\% CI]} \\", r"\midrule"]
    for run, _, _ in RUNS:
        wf_credit = nr.macro(R[run]["items"], "Credit").reindex(nr.WF_ORDER)
        best = wf_credit.max()
        cells = [(r"\textbf{" + f1(v) + "}") if abs(v - best) < 1e-9 else f1(v) for v in wf_credit]
        c = CI[run]
        T.append(RUN_LABEL[run] + " & " + " & ".join(cells) +
                 f" & {f1(c[0])} {{\\scriptsize[{f1(c[1])}, {f1(c[2])}]}} \\\\")
    T += [r"\bottomrule", r"\end{tabular}"]
    with open(os.path.join(gen, "tab_robust_runs.tex"), "w") as fh:
        fh.write("% Auto-generated by scripts/robustness_results.py\n" + "\n".join(T) + "\n")

    # ---- figure: credit by setting and workflow for each model (wordings pooled),
    # plus paired rephrasing and model effects
    plt = nr.setup_mpl()
    fig = plt.figure(figsize=(6.5, 2.55))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.95], wspace=0.3)
    settings = [("S1", "Inde-\npendent"), ("S2", "Conver-\nsation"), ("S3", "Hypo-\nthesis")]
    for k, (model, runs) in enumerate((("GLM-5.2", ("R1", "R2")), ("Haiku 4.5", ("R3", "R4")))):
        ax = fig.add_subplot(gs[k])
        it = pd.concat([R[r]["items"] for r in runs])
        tab = nr.macro(it, "Credit", ["Setting", "Workflow"]).unstack().reindex(columns=nr.WF_ORDER)
        x = np.arange(len(settings))
        width = 0.8 / len(nr.WF_ORDER)
        for j, wf in enumerate(nr.WF_ORDER):
            v = tab.reindex([s_ for s_, _ in settings])[wf].to_numpy()
            ax.bar(x - 0.4 + width * (j + 0.5), v, width=width, color=nr.WF_COLOR[wf], edgecolor=nr.SURFACE,
                   linewidth=0.8, label=nr.WF_LABEL[wf])
        ax.set_xticks(x)
        ax.set_xticklabels([lab for _, lab in settings], fontsize=7)
        ax.set_ylim(0, 100)
        ax.tick_params(axis="x", length=0)
        ax.set_title(("(a) " if k == 0 else "(b) ") + model, loc="left")
        if k == 0:
            ax.set_ylabel("Mean item credit (%)")
    sub = gs[2].subgridspec(1, 2, width_ratios=[0.62, 1], wspace=0)
    ax2 = fig.add_subplot(sub[1])
    rows = [("Rephrased, GLM", "RephGLM"), ("Rephrased, Haiku", "RephHaiku"),
            ("Haiku $-$ GLM, orig.", "ModelOrig"), ("Haiku $-$ GLM, reph.", "ModelReph")]
    for i, (lab, key) in enumerate(rows[::-1]):
        d, lo, hi, p, n = effects[key]
        ax2.errorbar(d, i, xerr=[[d - lo], [hi - d]], fmt="o", color=nr.INK, markersize=4.5,
                     elinewidth=1, capsize=2)
    ax2.axvline(0, color=nr.INK2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax2.set_yticks(range(len(rows)))
    ax2.set_yticklabels([r_[0] for r_ in rows[::-1]], fontsize=6.6)
    ax2.set_xlabel("Paired difference (pp)", fontsize=7)
    ax2.grid(True, axis="x")
    ax2.grid(False, axis="y")
    ax2.set_title("(c) Effects", loc="left")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=nr.WF_COLOR[w], label=nr.WF_LABEL[w]) for w in nr.WF_ORDER],
               loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.0), handlelength=1.2, columnspacing=1.2)
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.2, top=0.8)
    fig.savefig(os.path.join(img, "fig_robust.pdf"))
    plt.close(fig)

    # console summary
    print({k: (round(v[0], 1), round(v[1], 1), round(v[2], 1), round(v[3], 4), v[4]) for k, v in effects.items()})
    for run in R:
        print(run, round(CI[run][0], 1), TO[run], nr.macro(R[run]["items"], "Credit").round(1).to_dict())
    print({k: v.round(1).to_dict() for k, v in wf_eff.items()})


if __name__ == "__main__":
    main()
