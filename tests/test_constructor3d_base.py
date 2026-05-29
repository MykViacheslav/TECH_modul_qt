from pathlib import Path

from core.constructor3d_base import parse_ls5_modules


def test_parse_ls5_modules_reads_tab52_record(tmp_path: Path) -> None:
    source = """'(24 1 ((1 1 0 "Section") (3 1 0 "Object") ("KARKAS" 1 0 "Carcase") ("MODEL" 3 8 "Model") ("SHIFR" 11 3855 "Code_R") ("NAME" 11 5150 "Name_R") ("SHIFR2" 27 3855 "Code_L") ("NAME2" 27 5150 "Name_L") ("LISTV" 4 8 "Variables") ("LMAT" 4 8 "Material") ("SLD" 3 8 "Picture") ("KLASS" 1 8 "Class") ("CENA" 2 8 "Price")) (0 1 2 3 4 5 6 7 8 9 10 11 12) ((52 0 "Typical models") (72 52 "Base")) nil (72 56 2099 1 "tb52_1" "ASS/R.00.000" "Right cabinet" "ASS/L.00.000" "Left cabinet" (("H" "780" 780.0 "*") ("L" "800" 800.0 "*") ("W" "510" 510.0 "*")) (("MO" "main" 7 "PB18")) "tb52_1" 1 0.0))"""
    path = tmp_path / "tab52.ls5"
    path.write_text(source, encoding="cp1251")

    modules = parse_ls5_modules(path, base_name="BASE_TEST")

    assert [m.code for m in modules] == ["ASS/R.00.000", "ASS/L.00.000"]
    assert modules[0].name == "Right cabinet"
    assert modules[0].width == 800.0
    assert modules[0].height == 780.0
    assert modules[0].depth == 510.0
    assert modules[0].category == "Typical models / Base"
    assert modules[0].anchor == "3DC:BASE_TEST:ASS_R.00.000"
    assert modules[0].to_payload()["code3dc"] == "ASS/R.00.000"
