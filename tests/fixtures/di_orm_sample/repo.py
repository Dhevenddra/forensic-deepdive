"""Repository fixture (DEC-059) — instantiates the model on the path to the table."""

from models import Owner


def save_owner():
    o = Owner()
    return o
