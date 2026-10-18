"""Sessions: each user's work on a dataset is kept in a session that stores all previous messages,
so in a conversation or a hypothesis evaluation every workflow answers with the earlier turns as context."""
from __future__ import annotations

import json
import os
import time
import uuid

SESSIONS = os.path.join(os.path.dirname(__file__), "sessions")


class Session:
    def __init__(self, gse: str, workflow: str = "auto", sid: str | None = None):
        self.id = sid or uuid.uuid4().hex[:8]
        self.gse = gse
        self.workflow = workflow
        self.messages: list[dict] = []          # {"role": "user" | "assistant", "content": ..., "workflow": ...}
        self.created = time.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def path(self) -> str:
        return os.path.join(SESSIONS, f"{self.gse}_{self.id}.json")

    def add(self, role: str, content: str, **meta):
        self.messages.append({"role": role, "content": content, **meta})
        self.save()

    def history(self, last: int = 40) -> list[dict]:
        """The earlier turns, passed to every workflow as conversation context."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages[-last:]]

    def save(self):
        os.makedirs(SESSIONS, exist_ok=True)
        with open(self.path, "w") as fh:
            json.dump(self.__dict__, fh, indent=1)

    @classmethod
    def load(cls, gse: str, sid: str) -> "Session":
        with open(os.path.join(SESSIONS, f"{gse}_{sid}.json")) as fh:
            d = json.load(fh)
        s = cls(d["gse"], d["workflow"], d["id"])
        s.messages, s.created = d["messages"], d["created"]
        return s

    @staticmethod
    def list(gse: str | None = None) -> list[str]:
        if not os.path.isdir(SESSIONS):
            return []
        return sorted(f[:-5] for f in os.listdir(SESSIONS) if f.endswith(".json") and (not gse or f.startswith(gse)))
