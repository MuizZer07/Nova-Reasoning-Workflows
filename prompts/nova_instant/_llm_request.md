This node represents the actual outgoing API call to the active LLM provider/model.

It is assembled from, in order:
1. {{system_prompt_build.output}} — the full system prompt (this workflow's editable prompt above, plus the literature context block when literature tools are available this turn).
2. Conversation history — the last {{MAX_LLM_CONTEXT_MESSAGES}} messages.
3. Tool schemas for every enabled capability node above (experiment-data tools, literature tools).

Sent to: {{active_llm_provider}} / {{active_model}}.

This node has no separate literal prompt template of its own to edit — it is the mechanical
"send it" step. Edit the system_prompt_build node above to change what's actually sent.