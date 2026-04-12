from src.app.navigation_groups import GROUPS


def test_navigation_groups_has_operacje():
    assert any(name == "Operacje" for name, _tabs in GROUPS)
    assert any(name == "Operacje" and "OPERACJE" in tabs for name, tabs in GROUPS)
