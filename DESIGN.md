# Agent Framework — Design Spec
*"Napster for agents" — a substrate for personal-assistant agents to identify each other, exchange utility, and collaborate across networks.*

Status: **DRAFT for review** · 2026-06-17
Locked decisions: **hub-first** (decentralize later) · **Ed25519** keypair identity (DID-format later).

---

## 1. Purpose & ideology

**Why:** the substrate for personal-assistant agents to find each other's in-progress work and collaborate across networks — **with identity and trust built in from the start, not bolted on.**

**Anchoring use case (Phase 0):** instead of giving a family member website credentials, *her thoughts → her agent → Orion → website*. She expresses intent to her own agent; her agent asks Orion (who holds the publish capability); Orion verifies and does it. **You share intent, not access.**

**Ideology (governs every decision):**
- **Utility over attention; exchange over status.** Success = the agent's fastest path to its goal. No feed, no upvotes. The inversion of the attention economy.
- **Marketplace, not social network.** Match agent *need ↔ surplus* (data, answers, capabilities). Discovery index = the catalog.
- **Reputation = realized usefulness**, never popularity. Hard to game because gaming it requires delivering real utility.
- **Identity is the immune system.** A clean utility-market requires real identity, or it gets sybil-attacked.
- **Systems, not ad-hoc.** Even Phase 0 is the first *vertical slice* of the real architecture, never a throwaway.

---

## 2. Architecture

The reference systems aren't alternatives — **each nails one layer.** We compose them:

| Layer | Borrowed from | Mechanism |
|---|---|---|
| **Identity** | Signal / iMessage | Ed25519 keypair = identity; proven by signature |
| **Discovery** | Napster index + IRC channels | catalog of who-offers/has-what, subscribable by topic |
| **Messaging** | Signal (E2E + store-and-forward) | encrypted; offline agents still receive |
| **Capability call** | **MCP** | typed, schema'd, authorized "powers" — not chat |
| **Bulk transfer** | Napster / DCC | big payloads peer-to-peer; hub only introduces |

**Topology — hub-first.** A central **coordination hub** (runs on the relay host to start) does registry + discovery + message relay. It relays **end-to-end-encrypted** payloads it cannot read (Signal model) and **store-and-forwards** for offline agents. The hub is a convenience, not a trust root — identity and authority are cryptographic and survive the hub being replaced or federated later.

**Framework = identity + trust + discovery + transport, wrapped around MCP capability calls.**

---

## 3. Identity framework (Ed25519)

- Every agent owns an **Ed25519 keypair**. Its **identity = its public key** (agent ID = the key fingerprint, e.g. `ag:<base32(sha256(pubkey))[:16]>`).
- Authentication = **signing a challenge / signing every message**. The private key never leaves the agent. Nothing is shared to prove identity → works cross-network, no central password DB.
- **Root of trust:** the family owner (the operator) holds a **principal/root keypair**. It signs the **agent passports** below. (Family-scoped PKI-of-one now; generalizes to web-of-trust / multiple roots later.)
- **Agent passport (delegation credential):** a principal-signed statement binding an agent to a principal and its allowed powers:
  ```json
  { "agent": "ag:…", "principal": "alice",
    "grants": ["publish@blog.example.com"],
    "issued": 1781..., "expires": 1789..., 
    "sig": "<root_sig over the above>" }
  ```
- **Registry:** the hub maps `agent_id → {pubkey, display, passport}` for lookup/discovery. The registry is convenience; **the key proves identity, the registry doesn't.** A stolen/forged registry entry can't forge a signature.

---

## 4. Trust framework

Two orthogonal axes.

**A. Data classification — with a hard wall.**
Every datum carries a tier: `PUBLIC` / `SHAREABLE` / `PRIVATE` / **`NEVER`**.
- `NEVER` = private keys, credentials, raw secrets. Enforced **in the transport as a wall, not a policy**: NEVER-class material has no code path that serializes or transmits it. Not configurable, not overridable. **This is the absolute maxima.**
- The other tiers gate sharing by the requester's trust tier (below).

**B. Per-relationship trust + capability scope.**
- **Trust tiers:** `FAMILY` (high) / `KNOWN` / `STRANGER` (default deny). Set by the principal; later augmented by **outcome-based reputation** (did this agent's data/answers actually help — not popularity).
- **Capability scopes:** least-privilege. A passport granting `publish@blog` cannot `delete@*`. Every capability call is checked against the caller's grants.

Together these are the framework's immune system and what makes the eventual marketplace un-sybil-able.

---

## 5. Communication framework (the hub)

The hub provides:
1. **Registry** — agents register `pubkey + passport`; others look them up.
2. **Discovery** — agents advertise capabilities/data offers under a topic taxonomy (`area/category/subcategory`); others subscribe/query. (The marketplace catalog.)
3. **Relay** — store-and-forward message delivery between agents. Payloads are **end-to-end encrypted to the recipient's pubkey**; the hub forwards ciphertext it cannot read. Offline recipients get messages on reconnect.

**Capability requests ride as typed MCP calls**, not freeform chat (see §7). The hub routes; MCP defines the contract.

Central-first is pragmatic and buildable. Decentralization (multiple hubs / hub-optional P2P) is Phase 3 and is *enabled* by the cryptographic identity — nothing about identity or authority depends on a single hub.

---

## 6. Transfer framework

- **Small** (requests, messages, small results): through the hub relay.
- **Large** (datasets, files): **direct peer-to-peer, DCC-style** — the hub brokers the introduction, the bytes flow agent↔agent; relay-fallback when NAT/firewall blocks P2P.
- **Everything encrypted.** `NEVER`-class material is never a valid transfer target (§4A).

---

## 7. MCP as the capability layer

An agent exposes its "powers" as an **MCP server**; each power is a typed, schema'd tool with an input contract. The framework wraps MCP with:
- **who** may call it (identity + passport scope),
- **how** the call reaches it (hub relay / direct), 
- **proof** the call is authentic (signature) and authorized (delegation).

So "Orion can publish to the blog" is concretely: *Orion runs an MCP server exposing `publish_blog(title, markdown, …)`; the framework lets a verified, authorized, remote agent invoke it safely.*

---

## 8. Phase 0 — the vertical slice (buildable spec)

**Goal:** Alice's agent (or the operator on her behalf) publishes a blog post to `blog.example.com` without ever touching the server. Exercises identity → authority → capability → transport with 2 nodes and 1 capability.

**Components**
1. **Minimal blog** at `blog.example.com`: markdown posts → rendered list (reuse Ali's `stories.jsx`-style data model + nginx/sudo deploy). Replaces the current placeholder.
2. **Orion capability provider** (on the relay host): an MCP server exposing `publish_blog`, fronted by a small **request endpoint** (HTTPS POST) that does verification then invokes the tool.
3. **Requester** (Alice's agent): holds an Ed25519 keypair + a passport signed by the root key granting `publish@blog.example.com`.

**Request message (v1)**
```json
{ "v": 1, "from": "ag:…", "to": "orion", "capability": "publish_blog",
  "ts": 1781…, "nonce": "<random-128bit>",
  "payload": { "title": "...", "subtitle": "...", "tags": ["..."], "markdown": "..." },
  "passport": { … signed delegation … },
  "sig": "<Ed25519 over canonical(message minus sig)>" }
```

**Verification flow (Orion)**
1. `ts` fresh (±300s) and `nonce` unseen → replay protection.
2. `sig` verifies against `from` pubkey over the canonical message → **authentic**.
3. `passport`: signed by the root key, `passport.agent == from`, grants cover `publish@blog.example.com`, not expired → **authorized**.
4. Validate payload schema + sanitize content (family-facing site).
5. Render post → write to blog data → deploy (existing nginx/sudo path).
6. Return signed receipt `{status, url, sig}`.

**Transport (Phase 0):** requester → signed HTTPS POST → Orion endpoint. (Single node = hub+provider; the relay/E2E/store-forward of §5 arrive in Phase 1 when there are ≥3 agents.)

**Security covered in Phase 0:** spoofing → signatures; replay → ts+nonce; over-reach → passport scope; secret leakage → `NEVER` wall (no key ever in a message). 

---

## 9. Roadmap

- **Phase 0** — vertical slice: minimal blog + `publish_blog` capability + Ed25519 identity + passports + signed requests. *(this spec)*
- **Phase 1** — the hub: registry + discovery + E2E store-and-forward relay; classification wall + trust tiers; ≥3 family agents, more capabilities.
- **Phase 2** — marketplace: capability/data discovery by taxonomy, outcome-based reputation, DCC-style bulk P2P transfer.
- **Phase 3** — decentralize / generalize past the family: DID/verifiable-credential identity, multiple/federated hubs, cross-network trust.

---

## 10. Deferred decisions (revisit at the phase boundary, not now)
- Reputation scoring math (Phase 2).
- Marketplace pricing / token-economics — *who pays whose compute* (Phase 2).
- Hub federation & discovery-of-hubs (Phase 3).
- DID method + VC schema for the migration (Phase 3).
- Transport for Phase 1 relay (WebSocket vs gRPC vs message queue).
