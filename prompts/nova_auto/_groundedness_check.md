Deterministic, code-level check (not an LLM call) — scans the delegate's response for
citations already flagged as unverified/fabricated by stream_chat()'s own PMID-grounding scrub
(the "⚠ unverified" marker). If any are found, forces this attempt to "insufficient" regardless
of what {{response_verification}}'s LLM verdict concluded. Runs in parallel with
response_verification; both feed {{routing_decision}}.