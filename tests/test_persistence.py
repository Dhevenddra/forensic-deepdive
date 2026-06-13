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


# --- DEC-064: Django-vs-SQLAlchemy disambiguation on a bare `Model` base --------


def test_bare_model_base_without_django_signal_is_sqlalchemy():
    """The Superset ``coremodel`` shape: a Flask-AppBuilder ``Model`` base (SQLAlchemy)
    with no Django signal must NOT be mis-tagged Django — it falls through to
    SQLAlchemy with the lowered class name (INFERRED)."""
    recs = _records("class CoreModel(Model):\n    pass\n", "python", "m.py")
    assert [(r.model_qn_local, r.table_name, r.orm, r.literal) for r in recs] == [
        ("CoreModel", "coremodel", "sqlalchemy", False)
    ]


def test_qualified_models_model_base_is_django():
    recs = _records("class Visit(models.Model):\n    pass\n", "python", "m.py")
    assert (recs[0].table_name, recs[0].orm, recs[0].literal) == ("visit", "django", False)


def test_django_import_signal_promotes_bare_model_base():
    """``from django.db import models`` is a file-level Django signal: a bare
    ``Model`` base in such a file is Django, not SQLAlchemy."""
    src = "from django.db import models\nclass Pet(Model):\n    pass\n"
    recs = _records(src, "python", "m.py")
    assert (recs[0].table_name, recs[0].orm) == ("pet", "django")


def test_meta_plus_models_field_signal_is_django():
    """A bare ``Model`` base with a nested ``Meta`` + a ``models.*Field`` is Django."""
    src = (
        "class Animal(Model):\n"
        "    name = models.CharField(max_length=80)\n"
        "    class Meta:\n"
        "        db_table = 'animals'\n"
    )
    recs = _records(src, "python", "m.py")
    assert (recs[0].table_name, recs[0].orm, recs[0].literal) == ("animals", "django", True)
