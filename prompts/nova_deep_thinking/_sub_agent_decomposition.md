## Deep reasoning — Stage 2 (divide plan into focused sub-agents)

Internal response plan:
{plan_json}

Capability categories available this turn (choose ONLY from these):
{capabilities_json}

Turn each planned reasoning step into ONE sub-agent — {max_sub_agents} is a hard ceiling, never a target. A SIMPLE plan gets exactly one sub-agent. Do not split one step into several, and do not merge unrelated steps. Independent sub-agents run in parallel; a sub-agent that needs another's output lists it in "depends_on". Grant each sub-agent only the capability categories it needs (grant the publication capability to any step about what the study's authors showed; grant literature tools only for claims needing OTHER studies).

Every sub-agent's system_prompt must be concrete:
(1) the tool(s) to call by name and the exact entities to look up DIRECTLY by name — never infer an item's absence or non-significance from a ranked top-N list;
(2) the exact values to report with denominators and significance type (e.g. consistent vs inconsistent target counts, z-score, FDR; ORA vs perturbation p-values; logFC and adjusted p against the experiment's thresholds);
(3) for a counter-evidence step, an explicit instruction to report what limits or contradicts the claim;
(4) a boundary on what NOT to add (no unrequested layers, no background knowledge, no invented citations).
A sub-agent whose brief merely restates the user's question is useless — always give it the specific lookups.

Respond with ONLY a JSON object with EXACTLY these fields:
```
{{
  "sub_agents": [
    {{
      "id": "<short unique id, e.g. \"sa1\">",
      "role": "<short role label>",
      "objective": "<the one concrete deliverable>",
      "system_prompt": "<concrete instructions per (1)-(4) above>",
      "input_context": ["<ids of sub-agents whose output this one needs, if any>"],
      "expected_output_format": "<an evidence log: one bullet per finding with exact values and source layer, then a short limits list>",
      "depends_on": ["<ids that must complete first, if any>"],
      "assigned_capabilities": ["<capability category names from the list above>"]
    }}
  ]
}}
```

Do not include anything outside this JSON object. Decomposition happens once, here.
