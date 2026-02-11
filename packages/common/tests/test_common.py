from shared.utils import greeting


def test_greeting():
    """Test the greeting function."""
    assert greeting("World") == "Hello, World!"
    assert greeting("Python") == "Hello, Python!"
