from src.domain.module_models import ModuleDef


def test_module_def_keeps_edgebands_in_to_dict_and_from_dict():
    module1 = ModuleDef(
        name="TEST_EDGE_1",
        edgebands={
            "side": "ABS_WHITE_1MM",
            "front": "NO_EDGEBAND",
        },
    )

    d = module1.to_dict()
    module2 = ModuleDef.from_dict(d)

    assert d["edgebands"]["side"] == "ABS_WHITE_1MM"
    assert d["edgebands"]["front"] == "NO_EDGEBAND"

    assert module2.edgebands["side"] == "ABS_WHITE_1MM"
    assert module2.edgebands["front"] == "NO_EDGEBAND"