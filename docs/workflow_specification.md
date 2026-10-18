# Nova reasoning workflows: specification

This document specifies the four Nova reasoning workflows evaluated in the paper
(Sec. 3.1–3.2 and Table 2). All four share the same evidence sources, tools, rules
of evidence, and model; they differ only in how they organize the planning,
retrieval, and synthesis of evidence.

## Shared environment

| Component | Specification |
|---|---|
| Model | GLM-5.2 (open weights, self-hosted); a fast process (Instant) or a reasoning process (Thinking, Deep Thinking) |
| Analysis results | iPathwayGuide results of each dataset, queried through tool calls: differentially expressed genes (DEGs), impacted pathways, Gene Ontology (GO) terms, predicted upstream regulators, miRNAs, and disease associations |
| Literature | PubMed, searched through a lexical and semantic search service |
| Sessions | Each user's work on a dataset is kept in a session that stores all previous messages; in a conversation or a hypothesis evaluation, every workflow answers with the earlier turns as context |

### Rules of evidence (common system prompt)

1. Retrieve evidence before answering.
2. Verify named entities and claims of absence directly, with a tool call.
3. Use the appropriate evidence layer for each biological claim (for example,
   regulator activity versus the regulator's own transcript; over-representation
   versus pathway perturbation; corrected versus nominal significance).
4. Report exact values returned by the tools.
5. For a closed-form question, answer the question directly, then explain why and
   how that answer was chosen, with evidence from the experiment and the literature.
6. Consider counter-evidence.
7. Distinguish dataset observations, findings in the related literature, and
   biological inference.
8. Calibrate conclusions to the strength of the available evidence.
9. Take experiment-specific factual claims from retrieved evidence, never from the
   model's parametric knowledge.

### Output contract for hypothesis evaluation

Each hypothesis step ends with one status line:

```
Hypothesis status: <SUPPORTED | PARTIALLY_SUPPORTED | INSUFFICIENT_EVIDENCE | WEAKENED | CONTRADICTED>
```

The final assessment also states one decision:

```
Decision: <RETAIN | QUALIFY | REVISE | REJECT | INSUFFICIENT_EVIDENCE>
```

The evidence relation of each step (supports, qualifies, contradicts, or neutral)
is not declared by the workflow; the grader reads it from the answer.

## The four workflows

| Workflow | Planning / routing | Evidence execution | Synthesis / control | Process |
|---|---|---|---|---|
| Instant | None | Single round of parallel tool calls | Direct answer; no self-review | Fast |
| Thinking | Fixed plan: sub-questions, evidence needs, and counter-evidence | Sequential planned lookups; structured evidence log | Calibrated synthesis of gathered evidence | Reasoning |
| Deep Thinking | Complexity-adaptive plan and decomposition into scoped sub-agents | Parallel sub-agents with task-specific tools; dependencies preserved | Reconcile sub-agent evidence and synthesize | Reasoning |
| Auto | Classify and route to Instant, Thinking, or Deep Thinking | Uses the selected workflow | Assess sufficiency; if insufficient, enrich and re-route to a more intensive workflow | Adaptive |

### Nova-Instant (single pass)

The lowest-compute workflow and the direct grounded-retrieval baseline.

1. Issue all required tool calls in a single parallel round.
2. Answer directly from the returned evidence, without explicit planning, an
   intermediate evidence log, or self-review.

### Nova-Thinking (fixed multi-stage: plan, gather, synthesize)

1. **Plan.** Identify the sub-questions, named entities, evidence layers,
   quantitative values, and counter-evidence needed for the request.
2. **Gather.** Execute the planned lookups and record their results in a
   structured evidence log.
3. **Synthesize.** A separate reasoning stage produces a calibrated final response
   from the evidence log.

Thinking decides what evidence to retrieve, but its reasoning structure is fixed.

### Nova-Deep Thinking (dynamic decomposition across sub-agents)

1. **Plan.** Build a response plan sized to the complexity of the request.
2. **Decompose.** Map each distinct reasoning step to a focused sub-agent with a
   specific objective, evidence requirements, restricted tool access, and explicit
   output requirements.
3. **Execute.** Run independent sub-agents in parallel; steps with evidence
   dependencies wait for the steps they depend on.
4. **Reconcile and synthesize.** Collect and reconcile the sub-agents' evidence,
   then produce one calibrated response.

Unlike Thinking, the number and scope of reasoning steps are determined by the request.

### Nova-Auto (adaptive routing and assessment)

1. **Classify** whether the request falls within the experiment-specific analysis domain.
2. **Route** by the reasoning the request requires (not by query length):
   direct retrieval to Instant; interpretation and hypothesis evaluation to
   Thinking; broad multi-layer analyses that need independent lines of evidence to
   Deep Thinking.
3. **Assess** whether the response sufficiently addresses the request.
4. **Enrich and re-route** to a more intensive workflow when the response is insufficient.
5. If grounded evidence remains insufficient, return the supported partial result
   or report the evidence gap rather than filling it from parametric knowledge.

## Versions evaluated

The result workbooks identify the evaluated versions in the `Agent_ID` column:
Instant 1.2 (`chatbot@1.2`), Thinking 0.7 (`chatbot_thinking@0.7`),
Deep Thinking 1.7 (`chatbot_deep_thinking@1.7`), and Auto 0.7 (`chatbot_auto@0.7`).
