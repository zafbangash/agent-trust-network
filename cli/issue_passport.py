# cli/issue_passport.py
"""Root signs a passport for an agent. Prints the passport JSON (no secrets).

Usage:
  python cli/issue_passport.py \
    --root keys/root.pem --agent ag:xxxx --principal Alice \
    --grant publish@blog.example.com --days 365
"""
import argparse
import json
import sys
import time

sys.path.insert(0, "src")
from agentframe.identity import Identity  # noqa: E402
from agentframe.passport import issue  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--agent", required=True)
    ap.add_argument("--principal", required=True)
    ap.add_argument("--grant", action="append", required=True)
    ap.add_argument("--days", type=int, default=365)
    args = ap.parse_args()

    root = Identity.load(args.root)
    now = int(time.time())
    passport = issue(root, args.agent, args.principal, args.grant,
                     issued=now, expires=now + args.days * 86400)
    print(json.dumps(passport, indent=2))


if __name__ == "__main__":
    main()
