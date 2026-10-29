#!/usr/bin/env python3
"""Audit of the reference evidence relations (S3): what CONTRADICTS and QUALIFIES labels rest on.

Prompted by expert E02 (case HV-015): a CONTRADICTS reference resting only on non-significant trends, against a
QUALIFIES reference (HV-016) resting on a non-significant change. Each hypothesis step was classified by hand from
its Reference_Evidence, Expected_Reasoning, and Contradictory_or_Limiting_Evidence (data/expert_review/reference_*_audit.csv):

  basis             SIG (key evidence includes significant results), PUB (a publication statement or experiment),
                    NONSIG (only non-significant, flat, or unmeasured evidence), MIXED (significant evidence limited by
                    non-significant or missing evidence), SYNTH (integrates earlier steps, no new data)
  nonsig_direction  for NONSIG: PREDICTED (trend in the direction the hypothesis predicts), FLAT_OR_ABSENT,
                    OPPOSITE (trend against the prediction)
  rule_consistent   against the rule "a predicted change that is absent or reversed contradicts; a change in the
                    predicted direction that misses significance qualifies"

Prints the counts and the steps that do not fit the rule, then repeats the mixed-evidence numbers of the RQ3 text
(mixed_evidence.py) for the two main runs with those steps removed; writes nothing.
Usage: python reference_relation_audit.py
"""
import glob
import os

import pandas as pd

import gpt_comparison as gc          # imported first: registers the GPT-6 workflows with nova_results.load
import mixed_evidence as me
import nova_results as nr

PAPER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RES = os.path.join(PAPER, "data", "results")
AUDIT = os.path.join(PAPER, "data", "expert_review")
S3 = os.path.join(PAPER, "data", "benchmark", "S3_hypothesis_evaluation.xlsx")


def report(rel, steps):
    path = os.path.join(AUDIT, f"reference_{rel.lower()}_audit.csv")
    if not os.path.exists(path):
        print(f"\n{rel}: no audit file ({os.path.basename(path)})")
        return
    a = pd.read_csv(path).merge(steps[["Step_ID", "Generation_Source", "Hypothesis_State_Before",
                                       "Hypothesis_State_After"]], on="Step_ID", how="left", suffixes=("_a", ""))
    n = (steps.Evidence_Relationship_to_Hypothesis == rel).sum()
    assert len(a) == n and a.Step_ID.is_unique, f"{rel}: {len(a)} audited rows for {n} steps"
    a["Source"] = a.Generation_Source.str.extract(r"^(MANUAL_CURATED|LLM_ASSISTED)", expand=False)
    print(f"\n{rel}: {n} steps")
    print(a.basis.value_counts().to_string())
    ns = a[a.basis == "NONSIG"]
    print(f"resting only on non-significant evidence: {len(ns)}/{n} ({100 * len(ns) / n:.1f}%); by direction:")
    print(ns.nonsig_direction.value_counts().to_string())
    print("by provenance (non-significant / all):",
          {s: f"{(ns.Source == s).sum()}/{(a.Source == s).sum()}" for s in sorted(a.Source.unique())})
    print("rule_consistent:", a.rule_consistent.value_counts().to_dict())
    off = a[a.rule_consistent != "YES"]
    if len(off):
        print(off[["Step_ID", "basis", "nonsig_direction", "rule_consistent", "note"]].to_string(index=False))
    return set(off.Step_ID)


def sensitivity(off):
    c = nr.load(sorted(glob.glob(os.path.join(RES, "nova_run", "*.xlsx"))))[2]
    gp = nr.load(sorted(glob.glob(os.path.join(RES, "gpt6_run", "*.xlsx"))))[2]
    print(f"\nMixed-evidence numbers without the {len(off)} steps that do not fit the rule (as mixed_evidence.py: "
          "contradicts acc. | qualifies acc. | qualifies read as contradicting | wrong states weaker)")
    for name, s3 in (("Nova run", c), ("GPT-6 run", gp[gp.Workflow.isin(gc.GPT)])):
        for label, x in (("all steps", s3), ("rule-consistent", s3[~s3.Step_ID.isin(off)])):
            print(f"  {name:10s} {label:16s}", " | ".join(f"{v:5.1f}" for v in me.row(x)))


def main():
    steps = pd.read_excel(S3, "Hypothesis_Steps")
    print("Reference evidence relations:", steps.Evidence_Relationship_to_Hypothesis.value_counts().to_dict())
    off = set()
    for rel in ("CONTRADICTS", "QUALIFIES"):
        off |= report(rel, steps) or set()
    sensitivity(off)


if __name__ == "__main__":
    main()
