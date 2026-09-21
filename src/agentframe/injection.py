# src/agentframe/injection.py
"""Hard inbound wall against prompt injection.

Complements the R5 transport wall (classification.py). The transport wall stops
secrets going *out*; this wall stops instructions coming *in* to a reasoning core.

It is deterministic and non-LLM by design: a filter that itself calls a model can
itself be injected. It rejects two classes of content that have no legitimate place
in untrusted free text destined for a model:

  1. chat-template / control tokens (structural takeover of the prompt frame);
  2. high-signal instruction-override phrases (semantic takeover).

This is a denylist, and a denylist is a floor, not a proof. It raises the cost of
the cheapest, highest-signal attacks; it is paired with, not a substitute for,
least-privilege grants (an injected agent still cannot exceed its passport) and
the transport wall (an injected agent still cannot serialize a key).
"""
from __future__ import annotations

import re

# Structural: control tokens from common chat templates. None of these ever occur
# in legitimate natural-language payloads; their presence is takeover intent.
_CONTROL_TOKENS = (
    "<|im_start|>", "<|im_end|>", "<|system|>", "<|user|>", "<|assistant|>",
    "<|endoftext|>", "<|eot_id|>", "<|start_header_id|>", "<|end_header_id|>",
    "[inst]", "[/inst]", "<<sys>>", "<</sys>>", "<|begin_of_text|>",
)

# Semantic: high-signal override phrases. Word-boundary anchored, case-insensitive.
_OVERRIDE_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|preceding|earlier)\b.{0,40}\b(instruction|prompt|message|context|rule)",
    r"\bdisregard\s+(all\s+|the\s+|any\s+)?(previous|prior|above|system|earlier)\b",
    r"\bforget\s+(everything|all|the\s+above|previous|prior|your\s+instructions)\b",
    r"\byou\s+are\s+now\b.{0,40}\b(a|an|the|no\s+longer)\b",
    r"\bnew\s+(instructions?|rules?|task|system\s+prompt)\s*[:\-]",
    r"\b(reveal|print|show|repeat|output|leak)\b.{0,30}\b(system\s+prompt|your\s+(instructions|prompt|rules|keys|secret|passport|private\s+key))",
    r"\bdeveloper\s+mode\b",
    r"\bdo\s+anything\s+now\b",
    r"\bjailbreak\b",
    r"\boverride\s+(the\s+|your\s+|all\s+)?(safety|security|instructions?|guardrails?|rules?)",
    r"\bact\s+as\s+(if\s+you\s+are\s+)?(a\s+|an\s+)?(unrestricted|uncensored|different)\b",
    r"\bpretend\s+(that\s+)?you\s+(are|have)\b.{0,30}\b(no|different)\b",
))


def scan(text: str) -> tuple[bool, str]:
    """Return (ok, reason). ok=True means the text is clean.

    reason is 'ok' on pass, otherwise 'injection:control_token' or
    'injection:override_phrase'.
    """
    if not isinstance(text, str):
        return True, "ok"  # non-text fields are handled by schema validation
    low = text.lower()
    for tok in _CONTROL_TOKENS:
        if tok in low:
            return False, "injection:control_token"
    for pat in _OVERRIDE_PATTERNS:
        if pat.search(text):
            return False, "injection:override_phrase"
    return True, "ok"


def scan_fields(payload: dict, fields: tuple[str, ...]) -> tuple[bool, str]:
    """Scan the named free-text fields of a payload. First hit wins."""
    for f in fields:
        val = payload.get(f)
        if isinstance(val, str):
            ok, reason = scan(val)
            if not ok:
                return False, reason
    return True, "ok"
