## Deep reasoning — Stage 5 (final answer)

User request:
{query}

Internal response plan:
{plan}

Sub-agent evidence (each sub-agent's role, status and findings):
{digest}

Write the final answer to the user now.
- Lead with the direct answer in the first one or two sentences, then the evidence for each required output, then the limits.
- Use the exact values the sub-agents reported (counts with denominators, significance type explicit). Where sub-agents disagree, reconcile explicitly from the evidence or state the discrepancy.
- For an evaluation, grade support honestly (supported · partially supported · insufficient evidence · weakened · contradicted, or retain · qualify · revise · reject · insufficient evidence when a decision is asked) and name the evidence that limits it. Transcript-level data does not establish protein-level, binding or phenotype claims; untested is not supported.
- Keep separate, where it matters: what this dataset shows · what the publication's experiments showed · inference. Report contradicting or limiting evidence the sub-agents found.
- Stay consistent with conclusions established earlier in the conversation; if this evidence changes one, say so explicitly.
- If a sub-agent failed, answer from what succeeded and say plainly which part could not be completed — never fill it in.
- Length: as long as the question needs and no longer — typically 150-400 words; a multi-part evaluation may run to ~600. Spend words on decisive values and the reasoning that connects them, not on restating every gathered number.
- No preamble, no description of the plan or sub-agents, no generic closing.
- CITATION HARD RULE: no tool access here; use a [PMID:XXXX] only if it appears verbatim in the evidence above.
