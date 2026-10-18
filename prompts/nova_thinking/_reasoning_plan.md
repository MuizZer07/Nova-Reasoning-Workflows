

## Multi-hop reasoning — Stage 1 (planning only)

Do not answer yet. Write a short internal evidence plan that a gathering step will execute.

1. Answer type — one of: single fact · comparison · mechanism/interpretation · claim or hypothesis evaluation · summary of the conversation so far.
2. Sub-questions — the minimum set that fully answers the request (a narrow question is ONE sub-question). For each:
   - the exact entities to look up DIRECTLY by name (every gene, term, pathway, regulator, miRNA, disease the user mentions or the answer depends on);
   - the evidence layer that actually measures it (gene-level DE vs thresholds · upstream-regulator activity with consistent/inconsistent target counts · pathway ORA vs perturbation · GO term FDR · miRNA target enrichment · disease ORA · the study's own publication for what the authors showed experimentally · literature search only for OTHER studies);
   - the exact values the answer will need (effect sizes, FDRs, z-scores, counts with denominators, ranks).
3. Counter-evidence — for any claim or interpretation being evaluated, add a sub-question that looks specifically for evidence that limits or contradicts it (inconsistent targets, non-significant members, opposite-direction genes, untested links).
4. Reuse — note values already established earlier in this conversation that do not need re-querying.
5. Calibration note — what level of evidence each part of the answer can reach (directly measured · inferred from transcripts · shown by the publication · untested).

Keep the plan compact (bullets, no prose). Do not call tools. Do not write a user-facing answer.
