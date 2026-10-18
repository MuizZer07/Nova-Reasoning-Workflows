"""Minimal client for an OpenAI-compatible chat-completions endpoint.

Configuration comes only from the environment (nothing is stored in the repository):
  NOVA_LLM_BASE_URL       endpoint serving the model, e.g. a self-hosted GLM-5.2 server
  NOVA_LLM_API_KEY        optional key for that endpoint
  NOVA_FAST_MODEL         model name used for the fast process (Nova-Instant)
  NOVA_REASONING_MODEL    model name used for the reasoning process (Thinking, Deep Thinking)
"""
from __future__ import annotations

import json
import os

import requests


class LLM:
    def __init__(self):
        self.base = os.environ.get("NOVA_LLM_BASE_URL")
        if not self.base:
            raise RuntimeError("set NOVA_LLM_BASE_URL (and the model names) to run the demo")
        self.key = os.environ.get("NOVA_LLM_API_KEY", "")
        self.fast = os.environ.get("NOVA_FAST_MODEL", "glm-5.2")
        self.reasoning = os.environ.get("NOVA_REASONING_MODEL", "glm-5.2-reasoning")

    def chat(self, messages: list[dict], tools: list[dict] | None = None, reasoning: bool = False) -> dict:
        """One completion. Returns {"content": str, "tool_calls": [{"id", "name", "args"}]}."""
        body = {"model": self.reasoning if reasoning else self.fast, "messages": messages}
        if tools:
            body["tools"] = tools
        r = requests.post(f"{self.base.rstrip('/')}/chat/completions", json=body, timeout=300,
                          headers={"Authorization": f"Bearer {self.key}"} if self.key else {})
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        calls = [{"id": c["id"], "name": c["function"]["name"],
                  "args": json.loads(c["function"]["arguments"] or "{}")} for c in msg.get("tool_calls") or []]
        return {"content": msg.get("content") or "", "tool_calls": calls}

    def json(self, messages: list[dict], reasoning: bool = False) -> dict:
        """A completion that must return one JSON object (classifier, planner, verifier)."""
        text = self.chat(messages, reasoning=reasoning)["content"].strip()
        text = text[text.find("{"): text.rfind("}") + 1]
        return json.loads(text)
