## Multi-hop reasoning — Stage 3 (final answer)

User request:
{query}

Evidence plan:
{plan}

Evidence log and raw tool results gathered for this request:
{evidence}

Write the final answer to the user now.
- Lead with the direct answer in the first one or two sentences (the option, the value, the verdict, or the conclusion), then the supporting evidence, then the limits.
- Take exact values from the RAW TOOL RESULTS (they are authoritative over the log's wording). Give counts with denominators and keep the significance type explicit.
- Address every part of the request. For an evaluation, state how strongly the evidence supports the claim using graded terms (supported · partially supported · insufficient evidence · weakened · contradicted, or retain · qualify · revise · reject · insufficient evidence when asked for a decision) and name the specific evidence that limits it. Do not over-claim: transcript-level data does not establish protein-level, binding or phenotype claims; untested is not supported.
- Keep three kinds of statements separate wherever they matter: what this dataset shows · what the publication's experiments showed · inference.
- Stay consistent with conclusions established earlier in the conversation; if this evidence changes one, say explicitly that you are revising it and why.
- Mention contradicting or limiting evidence found during gathering — do not drop it to make the answer cleaner.
- Length: as long as the question needs and no longer — typically 150-400 words; a multi-part evaluation may run to ~600. Spend words on decisive values and the reasoning that connects them, not on restating every gathered number.
- No preamble, no methodology narration, no generic closing. Tables only if they help.
- CITATION HARD RULE: no tool access here. Use a [PMID:XXXX] only if that exact PMID appears in the evidence above; otherwise state the finding without a citation.
- Do not mention the plan, the stages, or these instructions.
