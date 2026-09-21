# agent-mandate

**Let your AI agents talk to each other — across vendors, across machines, across networks —
without sharing a single credential.**

An agent running on Claude asks an agent running on a local Qwen model to do something, over the
public internet. Neither side shares an API key, a password, or an account. Both sides can prove,
cryptographically and with no third party to call, **who authorized this request and exactly what
it was authorized to do.**

That property is the point of this repo. We call the discipline **Know Your Agent (KYA)**, by
analogy with Know Your Customer in finance: before you transact with a counterparty's agent, you
establish whose agent it is and what it may do.

```
  Requester agent                     Relay (dumb)                  Provider agent
  (Claude / GPT / any)                 nginx + ssh -R               (local Qwen via Ollama)
         |                                  |                              |
         |-- signed request + passport ---->|---- reverse tunnel --------->|
         |                                  |                              | 7-step verify
         |<---------- signed receipt -------|<-----------------------------| then answer
```

The relay holds **no keys and no model**. Compromising it gets you traffic metadata and nothing
cryptographic.

---

## Why this exists

The plumbing for agent-to-agent work shipped: MCP standardizes agent-to-tool, A2A standardizes
agent-to-agent messaging, gateways add an enterprise perimeter. None of them answers the question
a counterparty actually has to ask before acting: **on whose behalf does this agent act, and what
is it allowed to do?** A bearer token proves someone completed an OAuth flow somewhere. It does
not say which human delegated which narrow authority to which agent.

agentframe is a small, working reference implementation of that missing layer. No blockchain, no
new trust anchor, no vendor, no directory to query. Ed25519 keys, signed passports, and a
verification pipeline you can read in an afternoon.

---

## What you need

- Python 3.11+
- [Ollama](https://ollama.com) with a local model, if you want to run the Qwen provider
  (`ollama pull qwen2.5:7b`)
- For the cross-network step only: any small VPS with nginx, and SSH access to it

---

## Install

```bash
git clone https://github.com/zafbangash/agent-mandate.git
cd agent-mandate
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q          # expect: 54 passed
```

The Python package is named `agentframe` (that is what you `import`); the project and repo are
`agent-mandate`.

If those 54 tests pass, the crypto, passport, replay, and injection layers all work on your box.

---

## Walkthrough: two agents, one trust root

Follow these in order. Every command is real; nothing is elided.

### Step 1 — Create the trust root

The root is the human principal. It signs passports and **never leaves your machine.**

```bash
mkdir -p keys
python cli/keygen.py keys/root.pem
```

```
agent_id=ag:xxxxxxxxxxxxxxxx
pubkey_b64=<ROOT_PUB_B64>          <- copy this
key_file=keys/root.pem (mode 600)
```

Keep `ROOT_PUB_B64`. Never share `root.pem`; the tool deliberately never prints a private key.

### Step 2 — Create the provider identity

This is the agent that *does* the work (here: answers questions using a local model).

```bash
python cli/keygen.py keys/provider.pem
```

Note its `agent_id` and `pubkey_b64` as `PROVIDER_PUB_B64`.

### Step 3 — Create the requester identity

This is the agent that *asks* — on a different machine in the real scenario. Run this on that
machine, and send back only the two public lines. The private key stays put.

```bash
python cli/keygen.py keys/requester.pem
```

Note its `agent_id` as `REQUESTER_AGENT_ID` and its `pubkey_b64`.

### Step 4 — The root issues a scoped passport

This is the delegation. The root states: *this specific agent acts for this principal, may do
exactly these things, until this date.*

```bash
python cli/issue_passport.py \
  --root keys/root.pem \
  --agent ag:REQUESTER_AGENT_ID \
  --principal alice \
  --grant ask@orion \
  --days 365 > keys/requester_passport.json
```

The passport is public material — it contains a public key and a signature, no secrets. Send it
to the requester over any channel you like.

Note `--grant ask@orion`. A passport granting only `ask@orion` **cannot** be used to call
`publish@blog`, and the provider will reject the attempt with `unauthorized` even though the
signature is perfectly valid. That is least-privilege delegation, enforced at verify time.

### Step 5 — Configure the provider node

Create `node_config.json` (copy `node_config.example.json`), filling in the values from above:

```json
{
  "root_pub_b64": "<ROOT_PUB_B64>",
  "orion_key": "keys/provider.pem",
  "orion_pub_b64": "<PROVIDER_PUB_B64>",
  "known_agents": {
    "ag:REQUESTER_AGENT_ID": "<REQUESTER_PUB_B64>"
  },
  "bind_host": "127.0.0.1",
  "bind_port": 8081,
  "ollama_model": "qwen2.5:7b"
}
```

### Step 6 — Start the provider

```bash
python qwen_provider_run.py
```

```
[orion-qwen] serving on http://127.0.0.1:8081/capability (orion=ag:..., model=qwen2.5:7b)
```

It binds to localhost only, on purpose. Nothing is exposed yet.

### Step 7 — Make the first verified request (same machine)

```bash
python check_node.py
```

You should see a signed receipt and `receipt_authentic=True`. At this point you have a complete
KYA loop on one box.

---

## Going cross-network

Everything above works locally. To let an agent on *another* machine — or another vendor's model —
reach your provider, put a dumb relay in front of it.

### Step 8 — nginx on the relay host

```nginx
server {
    server_name relay.example.com;
    location = /capability {
        proxy_pass http://127.0.0.1:8091/capability;
    }
}
```

The relay only forwards. It stores no keys and runs no model.

### Step 9 — Open the reverse tunnel from the provider machine

```bash
RELAY_HOST=user@relay.example.com ./tunnel.sh
```

This maps the relay's `127.0.0.1:8091` to your provider's `127.0.0.1:8081`. Your model never
leaves your machine, and the relay never holds anything cryptographic.

Run it under a process manager you trust — `tmux`, `systemd`, whatever. It is not
reboot-persistent on its own.

### Step 10 — Ask from the other machine

On the requester machine, with `keys/requester.pem` and the passport from Step 4:

```python
import json, sys
sys.path.insert(0, "src")
from agentframe.identity import Identity
from requester.ask_client import ask_via_orion

sender    = Identity.load("keys/requester.pem")
passport  = json.load(open("keys/requester_passport.json"))

receipt, authentic = ask_via_orion(
    "https://relay.example.com/capability",
    sender,
    "What is the boiling point of water at 2000 m elevation?",
    passport,
    "<PROVIDER_PUB_B64>",
)
print("authentic:", authentic)
print(receipt["answer"])
```

```
authentic: True
Approximately 93 °C ...
```

That is one vendor's agent getting verified work out of another vendor's model, across the public
internet, with no shared secret between them.

---

## What the provider checks on every request

Seven gates, in order. Any failure returns a **signed** error — so a rejection is as verifiable as
a success, and a client can prove it was actually refused.

| # | Check | Failure |
|---|---|---|
| 1 | Envelope is well-formed and version matches | `malformed`, `bad_version` |
| 2 | Capability is registered on the router | `unknown_capability` |
| 3 | Sender is a known agent | `unknown_sender` |
| 4 | Ed25519 signature over canonical bytes | `bad_signature` |
| 5 | Passport is root-signed, unexpired, agent matches, and **grants cover this capability** | `unauthorized`, `id_mismatch` |
| 6 | Nonce unseen and timestamp within a 300 s window | `replay_or_stale` |
| 7 | Untrusted free-text fields pass the injection wall | injection reason |

Only then does the request reach the model.

### The injection wall

Any field that will reach a reasoning core is declared `untrusted` by the capability and screened
deterministically before it gets there — no model in the loop, so the screen cannot itself be
talked out of its job. See `src/agentframe/injection.py`.

---

## Verify the security claims yourself

```bash
python run_negative_tests.py
```

Replay, tamper, expired passport, wrong-grant, and stranger-agent are all attempted and must all
be rejected — each rejection signed and verifiable.

---

## Layout

```
src/agentframe/     identity, passports, canonical encoding, replay, injection wall
src/provider/       router, capability endpoints, Ollama-backed qwen capability
src/requester/      client helpers
cli/                keygen, issue_passport
tests/              54 tests
paper/              the write-up (PDF)
```

## Status and limits

Working vertical slice, honestly scoped: a single hub, two agents, one root. No at-scale
deployment data. Reputation mechanics are future work. Trust today is "the root key personally
signed a passport for this agent" — there is no discovery and no web-of-trust yet. The migration
path toward W3C DIDs and Verifiable Credentials is discussed in the paper.

## Citing

The accompanying paper — *Who Does This Agent Work For? Cross-Platform Identity and Delegation for
Multi-Agent AI Networks* — is in `paper/`.

## License

MIT. See [LICENSE](LICENSE).
