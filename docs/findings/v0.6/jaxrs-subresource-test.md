# JAX-RS sub-resource locators — v0.6 Step 3 acceptance (DEC-066)

v0.5's JAX-RS provider (DEC-062) handled only decorator-on-method routes; a **sub-resource
locator** (a `@Path` method with no verb, returning a resource object) was invisible — so
jersey's `bookstore-webapp` scored **0 routes**. Step 3 follows the locator's return type
into its resource class and recurses, over the **unchanged** Endpoint/`base.join` spine.

## The keystone held

`git diff` (non-test src) = `contracts/http/providers/jaxrs.py` only (+ a
`resolve_name_to_files` import). `base.join`/`registry`/`trace`/emit/`serve` untouched —
an HTTP-coverage extension.

## Real-repo acceptance — `jersey-examples/bookstore-webapp`

`C:\Dev\scratch\jersey-examples\examples\bookstore-webapp` (Jakarta REST, BSD-2). The
canonical locator chain:

```java
@Path("/")  class Bookstore {
    @Path("items/{itemid}/")  public Item getItem(...) { ... }   // locator → Item
}
class Item {                       // sub-resource, no class @Path
    @GET  public Item getXml() {}  // the real route under the locator path
}
```

| | v0.5 | **v0.6** |
|---|---|---|
| jaxrs Endpoints (bookstore) | **0** | **1** |
| → resolved HANDLES (cross-file) | 0 | **1, EXTRACTED** |

Result: `http::GET::/items/{param}` **HANDLES** `…/resource/Item.java::Item.getXml`
(**EXTRACTED**, resolved cross-file from `Bookstore.java`'s locator return type `Item`).
`Bookstore.getXml()` at `@Path("/")` is correctly noise-filtered (root path); no
regression on the plain verb-method resources.

## Fixture acceptance (`tests/fixtures/jaxrs_subresource_sample/`)

A root `@Path("/store")` resource with a locator → `Item` (separate file) and a nested
locator `Item.getTrack()` → `Track` (third file), plus an `Object`-return locator and a TS
consumer. `tests/test_jaxrs_subresource.py` (3 tests):

| route | HANDLES → handler | confidence |
|---|---|---|
| `http::GET::/store/items/{param}` | `Item.java::Item.read` | EXTRACTED |
| `http::GET::/store/items/{param}/track` (nested locator) | `Track.java::Track.read` | EXTRACTED |
| `http::*::/store/anything` (`Object` return) | **none** (unmatched locator) | AMBIGUOUS |

Plus a materialized **ROUTES_TO**: `client.ts::loadItem` → `Item.java::Item.read` via
`http::GET::/store/items/{param}` (a sub-resource route joining a frontend consumer).

## Confidence discipline (DEC-066 / invariant 2)

A return type resolving to exactly one concrete resource class → EXTRACTED (a declared,
concrete fact); several candidates → AMBIGUOUS (every candidate, never one); `Object` /
interface / unresolvable → the locator is emitted **unmatched** (Endpoint, no HANDLES),
never a guessed sub-route — no fabrication.

## Takeaway

The jersey `bookstore-webapp` that scored 0 now resolves its sub-resource chain on the
real code (0 → 1 EXTRACTED cross-file route), with nested-locator recursion and honest
AMBIGUOUS-unmatched handling for `Object` returns — the keystone held, a pure
`providers/` extension.
