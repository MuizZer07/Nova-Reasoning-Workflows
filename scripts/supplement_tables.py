#!/usr/bin/env python3
"""Supplementary Table S3: paired workflow comparisons on strict accuracy (all items) and on the
reference-based grades of open answers (correctness, completeness, reasoning).

Same definitions as main_patterns.py: differences are macro-averaged over the six datasets; strict
accuracy is tested with exact McNemar tests, the 0-10 grades with Wilcoxon signed-rank tests, and
p-values are Holm-corrected over the six workflow pairs of each measure. Prints LaTeX rows.
Usage: python scripts/supplement_tables.py
"""
import glob
import os
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

import nova_results as nr

PAPER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SHORT = {"Nova Instant": "Instant", "Nova Thinking": "Thinking", "Nova Deep Thinking": "Deep Thinking",
         "Nova Auto": "Auto"}


def paired(df, value, binary=False):
    w = df.pivot_table(index=["Dataset_ID", "Item"], columns="Workflow", values=value)
    w = w.reindex(columns=nr.WF_ORDER).dropna()
    rows = []
    for a, b in combinations(nr.WF_ORDER, 2):
        d = (w[b] - w[a]).to_numpy()
        if binary:
            p = nr.mcnemar_exact(w[a].to_numpy(), w[b].to_numpy())
        else:
            p = stats.wilcoxon(w[b], w[a]).pvalue if np.any(d != 0) else 1.0
        rows.append({"pair": (a, b), "diff": (w[b] - w[a]).groupby(level=0).mean().mean(), "p": p})
    out = pd.DataFrame(rows)
    out["p_holm"] = nr.holm(out.p)
    return out.set_index("pair"), len(w)


def fmt_p(p):
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def main():
    s1, s2, s3, _ = nr.load(sorted(glob.glob(os.path.join(PAPER, "data", "results", "nova_run", "*.xlsx"))))
    allit = pd.concat([s1, s2, s3], ignore_index=True)
    for c in ("Ref_Correctness", "Ref_Completeness", "Ref_Reasoning"):
        allit[c] = pd.to_numeric(allit[c], errors="coerce")
    closed = allit.Match_Method.astype(str).str.startswith("curated_exact")
    opn = allit[~closed]
    res = {"strict": paired(allit, "Strict", binary=True)}
    for k, c in (("corr", "Ref_Correctness"), ("compl", "Ref_Completeness"), ("reas", "Ref_Reasoning")):
        res[k] = paired(opn.dropna(subset=[c]), c)
    print("% n: strict", res["strict"][1], "| open answers", res["corr"][1])
    for a, b in combinations(nr.WF_ORDER, 2):
        cells = [f"{SHORT[b]} vs.\\ {SHORT[a]}"]
        r = res["strict"][0].loc[[(a, b)]].iloc[0]
        cells += [f"{100 * r['diff']:+.1f}".replace("-", "$-$"), fmt_p(r.p_holm)]
        for k in ("corr", "compl", "reas"):
            r = res[k][0].loc[[(a, b)]].iloc[0]
            cells += [f"{r['diff']:+.2f}".replace("-", "$-$"), fmt_p(r.p_holm)]
        print(" & ".join(cells) + " \\\\")


if __name__ == "__main__":
    main()
