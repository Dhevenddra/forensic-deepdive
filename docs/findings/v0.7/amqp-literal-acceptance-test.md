# AMQP literal-key real-repo acceptance — v0.7 Step 3 (DEC-074)

The #3 v0.6 carryover seed. v0.6 (DEC-067) built the topic-exchange topology (key on the
shared-literal exchange; `reconcile_amqp` refines each exchange-matched pair: exact →
EXTRACTED, wildcard → INFERRED, provable non-match → DROP, multi → AMBIGUOUS) but its only
real repo (`rabbitmq-tutorials`) computes routing keys/bindings at runtime (`sys.argv`), so
every real join was INFERRED — the **EXTRACTED** (exact-literal) and **DROP** (provable
non-match) paths were fixture-only. Step 3 is a **validation/matrix** step: exercise those
paths on real upstream code and harden any matcher edge case. **Keystone:** matcher/
`reconcile_amqp` only — no `base.join`/`trace`/emit/`serve` change (no src change at all
this step beyond a regression test; the matcher was already correct).

## Matcher validated bug-free (the `#` boundary cases)

The PRD flagged the `#` zero-word boundary as the likely edge case. A battery over the
canonical RabbitMQ topic rules — including `#` at the trailing (`kern.#` ~ `kern`), leading
(`#.kern` ~ `kern`), and interior (`a.#.b` ~ `a.b`) boundaries, `#` alone matching the empty
key, and the must-not-match cases (`kern.*` ✗ `kern.a.b`, `*` ✗ ``, `a.#.b` ✗ `a.b.c`) —
**all pass; zero bugs**. Locked as a regression test (`test_amqp_binding_matches_boundary_battery`).

## Real-repo acceptance — `pika/pika` `examples/` (real upstream, inline literal keys)

Unlike the dynamic rabbitmq-tutorials, pika's own examples use **inline literal** keys.
Extraction over `examples/` (literal `match_key` carried EXTRACTED-grade):

| signal | result |
|---|---|
| AMQP publishers with a literal routing key | **4 / 4** (`amqp::test` rk=`test`, `amqp::com.micex.sten` rk=`order.stop.create`, `amqp::amq.topic` rk=`hello.world`) |
| AMQP subscribers with a literal binding | **4 / 6** (`amqp::com.micex.sten` bind=`order.stop.create`, `amqp::test_exchange` bind=`standard_key`, …) |

**The EXTRACTED exact-key topic join, on real code:** `producer.py` publishes
`basic_publish(exchange='com.micex.sten', routing_key='order.stop.create')` and
`consumer_simple.py` binds `queue_bind(exchange='com.micex.sten', routing_key='order.stop.create')`
— an **exact** literal match → **EXTRACTED `ROUTES_TO`** (`amqp::com.micex.sten`,
producer→consumer). This is the exact-literal path the dynamic tutorials could never reach.

**The AMBIGUOUS fan-out, on real code:** across the *full* `examples/`, the same publisher
also matches `consumer_queued.py` (which binds the identical exact key) — so the full-repo
run yields **two AMBIGUOUS** edges (1 publisher → 2 exact-binding subscribers). Correct: the
exact-match path fired, multiplicity (two real co-located consumers) → AMBIGUOUS fan-out,
never a silent pick.

## Honest finding — no co-located DROP pair in a single real repo (the federation seam, v0.8 note)

The **DROP** path (a publisher + a subscriber on the *same* exchange whose literal binding
*provably cannot* match the literal routing key) has **no co-located instance** in pika (or
any single scratch repo): publishers and subscribers for a given exchange almost always live
in **different services/repos** (the cross-repo federation seam v0.5 identified). A
provable non-match needs both literal sides *in one corpus*, which is exactly what a single
real repo rarely contains. So DROP stays **fixture-proven** (`amqp_topic_sample`: `auth.*`
binding vs a `kern.critical` publish → dropped, asserted end-to-end) + **matcher-validated**
(the battery), and a real co-located DROP pair is a promoted v0.8 acceptance note — together
with widening the net via Spring AMQP `@RabbitListener`/`@QueueBinding(key=)` extraction
(currently only `@KafkaListener` + pika are supported), which would surface more single-repo
literal-key topologies.

## No regression — `rabbitmq-tutorials/python`

Re-run: the v0.6 topology is unchanged — 3 `amqp::` exchanges (`logs`, `direct_logs`,
`topic_logs`), keys still dynamic (`sys.argv`) → INFERRED, exactly as v0.6 documented.

## Takeaway

The DEC-067 matcher is correct on the full RabbitMQ rule set (now regression-locked), and
the **EXTRACTED exact-key topic join + AMBIGUOUS fan-out** are proven on real upstream code
(`pika/examples`). The only path without a real single-repo instance — **DROP** — is
fixture-proven + matcher-validated and promoted to v0.8 (a co-located non-match pair, or
Spring AMQP extraction to widen the corpus), reported, never fabricated.
