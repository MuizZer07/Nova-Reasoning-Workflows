Not an LLM call — pure control flow. If {{response_verification}} AND
{{groundedness_check}} both pass, or the retry limit ({{max_retries}}) is reached, the current
attempt becomes final (falling through to {{final_synthesis}} if still insufficient). Otherwise
the request is enriched with the verifier's feedback and the prior response, and the pipeline
loops back to {{classification}} — potentially escalating Nova Instant to Nova Thinking to Nova
Deep Thinking.

Two deterministic floors enforce this ladder in code (not left purely to the classifier/verifier
LLM calls, which can be inconsistent): (1) `complexity=="most_complex"` always forces Nova Deep
Thinking, regardless of what `family` the classifier separately picked. (2) Once a verifier
escalates, the next attempt's classification may never step back below that floor — rank only
ever moves up. On top of that, a same-family repeat backstop forces an upward escalation whenever
an attempt uses the SAME family as the immediately prior attempt and is still insufficient — the
verifier's own `escalate_to` field has no visibility into attempt history (it only ever sees the
current attempt, not the trace of prior ones), so it cannot reliably judge "was this family
already tried" on its own; this backstop guarantees the ladder actually reaches Nova Deep Thinking
within `max_retries` instead of bouncing at Nova Thinking indefinitely.