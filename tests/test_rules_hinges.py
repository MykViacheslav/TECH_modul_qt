from src.core.rules.hinges import hinges_count_for_door

def test_hinges_count():
    assert hinges_count_for_door(700) == 2
    assert hinges_count_for_door(1200) == 3
    assert hinges_count_for_door(1800) == 4
    assert hinges_count_for_door(2200) == 5