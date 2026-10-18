Conditional branch, not an LLM call: routes to {{delegate_to_instant}} when
classification.output.family == "chatbot" (Nova Instant), {{delegate_to_thinking}} when
family == "chatbot_thinking" (Nova Thinking), or {{delegate_to_deep_thinking}} when
family == "chatbot_deep_thinking" (Nova Deep Thinking). No separate prompt of its own — the
decision is made entirely by the classification node above.