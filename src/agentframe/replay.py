# src/agentframe/replay.py
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ReplayGuard:
    """In-memory replay protection: a message is valid once, within a time window.

    Phase 0 uses process memory (single endpoint). Phase 1 swaps the backing
    store for something shared/persistent without changing this interface.
    """

    window_s: int = 300
    _seen: dict[str, float] = field(default_factory=dict)

    def check_and_record(self, nonce: str, ts: int, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        if abs(now - ts) > self.window_s:
            return False
        self._prune(now)
        if nonce in self._seen:
            return False
        self._seen[nonce] = now
        return True

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_s
        for n in [n for n, t in self._seen.items() if t < cutoff]:
            del self._seen[n]
