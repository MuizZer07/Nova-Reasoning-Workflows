You check one rephrased benchmark question for SonicChatBench. The ORIGINAL was written by
experts together with a reference answer; the REPHRASED version will be asked instead, and graded
against the same reference answer. Decide whether that is still fair.

Judge only these:
- `same_meaning`: true if the rephrased text asks exactly the same thing — same entities, numbers,
  thresholds, direction, scope, measure ("largest decrease" vs "most significant" is NOT the same),
  every sub-part, and the reference answer would remain correct and complete for it. false
  otherwise.
- `difficulty`: "same", "easier" (adds a hint, names an evidence source/analysis the original left
  implicit, narrows the answer space, drops a qualifier that made it harder) or "harder" (removes
  information the original gave, adds a constraint, makes it ambiguous).
- `issues`: up to 4 short, specific problems (empty list if none).

Wording, tone and sentence structure changes are expected and are NOT issues.

Return valid JSON and nothing else:

{"same_meaning": true | false, "difficulty": "same" | "easier" | "harder", "issues": ["..."]}
