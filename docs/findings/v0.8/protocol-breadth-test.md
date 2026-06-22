# Protocol breadth + remaining repos — v0.8

Concise notes on the rest of the acceptance set (the four deep narratives are in their own
`*-test.md`; the precision claims are in [`precision-revalidation.md`](precision-revalidation.md)).

## spring_react_demo — clean cross-stack (HTTP)

4 files (Java + React/TS), 4 ROUTES_TO `[E] 2 / [I] 2 / [A] 0`. The smallest, clearest proof:
`addUser` → `POST /api/users` → `UserController.createUser` (EXTRACTED, confirmed by
`forensic trace addUser`). ARCHITECTURE.md renders 2 solid + 2 dashed edges. `--emit-vault`
produced the full Obsidian vault here. The reference case for the cross-stack story.

## spring-petclinic — DI + ORM (no HTTP routes)

30 Java files, 0 HTTP ROUTES_TO — but ARCHITECTURE.md is **not** empty: it shows `injects`
(Controller→Repository) and `persists` (entity→table) edges. Good demonstration that
"cross-boundary" ≠ "HTTP only", and that the Spring `@Autowired` / JPA extraction is intact.

## fastapi — HTTP + the honest AMBIGUOUS tier (Python)

75 source files / 1006 edges, 15 routes (`[E] 0 / [I] 1 / [A] 14`). The AMBIGUOUS dominance is
*correct* — duplicate `/docs` paths across doc tutorials (see precision-revalidation §DEC-083).
AGENT_BRIEF is high-signal: `FastAPI` most-called (330 callers), `applications.py`↔`routing.py`
co-change (59 commits), `release-notes.md` biggest churn (3373 commits). One INFERRED route is a
registry-dispatch (`registry::ml_models::answer_to_everything`) — protocol breadth beyond HTTP.

## ripgrep — intra-process Rust CLI

81 Rust files / 96 edges, 0 routes. The negative control: ARCHITECTURE.md degrades honestly
("No cross-boundary architecture detected … intra-process"). No fabricated diagram, no invented
routes. MAP/HOTPATHS still give a real call-graph/centrality view for a non-service codebase.

## rabbitmq-tutorials — messaging across 7 languages

204 files (Java 88, Go 32, Rust 26, Python 17, JS 16, Swift 13, Dart 12) / 174-file graph,
8 ROUTES_TO `[E] 1 / [I] 3 / [A] 4` over the AMQP topic protocol. Confirms the messaging
extractor and the polyglot inventory survive a genuinely mixed-language tutorial repo.
