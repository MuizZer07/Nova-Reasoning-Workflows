# Prompts

The prompts used in the study, as they were run.

| Folder | Contents |
|---|---|
| `nova_instant/`, `nova_thinking/`, `nova_deep_thinking/`, `nova_auto/` | The workflow stage prompts of the four Nova workflows (paper, Sec. 3.2 and Table 2) |
| `sonic_chat/` | The reference-free SonicChat judge (paper, Sec. 3.4) |
| `suite_rephraser/` | The rephrasing and equivalence-check prompts for the robustness subset (Gemini 3.1 Flash-Lite) |
| `benchmarking_generation/` | The benchmark generation prompt and the automated item validators (paper, Sec. 3.3) |

**Nova workflows.** All four share `_system_prompt_build.md` (the common system prompt: answer-first
format, evidence protocol, reasoning rules, calibration, conversations, and grounding) and
`_core_restrictions.md`. The other files are the stages of each workflow:

| Workflow | Stage prompts |
|---|---|
| Instant | `_llm_request.md` (one request: system prompt, conversation history, tool schemas) |
| Thinking | `_reasoning_plan.md` → `_evidence_gathering.md` → `_response_synthesis.md` |
| Deep Thinking | `_response_plan.md` → `_sub_agent_decomposition.md` → sub-agents → `_response_synthesis.md` |
| Auto | `_classification.md` → `_route_branch.md` / `_delegate_to_*.md` → `_response_verification.md` + `_groundedness_check.md` → `_routing_decision.md` → `_final_synthesis.md` |

Placeholders in braces (for example `{plan}` or `{query}`) are filled at run time; double braces mark
literal JSON. The experiment context and the tool descriptions are added at run time. Instructions for
platform features not used in this study, and keyword-routed skill prompts, are omitted.
[`scripts/nova_cli/`](../scripts/nova_cli) shows how the stages fit together.
