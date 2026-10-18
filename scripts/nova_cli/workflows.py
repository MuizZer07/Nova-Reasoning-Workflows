"""The four Nova reasoning workflows, built from the stage prompts in prompts/.

All four share the same system prompt (prompts/nova_*/_system_prompt_build.md plus _core_restrictions.md),
the same tools (tools.py), and the same model; they differ only in how planning, evidence retrieval, and
synthesis are organized (paper, Sec. 3.2 and Table 2):

  Instant        one round of parallel tool calls -> direct answer (fast process)
  Thinking       fixed plan -> planned lookups into an evidence log -> calibrated synthesis (reasoning process)
  Deep Thinking  complexity-sized plan -> scoped sub-agents in dependency waves -> reconcile and synthesize
  Auto           classify and route -> verify sufficiency -> enrich and re-route upward -> final assessment
"""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

from llm import LLM
from tools import ExperimentTools, tool_schemas

PROMPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "prompts"))
DIRS = {"instant": "nova_instant", "thinking": "nova_thinking",
        "deep_thinking": "nova_deep_thinking", "auto": "nova_auto"}


def prompt(workflow: str, name: str) -> str:
    with open(os.path.join(PROMPTS, DIRS[workflow], f"_{name}.md"), encoding="utf-8") as fh:
        return fh.read()


def system_prompt(workflow: str, tools: ExperimentTools) -> str:
    """Shared system prompt + core restrictions + the experiment context."""
    ctx = json.dumps(tools.get_experiment_info())
    return "\n\n".join([prompt(workflow, "system_prompt_build"), prompt(workflow, "core_restrictions"),
                        f"Experiment context: {ctx}"])


def run_tools(tools: ExperimentTools, calls: list[dict]) -> list[dict]:
    """Execute tool calls in parallel; every result is kept verbatim for the later stages."""
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda c: tools.call(c["name"], c["args"]), calls))
    return [{"tool": c["name"], "args": c["args"], "result": r} for c, r in zip(calls, results)]


def tool_loop(llm: LLM, tools: ExperimentTools, messages: list[dict], max_rounds: int,
              capabilities: list[str] | None = None, reasoning: bool = False) -> tuple[str, list[dict]]:
    """Let the model call tools for up to `max_rounds` rounds (each round's calls run in parallel)."""
    log, schemas = [], tool_schemas(capabilities)
    for _ in range(max_rounds):
        out = llm.chat(messages, tools=schemas, reasoning=reasoning)
        if not out["tool_calls"]:
            return out["content"], log
        results = run_tools(tools, out["tool_calls"])
        log += results
        messages = messages + [{"role": "assistant", "content": out["content"]},
                               {"role": "user", "content": "Tool results:\n" + json.dumps(results)[:60000]}]
    return llm.chat(messages, reasoning=reasoning)["content"], log


# ---------------------------------------------------------------- Nova-Instant
def instant(llm, tools, history, query):
    """Single round of parallel tool calls, then a direct answer: no planning, evidence log, or self-review."""
    msgs = [{"role": "system", "content": system_prompt("instant", tools)}, *history,
            {"role": "user", "content": query}]
    answer, log = tool_loop(llm, tools, msgs, max_rounds=1)
    return answer, log


# ---------------------------------------------------------------- Nova-Thinking
def thinking(llm, tools, history, query):
    """Fixed plan -> gather -> synthesize."""
    sys_ = {"role": "system", "content": system_prompt("thinking", tools)}
    plan = llm.chat([sys_, *history, {"role": "user", "content": query},
                     {"role": "user", "content": prompt("thinking", "reasoning_plan")}], reasoning=True)["content"]
    gather = [sys_, *history, {"role": "user", "content": query},
              {"role": "user", "content": prompt("thinking", "evidence_gathering").format(plan=plan)}]
    evidence_log, raw = tool_loop(llm, tools, gather, max_rounds=3)
    evidence = evidence_log + "\n\nRaw tool results:\n" + json.dumps(raw)[:60000]
    answer = llm.chat([sys_, *history, {"role": "user", "content": prompt("thinking", "response_synthesis")
                                        .format(query=query, plan=plan, evidence=evidence)}],
                      reasoning=True)["content"]
    return answer, raw


# ---------------------------------------------------------------- Nova-Deep Thinking
def deep_thinking(llm, tools, history, query, max_sub_agents: int = 5):
    """Complexity-sized plan -> scoped sub-agents (parallel; dependent steps wait) -> reconcile and synthesize."""
    sys_ = {"role": "system", "content": system_prompt("deep_thinking", tools)}
    plan = llm.json([sys_, *history, {"role": "user", "content": query},
                     {"role": "user", "content": prompt("deep_thinking", "response_plan")}], reasoning=True)
    decomposition = llm.json([sys_, {"role": "user", "content": prompt("deep_thinking", "sub_agent_decomposition").format(
        plan_json=json.dumps(plan), capabilities_json=json.dumps(list(ExperimentTools.CAPABILITIES)),
        max_sub_agents=max_sub_agents)}], reasoning=True)
    agents = {a["id"]: a for a in decomposition["sub_agents"][:max_sub_agents]}
    done: dict[str, dict] = {}

    def run_agent(a):
        inputs = {d: done[d]["findings"] for d in a.get("depends_on", []) if d in done}
        msgs = [{"role": "system", "content": a["system_prompt"]},
                {"role": "user", "content": f"Objective: {a['objective']}\nInputs: {json.dumps(inputs)}\n"
                                            f"Return: {a['expected_output_format']}"}]
        findings, raw = tool_loop(llm, tools, msgs, max_rounds=2, capabilities=a.get("assigned_capabilities"))
        return {"role": a["role"], "status": "ok", "findings": findings, "raw": raw}

    while len(done) < len(agents):                        # dependency waves
        wave = [a for i, a in agents.items() if i not in done and all(d in done for d in a.get("depends_on", []))]
        if not wave:                                      # unsatisfiable dependency: stop rather than guess
            break
        with ThreadPoolExecutor(max_workers=len(wave)) as ex:
            for a, res in zip(wave, ex.map(run_agent, wave)):
                done[a["id"]] = res
    digest = json.dumps([{k: v for k, v in r.items() if k != "raw"} for r in done.values()], indent=1)
    answer = llm.chat([sys_, *history, {"role": "user", "content": prompt("deep_thinking", "response_synthesis")
                                        .format(query=query, plan=json.dumps(plan), digest=digest)}],
                      reasoning=True)["content"]
    return answer, sum((r["raw"] for r in done.values()), [])


# ---------------------------------------------------------------- Nova-Auto
FAMILY = {"chatbot": instant, "chatbot_thinking": thinking, "chatbot_deep_thinking": deep_thinking}
LADDER = ["chatbot", "chatbot_thinking", "chatbot_deep_thinking"]


def grounded_citations(answer: str, log: list[dict]) -> bool:
    """Code-level check: every [PMID:x] in the answer must have been returned by a tool."""
    seen = json.dumps(log)
    return all(p in seen for p in re.findall(r"PMID:\s*(\d+)", answer))


def auto(llm, tools, history, query, max_retries: int = 2):
    """Classify and route by the reasoning required; verify; enrich and re-route upward when insufficient."""
    runtime = json.dumps({"experiment": tools.get_experiment_info(),
                          "capabilities": list(ExperimentTools.CAPABILITIES)})
    attempts, floor, request = [], 0, query
    for _ in range(max_retries + 1):
        prior = json.dumps([{k: a[k] for k in ("family", "missing")} for a in attempts])
        cls = llm.json([{"role": "user", "content": prompt("auto", "classification").format(
            runtime_context_json=runtime, prior_attempt_context=prior)}, *history,
                        {"role": "user", "content": request}])
        if not cls.get("in_domain", True):
            return cls.get("out_of_scope_reply", "That is outside what Nova can help with."), []
        rank = max(LADDER.index(cls.get("family", "chatbot_thinking")), floor)
        if cls.get("complexity") == "most_complex":
            rank = 2                                      # deterministic floor: most complex -> Deep Thinking
        family = LADDER[rank]
        answer, log = FAMILY[family](llm, tools, history, request)
        verdict = llm.json([{"role": "user", "content": prompt("auto", "response_verification").format(
            query=query, runtime_context_json=runtime, routing_decision_json=json.dumps(cls),
            prior_attempts_summary=prior, response_text=answer,
            tool_calls_summary=json.dumps([{"tool": r["tool"], "args": r["args"]} for r in log]))}])
        ok = verdict.get("sufficient") and grounded_citations(answer, log)
        attempts.append({"family": family, "missing": verdict.get("missing", []), "response": answer})
        if ok:
            return answer, log
        floor = min(rank + 1, 2)                          # escalation only moves up the ladder
        request = f"{query}\n\n[Reviewer feedback on the previous answer: {verdict.get('feedback', '')}]"
    summary = json.dumps(attempts, indent=1)[:60000]
    return llm.chat([{"role": "system", "content": system_prompt("auto", tools)}, *history,
                     {"role": "user", "content": prompt("auto", "final_synthesis").format(
                         n_attempts=len(attempts), query=query, attempts_summary=summary)}],
                    reasoning=True)["content"], []


WORKFLOWS = {"instant": instant, "thinking": thinking, "deep_thinking": deep_thinking, "auto": auto}
