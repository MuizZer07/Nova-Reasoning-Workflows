## Deep reasoning — Stage 1 (build response plan, planning only)

Do not answer yet. Produce an internal plan for a team of focused sub-agents.

Size it to the request — the number of reasoning steps must track real complexity, never a preference for more:
- SIMPLE (one fact, one lookup, one narrow question) → exactly ONE step.
- MODERATE (2-4 distinct sub-questions or evidence layers) → one step per genuinely distinct concern.
- COMPLEX (a broad, multi-layer request, or a claim whose evaluation needs several independent lines of evidence) → more steps, each single-purpose.

Each step must name the entities to look up DIRECTLY by name and the evidence layer that measures the claim (gene-level DE vs thresholds · upstream-regulator activity with consistent/inconsistent target counts · pathway ORA vs perturbation · GO FDR · miRNA target enrichment · disease ORA · the study's own publication for what the authors showed experimentally · literature search only for other studies). When the request evaluates a claim, interpretation or hypothesis, include a dedicated step that looks for the evidence that limits or contradicts it. When the request refers to the study's paper or the authors' experiments, include a publication step.

Respond with ONLY a JSON object with EXACTLY these fields:
```
{
  "complexity": "simple" | "moderate" | "complex",
  "intent": "<one or two sentences describing what the user actually wants, including the answer type: fact / comparison / mechanism / claim evaluation / summary>",
  "required_outputs": ["<each distinct deliverable the final answer must contain>"],
  "reasoning_steps": ["<each single-purpose step, naming the entities to look up and the evidence layer>"],
  "evidence_needs": ["<exact values each step must return (effect sizes, FDRs, z-scores, counts with denominators), including the counter-evidence step and any literature/publication need>"],
  "tool_service_requirements": ["<categories of tools/services likely needed, by name only>"],
  "task_dependencies": "<which steps depend on which others, or \"none\">",
  "expected_response_structure": "<answer-first, then evidence per part, then limits — plus any table that helps>"
}
```

Do not call any tools. Do not write a user-facing answer. Do not include anything outside this JSON object.
