# Django provider completion — v0.7 Step 1 acceptance (DEC-072)

The #1 v0.6 carryover seed. v0.6's Django provider recursed only **string** includes;
DEC-072 completes it: `include(<variable>)` recursion, CBV per-method verbs, DRF
`@action`, and deep dotted view paths — all on the **unchanged** `Endpoint`/`base.join`
spine (`django.py` only).

## Fixture acceptance (`tests/fixtures/django_v07_sample/`, all four features)

A root `mysite/urls.py` does `from apiapp import urls as api_urls; path("api/",
include(api_urls))`; the app `apiapp/urls.py` (reached via the **variable** include) holds
a CBV, a deep dotted view, and a DRF router with two `@action`s. `test_django_v07_completion`:

| feature | result |
|---|---|
| `include(<variable>)` recursion | every app route carries the `api/` parent prefix (`/api/account`, `/api/deep`, `/api/users`) — not bare |
| CBV per-method verbs | `AccountView` (get+post) → `http::GET::/api/account` **and** `http::POST::/api/account` (never `http::*::`) |
| deep dotted view path | `apiapp.deep.handlers.deep_view` → `http::*::/api/deep` HANDLES `apiapp/deep/handlers.py::deep_view` |
| DRF `@action` | `detail=True methods=['post']` → `http::POST::/api/users/{param}/set_password`; `detail=False` → `http::GET::/api/users/recent` |

## Real-repo acceptance — `wagtail/wagtail`

Re-extracted with the DEC-072 provider:

| signal | v0.6 | **v0.7** |
|---|---|---|
| django `Endpoint` nodes | 125 | **140** |
| cross-file `HANDLES` | 99 EXTRACTED | **105 EXTRACTED + 2 INFERRED** |
| endpoints with a located handler | 83 / 125 | **95 / 140** |
| endpoints with a multi-segment (prefixed) path | — | **99 / 140** |

The static module-level `include(<variable>)` mounts now resolve and recurse (the +15
endpoints carry their parent prefixes), and CBV routes carry specific verbs.

## Honest finding — the residual 9 are a *different* shape (v0.8 seed, not a defect)

The v0.6 ledger attributed wagtail's 9 collapsed endpoints (`/add`, `/multiple/add`, …) to
plain `include(<variable>)`. Re-investigation shows they are mounted **one level deeper** —
via wagtail's **hook system**:

```python
@hooks.register("register_admin_urls")
def register_admin_urls():
    return [path("images/", include(admin_urls, namespace="wagtailimages"))]
```

The `images/` prefix + the `include(admin_urls)` variable-include *are* there, but inside a
**decorated function's return value**, not a module-level `urlpatterns = [...]`. The
provider scans module-level `urlpatterns`, so these stay bare (collapsed). This is a
genuinely distinct mechanism — closer to the registry-dispatch protocol (a function
returning routes, dynamically registered) than to a URLconf table — and is a clarified
**v0.8 seed** (model `@hooks.register("register_admin_urls")` URL functions), reported, not
fabricated. The documented DEC-072 seed (static module-level `include(<variable>)`) is
delivered and proven; wagtail simply revealed its own collapse is one mechanism deeper.

## Keystone / no fabrication

`base.join`/`trace`/emit/`serve` untouched (a `providers/` + resolver change). An
unresolvable variable/view → the include is dropped (the file stays a root → honest bare
routes) / an honest unmatched Endpoint — never a synthetic prefix or `symbol_id`. Goldens
byte-identical (no fixture carries `urlpatterns`).

## Takeaway

The Django provider's four documented gaps are closed (fixture-proven; wagtail 125 → 140
Endpoints with prefixes + specific verbs), and the wagtail re-investigation reframed its
residual collapse as a hook-registered-URL shape — a precise v0.8 seed.
