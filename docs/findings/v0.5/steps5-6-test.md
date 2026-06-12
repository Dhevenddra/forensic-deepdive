# Steps 5–6 — service-to-service + framework breadth (gRPC · messaging · NestJS · JAX-RS)

Real-repo acceptance for the coverage track (DEC-060/061 gRPC + messaging; DEC-062
NestJS + JAX-RS). Four small upstream repos from `C:\Dev\scratch`. The fixtures
already prove the joins; these runs test the extractors on real generated/framework
code — and surfaced three honest refinements for v0.6.

| repo | protocol | result |
|---|---|---|
| `grpc/grpc` `examples/python/route_guide` | gRPC | **16 ROUTES_TO** (stub→servicer), all AMBIGUOUS — honest (dual sync+async servicer) |
| `rabbitmq/rabbitmq-tutorials` `python/` | messaging | **5 queue ROUTES_TO** incl. a clean `rpc_client→rpc_server` EXTRACTED |
| `nestjs/nest` `sample/01-cats-app` | NestJS | **3 routes** clean (`GET /cats`, `GET /cats/{param}`, `POST /cats`) ✅ |
| `eclipse-ee4j/jersey` `examples/helloworld` | JAX-RS | **1 route** clean (`GET /helloworld` → `HelloWorldResource.getHello`) ✅ |

## gRPC — joins materialize; bare keying reveals two AMBIGUOUS shapes

The stub↔servicer join works on real generated gRPC code. On `route_guide`
(55 symbols), **16 `ROUTES_TO`** materialize — every `route_guide_client.py` /
`asyncio_route_guide_client.py` stub call joins its `RouteGuideServicer` method:

```
route_guide_client.py::guide_get_one_feature → RouteGuideServicer.GetFeature  grpc::RouteGuide/GetFeature  AMBIGUOUS
…::guide_list_features                       → RouteGuideServicer.ListFeatures grpc::RouteGuide/ListFeatures AMBIGUOUS
```

All **AMBIGUOUS** — **honestly**, because this example ships **two** servicer
implementations of the same service (`route_guide_server.py` **and**
`asyncio_route_guide_server.py`), so `grpc::RouteGuide/GetFeature` has two real
providers → emit both, never pick one (DEC-025/037). That is the correct output.

**Discovery — the broad `examples/` run (585 symbols) produced 975 AMBIGUOUS joins.**
The gRPC examples monorepo reuses the **same** `Greeter`/`SayHello` service name across
~18 example subdirs (auth/, uds/, retry/, timeout/, …), so the **bare `<Svc>/<Method>`
key collides**: every `Greeter` client joins every `Greeter` servicer (cartesian).
This validates the **deferred package-qualified keying** (DEC-060): the generated
module name (`helloworld_pb2_grpc` vs `route_guide_pb2_grpc`) **is** statically
recoverable on both sides and would disambiguate the collision — but note it does **not**
reconcile trivially with the `.proto`'s own `package` declaration (`package routeguide;`
≠ module `route_guide_pb2_grpc`), so it's a real v0.6 enhancement (map proto-file →
generated module), not a one-line change. Flagged, not rushed.

(Note: spec-backed EXTRACTED gRPC joins require the `.proto` to be **inside** the
extracted tree; route_guide's `.proto` lives in a sibling `examples/protos/` not under
the run root, so these joins are AMBIGUOUS-not-spec-backed here. The spec-backed
EXTRACTED path is proven on the `grpc_sample` fixture.)

## messaging — direct queues join cleanly; topic-exchange binding deferred

`rabbitmq-tutorials/python` (27 symbols) → **5 `queue::` `ROUTES_TO`**, 3 queue
Endpoints (`queue::hello`, `queue::rpc_queue`, `queue::task_queue`). The cleanest:

```
rpc_client.py::FibonacciRpcClient.call → rpc_server.py  queue::rpc_queue  EXTRACTED
new_task.py → worker.py                                 queue::task_queue AMBIGUOUS
```

`rpc_client→rpc_server` is a textbook publish→subscribe join, EXTRACTED. Two honest
notes: (1) a script that **both** `queue_declare`s and `basic_publish`es at module
scope (e.g. `send.py`) produces a **self-`ROUTES_TO`** (it is both provider and
consumer of `queue::hello`) — correct but cosmetically noisy; (2) **topic exchanges =
0**: the tutorials' topic examples publish with a `routing_key` to a **topic exchange**
and bind a generated queue with a pattern (`queue_bind(routing_key='kern.*')`) — the
binding key ≠ a `basic_consume(queue=literal)`, so the publish/subscribe sides don't
share a key. Modeling RabbitMQ **exchange+binding-key** topology (beyond direct named
queues) is a clean v0.6 deferral.

## NestJS — clean

`sample/01-cats-app` (54 symbols) → all three `CatsController` routes detected exactly:
`GET /cats` (findAll), `GET /cats/{param}` (findOne), `POST /cats` (create). The
`@Controller('cats')` prefix + verb-decorator + enclosing-class-guard extractor works
verbatim on real NestJS.

## JAX-RS — clean on a plain resource; locators deferred (confirmed)

`examples/helloworld` (7 symbols) → `GET /helloworld` → `HelloWorldResource.getHello`,
clean. **`examples/bookstore-webapp` yielded 0** — and that's the **documented DEC-062
deferral confirmed on real code**: the bookstore is built almost entirely on
**sub-resource locators** (`@Path` methods that *return* a resource object rather than
carrying a `@GET`/`@POST` verb), which v0.5 intentionally doesn't model. The plain
verb-annotated resource path works; the locator pattern is the honest v0.6 gap.

## Takeaway

All four coverage-track protocols **fire on real upstream code** — NestJS and JAX-RS
plain resources clean, messaging direct-queue joins clean (incl. an EXTRACTED
rpc pair), gRPC stub↔servicer joins materializing with honest AMBIGUOUS where the code
genuinely has multiple impls. And the runs paid for themselves in **three concrete
v0.6 refinements** (gRPC package-qualified keying, RabbitMQ exchange/binding topology,
JAX-RS sub-resource locators) — the findings-drive-the-next-arc loop, exactly as v0.4's
Superset shortfall drove v0.5.
