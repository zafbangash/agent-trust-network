# src/provider/qwen_capability.py
"""Local Ollama (qwen) reasoning capability.

This is the first *reasoning* capability for the framework: where Phase 0's
publish_blog is deterministic, ask_qwen routes a verified, authorized request to
a local LLM (Ollama qwen2.5:7b on 127.0.0.1:11434) and returns its answer.

Kept deliberately small and dependency-light — the trust/identity/signing wall
lives in agentframe.* and is enforced by the endpoint BEFORE this is ever called.
"""
from __future__ import annotations

import requests

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:7b"

MAX_PROMPT_CHARS = 4000


def validate_ask(payload: dict) -> tuple[bool, str]:
    """Structural validation for an ask_qwen payload."""
    if not isinstance(payload, dict):
        return False, "malformed"
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return False, "empty_prompt"
    if len(prompt) > MAX_PROMPT_CHARS:
        return False, "prompt_too_long"
    return True, "ok"


def ask_qwen(prompt: str, *, system: str | None = None,
             num_predict: int = 256, model: str = DEFAULT_MODEL,
             ollama_url: str = DEFAULT_OLLAMA_URL,
             timeout: int = 120) -> dict:
    """Call the local Ollama model. Returns a small result dict (no streaming)."""
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.2},
    }
    if system:
        body["system"] = system
    r = requests.post(ollama_url, json=body, timeout=timeout)
    r.raise_for_status()
    d = r.json()
    return {
        "answer": (d.get("response") or "").strip(),
        "model": d.get("model", model),
        "eval_count": d.get("eval_count"),
        "duration_ms": (d.get("total_duration") or 0) // 1_000_000,
    }
