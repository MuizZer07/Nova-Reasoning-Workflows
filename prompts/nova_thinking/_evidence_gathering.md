

## Multi-hop reasoning — Stage 2 (evidence gathering)

Execute this evidence plan with your tools:

{plan}

Rules for this stage:
- Look up every named entity directly (entity-level tools) — never conclude something is absent, unchanged or non-significant from a ranked top-N list; query it and record its actual values.
- Record EXACT values with their denominators (e.g. "48 of 55 DE targets activation-consistent, 10 inhibition-consistent, z = 4.82, FDR 1.4e-13"). Keep the significance type explicit (ORA vs perturbation, FDR vs nominal p).
- Gather the counter-evidence items the plan lists, and report what you found even when it weakens the expected answer.
- Use the publication tools for what the study's authors showed; literature search only for other studies.
- Do not re-query values already established earlier in this conversation unless they need checking.

Output an EVIDENCE LOG, not the final answer: grouped by sub-question, one bullet per finding with its exact values and its source layer, followed by a short "limits / contradictions" list. A later stage writes the final answer from your log and the raw tool results.
