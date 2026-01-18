from tabs.module_widget import pick_nl_for_depth

def test_pick_nl_for_depth_basic():
    # zasada: NL <= D-50
    assert pick_nl_for_depth(525) == 450  # 525-50=475 -> najbliższe <=475 to 450
    assert pick_nl_for_depth(500) == 450
    assert pick_nl_for_depth(560) == 500

def test_pick_nl_for_depth_small():
    assert pick_nl_for_depth(260) == 250
    assert pick_nl_for_depth(240) == 250 or pick_nl_for_depth(240) == 0  # zależy od STD_NL_MM fallback
