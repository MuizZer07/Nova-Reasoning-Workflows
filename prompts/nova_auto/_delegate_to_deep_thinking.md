Invokes {{chatbot_deep_thinking@latest}} (Nova Deep Thinking) as a full sub-workflow — its own
plan -> divide into dynamic sub-agents -> execute in dependency waves -> reconcile -> synthesize
pipeline (with its own bounded loop-back if a first pass leaves gaps), same capability
gating as if the user had talked to Nova Deep Thinking directly. Reserved for the most complex
requests the classifier identifies, or an escalation from a Nova Instant/Nova Thinking attempt
the verifier judged insufficient. See the "Nova Deep Thinking" workflow for its own editable
prompts and dynamic execution config (max sub-agents, max waves, max decomposition rounds).
