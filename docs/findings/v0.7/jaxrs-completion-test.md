# JAX-RS provider completion — v0.7 Step 2 acceptance (DEC-073)

The #2 v0.6 carryover seed. DEC-073 completes the JAX-RS provider (DEC-062/066):
`@ApplicationPath` app-prefix, `@Produces`/`@Consumes` as a non-key Endpoint **property**
(`content_type`), and interface/abstract-return locators resolved via a single intra-repo
`implements` (INFERRED) — all on the **unchanged** `Endpoint`/`base.join`/`trace`/emit/
`serve` spine (`jaxrs.py` + the `Contract.content_type` field only).

## Fixture acceptance (`tests/fixtures/jaxrs_apppath_sample/`, all three features)

A `@ApplicationPath("/api")` `Application` subclass + a `@Path("/greetings")`
`@Produces(MediaType.APPLICATION_JSON)` resource (a CBV-style verb method, a method with an
overriding `@Produces({JSON, XML})`, a `@Consumes` method, and an **interface-return**
`widget()` locator → `WidgetService` with a single `WidgetServiceImpl`). 7 tests:

| feature | result |
|---|---|
| `@ApplicationPath` prefix | every route carries `/api` (`http::GET::/api/greetings`, …) — EXTRACTED |
| `@Produces`/`@Consumes` property | `list` → `produces=application/json` (class default); `create` → `produces=application/json; consumes=application/json`; `get` (method override) → `produces=application/json,application/xml` |
| content-type **never in the key** | `get`'s two media types collapse to one `http::GET::/api/greetings/{param}` Endpoint |
| `MediaType.*` constants + arrays + literals | mapped to media strings; braced arrays keep source order; string literals verbatim |
| interface-return locator | `widget()` → `WidgetService` interface → its single implementer `WidgetServiceImpl.read` → `http::GET::/api/greetings/widget` **INFERRED** |
| cross-stack join | TS `fetch("/api/greetings")` → `GreetingResource.list` ROUTES_TO (the prefix reaches the join) |

## Real-repo acceptance — jersey `bookstore-webapp`

Re-extracted with the DEC-073 provider (`examples/bookstore-webapp/src/main/java`):

| signal | v0.6 | **v0.7** |
|---|---|---|
| sub-resource route | `http::GET::/items/{param}` ← `Item.getXml` (EXTRACTED) | **unchanged — no regression** |
| content-type property | — | **`produces=application/xml,text/xml,application/json`** (real `@Produces({APPLICATION_XML, TEXT_XML, APPLICATION_JSON})` on `Item.getXml`) |

The DEC-066 sub-resource locator (`Bookstore.getItem` → `Item`) still resolves to exactly
the one EXTRACTED route, now carrying the real method-level content-type — proving the
`@Produces` property on real code with zero regression on the existing behavior.

## Honest finding — no `@ApplicationPath` repo in the local acceptance set (v0.8 note)

None of the local acceptance repos (`C:\Dev\scratch`, incl. all jersey-examples) use
`@ApplicationPath` — they configure the JAX-RS servlet mount via `web.xml`
(`<servlet-mapping>`), the older convention. The `@ApplicationPath` prefix is therefore
**fixture-proven** (the sample exercises it end-to-end, prefix → graph → consumer join), and
proving it on a real `@ApplicationPath`-annotated repo is a promoted v0.8 acceptance note
(reported, never fabricated, per KICKOFF §7). A future complement: read the `web.xml`
`<url-pattern>` mount as an alternate app-prefix source.

## Keystone / no fabrication

`jaxrs.py` + the additive `Contract.content_type` field (`contracts/base.py`, the DEC-067
`match_key` precedent) only — `base.join`/`registry`/`trace`/emit/`serve` untouched.
Content-type is a non-key display property (the DEC-057 version-property precedent), so it
never splits an Endpoint. An `Object` / multiply-implemented-interface / unresolvable
return → an honest **unmatched** locator (an Endpoint with no handler), never a guessed
sub-route. Goldens byte-identical (no fixture carries JAX-RS; `content_type` defaults `""`).

## Takeaway

The JAX-RS provider's documented gaps are closed (fixture-proven for all three; bookstore
proves the content-type property on real code with no sub-resource regression). The only
honest shortfall — a real `@ApplicationPath` repo — is captured by the fixture and promoted
to a v0.8 acceptance note (plus a `web.xml`-mount complement).
