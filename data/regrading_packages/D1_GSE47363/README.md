# Grading package v2 — run 79297d15 (NOVA_D1_GSE47363)

The evaluation harness grades every answer with TWO independent graders. Reproduce them as TWO separate passes, each in its
own NEW chat session, so neither grader ever sees the other's inputs or results:

1. `1_reference_grading/` — PROMPT.md + reference_grading_sheet.xlsx. The reference grader sees the frozen
   reference and produces the verdict, credit and reference-based scores. No data files.
2. `2_sonicchat_judge/` — PROMPT.md + judge_sheet.xlsx + data/. The SonicChat judge does NOT see the reference;
   it checks each answer against the experiment's data (and literature) and produces its own scores and a
   hallucination estimate. Never give this session pass 1's sheet or results.

Return both completed sheets together; they are merged by Row_ID.
Rows: 688 (1 failed answers are not graded).
