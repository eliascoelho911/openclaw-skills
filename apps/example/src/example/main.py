"""Main entry point for the example application."""

from shared.utils import greeting


def main() -> None:
    """Run the example application."""
    message = greeting("World")
    print(message)


if __name__ == "__main__":
    main()
