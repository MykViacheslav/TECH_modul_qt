from src.core.rules.drawers import DrawerCalcInput, pick_slide_length_mm

def test_pick_slide_overlay_no_tipon():
    inp = DrawerCalcInput(depth_mm=500, rear_clearance_mm=10, front_layout="overlay", tip_on=False)
    assert pick_slide_length_mm(inp) == 450  # 500-10=490 -> max<=490 z listy co 50 = 450

def test_pick_slide_inset_tipon():
    inp = DrawerCalcInput(depth_mm=500, rear_clearance_mm=10, front_layout="inset", front_thickness_mm=19, tip_on=True, tip_on_clearance_mm=20)
    # 500-10-19-20=451 -> max<=451 = 450
    assert pick_slide_length_mm(inp) == 450

def test_pick_slide_too_shallow():
    inp = DrawerCalcInput(depth_mm=260, rear_clearance_mm=10, front_layout="overlay", tip_on=False)
    # 260-10=250 -> max<=250 = 250
    assert pick_slide_length_mm(inp) == 250