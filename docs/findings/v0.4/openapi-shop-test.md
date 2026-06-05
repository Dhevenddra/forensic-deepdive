# openapi-shop — v0.4 purpose-built test (the Item-I codegen shortcut)

A **purpose-built** repo for the **Item I / DEC-048** showcase: a *committed*
`openapi.json` + a generated-style TS client + a FastAPI backend that implements
**2 of the 3** documented operations. Superset *generates* its OpenAPI spec at
runtime, so it can't prove the committed-spec path — per PRD §4.9 we pick a small
purpose-chosen repo and flag here that **this repo is the one that proves the
shortcut**.

## Repo shape (`C:/Dev/scratch/openapi_shop`, local-only)

```
openapi.json                 3 operations: getProduct, createProduct, getInventory
backend/app.py               FastAPI: get_product, create_product   (NO inventory handler)
client/src/shopClient.ts     templated axios: getProduct/createProduct/getInventory
```

| | |
|---|---|
| Date | 2026-06-05 |
| Tool version | v0.4 HEAD (`a5b3e02`) |
| spec format | JSON (stdlib `json`, zero-dep path — DEC-048) |

## Gate #3 — spec-backed EXTRACTED joins

All three spec operations become `spec_backed=True` Endpoints:

```
http::GET::/api/products/{param}   spec_backed=True
http::POST::/api/products          spec_backed=True
http::GET::/api/inventory          spec_backed=True
```

The headline: the client URLs are **templated** (`/api/products/${id}`) — on their
own a template consumer joins at **INFERRED** (DEC-047). Because the matching
providers are spec-backed, DEC-048 upgrades the joins to **EXTRACTED**:

| ROUTES_TO | confidence | why |
|---|---|---|
| `getProduct → get_product` | **EXTRACTED** | templated client, but provider spec-backed |
| `createProduct → create_product` | **EXTRACTED** | literal POST, provider spec-backed |

This is the gap GitNexus has open (their issue #306, no OpenAPI shortcut) — and
we're Apache-2.0 to their PolyForm-Noncommercial.

## Spec-coverage metric (the Item-L deliverable)

The set is **directly countable** because `trace`'s `unlocated=True` and the
spec-only Endpoints expose it:

| | count | members |
|---|---|---|
| spec operations | **3** | getProduct, createProduct, getInventory |
| located handlers | **2** | get_product, create_product |
| documented-but-unlocated | **1** | **getInventory** (in the spec, no backend handler) |

`getInventory` still produces an **EXTRACTED `CALLS_ENDPOINT`** to
`http::GET::/api/inventory` with **no HANDLES** — the honest "calls an endpoint we
can't locate" (DEC-043), here because the operation is documented but unimplemented.
Hit rate: **2/3 = 67 %** of documented operations resolve to a located handler; the
unresolved third is surfaced, not hidden.

## Honest finding — generated-marker interaction (DEC-021 ↔ DEC-048)

The first cut of the client carried an `// AUTO-GENERATED … DO NOT EDIT` header.
DEC-021 correctly classified it `generated` and **excluded it from the graph** —
so the consumer side vanished and **0 ROUTES_TO** materialized, even though the
providers were spec-backed. Committing the client as ordinary source (as many
projects do with their checked-in API clients) restores the EXTRACTED joins above.

**Takeaway (logged for v0.5):** generated API clients are exactly where the
codegen shortcut is most valuable, yet the generated-role exclusion can drop them.
A future option — *keep spec-generated clients in the graph (like `example`,
demoted but present) when they participate in a spec-backed contract* — would let
the shortcut fire on DO-NOT-EDIT clients too. Not a v0.4 gate item; the gate is met
with the client as source.

## Assessment

- **Gate #3 (codegen shortcut → spec_backed EXTRACTED): ✅** Two templated-client
  joins upgraded to EXTRACTED purely via the committed spec; 3/3 endpoints
  spec-backed; documented-but-unlocated countable (2 located / 1 unlocated).
- This repo (not Superset) is the one that proves the committed-spec shortcut.
