# src/provider/qwen_endpoint.py
"""ask_qwen faucet: routes a verified, authorized request to a local LLM.

Registered on the shared router (provider/router.py) exactly like publish_blog, so
the same trust substrate guards the reasoning core. Because this capability's
payload reaches an LLM, it declares `prompt` as an untrusted field and the router
runs the injection wall on it before the model is called.
Capability: ask_qwen, grant: ask@orion.
"""
from __future__ import annotations

from agentframe import identity as idmod
from provider.qwen_capability import (DEFAULT_MODEL, DEFAULT_OLLAMA_URL,
                                       ask_qwen, validate_ask)
from provider.router import Capability, create_router_app

CAPABILITY = "ask_qwen"
GRANT = "ask@orion"


def ask_capability(*, model: str = DEFAULT_MODEL,
                   ollama_url: str = DEFAULT_OLLAMA_URL,
                   system: str | None = None) -> Capability:
    def handle(payload: dict) -> dict:
        result = ask_qwen(payload["prompt"], system=system,
                          num_predict=int(payload.get("num_predict", 256)),
                          model=model, ollama_url=ollama_url)
        return {"answer": result["answer"], "model": result["model"],
                "eval_count": result["eval_count"]}

    return Capability(name=CAPABILITY, grant=GRANT, validate=validate_ask,
                      handle=handle, untrusted_fields=("prompt",))


def create_qwen_app(orion: "idmod.Identity", root_pub_b64: str,
                    known_agents: dict[str, str], *,
                    model: str = DEFAULT_MODEL,
                    ollama_url: str = DEFAULT_OLLAMA_URL,
                    system: str | None = None):
    return create_router_app(orion, root_pub_b64, known_agents,
                             [ask_capability(model=model, ollama_url=ollama_url,
                                             system=system)])
