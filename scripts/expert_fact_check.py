#!/usr/bin/env python3
"""Expert fact-check (E02): hand-coded issues per response, unblinded by workflow and set against the graders.

Expert E02 returned a fact-check sheet (no scoring grid) for the 10 overlap cases (HV-001 ... HV-022), 40 anonymized
responses. Every bullet of the sheet is one row of data/expert_review/E02_fact_check_coding.csv, coded from the sheet's text
on the blinded labels A-D (ALL = the bullet applies to all four responses). This script expands ALL, joins the
private label-to-workflow mapping, and summarizes issues per workflow, per case, and per issue type, next to the
grades the reference-based grader (Claude Opus 5.5) and the SonicChat judge gave the same responses.

Issue codes. Errors: DATA (value, count, or DE status misreported against the case evidence), FACT (domain knowledge or
terminology), CITE (citation does not support the claim), INCON (self-contradiction or status inconsistent with own
reasoning), CONTEXT (experimental context misread: contrast, unmeasured gene, control), OVER (overstated or unsupported
conclusion). Omissions: MISS_REF (misses a key point of the reference answer), MISS_EXP (misses a point the expert raised
that the reference does not make), OMIT (omits a relevant item of the evidence). Minor: UNVER (specific claim not
verifiable from the case), CITE_FLAG ([PMID: unverified] placeholder), STYLE (garbled text, formatting, wrong-setting
language). Not issues: GOOD, NOTE.

Reads the response key data/expert_review/E02_response_key.csv; writes CSVs and expert_fact_check.xlsx to
data/expert_review/results/, and tab_expert_fact_check.tex to $NOVA_NUMBERS_DIR (a temporary folder if unset). Prints the tables.
Usage: python expert_fact_check.py
"""
import os
import tempfile

import pandas as pd

PAPER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RUN = os.path.join(PAPER, "data", "expert_review")
FACT = RUN                                                  # coded sheet, case comments, public response key
OUT = os.path.join(RUN, "results")
NUMBERS = os.environ.get("NOVA_NUMBERS_DIR") or tempfile.mkdtemp(prefix="nova_numbers_")

EXPERT = "E02"
WORKFLOWS = ["Nova Instant", "Nova Thinking", "Nova Deep Thinking", "Nova Auto"]
ERRORS = ["DATA", "FACT", "CITE", "INCON", "CONTEXT", "OVER"]
OMISSIONS = ["MISS_REF", "MISS_EXP", "OMIT"]
MINOR = ["UNVER", "CITE_FLAG", "STYLE"]
LABELS = {"DATA": "Data value or DE status", "FACT": "Domain knowledge", "CITE": "Citation mismatch",
          "INCON": "Internal inconsistency", "CONTEXT": "Experimental context", "OVER": "Overstated conclusion",
          "MISS_REF": "Missed reference point", "MISS_EXP": "Missed expert point", "OMIT": "Omitted evidence",
          "UNVER": "Unverifiable claim", "CITE_FLAG": "Unverified-citation marker", "STYLE": "Wording or format"}


KEY_COLS = ["Case_ID", "Response_Label", "Workflow", "Setting", "Stratum", "Dataset_ID", "Item_ID", "RRL",
            "Difficulty", "Automated_Verdict", "Automated_Credit", "Automated_Overall", "Judge_Overall",
            "Automated_Hallucination", "Reference_Evidence_Relation", "Automated_Extracted_Relation",
            "Reference_Hypothesis_State", "Automated_Extracted_State"]


def response_key():
    """Label -> workflow and grades. Built from the private mapping when present (and saved as the public key
    fact_check/<EXPERT>_response_key.csv); otherwise read from that key."""
    key = os.path.join(FACT, f"{EXPERT}_response_key.csv")
    mapping = os.path.join(RUN, "private", "blinded_response_mapping.csv")
    if not os.path.exists(mapping):
        return pd.read_csv(key)
    m = pd.read_csv(mapping)
    m = m[m.Expert_ID == EXPERT].rename(columns={"Original_Workflow": "Workflow"})
    man = pd.read_csv(os.path.join(RUN, "validation_sampling_manifest.csv"))
    m = m.merge(man[["Case_ID", "Setting", "Stratum", "Dataset_ID", "Item_ID", "RRL", "Difficulty"]], on="Case_ID")
    m = m[KEY_COLS].sort_values(["Case_ID", "Response_Label"])
    m.to_csv(key, index=False)
    return m


def load():
    code = pd.read_csv(os.path.join(FACT, f"{EXPERT}_fact_check_coding.csv"))
    bad = set(code.Code) - set(ERRORS + OMISSIONS + MINOR + ["GOOD", "NOTE"])
    assert not bad, f"unknown codes: {bad}"
    m = response_key()
    assert len(m) == 40 and set(code.Case_ID) <= set(m.Case_ID)
    # ALL -> one row per response label
    allr = code[code.Response_Label == "ALL"].drop(columns="Response_Label")
    allr = allr.merge(pd.DataFrame({"Response_Label": list("ABCD")}), how="cross")
    code = pd.concat([code[code.Response_Label != "ALL"], allr], ignore_index=True)
    return code.merge(m[["Case_ID", "Response_Label", "Workflow"]], on=["Case_ID", "Response_Label"]), m


def per_response(code, m):
    counts = code.pivot_table(index=["Case_ID", "Response_Label"], columns="Code", aggfunc="size", fill_value=0)
    counts = counts.reindex(columns=ERRORS + OMISSIONS + MINOR + ["GOOD"], fill_value=0)
    r = m.set_index(["Case_ID", "Response_Label"]).join(counts).fillna({c: 0 for c in counts.columns}).reset_index()
    r["Errors"] = r[ERRORS].sum(axis=1)
    r["Any_Error"] = (r.Errors > 0).astype(int)
    r["Missed_Ref"] = (r.MISS_REF > 0).astype(int)
    r["Any_Error_or_Missed_Ref"] = ((r.Errors > 0) | (r.MISS_REF > 0)).astype(int)
    up = lambda s: s.astype(str).str.upper().where(s.notna())
    r["State_Match"] = (up(r.Automated_Extracted_State) == up(r.Reference_Hypothesis_State)).where(
        r.Reference_Hypothesis_State.notna()).astype(float)
    r["Relation_Match"] = (up(r.Automated_Extracted_Relation) == up(r.Reference_Evidence_Relation)).where(
        r.Reference_Evidence_Relation.notna()).astype(float)
    keep = ["Case_ID", "Response_Label", "Workflow", "Setting", "Stratum", "Dataset_ID", "Item_ID", "RRL",
            "Automated_Verdict", "Automated_Credit", "Automated_Overall", "Judge_Overall", "Automated_Hallucination",
            "Reference_Evidence_Relation", "Automated_Extracted_Relation", "Reference_Hypothesis_State",
            "Automated_Extracted_State", "Relation_Match", "State_Match", "Errors", "Any_Error", "Missed_Ref",
            "Any_Error_or_Missed_Ref"] + ERRORS + OMISSIONS + MINOR + ["GOOD"]
    return r[keep].sort_values(["Case_ID", "Response_Label"])


def summary(r, by):
    g = r.groupby(by)
    s = pd.DataFrame({
        "Responses": g.size(),
        "With_Error": g.Any_Error.sum(),
        "Errors": g.Errors.sum(),
        "Errors_per_Response": g.Errors.mean().round(2),
        "Missed_Ref_Point": g.Missed_Ref.sum(),
        "With_Error_or_Missed_Ref": g.Any_Error_or_Missed_Ref.sum(),
        "Unverifiable_Claims": g.UNVER.sum(),
        "Credit_Reference_Grader": g.Automated_Credit.mean().round(2),
        "Overall_Reference_Grader": g.Automated_Overall.mean().round(2),
        "Overall_SonicChat": g.Judge_Overall.mean().round(2),
        "Unsupported_Claims_SonicChat": g.Automated_Hallucination.mean().round(1),
        "State_Match_S3": g.State_Match.sum().astype(int).astype(str) + "/" + g.State_Match.count().astype(str),
        "Relation_Match_S3": g.Relation_Match.sum().astype(int).astype(str) + "/" + g.Relation_Match.count().astype(str),
    })
    for c in ERRORS:
        s[c] = g[c].sum()
    return s


def latex(w, tot):
    rows = []
    for name, x in list(w.iterrows()) + [("All", tot)]:
        label = name.replace("Nova ", "Nova-") if name != "All" else "All"
        rows.append(f"{label} & {x.With_Error}/{x.Responses} & {x.Errors_per_Response:.1f} & "
                    f"{x.Missed_Ref_Point}/{x.Responses} & {x.State_Match_S3} & {x.Credit_Reference_Grader:.2f} & "
                    f"{x.Overall_SonicChat:.1f} \\\\")
    return "\n".join(rows) + "\n"


def main():
    code, m = load()
    r = per_response(code, m)
    w = summary(r, "Workflow").reindex(WORKFLOWS)
    tot = summary(r.assign(All="All"), "All").iloc[0]
    case = summary(r, "Case_ID")
    cc = pd.read_csv(os.path.join(FACT, f"{EXPERT}_case_comments.csv")).set_index("Case_ID")
    case = case.join(cc[["Comment_Type", "Comment"]])
    setting = summary(r, "Setting")
    types = pd.DataFrame({"Issue": [LABELS[c] for c in ERRORS + OMISSIONS + MINOR],
                          "Mentions": [int(r[c].sum()) for c in ERRORS + OMISSIONS + MINOR],
                          "Responses": [int((r[c] > 0).sum()) for c in ERRORS + OMISSIONS + MINOR]},
                         index=ERRORS + OMISSIONS + MINOR)

    os.makedirs(OUT, exist_ok=True)
    r.to_csv(os.path.join(OUT, "fact_check_responses.csv"), index=False)
    w.to_csv(os.path.join(OUT, "fact_check_by_workflow.csv"))
    case.to_csv(os.path.join(OUT, "fact_check_by_case.csv"))
    setting.to_csv(os.path.join(OUT, "fact_check_by_setting.csv"))
    types.to_csv(os.path.join(OUT, "fact_check_issue_types.csv"))
    with pd.ExcelWriter(os.path.join(OUT, "expert_fact_check.xlsx")) as x:
        pd.concat([w, tot.to_frame("All").T]).to_excel(x, sheet_name="By workflow")
        setting.to_excel(x, sheet_name="By setting")
        case.to_excel(x, sheet_name="By case")
        types.to_excel(x, sheet_name="Issue types")
        r.to_excel(x, sheet_name="Responses", index=False)
        code.sort_values(["Case_ID", "Response_Label"]).to_excel(x, sheet_name="Coded bullets", index=False)
    os.makedirs(NUMBERS, exist_ok=True)
    with open(os.path.join(NUMBERS, "tab_expert_fact_check.tex"), "w") as f:
        f.write(latex(w, tot))

    pd.set_option("display.width", 250, "display.max_columns", 40)
    cols = ["Responses", "With_Error", "Errors_per_Response", "Missed_Ref_Point", "With_Error_or_Missed_Ref",
            "Unverifiable_Claims", "State_Match_S3", "Relation_Match_S3", "Credit_Reference_Grader",
            "Overall_Reference_Grader", "Overall_SonicChat"]
    print(f"Expert {EXPERT}: {len(r)} responses in {r.Case_ID.nunique()} cases; "
          f"reference-grader verdicts: {r.Automated_Verdict.value_counts().to_dict()}")
    print("\nBy workflow\n", pd.concat([w, tot.to_frame("All").T])[cols + ERRORS].to_string())
    print("\nBy setting\n", setting[cols].to_string())
    print("\nBy case\n", case[["With_Error", "Errors", "Missed_Ref_Point", "Comment_Type"]].to_string())
    print("\nIssue types\n", types.to_string())
    print(f"\nwrote {OUT} and {os.path.join(NUMBERS, 'tab_expert_fact_check.tex')}")


if __name__ == "__main__":
    main()
