from shared.utils import greeting


def test_integration() -> None:
    """Simple integration test ensuring modules work together."""
    result = greeting("Integration Test")
    assert result == "Hello, Integration Test!"
