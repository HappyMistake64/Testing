from pilot_app.main import add, greet


def test_greet() -> None:
    assert greet("trader") == "Hello, trader!"


def test_add() -> None:
    assert add(1, 1) == 2
