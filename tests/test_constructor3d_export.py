from core.constructor3d_export import Constructor3DModule, build_model_list_ini


def test_build_model_list_ini_uses_3dc_keys():
    text = build_model_list_ini(
        [
            Constructor3DModule(
                index=1,
                code="TK_N1.000",
                length=500,
                width=500,
                height=825,
                x=6950,
                y=12875,
                z=0,
                angle=0,
                coordinate_system=-1,
            )
        ]
    )

    assert "\u005b\u041c\u041e\u0414\u0423\u041b\u042c1\u005d" in text
    assert "\u0428\u0418\u0424\u0420=TK_N1.000" in text
    assert "\u0414\u041b\u0418\u041d\u0410=500" in text
    assert "\u0428\u0418\u0420\u0418\u041d\u0410=500" in text
    assert "\u0412\u042b\u0421\u041e\u0422\u0410=825" in text
    assert "\u0412\u0421\u0422\u0410\u0412\u041a\u0410=6950 12875 0" in text
    assert "\u0423\u0413\u041e\u041b=0" in text
    assert "\u0421\u041a=-1" in text
