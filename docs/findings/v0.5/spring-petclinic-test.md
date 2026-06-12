# spring-petclinic — v0.5 Step 4 acceptance (the DI/ORM traceability tail)

The canonical Spring repo, the DEC-059 acceptance target for the DI/ORM tail:
`@Autowired`/constructor injection + JPA `@Entity`/`@Table`. Does the
service→inject→repo→table chain materialize on real Spring code?

## Run summary

| | |
|---|---|
| Date | 2026-06-12 |
| Repo | spring-projects/spring-petclinic (`C:\Dev\scratch`, Apache-2.0) |
| Tool version | v0.5 HEAD (DEC-055 → DEC-062) |
| Symbols | **143** · extract **2 s** |

## DI/ORM tail — fully materialized

| edge | count | confidence | note |
|---|---|---|---|
| `INJECTS` | **6** | all **INFERRED** | every controller → its repository |
| `PERSISTS_TO` | **6** | all **EXTRACTED** | every `@Entity` → its `@Table` |
| `DbTable` nodes | **6** | — | `owners`, `pets`, `vets`, `types`, `specialties`, `visits` |
| Spring HTTP routes | **15** | — | the `@GetMapping`/`@PostMapping` controllers |

**`INJECTS` (constructor injection → repository):**

```
OwnerController     → OwnerRepository    (INFERRED)
PetController       → OwnerRepository    (INFERRED)
VisitController     → OwnerRepository    (INFERRED)
PetController       → PetTypeRepository  (INFERRED)
PetTypeFormatter    → PetTypeRepository  (INFERRED)
VetController       → VetRepository      (INFERRED)
```

**`PERSISTS_TO` (`@Entity` → `@Table`), all EXTRACTED:**

```
Owner → table::owners     Pet → table::pets       Visit → table::visits
Vet   → table::vets       PetType → table::types  Specialty → table::specialties
```

## Why the injections are INFERRED (an honest resolver detail)

The repositories are **Spring Data interfaces** (`interface OwnerRepository extends
Repository<Owner, Integer>`) with **no in-repo concrete impl** (Spring generates it
at runtime). So the interface→impl ladder finds no implementation and binds the
injection to the **interface itself**. And because petclinic uses **same-package**
classes (Java needs no explicit `import` for those), the injected type resolves not
by an import but by the **single cross-file same-language fallback** → **INFERRED**
(one candidate definition, matched by name). That is the correct confidence: we
located the dependency by a name match across files, not by a direct import or a
located concrete bean — honest, not over-claimed as EXTRACTED.

The `@Entity`→`@Table` bindings, by contrast, are **EXTRACTED**: `@Table` names are
literal syntactic facts in the same file as the model.

## What this unlocks

`trace('OwnerController.<method>', downstream)` can now walk past the handler:
controller →`INJECTS`→ `OwnerRepository` → … → `Owner` →`PERSISTS_TO`→ `table::owners`
— the service→repository→table tail the v0.4 `trace` `boundary` note promised for
v0.5, now delivered (DEC-059). The `DbTable` node is the one DEC'd new-node exception
to the Endpoint-reuse keystone.

## Takeaway

The DI/ORM tail works cleanly on the canonical Spring repo with a fully honest
confidence split: literal ORM table names → EXTRACTED, interface-resolved injections
→ INFERRED, and (where a repo has multiple impls) AMBIGUOUS-all — proven on the
`di_ladder_sample` fixture, not present in petclinic's single-impl world.
