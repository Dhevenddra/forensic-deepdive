# Apache Superset — v0.6 Step 1 acceptance (ORM Django/SQLAlchemy disambiguation)

The v0.5 Superset run materialized **55 `DbTable` nodes** over its SQLAlchemy layer but
**mis-tagged 1 of 55** (`table::coremodel`) as `django`: a class with a bare `Model`
base that is *not* a Django model was classified by the Django branch. The v0.5 findings
flagged this as a clean v0.6 follow-on (the findings-drive-the-next-fix loop). This run
tests the DEC-064 fix on the real codebase.

## The fix (DEC-064)

`static/persistence.py` only. The Django branch is now **gated on a Django-specific
signal** — any of:
- a `django.db.models` import (`from django.db import models` / `from django.db.models import …`),
- a **qualified** `models.Model` / `django.db.models.Model` base (vs a bare `Model`),
- a nested `class Meta` **and** a `models.*Field` assignment.

A class with a bare `Model` base and **none** of those falls through to **SQLAlchemy**
with the lowered class name (INFERRED — the Flask-AppBuilder / declarative auto-
`__tablename__` convention). `DbTable` + `PERSISTS_TO` are unchanged — **only the `orm`
property changes.** `PARSER_VERSION` 4→5 forces cached repos to re-parse.

## The mis-tagged class, on the real source

`superset-core/src/superset_core/common/models.py:50`:
```python
from flask_appbuilder import Model          # NOT django
...
class CoreModel(Model):                      # bare `Model` base, no Django signal
    __abstract__ = True
```
`from flask_appbuilder import Model`; a bare `Model` base; no qualified `models.Model`,
no Django import, no `Meta`+`models.*Field`. Pre-fix → `django`; post-fix → `sqlalchemy`.
Running the new `extract_persistence` on this exact file: `CoreModel → coremodel |
sqlalchemy | literal=False` (0 django tags).

## Run summary

| | |
|---|---|
| Date | 2026-06-13 |
| Repo | apache/superset (`C:\Dev\scratch\superset`, Apache-2.0) |
| Tool version | v0.6 HEAD (DEC-063 → DEC-064) |

## DbTable ORM tags — before / after (same methodology: graph `DbTable` nodes)

| | v0.5 (before) | **v0.6 (after)** |
|---|---|---|
| `DbTable` total | 55 | **55** |
| → `sqlalchemy` | 54 | **55** |
| → `django` (mis-tag) | **1** (`coremodel`) | **0** |
| correct ORM tags | 54/55 | **55/55** |

`PERSISTS_TO` stays **210** (table + edge were always correct — only the `orm` property
flipped). `coremodel` is now `sqlalchemy`.

Cross-check (the per-file `extract_persistence` pass over **all** of Superset, a superset
of the pipeline's role-filtered set): **65 `DbTable` names, 0 `django`, 65 `sqlalchemy`**
— so no `Model`-base class in the repo is django-tagged anymore, and the pipeline's
role-filtered subset is necessarily 100 % correct.

## Keystone

`git diff` for Step 1 touches **only** `static/persistence.py` + `parse_cache.py` (the
version bump) + `tests/test_persistence.py`. No `base.join`/`trace`/emit/`serve` change —
a pure correctness fix on the `orm` property. Goldens byte-identical; 714 tests green.

## Takeaway

The v0.5 ORM mis-tag is closed on the real code: Superset's `DbTable` ORM tags go
**54/55 → 55/55** with no fabrication and no surfacing-layer change — the v0.6 warm-up
correctness fix, mirroring the v0.5 Step-1 gate-closer discipline.
