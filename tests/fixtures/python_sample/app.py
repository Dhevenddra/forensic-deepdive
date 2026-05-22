"""Entry point that exercises the Greeter library."""

from greeter import Greeter, format_message


def run() -> None:
    """Greet the world and print a second message."""
    greeter = Greeter("world")
    print(greeter.greet())
    print(format_message("again"))


if __name__ == "__main__":
    run()
