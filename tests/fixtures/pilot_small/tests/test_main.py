from pilot_app.main import add, greet


def test_greet() -> None:
    assert greet("FADE") == "Hello, FADE!"


def test_add() -> None:
    assert add(2, 3) == 5
