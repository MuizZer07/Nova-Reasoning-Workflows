# Suite rephraser: runtime user message

`research-agent/services/suite_grading.py::rephrase_suite_texts` sends `suite_question_rephrase.md` as the system prompt, with temperature 0. The user message is built like this:

```text
REPHRASE TASK

KIND: <label>

DEGREE OF CHANGE: <lexical | structural>

PATTERN (within the degree, where it fits): <pattern>        # optional; chosen by the set's rephrase seed

ORIGINAL TEXT:
<text>
   (or, for a whole conversation or hypothesis:)
ORIGINAL TEXTS (rephrase every one, same order):
1. <text>
2. <text>

Rephrase now.
```

## Kind labels

```python
{
    "s1": "SINGLE QUESTION",
    "s1_mcq": "MCQ STEM",
    "s1_tf": "TRUE_FALSE STATEMENT",
    "s2": "CONVERSATION TURN",
    "s2_trajectory": "CONVERSATION",
    "s3_hypothesis": "HYPOTHESIS STATEMENT",
    "s3_step": "HYPOTHESIS STEP",
    "s3_final": "FINAL ASSESSMENT",
    "s3_hypothesis_set": "HYPOTHESIS",
}
```

## Patterns

```python
{
    "structural": (
        "lead with the condition or context, then ask",
        "put the main question first, then the qualifiers",
        "turn an instruction into a question or a question into an instruction",
        "split one long sentence into two, or merge two short ones",
    ),
    "lexical": (
        "prefer replacing verbs and connectives",
        "prefer replacing nouns and descriptive phrases",
    ),
}
```

`suite_rephrase_equivalence.md` is the separate LLM check of whether a rephrasing is equivalent to the original. The rule-based checks (protected tokens, added hints, degree) run in `bioinsight/backend/services/rephrase_check.py`, with no LLM.
