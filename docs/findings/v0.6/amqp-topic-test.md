# AMQP topic-exchange + binding-key topology — v0.6 Step 4 acceptance (DEC-067)

v0.5's messaging contract (DEC-060) keyed RabbitMQ on the publisher's `routing_key` as if
it were a queue name — correct only for the direct/default-exchange pattern. Topic
exchanges route `(exchange, routing_key)` → `(exchange, binding_pattern)` with `*`/`#`
wildcards, and v0.5 had no `queue_bind` handling → **0 exchange-based joins**. Step 4
keys on the **shared-literal exchange** and refines the routing match in a contract-layer
prune, over the **unchanged** `base.join`.

## The keystone held

`base.join` matches `amqp::<exchange>` by exact key (unchanged — the exchange is the
shared literal both sides write). The `*`/`#` wildcard matching lives in
`messaging/normalize.py` + the new `base.reconcile_amqp` prune (the DEC-060
`reconcile_spec_backed` precedent), wired once in `ContractPhase.run` after `join`.
`base.join`/`trace`/emit/`serve` untouched.

## Confidence ladder (DEC-067 / invariant 2)

| publisher routing_key vs subscriber binding | result |
|---|---|
| literal equality (`kern.critical` = `kern.critical`) | **EXTRACTED** |
| wildcard match (`kern.critical` ~ `kern.*`) | **INFERRED** |
| provable non-match (`kern.critical` ✗ `auth.*`) | **DROP** (no edge) |
| several subscribers match one publisher | **AMBIGUOUS** (every candidate) |
| either key dynamic / non-literal (unknown) | **INFERRED** (exchange shared, routing indeterminate) |

## Real-repo acceptance — `rabbitmq-tutorials/python`

`C:\Dev\scratch\rabbitmq-tutorials/python` (Apache-2.0). v0.5 = **0** exchange ROUTES_TO;
v0.6:

| | v0.5 | **v0.6** |
|---|---|---|
| `amqp::<exchange>` Endpoints | 0 | **3** (`direct_logs`, `logs`, `topic_logs`) |
| exchange ROUTES_TO | 0 | **3** (all INFERRED) |
| total messaging ROUTES_TO | (queues only) | **8** |

The three materialized exchange joins:
- `emit_log_topic.py → receive_logs_topic.py` via `amqp::topic_logs` (the headline topic exchange)
- `emit_log_direct.py → receive_logs_direct.py` via `amqp::direct_logs`
- `emit_log.py → receive_logs.py` via `amqp::logs` (fanout)

All **INFERRED** — honestly: the tutorials compute their routing keys/bindings at runtime
(`routing_key = sys.argv[1]`, `binding_keys = sys.argv[1:]`), so the keys are statically
unknown. The exchange is the one proven shared literal → INFERRED (never EXTRACTED, never
dropped). This is the indeterminate-key honesty rule in action on real code.

## Fixture acceptance (`tests/fixtures/amqp_topic_sample/`)

The literal-key matching the dynamic tutorial can't exercise — a topic publisher per
exchange + subscribers binding exact/wildcard/non-match/dual patterns (`tests/
test_amqp_topic.py`, 6 tests):

- `emit_log` (`kern.critical`) → `bind_kern` (`kern.*`) **INFERRED**; `bind_auth` (`auth.*`) **dropped**.
- `emit_event` (`user.created`) → `bind_event` (`user.created`) **EXTRACTED** (exact).
- `emit_multi` (`a.b`) → both `bind_multi_star` (`a.*`) and `bind_multi_exact` (`a.b`) **AMBIGUOUS** (fan-out).

Plus pure-unit coverage of `amqp_binding_matches` (`*`/`#` rules, incl. `#` matching zero
words) and `reconcile_amqp` (prune + non-AMQP passthrough).

## Takeaway

RabbitMQ topic exchanges now join publisher→subscriber on the real tutorials (0 → 3
exchange ROUTES_TO) keyed on the exchange, with `*`/`#` wildcard matching, an honest
DROP for provable non-matches, AMBIGUOUS fan-out, and an indeterminate→INFERRED rule for
dynamic keys — all in the matcher + a contract-layer prune, with `base.join` untouched.
