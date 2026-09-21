# cli/keygen.py
"""Generate an Ed25519 identity. Writes a 0600 key file; prints ONLY the public id.

Usage: python cli/keygen.py keys/Alice.pem
"""
import sys

sys.path.insert(0, "src")
from agentframe.identity import Identity  # noqa: E402


def main(path: str) -> None:
    ident = Identity.generate()
    ident.save(path)
    # NEVER print the private key. Public material only.
    print(f"agent_id={ident.agent_id}")
    print(f"pubkey_b64={ident.pub_b64}")
    print(f"key_file={path} (mode 600)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python cli/keygen.py <out.pem>")
    main(sys.argv[1])
