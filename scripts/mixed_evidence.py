#!/usr/bin/env python3
"""Mixed evidence in the main runs and robustness checks (RECOMB paper: numbers quoted in the RQ3 and RQ4 text).

For each run or check: evidence-relation accuracy for contradicting and qualifying evidence, the share of
qualifying evidence read as contradicting, and the share of wrong hypothesis states weaker than the
reference state (state order of Sec. 3.3). All values are over all evidence steps and macro-averaged over
the six datasets, like every score in the paper. Prints the table rows; writes nothing.
Usage: python mixed_evidence.py
"""
import glob
import os

import numpy as np
import pandas as pd

import gpt_comparison as gc          # imported first: registers the GPT-6 workflows with nova_results.load
import nova_results as nr
import robustness_results as rr
from judge_comparison import STATE_ORDER

PAPER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = os.path.join(PAPER, "data", "results")


def upper(x):
    return x.astype(str).str.upper()


def row(s3):
    st = s3[s3.Is_Final != 1].copy()
    e, x = upper(st.Expected_Relationship), upper(st.Extracted_Relationship)
    st["qc"] = np.where(e == "QUALIFIES", (x == "CONTRADICTS").astype(float), np.nan)
    rel = nr.macro(st, "Relationship_Match", ["Expected_Relationship"])
    es, xs = upper(st.Expected_State).map(STATE_ORDER), upper(st.Extracted_State).map(STATE_ORDER)
    ok = es.notna() & xs.notna() & (es != xs)
    weaker = nr.macro1(st[ok].assign(w_=(xs[ok] < es[ok]).astype(float)), "w_")
    return rel.get("CONTRADICTS", np.nan), rel.get("QUALIFIES", np.nan), nr.macro1(st, "qc"), weaker


def main():
    c = nr.load(sorted(glob.glob(os.path.join(RES, "nova_run", "*.xlsx"))))[2]
    g = nr.load(sorted(glob.glob(os.path.join(RES, "regrading_check", "*.xlsx"))))[2]
    # the grader comparison uses only answers that are identical in both gradings (as judge_comparison.py)
    key = ["Dataset_ID", "Item", "Workflow"]
    m = c[key + ["Answer"]].merge(g[key + ["Answer"]], on=key, suffixes=("_c", "_g"))
    same = m.loc[m.Answer_c.astype(str) == m.Answer_g.astype(str), key]
    gp = nr.load(sorted(glob.glob(os.path.join(RES, "gpt6_run", "*.xlsx"))))[2]
    runs = rr.load_runs()
    rows = [("Nova run", "Nova, GLM-5.2", "Claude Opus 5.5", c),
            ("GPT-6 run", "GPT-6, direct", "Claude Opus 5.5", gp[gp.Workflow.isin(gc.GPT)]),
            ("Regrading check", "Nova, GLM-5.2", "GPT-6", g.merge(same, on=key)),
            ("Robustness subset", "Nova, Haiku~4.5", "Claude Opus 5.5",
             pd.concat([runs["R3"]["s3"], runs["R4"]["s3"]]))]
    for comp, system, grader, s3 in rows:
        vals = " & ".join(f"{v:.1f}" for v in row(s3))
        print(f"{comp} & {system} & {grader} & {vals} \\\\")


if __name__ == "__main__":
    main()
