import math

from tabs.module_widget import mm2_to_m2, safe_float, safe_int, clamp

def test_mm2_to_m2():
    assert mm2_to_m2(1_000_000) == 1.0
    assert mm2_to_m2(250_000) == 0.25

def test_safe_float():
    assert safe_float("12.5") == 12.5
    assert safe_float(None, 7.0) == 7.0
    assert safe_float("abc", 3.0) == 3.0

def test_safe_int():
    assert safe_int("12") == 12
    assert safe_int(None, 5) == 5
    assert safe_int("abc", 9) == 9

def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
