#!/usr/bin/env python3
"""Nova benchmark results pipeline.

Reads one or more SonicSuiteBench result workbooks (one per dataset), pools the
item-level results, computes every metric, statistic, and figure reported in
the paper, and writes:

  figures/fig_*.pdf                 figures (vector, included by the paper)
  numbers/results_macros.tex     \\newcommand macros for every number in the text
  numbers/tab_main.tex           main results table
  numbers/tab_pairwise.tex       pairwise workflow comparisons
  numbers/results_summary.csv    all workflow-level metrics, for inspection

Usage (from the repository root):
  python scripts/nova_results.py                       # all files in data/results/nova_run
  python scripts/nova_results.py a.xlsx b.xlsx         # explicit files

Metrics are always recomputed from the item-level sheets (S1_Results,
S2_Results, S3_Results) rather than averaged from per-dataset summaries, so
pooled numbers weight every item equally regardless of how many datasets are
present. Definitions reproduce the suite's own Summary_Wide values exactly for
a single dataset (checked by --selfcheck).
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import warnings
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.dirname(HERE)  # repository root; scripts live in <repo>/scripts


def numbers_dir():
    """Numbers and tables are written for checking only; the paper hardcodes them."""
    import tempfile
    d = os.environ.get("NOVA_NUMBERS_DIR") or tempfile.mkdtemp(prefix="nova_numbers_")
    os.makedirs(d, exist_ok=True)
    return d

# ---------------------------------------------------------------- constants
# Nova-Auto routes among the other three, so it is listed last.
WF_ORDER = ["Nova Instant", "Nova Thinking", "Nova Deep Thinking", "Nova Auto"]
WF_LABEL = {"Nova Instant": "Nova-Instant", "Nova Thinking": "Nova-Thinking",
            "Nova Auto": "Nova-Auto", "Nova Deep Thinking": "Nova-Deep Thinking"}
WF_SHORT = {"Nova Instant": "Instant", "Nova Thinking": "Thinking",
            "Nova Auto": "Auto", "Nova Deep Thinking": "Deep Thinking"}
WF_MACRO = {"Nova Instant": "Inst", "Nova Thinking": "Think",
            "Nova Auto": "Auto", "Nova Deep Thinking": "Deep"}
SERIES_TO_WF = {"chatbot": "Nova Instant", "chatbot_thinking": "Nova Thinking",
                "chatbot_auto": "Nova Auto", "chatbot_deep_thinking": "Nova Deep Thinking"}
# Reference categorical palette, slots 1-4 (validated adjacent-pair order).
WF_COLOR = {"Nova Instant": "#2a78d6", "Nova Thinking": "#eb6834",
            "Nova Auto": "#1baf7a", "Nova Deep Thinking": "#eda100"}
WF_MARKER = {"Nova Instant": "o", "Nova Thinking": "s", "Nova Auto": "^", "Nova Deep Thinking": "D"}
RRL = ["R0", "R1", "R2", "R3", "R4"]
RRL_LABEL = {r: "L" + r[1] for r in RRL}          # paper uses L0-L4
DIFF = ["EASY", "MODERATE", "HARD", "EXPERT"]
DIFF_LABEL = {"EASY": "Easy", "MODERATE": "Moderate", "HARD": "Hard", "EXPERT": "Expert"}
REL = ["SUPPORTS", "QUALIFIES", "CONTRADICTS", "NEUTRAL"]
DECISIONS = ["RETAIN", "QUALIFY", "REVISE", "REJECT", "INSUFFICIENT_EVIDENCE"]
DEC_LABEL = {"RETAIN": "Retain", "QUALIFY": "Qualify", "REVISE": "Revise",
             "REJECT": "Reject", "INSUFFICIENT_EVIDENCE": "Insufficient"}
NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
             7: "seven", 8: "eight", 9: "nine", 10: "ten"}

INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#ffffff"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

N_BOOT = 2000
RNG = np.random.default_rng(20261005)


# ---------------------------------------------------------------- loading
def _bool(series):
    """Coerce True/False/'True'/1.0/NaN columns to float (1, 0, NaN)."""
    def f(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return np.nan
        if isinstance(v, str):
            v = v.strip().lower()
            if v in ("true", "1", "1.0", "yes"):
                return 1.0
            if v in ("false", "0", "0.0", "no"):
                return 0.0
            return np.nan
        return float(bool(v))
    return series.map(f)


def load(files):
    s1, s2, s3, info = [], [], [], []
    for f in files:
        ri = pd.read_excel(f, sheet_name="Run_Info")
        ri["File"] = os.path.basename(f)
        info.append(ri)
        for name, acc in (("S1_Results", s1), ("S2_Results", s2), ("S3_Results", s3)):
            d = pd.read_excel(f, sheet_name=name)
            d["Run_ID"] = d["Run_ID"].astype(str)
            acc.append(d)
    info = pd.concat(info, ignore_index=True)
    # one run per dataset: keep the most recent if duplicated
    info["Created_At"] = pd.to_datetime(info["Created_At"], utc=True)
    info = info.sort_values("Created_At").drop_duplicates("Dataset_ID", keep="last")
    keep = set(info["Run_ID"].astype(str))
    out = []
    for acc in (s1, s2, s3):
        d = pd.concat(acc, ignore_index=True)
        d = d[d["Run_ID"].isin(keep)].copy()
        base = d["Series_ID"].astype(str).str.split("::").str[0]
        d["Workflow"] = base.map(SERIES_TO_WF).fillna(d["Workflow"])
        d = d[d["Workflow"].isin(WF_ORDER)]
        d["Credit"] = pd.to_numeric(d["Credit"], errors="coerce").fillna(0.0)
        d["Strict"] = (d["Verdict"] == "match").astype(float)
        d["Hallucination_Rate"] = pd.to_numeric(d["Hallucination_Rate"], errors="coerce")
        d["Tool_Match"] = _bool(d["Tool_Category_Match"])
        # Timeouts: an explicit time-budget message, an empty response returned at the
        # deadline, or a turn skipped after the harness stopped a failing conversation.
        status = d["Eval_Status"].astype(str).str.lower() if "Eval_Status" in d else pd.Series("", index=d.index)
        d["Timeout"] = (d["Answer"].astype(str).str.contains("exceeded the time budget", case=False)
                        | status.isin(["empty", "skipped"])).astype(float)
        d["Unclear"] = (d["Verdict"].isin(["unclear", "no_answer"]) & (d["Timeout"] == 0)).astype(float)
        d["VerdictCat"] = np.where(d["Timeout"] == 1, "timeout", d["Verdict"].astype(str))
        d["Factual_Error"] = d["Factual_Errors"].notna().astype(float)
        out.append(d)
    s1, s2, s3 = out
    for c in ("Challenge_Turn", "Revision_Expected", "Consistency_Applicable",
              "Consistency_OK", "Revision_OK"):
        s2[c] = _bool(s2[c])
    for c in ("Is_Final", "Relationship_Match", "State_Declared", "State_Match",
              "Decision_Match", "Calibration_OK", "Revision_OK"):
        s3[c] = _bool(s3[c])
    s1["Item"] = s1["Question_ID"]
    s1["Cluster"] = s1["Question_ID"]
    s2["Item"] = s2["Turn_ID"]
    s2["Cluster"] = s2["Trajectory_ID"]
    s3["Item"] = np.where(s3["Is_Final"] == 1, s3["Step_ID"] + "-FINAL", s3["Step_ID"])
    s3["Cluster"] = s3["Hypothesis_ID"]
    return s1, s2, s3, info


# ---------------------------------------------------------------- metrics
# Every score is a macro average: computed within each dataset, then averaged over
# the six datasets (each dataset weighs equally). Significance tests stay item-level.
def macro(df, value, by=("Workflow",), scale=100.0):
    """Macro mean of `value` over datasets, per group `by` (a Series indexed by `by`)."""
    by = [by] if isinstance(by, str) else list(by)
    d = df.dropna(subset=[value])
    g = d.groupby(["Dataset_ID"] + by)[value].mean()
    return g.groupby(level=list(range(1, len(by) + 1))).mean() * scale


def macro1(df, value, scale=100.0):
    """Macro mean of `value` over datasets (a scalar)."""
    d = df.dropna(subset=[value])
    return d.groupby("Dataset_ID")[value].mean().mean() * scale if len(d) else np.nan


def _m(x):
    x = pd.Series(x, dtype=float).dropna()
    return 100 * x.mean() if len(x) else np.nan


def setting_metrics(s1, s2, s3, pooled=False, suite_defs=False):
    """Workflow-level metrics, macro-averaged over datasets (pooled=True: one pool;
    definitions reproduce Summary_Wide, which the self-check compares per dataset)."""
    if not pooled:
        per = [setting_metrics(s1[s1.Dataset_ID == d], s2[s2.Dataset_ID == d], s3[s3.Dataset_ID == d], pooled=True)
               for d in sorted(set(s1.Dataset_ID) | set(s2.Dataset_ID) | set(s3.Dataset_ID))]
        cat = pd.concat(per)
        out = cat.groupby(level=0).mean().reindex(WF_ORDER)
        for c in ("NTimeout", "N", "CostTotal"):
            out[c] = cat.groupby(level=0)[c].sum().reindex(WF_ORDER)
        out["NTimeout"] = out["NTimeout"].astype(int)
        return out
    rows = []
    for wf in WF_ORDER:
        a, b, c = s1[s1.Workflow == wf], s2[s2.Workflow == wf], s3[s3.Workflow == wf]
        steps, finals = c[c.Is_Final != 1], c[c.Is_Final == 1]
        allr = pd.concat([a, b, c])
        r = {"Workflow": wf}
        r["S1_Acc"] = _m(a.Credit)
        r["S1_Strict"] = _m(a.Strict)
        r["S1_Ref"] = a.Ref_Score_0_10.mean()
        r["S2_Acc"] = _m(b.Credit)
        r["S2_Chal"] = _m(b.loc[b.Challenge_Turn == 1, "Credit"])
        r["S2_Cons"] = _m(b.loc[b.Consistency_Applicable == 1, "Consistency_OK"])
        r["S2_Rev"] = _m(b.loc[b.Revision_Expected == 1, "Revision_OK"])
        traj = b.groupby(["Dataset_ID", "Trajectory_ID"]).Credit.min()
        r["S2_Pass"] = _m(traj >= 0.5)
        # hypothesis items are the evidence steps and the final decision (suite_defs: steps only, as Summary_Wide)
        r["S3_Step"] = _m(steps.Credit) if suite_defs else _m(c.Credit)
        r["S3_Rel"] = _m(steps.Relationship_Match)
        r["S3_State"] = _m(steps.State_Match)
        r["S3_Dec"] = _m(finals.Decision_Match)
        r["S3_Final"] = _m(finals.State_Match)
        r["S3_Cal"] = _m(finals.Calibration_OK)
        r["S3_Decl"] = _m(c.State_Declared)
        r["S3_Score"] = np.nanmean([r["S3_Step"], r["S3_State"], r["S3_Dec"]])
        r["Suite"] = np.nanmean([r["S1_Acc"], r["S2_Acc"], r["S3_Score"]])
        r["Judge"] = allr.LLM_Judge_Overall.mean()
        r["Hall"] = allr.Hallucination_Rate.mean()
        r["Tool"] = _m(allr.Tool_Match)
        r["Unclear"] = _m(allr.Unclear)
        r["Timeout"] = _m(allr.Timeout)
        r["NTimeout"] = int(allr.Timeout.sum())
        r["FactErr"] = _m(allr.Factual_Error)
        r["Latency"] = allr.Response_Time_s.mean()
        r["Calls"] = allr.Tool_Call_Count.mean()
        r["Tokens"] = allr.Total_Tokens.mean()
        r["TokensK"] = allr.Total_Tokens.mean() / 1000
        r["CostPerAns"] = allr.Est_Cost_USD.mean()
        r["CostTotal"] = allr.Est_Cost_USD.sum()
        r["N"] = len(allr)
        rows.append(r)
    return pd.DataFrame(rows).set_index("Workflow")


# --------------------------------------------------------- cluster bootstrap
def _cluster_arrays(s1, s2, s3):
    """Per-cluster sums so a bootstrap replicate is pure numpy indexing.

    Clusters: S1 question, S2 trajectory, S3 hypothesis. Resampling is
    stratified by dataset so each replicate keeps the dataset mix.
    """
    def agg(df, cols, key="Cluster"):
        g = df.groupby(["Dataset_ID", key, "Workflow"])
        out = {}
        for name, (col, fn) in cols.items():
            out[name] = getattr(g[col], fn)().unstack("Workflow").reindex(columns=WF_ORDER)
        return out
    steps, finals = s3[s3.Is_Final != 1], s3[s3.Is_Final == 1]
    A = agg(s1, {"c": ("Credit", "sum"), "n": ("Credit", "count")})
    B = agg(s2, {"c": ("Credit", "sum"), "n": ("Credit", "count")})
    C = agg(s3, {"c": ("Credit", "sum"), "n": ("Credit", "count")})       # steps and final decisions
    Cs = agg(steps, {"st": ("State_Match", "sum"), "stn": ("State_Match", "count")})
    for k in Cs:
        C[k] = Cs[k].reindex(C["c"].index).fillna(0)
    F = agg(finals, {"d": ("Decision_Match", "sum"), "dn": ("Decision_Match", "count")})
    for k in F:
        F[k] = F[k].reindex(C["c"].index).fillna(0)
    return A, B, C, F


def _strata_idx(index):
    ds = index.get_level_values(0).to_numpy()
    return [np.where(ds == d)[0] for d in pd.unique(ds)]


def bootstrap_ci(s1, s2, s3, n_boot=N_BOOT):
    """95% percentile CIs for the four headline scores, per workflow."""
    A, B, C, F = _cluster_arrays(s1, s2, s3)
    sa, sb, sc = _strata_idx(A["c"].index), _strata_idx(B["c"].index), _strata_idx(C["c"].index)
    a_c, a_n = A["c"].to_numpy(), A["n"].to_numpy()
    b_c, b_n = B["c"].to_numpy(), B["n"].to_numpy()
    c_c, c_n, c_s, c_sn = (C[k].to_numpy() for k in ("c", "n", "st", "stn"))
    f_d, f_n = F["d"].to_numpy(), F["dn"].to_numpy()

    def ratio(num, den, strata):
        """Macro mean over datasets of a resampled ratio (strata: one index array per dataset)."""
        vals = []
        for st in strata:
            i = RNG.choice(st, size=len(st), replace=True)
            vals.append(num[i].sum(0) / np.maximum(den[i].sum(0), 1))
        return 100 * np.mean(vals, axis=0)

    res = {k: [] for k in ("S1_Acc", "S2_Acc", "S3_Score", "Suite")}
    for _ in range(n_boot):
        s1a = ratio(a_c, a_n, sa)
        s2a = ratio(b_c, b_n, sb)
        s3_ds = []
        for st in sc:                                   # same hypotheses for step, state and decision
            i = RNG.choice(st, size=len(st), replace=True)
            step = c_c[i].sum(0) / np.maximum(c_n[i].sum(0), 1)
            state = c_s[i].sum(0) / np.maximum(c_sn[i].sum(0), 1)
            dec = f_d[i].sum(0) / np.maximum(f_n[i].sum(0), 1)
            s3_ds.append(100 * (step + state + dec) / 3)
        s3s = np.mean(s3_ds, axis=0)
        res["S1_Acc"].append(s1a)
        res["S2_Acc"].append(s2a)
        res["S3_Score"].append(s3s)
        res["Suite"].append((s1a + s2a + s3s) / 3)
    out = {}
    for k, v in res.items():
        v = np.array(v)
        out[k] = pd.DataFrame({"lo": np.percentile(v, 2.5, axis=0),
                               "hi": np.percentile(v, 97.5, axis=0)}, index=WF_ORDER)
    return out


def boot_mean_ci(df, value, by, cluster="Cluster", n_boot=N_BOOT):
    """CI for mean(value) within groups `by` x workflow, clustered resampling."""
    rows = []
    for key, g in df.groupby(by):
        piv = g.groupby(["Dataset_ID", cluster, "Workflow"])[value].agg(["sum", "count"])
        s = piv["sum"].unstack("Workflow").reindex(columns=WF_ORDER).fillna(0).to_numpy()
        n = piv["count"].unstack("Workflow").reindex(columns=WF_ORDER).fillna(0).to_numpy()
        idx = piv["sum"].unstack("Workflow").index
        strata = _strata_idx(idx)
        reps = []
        with np.errstate(invalid="ignore", divide="ignore"):
            for _ in range(n_boot // 2):
                per = []
                for st in strata:
                    i = RNG.choice(st, size=len(st), replace=True)
                    per.append(s[i].sum(0) / n[i].sum(0))
                reps.append(100 * np.nanmean(per, axis=0))
            point = 100 * np.nanmean([s[st].sum(0) / n[st].sum(0) for st in strata], axis=0)
        reps = np.array(reps)
        for j, wf in enumerate(WF_ORDER):
            rows.append({"group": key, "Workflow": wf, "mean": point[j],
                         "lo": np.nanpercentile(reps[:, j], 2.5),
                         "hi": np.nanpercentile(reps[:, j], 97.5), "n": int(n[:, j].sum())})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- statistics
def holm(p):
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = len(p)
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p[i])
        adj[i] = min(1.0, running)
    return adj


def wide(df, value):
    w = df.pivot_table(index=["Dataset_ID", "Item"], columns="Workflow", values=value, aggfunc="mean")
    return w.reindex(columns=WF_ORDER).dropna()


def rank_biserial(d):
    d = d[d != 0]
    if len(d) == 0:
        return 0.0
    r = stats.rankdata(np.abs(d))
    wp, wn = r[d > 0].sum(), r[d < 0].sum()
    return (wp - wn) / (wp + wn)


def friedman(w):
    if len(w) < 3:
        return np.nan, np.nan
    try:
        chi, p = stats.friedmanchisquare(*[w[c].to_numpy() for c in WF_ORDER])
    except ValueError:
        return np.nan, np.nan
    return chi, p


def kendall_w(chi, n, k=4):
    return chi / (n * (k - 1)) if n else np.nan


def cochran_q(x):
    """x: n x k binary matrix."""
    x = np.asarray(x, float)
    k = x.shape[1]
    col, row = x.sum(0), x.sum(1)
    num = (k - 1) * (k * (col ** 2).sum() - col.sum() ** 2)
    den = k * row.sum() - (row ** 2).sum()
    if den == 0:
        return np.nan, np.nan
    q = num / den
    return q, stats.chi2.sf(q, k - 1)


def mcnemar_exact(a, b):
    n01 = int(((a == 0) & (b == 1)).sum())
    n10 = int(((a == 1) & (b == 0)).sum())
    n = n01 + n10
    if n == 0:
        return 1.0
    return min(1.0, 2 * stats.binom.cdf(min(n01, n10), n, 0.5))


def pairwise(df, value="Credit", n_boot=N_BOOT):
    """Paired comparisons on item-level credit, clustered bootstrap CI."""
    w = wide(df, value)
    clusters = df.drop_duplicates(["Dataset_ID", "Item"]).set_index(["Dataset_ID", "Item"])["Cluster"]
    cl = clusters.reindex(w.index).to_numpy()
    ds = w.index.get_level_values(0).to_numpy()
    keys = pd.Series(list(zip(ds, cl)))
    uniq = pd.unique(keys)
    code = keys.map({k: i for i, k in enumerate(uniq)}).to_numpy()
    strata = [np.array([i for i, k in enumerate(uniq) if k[0] == d]) for d in pd.unique(ds)]
    members = [np.where(code == i)[0] for i in range(len(uniq))]
    rows, ps = [], []
    for a, b in combinations(WF_ORDER, 2):
        d = (w[b] - w[a]).to_numpy()
        try:
            p = stats.wilcoxon(w[b], w[a], zero_method="wilcox").pvalue if np.any(d != 0) else 1.0
        except ValueError:
            p = 1.0
        sums = np.array([d[m].sum() for m in members])
        cnts = np.array([len(m) for m in members])
        reps = []
        for _ in range(n_boot):
            per = []
            for st in strata:
                i = RNG.choice(st, size=len(st), replace=True)
                per.append(sums[i].sum() / cnts[i].sum())
            reps.append(np.mean(per))
        dmac = np.mean([sums[st].sum() / cnts[st].sum() for st in strata])
        rows.append({"A": a, "B": b, "diff": 100 * dmac,
                     "lo": 100 * np.percentile(reps, 2.5), "hi": 100 * np.percentile(reps, 97.5),
                     "r": rank_biserial(d), "p": p, "n": len(d)})
        ps.append(p)
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(ps)
    return out


def strict_tests(df):
    w = wide(df, "Strict")
    q, p = cochran_q(w.to_numpy())
    pw = []
    for a, b in combinations(WF_ORDER, 2):
        pw.append({"A": a, "B": b, "p": mcnemar_exact(w[a].to_numpy(), w[b].to_numpy())})
    pw = pd.DataFrame(pw)
    pw["p_holm"] = holm(pw.p)
    return q, p, pw, len(w)


def mixed_rrl(allitems, with_difficulty=False):
    """Linear mixed model: credit ~ workflow * RRL (numeric 0-4) [+ difficulty]
    + setting [+ dataset], random intercept per item."""
    import statsmodels.formula.api as smf
    d = allitems.copy()
    d["rrl"] = d["RRL"].str[1].astype(float)
    d = d.dropna(subset=["rrl"] + (["Difficulty"] if with_difficulty else []))
    d["wf"] = pd.Categorical(d["Workflow"].map(WF_MACRO), categories=[WF_MACRO[w] for w in WF_ORDER])
    d["grp"] = d["Dataset_ID"].astype(str) + "|" + d["Item"].astype(str)
    f = "Credit ~ C(wf, Treatment('Inst')) * rrl + C(Setting)"
    if d["Dataset_ID"].nunique() > 1:
        f += " + C(Dataset_ID)"
    if with_difficulty:
        f += " + C(Difficulty)"
    try:
        m = smf.mixedlm(f, d, groups=d["grp"]).fit(reml=True, method="lbfgs")
    except Exception as e:  # pragma: no cover
        print("mixed model failed:", e, file=sys.stderr)
        return None
    out = {}
    for wf in WF_ORDER[1:]:
        k = WF_MACRO[wf]
        name = f"C(wf, Treatment('Inst'))[T.{k}]:rrl"
        out[k] = (m.params.get(name, np.nan), m.bse.get(name, np.nan), m.pvalues.get(name, np.nan))
    out["slope"] = (m.params.get("rrl", np.nan), m.bse.get("rrl", np.nan), m.pvalues.get("rrl", np.nan))
    return out


def judge_auc(s1):
    """Agreement of the LLM judge's correctness score with deterministic
    exact-match grading on closed-form items (MCQ, true/false)."""
    c = s1[s1.Match_Method.astype(str).str.startswith("curated_exact")]
    c = c.dropna(subset=["LLM_Judge_Correctness"])
    pos = c.loc[c.Credit >= 1, "LLM_Judge_Correctness"]
    neg = c.loc[c.Credit < 1, "LLM_Judge_Correctness"]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan, len(c)
    u = stats.mannwhitneyu(pos, neg, alternative="two-sided").statistic
    return u / (len(pos) * len(neg)), len(c)


# ---------------------------------------------------------------- formatting
def f1(x):
    return "--" if pd.isna(x) else f"{x:.1f}"


def f2(x):
    return "--" if pd.isna(x) else f"{x:.2f}"


def sgn(x, fmt="{:+.1f}"):
    """Signed number with a typographic minus for LaTeX tables."""
    return fmt.format(x).replace("-", "$-$")


def fp(p):
    if pd.isna(p):
        return "--"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def fp_tex(p):
    """p-value as math: '$p<0.001$' or '$p=0.034$'."""
    if pd.isna(p):
        return "$p$ n/a"
    return "$p<0.001$" if p < 0.001 else f"$p={p:.3f}$"


def macro_name(*parts):
    s = "".join(p[:1].upper() + p[1:] for p in parts)
    return "".join(ch for ch in s if ch.isalpha())


# ---------------------------------------------------------------- figures
def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "mathtext.fontset": "stix", "font.size": 8, "axes.titlesize": 8.5,
        "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "legend.fontsize": 7.5, "axes.edgecolor": INK2, "axes.labelcolor": INK,
        "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.axisbelow": True, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "pdf.fonttype": 42, "lines.linewidth": 2,
        "legend.frameon": False,
    })
    return plt


def _legend(fig, plt, ncol=4, y=1.0):
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    h = [Patch(facecolor=WF_COLOR[w], edgecolor="none", label=WF_LABEL[w]) for w in WF_ORDER]
    fig.legend(handles=h, loc="upper center", ncol=ncol, bbox_to_anchor=(0.5, y),
               handlelength=1.2, columnspacing=1.4)


def _bars(ax, groups, values, lo=None, hi=None, ylabel="", ylim=(0, 100), labels=True):
    """Grouped bars: groups on x, one bar per workflow; 2px gap between bars."""
    n = len(WF_ORDER)
    width = 0.8 / n
    x = np.arange(len(groups))
    for j, wf in enumerate(WF_ORDER):
        xs = x - 0.4 + width * (j + 0.5)
        v = np.array([values[g][wf] for g in groups], float)
        ax.bar(xs, v, width=width, color=WF_COLOR[wf], edgecolor=SURFACE, linewidth=1.0, zorder=2)
        if lo is not None:
            l = np.array([lo[g][wf] for g in groups], float)
            h = np.array([hi[g][wf] for g in groups], float)
            ax.errorbar(xs, v, yerr=[v - l, h - v], fmt="none", ecolor=INK2, elinewidth=0.8,
                        capsize=1.6, zorder=3)
        if labels:
            for xi, vi in zip(xs, v):
                if not np.isnan(vi):
                    ax.text(xi, (hi[groups[0]][wf] if False else vi) + 1.2, f"{vi:.0f}",
                            ha="center", va="bottom", fontsize=5.6, color=INK2, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylim(*ylim)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", length=0)


def fig_overall(plt, M, CI, path):
    groups = ["Single-turn\naccuracy", "Interactive\nturn accuracy", "Hypothesis\nscore", "Suite\nscore"]
    keys = ["S1_Acc", "S2_Acc", "S3_Score", "Suite"]
    vals = {g: M[k].to_dict() for g, k in zip(groups, keys)}
    lo = {g: CI[k]["lo"].to_dict() for g, k in zip(groups, keys)}
    hi = {g: CI[k]["hi"].to_dict() for g, k in zip(groups, keys)}
    fig, ax = plt.subplots(figsize=(6.5, 2.5))
    _bars(ax, groups, vals, lo, hi, ylabel="Score (%)", ylim=(0, 100), labels=False)
    for j, wf in enumerate(WF_ORDER):  # value labels above the CI whisker
        for gi, g in enumerate(groups):
            xs = gi - 0.4 + 0.2 * (j + 0.5)
            ax.text(xs, hi[g][wf] + 1.5, f"{vals[g][wf]:.1f}", ha="center", va="bottom",
                    fontsize=5.6, color=INK2)
    _legend(fig, plt)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path)
    plt.close(fig)


def _lines(ax, tab, groups, glabels, ylabel, dodge=0.09):
    x = np.arange(len(groups))
    for j, wf in enumerate(WF_ORDER):
        t = tab[tab.Workflow == wf].set_index("group").reindex(groups)
        xs = x + (j - 1.5) * dodge
        ax.errorbar(xs, t["mean"], yerr=[t["mean"] - t["lo"], t["hi"] - t["mean"]],
                    color=WF_COLOR[wf], marker=WF_MARKER[wf], markersize=4.5, linewidth=1.6,
                    elinewidth=0.8, capsize=1.6, markeredgecolor=SURFACE, markeredgewidth=0.6,
                    label=WF_LABEL[wf])
    ax.set_xticks(x)
    ax.set_xticklabels(glabels)
    ax.set_ylim(0, 100)
    ax.set_ylabel(ylabel)


def fig_rrl(plt, allitems, path):
    t_rrl = boot_mean_ci(allitems, "Credit", "RRL")
    t_dif = boot_mean_ci(allitems, "Credit", "Difficulty")
    groups_r = [r for r in RRL if r in set(allitems.RRL)]
    groups_d = [d for d in DIFF if d in set(allitems.Difficulty)]
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.45), sharey=True)
    _lines(axes[0], t_rrl, groups_r, [RRL_LABEL[r] for r in groups_r], "Mean credit (%)")
    axes[0].set_title("(a) By Reasoning Requirement Level", loc="left")
    _lines(axes[1], t_dif, groups_d, [DIFF_LABEL[d] for d in groups_d], "")
    axes[1].set_title("(b) By difficulty", loc="left")
    for ax, t, gs in ((axes[0], t_rrl, groups_r), (axes[1], t_dif, groups_d)):
        ns = t[t.Workflow == WF_ORDER[0]].set_index("group").reindex(gs)["n"]
        ax.set_xticklabels([f"{lab}\n$n$={n}" for lab, n in zip([tl.get_text() for tl in ax.get_xticklabels()], ns)])
    _legend(fig, plt)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path)
    plt.close(fig)
    return t_rrl, t_dif


def fig_interactive(plt, s2, M, path):
    d = s2.copy()
    tn = d["Turn_Number"].astype(int)
    bins = [(1, 3), (4, 6), (7, 9), (10, 12)]
    d["pos"] = pd.cut(tn, [0, 3, 6, 9, 12], labels=[f"{a}--{b}" if False else f"{a}-{b}" for a, b in bins])
    t = boot_mean_ci(d, "Credit", "pos")
    groups = [f"{a}-{b}" for a, b in bins if f"{a}-{b}" in set(t.group.astype(str))]
    t["group"] = t["group"].astype(str)
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.45), gridspec_kw={"width_ratios": [1, 1.5]})
    _lines(axes[0], t, groups, [g.replace("-", "–") for g in groups], "Mean turn credit (%)")
    axes[0].set_xlabel("Turn position in conversation")
    axes[0].set_title("(a) Accuracy across the conversation", loc="left")
    groups_b = ["Turn\naccuracy", "Challenge\nturns", "Fact\npreservation", "Revision"]
    keys = ["S2_Acc", "S2_Chal", "S2_Cons", "S2_Rev"]
    _bars(axes[1], groups_b, {g: M[k].to_dict() for g, k in zip(groups_b, keys)},
          ylabel="Rate (%)", labels=True)
    axes[1].set_title("(b) Interactive-setting criteria", loc="left")
    _legend(fig, plt)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path)
    plt.close(fig)


def fig_hypothesis(plt, s3, M, path):
    steps, finals = s3[s3.Is_Final != 1], s3[s3.Is_Final == 1]
    fig = plt.figure(figsize=(6.5, 2.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.05, 0.95], wspace=0.5)
    ax = fig.add_subplot(gs[0])
    groups = ["Step\ncredit", "Evidence\nrelation", "State\ntracking", "Final\ndecision"]
    keys = ["S3_Step", "S3_Rel", "S3_State", "S3_Dec"]
    _bars(ax, groups, {g: M[k].to_dict() for g, k in zip(groups, keys)}, ylabel="Rate (%)", labels=True)
    ax.set_title("(a) Hypothesis-setting criteria", loc="left")
    ax2 = fig.add_subplot(gs[1])
    rel = macro(steps, "Relationship_Match", ["Expected_Relationship", "Workflow"]).unstack()
    rel = rel.reindex(index=[r for r in REL if r in rel.index], columns=WF_ORDER)
    vals = {r.capitalize(): rel.loc[r].to_dict() for r in rel.index}
    _bars(ax2, list(vals), vals, ylabel="Relation accuracy (%)", ylim=(0, 105), labels=False)
    short = {"SUPPORTS": "Supp.", "QUALIFIES": "Qual.", "CONTRADICTS": "Contr.", "NEUTRAL": "Neut."}
    ax2.set_xticklabels([short[r] for r in rel.index], fontsize=6.6)
    ax2.set_title("(b) By true evidence relation", loc="left")
    ax3 = fig.add_subplot(gs[2])
    cm = pd.crosstab(finals.Expected_Decision, finals.Extracted_Decision.fillna("NONE"))
    cols = DECISIONS + (["NONE"] if "NONE" in cm.columns else [])
    cm = cm.reindex(index=DECISIONS, columns=cols, fill_value=0)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#f7f7f5"] + BLUE_RAMP[1:])
    ax3.imshow(cm.to_numpy(), cmap=cmap, aspect="auto", vmin=0, vmax=max(1, cm.to_numpy().max()))
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            v = cm.iat[i, j]
            if v:
                dark = v > 0.55 * cm.to_numpy().max()
                ax3.text(j, i, str(v), ha="center", va="center", fontsize=6.5,
                         color=SURFACE if dark else INK)
    lab = [DEC_LABEL.get(c, "None") for c in cols]
    ax3.set_xticks(range(len(cols)))
    ax3.set_xticklabels(lab, rotation=45, ha="right", fontsize=6.3)
    ax3.set_yticks(range(len(DECISIONS)))
    ax3.set_yticklabels([DEC_LABEL[d] for d in DECISIONS], fontsize=6.3)
    ax3.set_xlabel("Workflow decision", fontsize=7)
    ax3.set_ylabel("Reference decision", fontsize=7)
    ax3.grid(False)
    for s in ax3.spines.values():
        s.set_visible(False)
    ax3.set_title("(c) Final decisions", loc="left")
    _legend(fig, plt)
    fig.subplots_adjust(left=0.07, right=0.985, bottom=0.27, top=0.8)
    fig.savefig(path)
    plt.close(fig)


def fig_cost(plt, M, CI, path):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 1.8), sharey=True)
    for ax, key, xl in ((axes[0], "TokensK", "Mean tokens per answer (thousands)"),
                        (axes[1], "Latency", "Mean response time per answer (s)")):
        xs, ys = M[key].to_numpy(), M["Suite"].to_numpy()
        # Pareto frontier: cheaper-or-equal and better-or-equal
        order = np.argsort(xs)
        best, front = -np.inf, []
        for i in order:
            if ys[i] > best:
                front.append(i)
                best = ys[i]
        ax.plot(xs[front], ys[front], color=INK2, linewidth=0.9, linestyle=(0, (3, 2)), zorder=1)
        for wf in WF_ORDER:
            x, y = M.loc[wf, key], M.loc[wf, "Suite"]
            lo, hi = CI["Suite"].loc[wf, "lo"], CI["Suite"].loc[wf, "hi"]
            ax.errorbar(x, y, yerr=[[y - lo], [hi - y]], fmt=WF_MARKER[wf], color=WF_COLOR[wf],
                        markersize=7, markeredgecolor=SURFACE, markeredgewidth=0.8,
                        elinewidth=0.8, capsize=2, zorder=3)
            off, ha = {"Nova Instant": (7, -11)}.get(wf, (7, 4)), "left"
            # Thinking and Auto sit close together: label the left one on its left
            pair = [M.loc[w, key] for w in ("Nova Thinking", "Nova Auto")]
            if wf in ("Nova Thinking", "Nova Auto") and x == min(pair):
                off, ha = (-7, 4), "right"
            ax.annotate(WF_SHORT[wf], (x, y), xytext=off, textcoords="offset points",
                        fontsize=7, color=INK, ha=ha)
        ax.set_xlabel(xl)
        ax.grid(True, axis="both")
        pad = (xs.max() - xs.min()) * 0.25 or 1
        ax.set_xlim(max(0, xs.min() - pad * 0.4), xs.max() + pad)
    axes[0].set_ylabel("Suite score (%)")
    lo = min(CI["Suite"]["lo"].min(), M["Suite"].min()) - 5
    hi = max(CI["Suite"]["hi"].max(), M["Suite"].max()) + 6
    axes[0].set_ylim(max(0, lo), min(100, hi))
    axes[0].set_title("(a) Quality vs. tokens", loc="left")
    axes[1].set_title("(b) Quality vs. latency", loc="left")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def fig_errors(plt, allitems, M, path):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.3), gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    cats = [("match", "Full match", BLUE_RAMP[5]), ("partial", "Partial", BLUE_RAMP[2]),
            ("mismatch", "Mismatch", "#eb6834"), ("unclear", "Declined", "#b9b8b2"),
            ("timeout", "Timed out", "#52514e")]
    comp = allitems.groupby("Workflow").VerdictCat.value_counts(normalize=True).unstack().reindex(WF_ORDER).fillna(0) * 100
    y = np.arange(len(WF_ORDER))[::-1]
    left = np.zeros(len(WF_ORDER))
    for key, lab, col in cats:
        v = comp.get(key, pd.Series(0, index=WF_ORDER)).to_numpy()
        ax.barh(y, v, left=left, color=col, edgecolor=SURFACE, linewidth=1.0, height=0.62, label=lab)
        for yi, li, vi in zip(y, left, v):
            if vi >= 7:
                ax.text(li + vi / 2, yi, f"{vi:.0f}", ha="center", va="center", fontsize=6.3,
                        color=SURFACE if key in ("match", "mismatch", "timeout") else INK)
        left += v
    ax.set_yticks(y)
    ax.set_yticklabels([WF_LABEL[w] for w in WF_ORDER])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of answers (%)")
    ax.grid(True, axis="x")
    ax.grid(False, axis="y")
    ax.legend(loc="upper center", bbox_to_anchor=(0.42, 1.27), ncol=5, fontsize=6.2,
              handlelength=0.9, columnspacing=0.6, handletextpad=0.4)
    ax.set_title("(a) Grading verdicts", loc="left", pad=22)
    groups = ["Wrong tool\ncategory", "Factual\nerror", "Declined", "Timed\nout", "Halluc.\nrate"]
    vals = {groups[0]: (100 - M["Tool"]).to_dict(), groups[1]: M["FactErr"].to_dict(),
            groups[2]: M["Unclear"].to_dict(), groups[3]: M["Timeout"].to_dict(), groups[4]: M["Hall"].to_dict()}
    ymax = max(max(v.values()) for v in vals.values())
    _bars(axes[1], groups, vals, ylabel="Rate (%)", ylim=(0, min(100, ymax * 1.15 + 5)), labels=False)
    axes[1].tick_params(axis="x", labelsize=6.8)
    axes[1].set_title("(b) Process and grounding errors", loc="left", pad=22)
    _legend(fig, plt, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.savefig(path)
    plt.close(fig)


def fig_datasets(plt, s1, s2, s3, path):
    rows = []
    for ds in sorted(pd.unique(pd.concat([s1.Dataset_ID, s2.Dataset_ID, s3.Dataset_ID]))):
        m = setting_metrics(s1[s1.Dataset_ID == ds], s2[s2.Dataset_ID == ds], s3[s3.Dataset_ID == ds])
        rows.append(m["Suite"].rename(ds.split("_")[-1]))
    t = pd.DataFrame(rows)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#f7f7f5"] + BLUE_RAMP[1:])
    h = 0.55 + 0.3 * len(t)
    fig, ax = plt.subplots(figsize=(4.2, h + 0.6))
    im = ax.imshow(t.to_numpy(), cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(t.shape[0]):
        for j in range(t.shape[1]):
            v = t.iat[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7,
                    color=SURFACE if v > 60 else INK)
    ax.set_xticks(range(len(WF_ORDER)))
    ax.set_xticklabels([WF_LABEL[w].replace("Nova-", "") for w in WF_ORDER])
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels(t.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03)
    cb.set_label("Suite score (%)", fontsize=7)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=6.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return t


# ---------------------------------------------------------------- main
def selfcheck(files, s1, s2, s3):
    """Per dataset, recomputed metrics must equal the suite's Summary_Wide."""
    pairs = {"S1_Accuracy": "S1_Acc", "S1_Strict_Accuracy": "S1_Strict",
             "S2_Turn_Accuracy": "S2_Acc", "S2_Challenge_Accuracy": "S2_Chal",
             "S2_Consistency_Rate": "S2_Cons", "S2_Revision_Rate": "S2_Rev",
             "S2_Trajectory_Pass_Rate": "S2_Pass", "S3_Score": "S3_Score",
             "S3_Step_Accuracy": "S3_Step", "S3_Relationship_Accuracy": "S3_Rel",
             "S3_State_Tracking_Accuracy": "S3_State", "S3_Decision_Accuracy": "S3_Dec",
             "S3_Final_State_Accuracy": "S3_Final", "Suite_Score": "Suite"}
    bad = 0
    for f in files:
        w = pd.read_excel(f, sheet_name="Summary_Wide")
        ds = w.Dataset_ID.iloc[0]
        m = setting_metrics(s1[s1.Dataset_ID == ds], s2[s2.Dataset_ID == ds], s3[s3.Dataset_ID == ds],
                            pooled=True, suite_defs=True)
        for _, r in w.iterrows():
            wf = SERIES_TO_WF.get(str(r.Series_ID).split("::")[0], r.Workflow)
            for a, b in pairs.items():
                if abs(float(r[a]) - m.loc[wf, b]) > 0.11:
                    bad += 1
                    print(f"  MISMATCH {ds} {wf} {a}: suite {r[a]} vs recomputed {m.loc[wf, b]:.2f}")
    print("selfcheck:", "OK" if bad == 0 else f"{bad} mismatches")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--images", default=os.path.join(PAPER, "figures"))
    ap.add_argument("--generated", default=numbers_dir(),
                    help="where to write the numbers and tables (default: $NOVA_NUMBERS_DIR or a temp dir)")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    args = ap.parse_args()
    # main-run workbooks: Results/v2/runs (override with NOVA_RESULTS_DIR)
    results_dir = os.environ.get("NOVA_RESULTS_DIR", os.path.join(PAPER, "data", "results", "nova_run"))
    files = args.files or sorted(glob.glob(os.path.join(results_dir, "*.xlsx")))
    files = [f for f in files if not os.path.basename(f).startswith("~$")]
    if not files:
        sys.exit("no result workbooks found")
    os.makedirs(args.images, exist_ok=True)
    os.makedirs(args.generated, exist_ok=True)
    print(f"reading {len(files)} workbook(s)")
    s1, s2, s3, info = load(files)
    selfcheck(files, s1, s2, s3)

    datasets = sorted(info.Dataset_ID.unique())
    n_ds = len(datasets)
    model = str(info.Model.iloc[0]).replace("Anthropic - ", "")
    judge = str(info.LLM_Judge.iloc[0])

    M = setting_metrics(s1, s2, s3)
    CI = bootstrap_ci(s1, s2, s3, args.boot)
    M.round(3).to_csv(os.path.join(args.generated, "results_summary.csv"))

    steps = s3[s3.Is_Final != 1]
    allitems = pd.concat([s1.assign(Setting="S1"), s2.assign(Setting="S2"), s3.assign(Setting="S3")],
                         ignore_index=True)

    # ---- statistics
    tests = {}
    for name, df in (("All", allitems), ("SOne", s1), ("STwo", s2), ("SThree", steps)):
        w = wide(df, "Credit")
        chi, p = friedman(w)
        tests[name] = (chi, p, len(w), kendall_w(chi, len(w)))
    pw = pairwise(allitems, n_boot=args.boot)
    q, qp, pw_strict, nq = strict_tests(s1)
    wh = wide(allitems, "Hallucination_Rate")
    hall_chi, hall_p = friedman(wh)
    wl = wide(allitems, "Response_Time_s")
    lat_chi, lat_p = friedman(wl)
    mm = mixed_rrl(allitems)
    mm_d = mixed_rrl(allitems, with_difficulty=True)
    mm_s1 = mixed_rrl(s1.assign(Setting="S1"))
    auc, n_auc = judge_auc(s1)
    rho, rho_p = stats.spearmanr(allitems.LLM_Judge_Overall, allitems.Credit, nan_policy="omit")

    prov = allitems.assign(Prov=np.where(allitems.Generation_Source.astype(str).str.startswith("MANUAL"), "Man", "LLM"))
    prov_acc = macro(prov, "Credit", ["Prov", "Workflow"]).unstack()
    prov_n = prov[prov.Workflow == WF_ORDER[0]].Prov.value_counts()
    prov_chi, prov_chi_noto = {}, {}
    to_keys = set(map(tuple, allitems.loc[allitems.Timeout == 1, ["Dataset_ID", "Item"]].drop_duplicates().to_numpy()))
    prov_noto = prov[~prov[["Dataset_ID", "Item"]].apply(tuple, axis=1).isin(to_keys)]
    for pv in ("Man", "LLM"):
        chi, p = friedman(wide(prov[prov.Prov == pv], "Credit"))
        prov_chi[pv] = (chi, p)
        chi, p = friedman(wide(prov_noto[prov_noto.Prov == pv], "Credit"))
        prov_chi_noto[pv] = (chi, p)
    prov_acc_noto = macro(prov_noto, "Credit", ["Prov", "Workflow"]).unstack()
    to_prov = prov[prov.Timeout == 1].drop_duplicates(["Dataset_ID", "Item"]).Prov.value_counts()

    # RRL gain: best-suite workflow minus Instant, low (L0-L1) vs high (L3-L4) levels
    rrl_tab = macro(allitems, "Credit", ["RRL", "Workflow"]).unstack().reindex(columns=WF_ORDER)

    # ---- figures
    plt = setup_mpl()
    fig_overall(plt, M, CI, os.path.join(args.images, "fig_overall.pdf"))
    t_rrl, t_dif = fig_rrl(plt, allitems, os.path.join(args.images, "fig_rrl.pdf"))
    fig_interactive(plt, s2, M, os.path.join(args.images, "fig_interactive.pdf"))
    fig_hypothesis(plt, s3, M, os.path.join(args.images, "fig_hypothesis.pdf"))
    fig_cost(plt, M, CI, os.path.join(args.images, "fig_cost.pdf"))
    fig_errors(plt, allitems, M, os.path.join(args.images, "fig_errors.pdf"))
    ds_tab = fig_datasets(plt, s1, s2, s3, os.path.join(args.images, "fig_datasets.pdf"))

    # ---- macros
    L = ["% Auto-generated by scripts/nova_results.py -- do not edit by hand.",
         f"% Source workbooks: {', '.join(os.path.basename(f) for f in files)}"]

    def mac(name, val):
        v = str(val)
        if len(v) > 1 and v[0] in "+-" and v[1].isdigit():
            v = v.replace("-", "$-$", 1)
        L.append(f"\\newcommand{{\\{name}}}{{{v}}}")

    ph = info[info.get("Status", pd.Series("", index=info.index)).astype(str).str.lower() == "placeholder"]
    n_ph = len(ph)
    if n_ph:
        print(f"WARNING: {n_ph} placeholder workbook(s) included: {', '.join(ph.Dataset_ID)}")
    mac("NPlaceholder", n_ph)
    notes = []
    if n_ph:
        notes.append("workflow outcomes for " + NUM_WORDS.get(n_ph, str(n_ph)) + " of the " +
                     NUM_WORDS.get(n_ds, str(n_ds)) + " datasets (" +
                     ", ".join(d.split("_")[-1] for d in ph.Dataset_ID) +
                     ") are placeholder data resampled from GSE47363")
    # The paper states the workflows run on GLM-5.2; flag runs that used another model.
    other = sorted({str(m).replace("Anthropic - ", "") for m in info.Model if "glm" not in str(m).lower()})
    if other:
        print(f"WARNING: workflow model in result workbooks is not GLM-5.2: {', '.join(other)}")
        notes.append("current results were produced with " + ", ".join(other).replace("_", "\\_") +
                     ", not GLM-5.2, and will be rerun")
    mac("DataStatusNote", "" if not notes else
        "\\textbf{[Draft: " + "; ".join(notes) + "; replace before submission.]} ")
    mac("NDatasets", n_ds)
    mac("NDatasetsWord", NUM_WORDS.get(n_ds, str(n_ds)))
    mac("DatasetList", ", ".join(d.split("_")[-1] for d in datasets))
    mac("ModelID", model.replace("_", "\\_"))
    mac("JudgeID", judge.replace("_", "\\_"))
    mac("NAnswers", f"{len(pd.concat([s1, s2, s3])):,}".replace(",", "{,}"))
    mac("NItemsPerWF", f"{len(allitems) // 4:,}".replace(",", "{,}"))
    mac("NSOne", len(s1) // 4)
    mac("NSTwo", len(s2) // 4)
    mac("NSThree", len(s3) // 4)
    mac("NTraj", s2.drop_duplicates(["Dataset_ID", "Trajectory_ID"]).shape[0])
    mac("NHyp", s3.drop_duplicates(["Dataset_ID", "Hypothesis_ID"]).shape[0])
    mac("NBoot", f"{args.boot:,}".replace(",", "{,}"))
    metric_fmt = {"S1_Acc": f1, "S1_Strict": f1, "S1_Ref": f2, "S2_Acc": f1, "S2_Chal": f1,
                  "S2_Cons": f1, "S2_Rev": f1, "S2_Pass": f1, "S3_Step": f1, "S3_Rel": f1,
                  "S3_State": f1, "S3_Dec": f1, "S3_Final": f1, "S3_Cal": f1, "S3_Decl": f1,
                  "S3_Score": f1, "Suite": f1, "Judge": f2, "Hall": f1, "Tool": f1,
                  "Unclear": f1, "FactErr": f1, "Latency": f1, "Calls": f1,
                  "Tokens": lambda x: f"{x / 1000:.0f}k", "CostPerAns": lambda x: f"{x:.3f}",
                  "CostTotal": lambda x: f"{x:.2f}"}
    for wf in WF_ORDER:
        for k, fmt in metric_fmt.items():
            mac(macro_name(k.replace("S1", "SOne").replace("S2", "STwo").replace("S3", "SThree"), WF_MACRO[wf]),
                fmt(M.loc[wf, k]))
        for k in ("S1_Acc", "S2_Acc", "S3_Score", "Suite"):
            kk = k.replace("S1", "SOne").replace("S2", "STwo").replace("S3", "SThree")
            mac(macro_name(kk, WF_MACRO[wf], "Lo"), f1(CI[k].loc[wf, "lo"]))
            mac(macro_name(kk, WF_MACRO[wf], "Hi"), f1(CI[k].loc[wf, "hi"]))
    # rankings
    for k, nm in (("Suite", "Suite"), ("S1_Acc", "SOneAcc"), ("S2_Acc", "STwoAcc"), ("S3_Score", "SThreeScore")):
        order = M[k].sort_values(ascending=False).index
        mac(f"Best{nm}WF", WF_LABEL[order[0]])
        mac(f"Worst{nm}WF", WF_LABEL[order[-1]])
        mac(f"Range{nm}", f1(M[k].max() - M[k].min()))
    # Compute cost is measured in tokens (self-hosted model: no per-call price).
    cheapest, dearest = M.Tokens.idxmin(), M.Tokens.idxmax()
    mac("CostRatio", f"{M.Tokens.max() / M.Tokens.min():.1f}")
    mac("CallRatio", f"{M.Calls.max() / M.Calls.min():.1f}")
    mac("LatencyRatio", f"{M.Latency.max() / M.Latency.min():.1f}")
    mac("CheapestWF", WF_LABEL[cheapest])
    mac("CostRatioThinkInst", f"{M.Tokens['Nova Thinking'] / M.Tokens['Nova Instant']:.1f}")
    mac("CostRatioAutoInst", f"{M.Tokens['Nova Auto'] / M.Tokens['Nova Instant']:.1f}")
    mac("CostRatioDeepInst", f"{M.Tokens['Nova Deep Thinking'] / M.Tokens['Nova Instant']:.1f}")
    for k, nm in (("Suite", "Suite"), ("S1_Acc", "SOneAcc"), ("S2_Acc", "STwoAcc"), ("S3_Score", "SThreeScore")):
        mac(f"Best{nm}Val", f1(M[k].max()))
        mac(f"Worst{nm}Val", f1(M[k].min()))
    mac("DearestWF", WF_LABEL[dearest])
    mac("TotalCostAll", f"{M.CostTotal.sum():,.0f}")
    # Pareto set on cost
    order = M.Tokens.sort_values().index
    best, front = -np.inf, []
    for wf in order:
        if M.loc[wf, "Suite"] > best:
            front.append(WF_SHORT[wf])
            best = M.loc[wf, "Suite"]
    mac("ParetoSet", ", ".join(front))
    mac("NPareto", len(front))
    # tests
    for name, (chi, p, n, kw) in tests.items():
        mac(f"Friedman{name}Chi", f2(chi))
        mac(f"Friedman{name}P", fp_tex(p))
        mac(f"Friedman{name}N", n)
        mac(f"Friedman{name}W", f"{kw:.3f}" if not pd.isna(kw) else "--")
    mac("NSigPairs", int((pw.p_holm < 0.05).sum()))
    mac("CochranQ", f2(q))
    mac("CochranP", fp_tex(qp))
    mac("CochranN", nq)
    mac("NSigStrict", int((pw_strict.p_holm < 0.05).sum()))
    mac("HallChi", f2(hall_chi))
    mac("HallP", fp_tex(hall_p))
    mac("LatChi", f2(lat_chi))
    mac("LatP", fp_tex(lat_p))
    lowest_h = M.Hall.idxmin()
    mac("LowestHallWF", WF_LABEL[lowest_h])
    for tag, model_res in (("", mm), ("Diff", mm_d), ("SOne", mm_s1)):
        if model_res is None:
            continue
        b, se, p = model_res["slope"]
        mac(f"RRLSlope{tag}", f"{100 * b:.1f}")
        mac(f"RRLSlope{tag}P", fp_tex(p))
        for k in ("Think", "Deep", "Auto"):
            b, se, p = model_res[k]
            mac(f"RRLx{k}{tag}", f"{100 * b:+.1f}")
            mac(f"RRLx{k}{tag}SE", f"{100 * se:.1f}")
            mac(f"RRLx{k}{tag}P", fp_tex(p))
        ps = [model_res[k][2] for k in ("Think", "Deep", "Auto")]
        mac(f"RRLxMinP{tag}", fp_tex(min(ps)))
        mac(f"RRLxNSig{tag}", int(sum(p < 0.05 for p in ps)))
    for r in RRL:
        if r in rrl_tab.index:
            for wf in WF_ORDER:
                mac(macro_name("RRL", RRL_LABEL[r].replace("0", "Zero").replace("1", "One").replace("2", "Two")
                               .replace("3", "Three").replace("4", "Four"), WF_MACRO[wf]), f1(rrl_tab.loc[r, wf]))
    lowr = [r for r in ("R0", "R1") if r in rrl_tab.index]
    highr = [r for r in ("R3", "R4") if r in rrl_tab.index]
    low_mean = macro(allitems[allitems.RRL.isin(lowr)], "Credit")
    high_mean = macro(allitems[allitems.RRL.isin(highr)], "Credit")
    for wf in WF_ORDER:
        mac(macro_name("LowRRL", WF_MACRO[wf]), f1(low_mean[wf]))
        mac(macro_name("HighRRL", WF_MACRO[wf]), f1(high_mean[wf]))
    mac("SpreadLowRRL", f1(low_mean.max() - low_mean.min()))
    mac("SpreadHighRRL", f1(high_mean.max() - high_mean.min()))
    mac("JudgeAUC", f2(auc))
    mac("JudgeAUCN", n_auc // 1)
    mac("JudgeRho", f2(rho))
    mac("JudgeRhoP", fp_tex(rho_p))
    for pv, nm in (("Man", "Man"), ("LLM", "LLM")):
        if pv in prov_acc.index:
            for wf in WF_ORDER:
                mac(macro_name("Prov", nm, WF_MACRO[wf]), f1(prov_acc.loc[pv, wf]))
            mac(f"Prov{nm}N", int(prov_n.get(pv, 0)))
            mac(f"Prov{nm}Chi", f2(prov_chi[pv][0]))
            mac(f"Prov{nm}P", fp_tex(prov_chi[pv][1]))
            mac(f"ProvBest{nm}WF", WF_LABEL[prov_acc.loc[pv].idxmax()])
            mac(f"Prov{nm}NoTOP", fp_tex(prov_chi_noto[pv][1]))
            mac(f"Prov{nm}TOItems", int(to_prov.get(pv, 0)))
            for wf in WF_ORDER:
                mac(macro_name("Prov", nm, "NoTO", WF_MACRO[wf]), f1(prov_acc_noto.loc[pv, wf]))
    mac("MaxCal", f1(M.S3_Cal.max()))
    mac("MaxPass", f1(M.S2_Pass.max()))
    mac("MeanRelAcc", f1(macro1(steps, "Relationship_Match")))
    rel_acc = macro(steps, "Relationship_Match", "Expected_Relationship")
    for r in REL:
        if r in rel_acc.index:
            mac(macro_name("RelAcc", r.lower()), f1(rel_acc[r]))
    fin = s3[s3.Is_Final == 1]
    mac("DecAccAll", f1(macro1(fin, "Decision_Match")))
    over_reject = ((fin.Extracted_Decision == "REJECT") & (fin.Expected_Decision != "REJECT")).sum()
    mac("NOverReject", int(over_reject))
    mac("NFinals", len(fin))
    insuff = fin[fin.Expected_Decision == "INSUFFICIENT_EVIDENCE"]
    mac("NTimeoutAll", int(sum(M.NTimeout)))
    for wf in WF_ORDER:
        mac(macro_name("Timeout", WF_MACRO[wf]), f1(M.loc[wf, "Timeout"]))
        mac(macro_name("NTimeout", WF_MACRO[wf]), int(M.loc[wf, "NTimeout"]))
    mac("FailRate", f1(100 * pd.concat([s1, s2, s3]).Error.notna().mean()))
    # sensitivity: drop every item on which any workflow timed out (keeps pairing)
    to_items = allitems.loc[allitems.Timeout == 1, ["Dataset_ID", "Item"]].drop_duplicates()
    keyset = set(map(tuple, to_items.to_numpy()))
    keep_mask = ~allitems[["Dataset_ID", "Item"]].apply(tuple, axis=1).isin(keyset)
    no_to = allitems[keep_mask]
    mac("NNoTimeoutItems", len(no_to) // 4)
    mac("NTimeoutItems", len(keyset))
    chi, p = friedman(wide(no_to, "Credit"))
    mac("FriedmanNoTOChi", f2(chi))
    mac("FriedmanNoTOP", fp_tex(p))
    acc_no = macro(no_to, "Credit")
    for wf in WF_ORDER:
        mac(macro_name("AccNoTO", WF_MACRO[wf]), f1(acc_no[wf]))
    pw_no = pairwise(no_to, n_boot=max(500, args.boot // 2))
    rr = pw_no[(pw_no.A == "Nova Deep Thinking") & (pw_no.B == "Nova Auto")].iloc[0]
    mac("PairAutoDeepNoTODiff", f"{rr['diff']:+.1f}")
    mac("PairAutoDeepNoTOP", fp_tex(rr.p_holm))
    s1_no = s1[~s1[["Dataset_ID", "Item"]].apply(tuple, axis=1).isin(keyset)]
    a1 = macro(s1_no, "Credit")
    for wf in WF_ORDER:
        mac(macro_name("SOneAccNoTO", WF_MACRO[wf]), f1(a1[wf]))
    chi, p = friedman(wide(s1_no, "Credit"))
    mac("FriedmanSOneNoTOP", fp_tex(p))
    tn = s2["Turn_Number"].astype(int)
    mac("EarlyTurnAcc", f1(macro1(s2.loc[tn <= 3], "Credit")))
    mac("LateTurnAcc", f1(macro1(s2.loc[tn >= 10], "Credit")))
    hu = M.Unclear.idxmax()
    mac("HighestUnclearWF", WF_LABEL[hu])
    mac("HighestUnclear", f1(M.Unclear.max()))
    mac("MaxOtherUnclear", f1(M.Unclear.drop(hu).max()))
    mac("LowestDeclWF", WF_LABEL[M.S3_Decl.idxmin()])
    mac("LowestDecl", f1(M.S3_Decl.min()))
    mac("MinSTwoAcc", f1(M.S2_Acc.min()))
    mac("MaxSTwoAcc", f1(M.S2_Acc.max()))
    mac("MinSOneAcc", f1(M.S1_Acc.min()))
    mac("MaxSOneAcc", f1(M.S1_Acc.max()))
    mac("MinState", f1(M.S3_State.min()))
    mac("MaxState", f1(M.S3_State.max()))
    mac("MinDec", f1(M.S3_Dec.min()))
    mac("MaxDec", f1(M.S3_Dec.max()))
    mac("MaxRev", f1(M.S2_Rev.max()))
    mac("MinUnclear", f1(M.Unclear.min()))
    mac("MaxUnclear", f1(M.Unclear.max()))
    mac("MinCons", f1(M.S2_Cons.min()))
    mac("MaxCons", f1(M.S2_Cons.max()))
    mac("MinTool", f1(M.Tool.min()))
    mac("MaxTool", f1(M.Tool.max()))
    pred = fin.Extracted_Decision.value_counts()
    mac("NPredInsuff", int(pred.get("INSUFFICIENT_EVIDENCE", 0)))
    mac("NRefInsuff", int((fin.Expected_Decision == "INSUFFICIENT_EVIDENCE").sum()))
    mac("NPredReject", int(pred.get("REJECT", 0)))
    mac("NRefReject", int((fin.Expected_Decision == "REJECT").sum()))
    nrr = (fin.Expected_Decision == "REJECT").sum()
    mac("RejectRatio", f"{pred.get('REJECT', 0) / nrr:.1f}" if nrr else "--")
    mac("InsuffAcc", f1(macro1(insuff, "Decision_Match")) if len(insuff) else "--")
    with open(os.path.join(args.generated, "results_macros.tex"), "w") as fh:
        fh.write("\n".join(L) + "\n")

    # ---- results tables: four short tables (overall, single-turn,
    # interactive, hypothesis), metrics as rows and workflows as columns.
    def cells(key, fmt=f1, best="max", ci=None):
        vals = M[key]
        tgt = vals.max() if best == "max" else vals.min() if best == "min" else None
        if vals.round(6).nunique() <= 1:
            tgt = None  # all tied: no best workflow to mark
        out = []
        for wf in WF_ORDER:
            c = fmt(vals[wf])
            if tgt is not None and not pd.isna(vals[wf]) and abs(vals[wf] - tgt) < 1e-9:
                c = r"\textbf{" + c + "}"
            out.append(c)
        return out

    def ci_row(key):
        return (r"\quad {\scriptsize 95\% CI}",
                [r"{\scriptsize " + f"{f1(CI[key].loc[wf, 'lo'])}--{f1(CI[key].loc[wf, 'hi'])}" + "}"
                 for wf in WF_ORDER])

    def write_table(name, rows):
        hdr = " & ".join(r"\textbf{" + WF_SHORT[w] + "}" for w in WF_ORDER)
        T = [r"\setlength{\tabcolsep}{7pt}", r"\begin{tabular}{@{}lcccc@{}}", r"\toprule",
             r"\textbf{Metric} & " + hdr + r" \\", r"\midrule"]
        for label, vals in rows:
            T.append(label + " & " + " & ".join(vals) + r" \\")
        T += [r"\bottomrule", r"\end{tabular}"]
        with open(os.path.join(args.generated, name), "w") as fh:
            fh.write("% Auto-generated by scripts/nova_results.py\n" + "\n".join(T) + "\n")

    cost = lambda x: f"{x:.3f}"  # noqa: E731
    write_table("tab_overall.tex", [
        (r"Suite score (\%)", cells("Suite")), ci_row("Suite"),
        (r"Judge overall score (0--10)", cells("Judge", f2)),
        (r"Hallucination rate (\%)", cells("Hall", best="min")),
        (r"Expected tool category used (\%)", cells("Tool")),
        (r"Tool calls per answer", cells("Calls", best=None)),
        (r"Timed-out answers (\%)", cells("Timeout", best="min")),
        (r"Response time (s)", cells("Latency", best="min")),
        (r"Tokens per answer (thousands)", cells("TokensK", best="min"))])
    write_table("tab_single.tex", [
        (r"Accuracy (\%)", cells("S1_Acc")), ci_row("S1_Acc"),
        (r"Strict accuracy (\%)", cells("S1_Strict")),
        (r"Reference score (0--10)", cells("S1_Ref", f2))])
    write_table("tab_interactive.tex", [
        (r"Turn accuracy (\%)", cells("S2_Acc")), ci_row("S2_Acc"),
        (r"Challenge-turn accuracy (\%)", cells("S2_Chal")),
        (r"Consistency (\%)", cells("S2_Cons")),
        (r"Revision when expected (\%)", cells("S2_Rev")),
        (r"Trajectory pass (\%)", cells("S2_Pass"))])
    write_table("tab_hypothesis.tex", [
        (r"Hypothesis score (\%)", cells("S3_Score")), ci_row("S3_Score"),
        (r"Step credit (\%)", cells("S3_Step")),
        (r"Evidence-relation accuracy (\%)", cells("S3_Rel")),
        (r"State-tracking accuracy (\%)", cells("S3_State")),
        (r"Decision accuracy (\%)", cells("S3_Dec")),
        (r"Calibration met (\%)", cells("S3_Cal"))])
    old = os.path.join(args.generated, "tab_main.tex")
    if os.path.exists(old):
        os.remove(old)

    # ---- pairwise table
    pw1 = pairwise(s1, n_boot=args.boot)
    P = [r"\begin{tabular}{@{}l@{\hspace{1.2em}}rcrc@{\hspace{1.6em}}rc@{\hspace{1.6em}}c@{}}", r"\toprule",
         r"& \multicolumn{4}{c}{\textbf{Credit, all settings}} & \multicolumn{2}{c}{\textbf{Credit, single-turn}} & \textbf{Strict} \\",
         r"\cmidrule(lr){2-5}\cmidrule(lr){6-7}\cmidrule(l){8-8}",
         r"\textbf{Comparison} & \textbf{$\Delta$ (pp)} & \textbf{95\% CI} & \textbf{$r_{rb}$} & \textbf{$p_{\mathrm{Holm}}$} & \textbf{$\Delta$ (pp)} & \textbf{$p_{\mathrm{Holm}}$} & \textbf{$p_{\mathrm{Holm}}$} \\",
         r"\midrule"]
    for (_, r), (_, r1), (_, rs) in zip(pw.iterrows(), pw1.iterrows(), pw_strict.iterrows()):
        P.append(f"{WF_SHORT[r.B]} vs.\\ {WF_SHORT[r.A]} & {sgn(r['diff'])} & [{sgn(r.lo)}, {sgn(r.hi)}] & "
                 f"{sgn(r.r, '{:+.2f}')} & {fp(r.p_holm)} & {sgn(r1['diff'])} & {fp(r1.p_holm)} & {fp(rs.p_holm)} \\\\")
    P += [r"\bottomrule", r"\end{tabular}"]
    with open(os.path.join(args.generated, "tab_pairwise.tex"), "w") as fh:
        fh.write("% Auto-generated by scripts/nova_results.py\n" + "\n".join(P) + "\n")
    # pairwise macros (appended)
    def tex_signed(x, fmt="{:+.1f}"):
        return fmt.format(x).replace("-", "$-$")
    with open(os.path.join(args.generated, "results_macros.tex"), "a") as fh:
        for tag, tab in (("", pw), ("SOne", pw1)):
            for _, r in tab.iterrows():
                nm = f"Pair{WF_MACRO[r.B]}{WF_MACRO[r.A]}{tag}"
                fh.write(f"\\newcommand{{\\{nm}Diff}}{{{tex_signed(r['diff'])}}}\n")
                fh.write(f"\\newcommand{{\\{nm}Lo}}{{{tex_signed(r.lo)}}}\n")
                fh.write(f"\\newcommand{{\\{nm}Hi}}{{{tex_signed(r.hi)}}}\n")
                fh.write(f"\\newcommand{{\\{nm}P}}{{{fp_tex(r.p_holm)}}}\n")
                fh.write(f"\\newcommand{{\\{nm}R}}{{{tex_signed(r.r, '{:+.2f}')}}}\n")
        best1 = pw1.loc[pw1.p_holm.idxmin()]
        fh.write(f"\\newcommand{{\\NSigPairsSOne}}{{{int((pw1.p_holm < 0.05).sum())}}}\n")
        fh.write(f"\\newcommand{{\\MinPairPSOne}}{{{fp_tex(best1.p_holm)}}}\n")
        fh.write(f"\\newcommand{{\\MinPairSOne}}{{{WF_LABEL[best1.B]} vs.\\ {WF_LABEL[best1.A]}}}\n")
        fh.write(f"\\newcommand{{\\MinPairSOneDiff}}{{{tex_signed(best1['diff'])}}}\n")
        bigp = pw.loc[pw['diff'].abs().idxmax()]
        fh.write(f"\\newcommand{{\\MaxPairAll}}{{{WF_LABEL[bigp.B]} vs.\\ {WF_LABEL[bigp.A]}}}\n")
        fh.write(f"\\newcommand{{\\MaxPairAllDiff}}{{{tex_signed(bigp['diff'])}}}\n")
        fh.write(f"\\newcommand{{\\MaxPairAllLo}}{{{tex_signed(bigp.lo)}}}\n")
        fh.write(f"\\newcommand{{\\MaxPairAllHi}}{{{tex_signed(bigp.hi)}}}\n")
        fh.write(f"\\newcommand{{\\MaxPairAllP}}{{{fp_tex(bigp.p_holm)}}}\n")

    print(M[["S1_Acc", "S2_Acc", "S3_Score", "Suite", "Hall", "Latency", "CostPerAns"]].round(2))
    print(pw[["A", "B", "diff", "lo", "hi", "r", "p_holm"]].round(3))
    print("friedman:", {k: (round(v[0], 2), round(v[1], 4)) for k, v in tests.items()})
    print("mixed:", mm)
    print(f"wrote figures to {args.images} and tables/macros to {args.generated}")


if __name__ == "__main__":
    main()
