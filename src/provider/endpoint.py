# src/provider/endpoint.py
"""blog-publishing faucet, registered on the shared router (provider/router.py).

Kept as its own factory for backward-compatible wiring (provider_run.py, tests),
but the plumbing now lives in the router: this file only declares one Capability.
"""
from __future__ import annotations

from agentframe import identity as idmod
from provider.build_blog import build_site
from provider.publish import save_post, validate_payload
from provider.router import Capability, create_router_app

CAPABILITY = "publish_blog"
GRANT = "publish@blog.example.com"


def publish_capability(posts_dir: str, site_dir: str) -> Capability:
    def handle(payload: dict) -> dict:
        record = save_post(posts_dir, payload)
        build_site(posts_dir, site_dir)
        return {"url": record["url"]}

    return Capability(name=CAPABILITY, grant=GRANT,
                      validate=validate_payload, handle=handle)


def create_app(orion: "idmod.Identity", root_pub_b64: str,
               known_agents: dict[str, str], posts_dir: str, site_dir: str):
    """Build the provider app. known_agents maps agent_id -> pubkey_b64 (the registry)."""
    return create_router_app(orion, root_pub_b64, known_agents,
                             [publish_capability(posts_dir, site_dir)])
