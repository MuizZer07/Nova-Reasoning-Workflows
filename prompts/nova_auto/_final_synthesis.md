

## Nova Auto — phase 3: final assessment (retry limit reached)

The routing/retry loop made {n_attempts} attempt(s) at the request below — instant, then (if needed) thinking, then (if needed) deep thinking — and none were judged fully sufficient. There will be no further retries. Your job now is to ASSESS, not to force an answer:

1. Look at the original request and everything gathered across the attempts below. Decide honestly: does this collectively contain enough real, grounded evidence to actually answer the request (even partially)?
2. If YES — call additional tools now ONLY if a specific missing piece can be directly filled that way (do not repeat a call that already failed with the same arguments), then combine the useful, grounded parts of the attempts below into ONE comprehensive, precise, pinpoint answer. Do not simply concatenate the prior attempts.
3. If NO — do NOT force an answer, do NOT pad a thin result to look comprehensive, and do NOT guess from background knowledge to fill the gap. Instead, reply with a brief, honest acknowledgment that this couldn't be fully answered with the data/tools available, in 1-3 sentences: say plainly what couldn't be found or done, and — only if something partial and genuinely grounded WAS established — state that part too. A clear "I wasn't able to find X" is a correct, complete answer here; a padded or fabricated one is not.

Original request:
{query}

Prior attempt(s) — family used, what was judged missing/insufficient, and the response text:
{attempts_summary}

Hard rules:
- Do not mention "attempts", "retries", "verification", "routing", or this assessment process
  itself to the user — respond as if this were a single, direct turn (whether that's a full
  answer or an honest "couldn't find this").
- Be precise and pinpoint: state findings directly, do not pad with restated caveats or
  methodology narration from the prior attempts.
- Only state a finding if it is grounded in tool data from the attempts above or a new tool call
  you make now — never fill a gap from memory, and never fabricate a citation, number, or claim
  just to appear complete.