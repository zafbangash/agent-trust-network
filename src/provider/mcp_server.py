# src/provider/mcp_server.py
"""MCP server exposing Orion's blog capability as a typed tool.

Run:  python -m provider.mcp_server
Env:  BLOG_POSTS_DIR, BLOG_SITE_DIR (default ./blog/posts, ./blog/site)
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from provider.build_blog import build_site
from provider.publish import save_post, validate_payload

POSTS_DIR = os.environ.get("BLOG_POSTS_DIR", "blog/posts")
SITE_DIR = os.environ.get("BLOG_SITE_DIR", "blog/site")

mcp = FastMCP("orion-blog")


@mcp.tool()
def publish_blog(title: str, markdown: str, subtitle: str = "",
                 tags: list[str] | None = None) -> dict:
    """Publish a post to blog.example.com. Returns the created post's url."""
    payload = {"title": title, "markdown": markdown,
               "subtitle": subtitle, "tags": tags or []}
    ok, reason = validate_payload(payload)
    if not ok:
        return {"status": "error", "reason": reason}
    record = save_post(POSTS_DIR, payload)
    build_site(POSTS_DIR, SITE_DIR)
    return {"status": "ok", "url": record["url"]}


if __name__ == "__main__":
    mcp.run()
