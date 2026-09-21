# src/provider/build_blog.py
from __future__ import annotations

import glob
import html
import json
import os

import markdown as md


def _load_posts(posts_dir: str) -> list[dict]:
    posts = []
    for path in glob.glob(os.path.join(posts_dir, "*.json")):
        with open(path) as f:
            posts.append(json.load(f))
    posts.sort(key=lambda p: p["ts"], reverse=True)
    return posts


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title></head><body>{body}</body></html>"
    )


def build_site(posts_dir: str, site_dir: str) -> None:
    """Render all post JSON records into a static site under site_dir."""
    posts = _load_posts(posts_dir)
    os.makedirs(os.path.join(site_dir, "posts"), exist_ok=True)

    items = []
    for p in posts:
        items.append(
            f"<li><a href='{html.escape(p['url'])}'>{html.escape(p['title'])}</a></li>"
        )
        rendered = md.markdown(p["markdown"])
        body = f"<h1>{html.escape(p['title'])}</h1>{rendered}"
        with open(os.path.join(site_dir, "posts", f"{p['slug']}.html"), "w") as f:
            f.write(_page(p["title"], body))

    index_body = "<h1>blog.example.com</h1><ul>" + "".join(items) + "</ul>"
    with open(os.path.join(site_dir, "index.html"), "w") as f:
        f.write(_page("blog.example.com", index_body))
