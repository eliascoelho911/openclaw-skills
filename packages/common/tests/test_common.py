from shared.utils import greeting


def test_greeting() -> None:
    """Test the greeting function."""
    assert greeting("World") == "Hello, World!"
    assert greeting("Python") == "Hello, Python!"
