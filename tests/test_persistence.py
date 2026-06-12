"""ORM extraction (DEC-059, v0.5 Step 4) — ``static/persistence.py``.

Covers SQLAlchemy ``__tablename__`` + Django ``Meta.db_table``/derived (Python) and
JPA ``@Entity``/``@Table`` literal + class-name-derived (Java). ``literal`` drives
the EXTRACTED (syntactic) vs INFERRED (convention) PERSISTS_TO confidence.
"""

from __future__ import annotations

from pathlib import Path

from forensic_deepdive.static.parse import ParsedFile, parse_source
from forensic_deepdive.static.persistence import extract_persistence


def _records(src: str, language: str, name: str):
    data = src.encode()
    pf = ParsedFile(
        path=Path(name),
        rel_path=name,
        language=language,
        source=data,
        tree=parse_source(data, language),
    )
    return extract_persistence(pf)


def test_sqlalchemy_tablename_is_literal():
    recs = _records('class Owner(Base):\n    __tablename__ = "owners"\n', "python", "m.py")
    assert [(r.model_qn_local, r.table_name, r.orm, r.literal) for r in recs] == [
        ("Owner", "owners", "sqlalchemy", True)
    ]


def test_django_meta_db_table_literal_and_derived():
    literal = _records(
        'class Vet(models.Model):\n    class Meta:\n        db_table = "vets"\n', "python", "m.py"
    )
    assert (literal[0].table_name, literal[0].orm, literal[0].literal) == ("vets", "django", True)
    derived = _records("class Visit(models.Model):\n    pass\n", "python", "m.py")
    assert (derived[0].table_name, derived[0].literal) == ("visit", False)


def test_jpa_entity_table_literal_and_derived():
    literal = _records(
        '@Entity\n@Table(name = "owners")\npublic class Owner {}\n', "java", "O.java"
    )
    assert (literal[0].table_name, literal[0].orm, literal[0].literal) == ("owners", "jpa", True)
    derived = _records("@Entity\npublic class Vet {}\n", "java", "V.java")
    assert (derived[0].table_name, derived[0].literal) == ("Vet", False)


def test_non_entity_class_is_ignored():
    assert _records("public class Helper {}\n", "java", "H.java") == []
    assert _records("class Plain:\n    pass\n", "python", "p.py") == []
