# Nova command-line chat (illustrative)

A minimal command-line chat that shows how Nova is assembled: the workflow stage prompts in
[`prompts/`](../../prompts), experiment-data tools over a dataset's iPathwayGuide results
([`data/input-datasets/ipathwayguide_results/`](../../data/input-datasets/ipathwayguide_results)), the
PubMed literature engine ([`scripts/literature_engine/`](../literature_engine)), and sessions that keep
every earlier turn as context. It is a readable sketch of the design, not the production system.

| File | What it does |
|---|---|
| `workflows.py` | The four workflows: Instant (one round of parallel tool calls, direct answer), Thinking (plan → evidence log → calibrated synthesis), Deep Thinking (complexity-sized plan → scoped sub-agents in dependency waves → reconcile and synthesize), and Auto (classify and route → verify → enrich and re-route upward → final assessment) |
| `tools.py` | Direct-lookup and ranked tools over the iPathwayGuide tables (genes, pathways, upstream regulators, GO, miRNAs, diseases) and literature search |
| `session.py` | Sessions per dataset that store all previous messages |
| `llm.py` | A client for any OpenAI-compatible endpoint, configured only through environment variables |
| `cli.py` | The chat loop |

```bash
pip install -r scripts/nova_cli/requirements.txt
export NOVA_LLM_BASE_URL=...  NOVA_FAST_MODEL=...  NOVA_REASONING_MODEL=...   # your model endpoint
python scripts/nova_cli/cli.py --dataset GSE47363 --workflow auto
```

Inside the chat, `/workflow thinking` switches workflow while keeping the session, `/history` shows the
conversation, `/sessions` lists saved sessions, and `/quit` exits. Literature search additionally needs
the literature engine's requirements and an embedding provider (see `scripts/literature_engine/`).
