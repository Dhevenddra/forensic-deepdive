# HOTPATHS — spring-petclinic

> The code most other code depends on, and the files that change most.
> **Confidence:** facts are `EXTRACTED` (deterministic from AST and git) unless a section / line says otherwise.

## Dependency hot spots

Symbols ranked by **distinct callers** — the count of distinct symbols with a `CALLS` edge into them (structural in-degree; the call-graph resolver). The load-bearing callees — signature changes touch every caller. The confidence mix is over the underlying call edges (a callee may have more edges than callers).

| Symbol | Defined in | Callers | Confidence mix |
| --- | --- | --- | --- |
| `Vet.getSpecialtiesInternal` | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | 3 | 3 `EXTRACTED` |
| `Owner.getPet` | `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | 2 | 2 `EXTRACTED` |
| `Owner.getPets` | `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | 2 | 3 `EXTRACTED` |
| `Pet` | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 2 | 2 `AMBIGUOUS` |
| `Vets` | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | 2 | 2 `AMBIGUOUS` |
| `NamedEntity.getName` | `src/main/java/org/springframework/samples/petclinic/model/NamedEntity.java` | 1 | 1 `INFERRED` |
| `Owner` | `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | 1 | 1 `AMBIGUOUS` |
| `OwnerController.addPaginationModel` | `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | 1 | 1 `EXTRACTED` |
| `OwnerController.findPaginatedForOwnersLastName` | `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | 1 | 1 `EXTRACTED` |
| `Pet.getVisits` | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 1 | 1 `EXTRACTED` |
| `PetController.updatePetDetails` | `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | 1 | 1 `EXTRACTED` |
| `PetValidator` | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | 1 | 1 `AMBIGUOUS` |
| `Visit` | `src/main/java/org/springframework/samples/petclinic/owner/Visit.java` | 1 | 1 `AMBIGUOUS` |
| `CacheConfiguration.cacheConfiguration` | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | 1 | 1 `EXTRACTED` |
| `WebConfiguration.localeChangeInterceptor` | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | 1 | 1 `EXTRACTED` |

## Cross-file dependencies

File-to-file dependencies aggregated from symbol-level `CALLS` edges (the call-graph resolver). Self-edges (intra-file calls) excluded.

| From | To | Calls | Top callee |
| --- | --- | --- | --- |
| `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 2 | `Pet` |
| `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | 2 | `Vets` |
| `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | 1 | `Owner` |
| `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | 1 | `PetValidator` |
| `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | `src/main/java/org/springframework/samples/petclinic/owner/Visit.java` | 1 | `Visit` |

## Co-change clusters

_Confidence: `INFERRED`._

Files most frequently committed together. The shared-commit count is EXTRACTED from git; the implication 'these should change together' is the derivation.

| File A | File B | Shared commits |
| --- | --- | --- |
| `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | 16 |
| `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | 16 |
| `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | 14 |
| `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 12 |
| `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | 12 |
| `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 12 |
| `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | 12 |
| `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | 11 |
| `src/main/java/org/springframework/samples/petclinic/model/BaseEntity.java` | `src/main/java/org/springframework/samples/petclinic/model/NamedEntity.java` | 10 |
| `src/main/java/org/springframework/samples/petclinic/model/BaseEntity.java` | `src/main/java/org/springframework/samples/petclinic/model/Person.java` | 10 |

## Change hot spots

Files touched by the most commits (git churn).

| File | Commits |
| --- | --- |
| `pom.xml` | 332 |
| `readme.md` | 100 |
| `build.gradle` | 49 |
| `src/main/webapp/WEB-INF/web.xml` | 35 |
| `src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java` | 32 |
| `src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java` | 32 |
| `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | 29 |
| `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | 27 |
| `src/main/resources/application.properties` | 25 |
| `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | 24 |
| `src/main/java/org/springframework/samples/petclinic/repository/jdbc/JdbcOwnerRepositoryImpl.java` | 24 |
| `src/main/webapp/WEB-INF/jsp/pets/createOrUpdatePetForm.jsp` | 23 |
| `src/test/java/org/springframework/samples/petclinic/model/ValidatorTests.java` | 23 |
| `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 22 |
| `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | 22 |

## Churn × centrality

_Confidence: `INFERRED`._

Files that are **both** highly depended-on and frequently changed — the riskiest edits in the repo. Commit counts are EXTRACTED; the centrality column and the risk framing are the derivation.

| File | Centrality | Commits |
| --- | --- | --- |
| `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | 0.0651 | 24 |
| `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | 0.0527 | 22 |
| `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | 0.0352 | 27 |
| `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | 0.0352 | 29 |
| `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | 0.0352 | 22 |

---

*Generated by forensic-deepdive 0.9.0 on 2026-07-09. Regenerate with `forensic update` — do not hand-edit.*
