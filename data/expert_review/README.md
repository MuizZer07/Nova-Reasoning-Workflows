# Expert fact-check

A domain expert (E02) fact-checked 10 benchmark cases and the four Nova workflows' answers to each (40 answers),
blinded to which workflow wrote which answer. The cases are the clearest and most informative items with
high-scoring answers: 3 independent questions, 2 conversation turns, and 5 hypothesis steps, from all six
datasets. Answers were shuffled per case and labelled A-D, and names of systems and models were removed. The
expert returned written notes per case and per answer rather than numerical scores.

| File | Content |
|---|---|
| `E02_fact_check_notes.md` | The expert's notes, verbatim |
| `E02_fact_check_coding.csv` | Every note coded into one issue type (one row per note; `ALL` = applies to all four answers) |
| `E02_case_comments.csv` | The expert's comment on each question and reference answer |
| `E02_response_key.csv` | Case and label to benchmark item and workflow, with the grades of the reference-based grader (`Automated_*`) and the SonicChat judge (`Judge_Overall`; `Automated_Hallucination` = unsupported claims) |
| `reference_contradicts_audit.csv`, `reference_qualifies_audit.csv` | Audit of what each CONTRADICTS (61) and QUALIFIES (127) reference relation rests on |
| `results/` | Tables written by `scripts/expert_fact_check.py` |

## Issue codes

| Code | Meaning |
|---|---|
| `DATA` | A value, count, or DE status misreported against the case evidence |
| `FACT` | An error of domain knowledge or terminology |
| `CITE` | A citation that does not support the claim it is cited for |
| `INCON` | A self-contradiction, or a declared status inconsistent with the answer's own reasoning |
| `CONTEXT` | The experimental context misread (contrast, unmeasured gene, control) |
| `OVER` | An overstated or unsupported conclusion |
| `MISS_REF` | Misses a key point of the reference answer |
| `MISS_EXP` | Misses a point the expert raised that the reference answer does not make |
| `OMIT` | Omits a relevant item of the evidence |
| `UNVER` | A specific claim the expert could not verify from the case |
| `CITE_FLAG` | A `[PMID: unverified]` placeholder |
| `STYLE` | Garbled text, formatting, or language of the wrong setting |
| `GOOD`, `NOTE` | A strength or an observation (not an issue) |

`DATA` to `OVER` are counted as errors. Each note was coded from its text alone, on the blinded labels.

## Reference-relation audit

Each CONTRADICTS and QUALIFIES hypothesis step was classified by what its reference evidence rests on (`basis`:
significant results, a publication statement, only non-significant evidence, mixed, or a synthesis of earlier
steps) and, for non-significant evidence, by its direction relative to the hypothesis's prediction. `rule_consistent`
records whether the label follows the rule that a predicted change that is absent or reversed contradicts, whereas
a change in the predicted direction that misses significance qualifies. `scripts/reference_relation_audit.py` prints
the counts and repeats the mixed-evidence numbers with the steps that do not fit the rule removed.

```bash
.venv/bin/python scripts/expert_fact_check.py
.venv/bin/python scripts/reference_relation_audit.py
```
