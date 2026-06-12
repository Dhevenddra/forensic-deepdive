"""A tool-registry fixture (DEC-058) — the registration (provider) side.

Exercises all three registration shapes: a decorator with a literal key, a bare
decorator (key = function name), a dict-literal map, and a subscript assignment.
"""

registry = Registry()


@registry.register("greet")
def greet_handler(name):
    return f"hello {name}"


@registry.register
def wave(name):
    return f"o/ {name}"


def add(a, b):
    return a + b


def sub(a, b):
    return a - b


def mul(a, b):
    return a * b


TOOLS = {"add": add, "sub": sub}

TOOLS["mul"] = mul
