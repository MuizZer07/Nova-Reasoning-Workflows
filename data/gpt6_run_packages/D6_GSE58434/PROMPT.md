# Nova benchmark — external evaluation (NOVA_D6_GSE58434)

You are being evaluated as a bioinformatics analysis assistant. You have the raw results of one
differential-expression experiment analysed with iPathwayGuide, and a sheet of questions about it.
Answer every question **from the attached data** — exactly as an analyst with these result tables would.

## The experiment
- Dataset: **NOVA_D6_GSE58434**
- Comparison: **Condition** vs **Control** (log fold changes are Condition relative to Control)
- **DE definition: adjusted p-value < 0.05 and |logFC| > 0.6** — use it whenever a question asks whether a gene is DE.

## Attached files
- `NOVA_D6_GSE58434_questions_full.xlsx` — the questions. Fill in the **Answer** column.
- `gene_analyses.tsv` — Differential expression results for every assayed gene: logfc (log2 fold change), adjpv (adjusted p-value), entrez, symbol.
- `go_analyses_BP.tsv` — Gene Ontology Biological Process enrichment: goName, countDE, countAll, pv, pv_fdr, pv_bonferroni, pv_elim, pv_weight.
- `go_analyses_MF.tsv` — Gene Ontology Molecular Function enrichment (same columns as BP).
- `go_analyses_CC.tsv` — Gene Ontology Cellular Component enrichment (same columns as BP).
- `pathway_analyses.tsv` — KEGG pathway analysis: pName, pAcc (perturbation), pORA (over-representation), pComb (combined), each with FDR / Bonferroni corrections.
- `upstream_gene.tsv` — Predicted upstream regulator genes: zscore, cDE, cDE_p / cDE_n (DE targets consistent with activation / inhibition), pv, pv_fdr, pv_zscore and corrections, plus the regulator's own logfc / adjpv.
- `mirna_analyses.tsv` — Predicted upstream miRNAs: cDE / cAll targets, cDE_p / cDE_n (up / down targets), pv / pv_fdr (all DE targets), pvn / pvn_fdr (down-regulated targets).
- `upstream_chemical_positive.tsv` — Predicted upstream chemicals / drugs whose effect matches the observed changes.
- `upstream_chemical_negative.tsv` — Predicted upstream chemicals / drugs whose effect opposes the observed changes.
- `disease_analyses.tsv` — Disease associations: diseaseName, countDE, countAll, pv, pv_fdr, pv_bonferroni.
- `enrichment_collection_29.tsv` — Gene-set enrichment against MSigDB Hallmark gene sets: gene_set_name, countAll, countDE (DE genes in the set), pv, pv_fdr, pv_bonferroni.
- `enrichment_collection_30.tsv` — Gene-set enrichment against MSigDB oncogenic signatures: gene_set_name, countAll, countDE (DE genes in the set), pv, pv_fdr, pv_bonferroni.
- `enrichment_collection_31.tsv` — Gene-set enrichment against MSigDB immunologic signatures: gene_set_name, countAll, countDE (DE genes in the set), pv, pv_fdr, pv_bonferroni.
- `enrichment_collection_32.tsv` — Gene-set enrichment against cell-type signature gene sets: gene_set_name, countAll, countDE (DE genes in the set), pv, pv_fdr, pv_bonferroni.
- `enrichment_collection_70.tsv` — Gene-set enrichment against organ / tissue signatures: gene_set_name, countAll, countDE (DE genes in the set), pv, pv_fdr, pv_bonferroni.
- `enrichment_collection_76.tsv` — Gene-set enrichment against toxicity signatures: gene_set_name, countAll, countDE (DE genes in the set), pv, pv_fdr, pv_bonferroni.

These are the raw analysis results only — no summaries or interpretation. Work everything else out yourself.

## How to answer
1. **Use the data.** Look up every gene, pathway, GO term, regulator, miRNA or disease by name in the tables and
   quote the exact values (logFC, adjusted p-value, counts, z-scores). Never assume something is absent because it is
   not in a top-N list — search the full table. If the data cannot answer a question, say so plainly.
2. **Sheet `S1_Questions`** — 66 independent questions. Answer each one on its own; do not use the other
   questions as hints. Multiple-choice and true/false answers must **start with `Answer: <letter>`** (or
   `Answer: TRUE` / `Answer: FALSE`), followed by a short justification with the decisive values.
3. **Sheet `S2_Conversations`** — 50 turns grouped by `Trajectory_ID`. Each trajectory is ONE conversation:
   answer its turns in `Turn_Number` order, treating your own earlier answers in that trajectory as what you have
   already said. Stay consistent with them unless the new evidence requires a correction — then say what changed.
   Do not read ahead to later turns before answering an earlier one.
4. **Sheet `S3_Hypotheses`** — 55 steps grouped by `Hypothesis_ID`. Each hypothesis is ONE conversation,
   steps in `Step_Number` order, the final decision (`Is_Final` = TRUE) last. Every step's question states the
   status line(s) it needs — end each answer with them **exactly** as asked (e.g. `Hypothesis status: <STATE>`, and
   for the final step also `Decision: <DECISION>`), using only the allowed values listed in the question.
5. Keep answers focused: lead with the answer, then the evidence. No generic background.
6. Do **not** search the web for this benchmark, its questions or its answers.

## What to return
**Preferred:** return the same Excel workbook (`NOVA_D6_GSE58434_questions_full.xlsx`) with every **Answer** cell filled, and in the
`Run_Info` sheet fill `Model` and `Provider` (and anything else you know). Leave the ID and question columns unchanged.
If you track them, also fill `Input_Tokens`, `Output_Tokens`, `Total_Tokens`, `Response_Time_s`.

**If you cannot produce an Excel file**, return ONE JSON code block in exactly this shape instead (every ID from the
sheet, answers as plain text):

```json
{
  "model": "<your model name>",
  "provider": "<your provider>",
  "answers": {
    "<Question_ID / Turn_ID / Step_ID>": "<full answer text>"
  }
}
```

Both formats are graded against the reference annotations with the same pipeline used for the Nova workflows. You will not be shown the references.
