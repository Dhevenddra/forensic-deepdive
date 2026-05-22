"""A tiny greeting library used by the static-analysis fixtures."""


class Greeter:
    """Holds a name and produces greetings."""

    def __init__(self, name: str) -> None:
        self.name = name

    def greet(self) -> str:
        """Return a greeting for the stored name."""
        return format_message(self.name)


def format_message(name: str) -> str:
    """Build a greeting string for *name*."""
    return f"hello, {name}"
