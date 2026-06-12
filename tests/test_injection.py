"""DI extraction (DEC-059, v0.5 Step 4) — ``static/injection.py``.

Covers the FastAPI ``Depends`` shape (Python) and the Spring ``@Autowired`` field
+ constructor-injection shapes (Java). Resolution to a Symbol + the interface→impl
ladder are exercised end-to-end in ``test_di_orm_e2e``.
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.injection import extract_injection
from forensic_deepdive.static.parse import ParsedFile, parse_source


def _records(src: str, language: str, name: str):
    data = src.encode()
    pf = ParsedFile(
        path=Path(name),
        rel_path=name,
        language=language,
        source=data,
        tree=parse_source(data, language),
    )
    return extract_injection(pf)


def test_fastapi_depends_is_extracted():
    recs = _records("def list_owners(db = Depends(get_db)):\n    return db\n", "python", "api.py")
    assert [(r.injector_qn_local, r.injected_type_name, r.kind) for r in recs] == [
        ("list_owners", "get_db", "depends")
    ]


def test_fastapi_annotated_depends():
    recs = _records(
        "def h(db: Annotated[Session, Depends(get_db)]):\n    return db\n", "python", "api.py"
    )
    assert ("h", "get_db", "depends") in [
        (r.injector_qn_local, r.injected_type_name, r.kind) for r in recs
    ]


def test_spring_autowired_field_and_ctor():
    src = (
        "@Service\n"
        "public class OwnerController {\n"
        "  @Autowired\n"
        "  private OwnerRepository owners;\n"
        "  public OwnerController(VisitRepository visits) {}\n"
        "}\n"
    )
    recs = {(r.injected_type_name, r.kind) for r in _records(src, "java", "X.java")}
    assert recs == {("OwnerRepository", "autowired-field"), ("VisitRepository", "ctor")}


def test_non_stereotype_ctor_is_not_injection():
    # A plain class (no Spring stereotype, no @Autowired ctor) is not DI.
    recs = _records("public class Plain {\n  public Plain(Foo f) {}\n}\n", "java", "P.java")
    assert recs == []
