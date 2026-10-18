# SonicChatBench grading — PASS 1 of 2: REFERENCE GRADER (NOVA_D3_GSE150316, run e03aed10, package v2)

You are ONLY the **reference grader**. You judge each answer against its FROZEN expert reference (the row's
`Reference_Material`) — not against your own knowledge, not against any data, not on style. You do not see,
and must not look for, the experiment's data files: the reference is the ground truth for this pass.
(The SonicChat judge is a separate pass, in a separate session, by design — do not do its job here.)

Grade every row on its own: as if it were the only answer you had seen. Do not compare answers, do not calibrate
against other rows or series, and do not let an earlier row influence a later one. Never change an input column.

Rows: 591 `reference`, 96 exact-answer (`exact_mcq` / `exact_true_false`),
1 `not_graded` (failed / empty answers — leave blank).

## File
`reference_grading_sheet.xlsx`, sheet `Grading`. Inputs (never change): Row_ID, Series_ID, Series_Name, Dataset_ID, Setting, Item_ID, Grading_Mode, Grading_Setting, Question, Answer, Reference_Material, Options.
Fill: Extracted_Answer, Verdict, Ref_Correctness, Ref_Completeness, Ref_Reasoning, Key_Points_Missed, Factual_Errors, Consistency_OK, Revision_OK, Relationship, Hypothesis_State, Decision, Calibration_OK, Answer_Summary, Basis. Sheet `Run_Info`: fill `Grader_Model`, `Grader_Provider`, `Grading_Date`.

## `reference` rows — Appendix A
System prompt: Appendix A, verbatim. User message, assembled exactly:
```
GRADING TASK

SETTING: <label for Grading_Setting>

QUESTION ASKED:
<Question>

<Reference_Material>

MODEL'S ANSWER:
<Answer>

Grade the model's answer now.
```
Setting labels: {"s1": "Setting 1 — single-turn question (no conversation context)", "s2": "Setting 2 — one turn of a scripted multi-turn conversation", "s3_step": "Setting 3 — one evidence step while evaluating a hypothesis", "s3_final": "Setting 3 — final assessment of a hypothesis"}
From its JSON fill Verdict, Ref_Correctness, Ref_Completeness, Ref_Reasoning (0-10, consistent with the verdict's band),
Key_Points_Missed and Factual_Errors (up to 4 each, separated by " | "), Consistency_OK, Revision_OK, Calibration_OK
(TRUE / FALSE, blank for null), Relationship, Hypothesis_State, Decision (exact vocabulary, blank for null),
Answer_Summary, Basis.

## `exact_mcq` / `exact_true_false` rows — Appendix B
Fill Appendix B's placeholders with Question, ANSWER_TYPE (`mcq` / `true_false`), Options (mcq) and Answer. Put its
`extracted_answer` (option letter, True / False, or `unclear`) in **Extracted_Answer** and leave the other columns blank —
the harness compares it with the correct answer itself (you are not given the correct answers).

## The harness computes these itself — don't
Overall = mean of the three dimensions; credit from the verdict; exact-answer verdicts; a "Hypothesis status:" /
"Decision:" line written in the answer overrides your Hypothesis_State / Decision; all aggregation.

## Return
The same workbook with the output columns filled. (No file possible? One JSON block:
`{"pass": "reference", "source_run_id": "e03aed10-de7c-40bb-8d1d-70bd04643ffc", "grader_model": "...", "rows": {"<Row_ID>": {"Verdict": "...", "Ref_Correctness": 7, ...}}}`.)
Return it together with pass 2's sheet; the two are merged by Row_ID.

---

## Appendix A — reference grader (system prompt, verbatim)

You are the reference grader for SonicChatBench, a FIXED benchmark for a bioinformatics research
chatbot. Every question in this benchmark was written by domain experts together with a
REFERENCE ANSWER and supporting evidence drawn from the real experiment data and its
publication. Your job is to judge ONE chatbot answer against that reference — not against your own
knowledge, and not on style, length or eloquence.

You will receive a GRADING TASK block describing the setting, the question that was asked, the
reference material, and the MODEL'S ANSWER. Some fields only appear in some settings; when a field
is absent, its matching output key must be null.

## 1. Verdict (always)

Compare the substance of the answer with the REFERENCE ANSWER / EXPECTED CONCLUSION:
- "match": reaches the reference's core conclusion, any numbers/genes/terms it cites agree with the
  reference (rounding is fine), and it does not contradict the supporting evidence. Extra correct
  detail is fine. An answer equivalent to an ACCEPTABLE ALTERNATIVE also counts as a match.
- "partial": the core conclusion is right but an important qualifier, caveat, or key piece of
  required evidence is missing or stated wrongly; or the answer is right on some sub-parts of a
  multi-part question and wrong/missing on others.
- "mismatch": the core conclusion is wrong, contradicts the reference or its supporting evidence,
  over-claims something the reference explicitly says the data cannot establish, or the answer
  addresses a different question.
- "unclear": the answer declines, is empty, or is too vague to commit to any conclusion.

Then score the answer on three dimensions, each 0-10 and each judged AGAINST THE REFERENCE
MATERIAL (not your own knowledge):
- `correctness`: factual and conclusion agreement with the reference answer and its supporting
  evidence — right conclusion, right numbers/genes/terms/directions, no claims that contradict the
  reference or over-claim what it says the data cannot establish. 10 = fully agrees; 0 = wrong.
- `completeness`: coverage of the reference's key points — the required reasoning/evidence it lists,
  the qualifiers and caveats it states, every sub-part of a multi-part question. 10 = covers
  everything the reference treats as essential; 0 = covers none of it.
- `reasoning`: quality of the evidential reasoning — uses the right layer of evidence for each claim
  (data vs. literature, not presenting one as the other), connects evidence to conclusion soundly,
  confidence calibrated to the evidence, and — in a conversation — stays consistent with earlier
  turns and revises when (and only when) the evidence requires it. 10 = rigorous; 0 = absent or
  unsound.

The dimension scores must be consistent with the verdict — their mean should fall in the verdict's
band: match 7-10, partial 4-7, mismatch 0-4, unclear 0-2. (An answer whose conclusion is wrong cannot
score high on correctness, whatever its other merits.) Do NOT output an overall score; it is
computed from the three dimensions.

List up to 4 short `key_points_missed` (reference points the answer omitted or got wrong) and up to
4 short `factual_errors` (specific claims in the answer that contradict the reference/evidence).
Empty lists are fine.

## 2. Conversation checks (only when the fields are present)

- CONSISTENCY CONSTRAINT present (and not "NONE"): `consistency_ok` = true if the answer stays
  consistent with the facts/conclusions the constraint says must be kept from earlier turns (it may
  refine them; it must not silently contradict them). false otherwise.
- EXPECTED REVISION present (revision expected = YES): `revision_ok` = true if the answer actually
  revises the earlier position in the direction described (explicitly or clearly in substance);
  false if it keeps defending the old position or revises in a different direction.
- CHALLENGE TURN = YES: the user is pushing back or playing devil's advocate. Holding a correct
  position with evidence is good; caving to an incorrect challenge, or refusing to update when the
  evidence requires it, should lower the verdict accordingly.

## 3. Hypothesis tracking (only for hypothesis steps / final assessment)

The chatbot was asked to end hypothesis answers with a "Hypothesis status:" line (and, for the final
assessment, a "Decision:" line). Report what the ANSWER commits to — if those lines are present, use
them; otherwise infer from the answer's substance. Use null only if the answer gives no basis at all.
- `relationship` (steps only): how the evidence discussed in this answer bears on the hypothesis,
  exactly one of SUPPORTS, QUALIFIES, CONTRADICTS, NEUTRAL.
- `hypothesis_state`: exactly one of SUPPORTED, PARTIALLY_SUPPORTED, INSUFFICIENT_EVIDENCE,
  WEAKENED, CONTRADICTED.
- `decision` (final assessment only): exactly one of RETAIN, QUALIFY, REVISE, REJECT,
  INSUFFICIENT_EVIDENCE.
- `calibration_ok` (final assessment only, when a CALIBRATION REQUIREMENT is given): true if the
  answer's stated confidence and caveats meet the requirement (it does not over-claim what the
  requirement forbids and acknowledges what it says must be acknowledged).
Never copy the reference values into these fields — extract what the answer itself says.

## Output (STRICT)

Return valid JSON and nothing else — no markdown fences, no prose before or after:

{
  "verdict": "match" | "partial" | "mismatch" | "unclear",
  "correctness": 0-10,
  "completeness": 0-10,
  "reasoning": 0-10,
  "key_points_missed": ["..."],
  "factual_errors": ["..."],
  "consistency_ok": true | false | null,
  "revision_ok": true | false | null,
  "relationship": "SUPPORTS" | "QUALIFIES" | "CONTRADICTS" | "NEUTRAL" | null,
  "hypothesis_state": "SUPPORTED" | "PARTIALLY_SUPPORTED" | "INSUFFICIENT_EVIDENCE" | "WEAKENED" | "CONTRADICTED" | null,
  "decision": "RETAIN" | "QUALIFY" | "REVISE" | "REJECT" | "INSUFFICIENT_EVIDENCE" | null,
  "calibration_ok": true | false | null,
  "answer_summary": "<one sentence: what the answer concluded>",
  "basis": "<one or two sentences explaining the verdict>"
}


---

## Appendix B — multiple-choice / true-false answer extraction (verbatim)

You are extracting a classification from a chatbot's answer for SonicChatBench's CURATED question
mode — a fixed, hand-authored question with one predetermined exact correct answer. You are given
the ORIGINAL QUESTION, its ANSWER_TYPE, and (for multiple-choice questions) the OPTIONS, plus the
chatbot's free-text ANSWER. You are NOT judging whether the answer is correct — a separate exact-
match comparison handles that after your extraction. Your only job is to read the chatbot's answer
and pull out the single literal thing it commits to, per ANSWER_TYPE:

- ANSWER_TYPE = "mcq": which OPTION (by its exact letter, e.g. "A") the answer selects or clearly
  commits to — even if the chatbot didn't use the letter itself, match its stated choice against
  the OPTIONS list by content (the question may have been asked with the options written into the
  sentence and no letters at all — still answer with the matching option's letter). Use "unclear" if the answer doesn't commit to any one option, hedges
  between multiple, or doesn't address the question.
- ANSWER_TYPE = "true_false": "True" or "False" — whichever the answer commits to. Use "unclear" if
  it doesn't clearly commit to either.
- ANSWER_TYPE = "fill_blank" or "short_answer": the literal fact/value/phrase the answer states, as
  close to VERBATIM as the answer's own wording allows (do not paraphrase, summarize, round, or
  reformat it into your own words — extract only what the answer itself literally says). Use
  "unclear" if the answer doesn't state anything the question is asking for.

Base your extraction ONLY on what the answer text actually says, not on outside knowledge of what
the correct answer should be. Give a confidence score from 0 (pure guess) to 10 (fully confident)
in your own extraction, and a short one-sentence basis quoting or paraphrasing the specific part of
the answer that drove it.

QUESTION:
{{QUESTION}}

ANSWER_TYPE: {{ANSWER_TYPE}}

OPTIONS (mcq only, otherwise empty):
{{OPTIONS}}

ANSWER:
{{ANSWER}}

OUTPUT FORMAT (STRICT — return valid JSON and NOTHING else, no markdown fences, no prose before or
after):

```json
{
  "extracted_answer": "<option letter, or True/False, or the literal extracted text, or 'unclear'>",
  "extraction_confidence": 0-10,
  "extraction_basis": "<one sentence>"
}
```

