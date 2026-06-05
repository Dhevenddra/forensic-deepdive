# spring-react-demo — v0.4 purpose-built test (clean cross-language ROUTES_TO)

A **purpose-built** Spring+React fixture with clean, known routes — the §4.9
"clean cross-language join" check. spring-petclinic (the v0.3 Spring repo) is
Thymeleaf/JSP server-rendered with **no React fetch**, so it's a *provider-only*
check; this repo adds the matching TS frontend so the **TS→Java ROUTES_TO** join
is exercised end-to-end with known-correct expectations.

## Repo shape (`C:/Dev/scratch/spring_react_demo`, local-only)

```
backend/.../com/acme/UserController.java    @RequestMapping("/api/users")
                                              GET /{id} createUser POST listUsers GET
backend/.../com/acme/OrderController.java    @RequestMapping("/api/orders")  GET /{orderId}
frontend/src/api.ts                          fetch/axios → /api/users[/${id}], /api/orders/${orderId}
```

| | |
|---|---|
| Date | 2026-06-05 |
| Tool version | v0.4 HEAD (`a5b3e02`) |
| Files | 4 source (java 2, tsx 1, ts 1) |

## Gate #2 (cross-stack) — TS→Java ROUTES_TO + confidence split

4 endpoints, 4 HANDLES, and **4 ROUTES_TO joining the React client to the Spring
controllers across languages**, with the DEC-047 confidence model on display:

| ROUTES_TO (consumer → provider) | endpoint | confidence | why |
|---|---|---|---|
| `addUser → UserController.createUser` | `POST /api/users` | **EXTRACTED** | literal path **and** method on both sides |
| `listUsers → UserController.listUsers` | `GET /api/users` | **EXTRACTED** | literal path + method both sides |
| `loadUser → UserController.getUser` | `GET /api/users/{param}` | **INFERRED** | client templates `${id}` → param |
| `loadOrder → OrderController.getOrder` | `GET /api/orders/{param}` | **INFERRED** | client templates `${orderId}` → param |

**Split: 2 EXTRACTED / 2 INFERRED / 0 AMBIGUOUS** — exactly the DEC-047 rule:
only param-free literal routes with a literal provider earn EXTRACTED; a templated
client URL caps the join at INFERRED even when the match is unique. No false
EXTRACTED, no AMBIGUOUS (every path is unique → no multi-provider collisions).

`trace('loadUser', downstream)` walks the cross-language chain:
`frontend/src/api.ts::loadUser` —`GET /api/users/{param}`→
`…/UserController.java::UserController.getUser`. The Spring class-level
`@RequestMapping("/api/users")` prefix is correctly joined with the method-level
`@GetMapping("/{id}")` to form the contract.

## Honest finding — `example`-role false positive on `com.example.demo`

The first cut used the conventional Spring package `com.demo`. DEC-049's
`example`-role heuristic matches a path **segment** equal to `demo`/`demos`/
`example`/`sample`/… — so `backend/.../com/demo/UserController.java` was
classified **`example`** and demoted out of the source count (still in the graph,
so ROUTES_TO were unaffected). But **`com.example.demo` is the default Spring
Initializr package**, meaning a vanilla Spring Boot starter's main code would be
mis-demoted to `example`.

Renaming to `com.acme` restored all 4 files to `source`. **Logged for v0.5:** the
`example`-role matcher should not fire on `demo`/`example` segments that are part
of a Java package path under `src/main/` (or require the segment to be a
top-level/leaf directory). Not a v0.4 gate item — the cross-stack joins are
correct in both cases (example files stay in the graph); it's a
classification-precision follow-on.

## Assessment

- **Gate #2 (cross-stack ROUTES_TO + honest confidence split): ✅** on clean
  known routes — 4/4 TS→Java joins correct, **2 EXTRACTED / 2 INFERRED**, `trace`
  walks the chain. AGENT_BRIEF 1,504 B ≤5120 ✅.
- Discovered + logged the `com.example.demo` `example`-role false positive (v0.5).
