# src/provider/publish.py
from __future__ import annotations

import json
import os
import re
import time

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    s = _SLUG_RE.sub("-", title.lower()).strip("-")[:60]
    return s or "post"


def validate_payload(payload: dict) -> tuple[bool, str]:
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        return False, "title_required"
    if not isinstance(payload.get("markdown"), str) or not payload["markdown"].strip():
        return False, "markdown_required"
    if "tags" in payload and not all(isinstance(t, str) for t in payload["tags"]):
        return False, "bad_tags"
    return True, "ok"


def save_post(posts_dir: str, payload: dict, ts: int | None = None) -> dict:
    ts = int(time.time()) if ts is None else ts
    slug = f"{ts}-{slugify(payload['title'])}"
    record = {
        "slug": slug,
        "title": payload["title"],
        "subtitle": payload.get("subtitle", ""),
        "tags": payload.get("tags", []),
        "markdown": payload["markdown"],
        "ts": ts,
        "url": f"/posts/{slug}.html",
    }
    os.makedirs(posts_dir, exist_ok=True)
    with open(os.path.join(posts_dir, f"{slug}.json"), "w") as f:
        json.dump(record, f, indent=2)
    return record
