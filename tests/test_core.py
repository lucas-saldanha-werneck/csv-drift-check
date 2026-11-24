from csv_drift_check.cli import main
from csv_drift_check.core import column_type, compare, infer_type, profile_csv


def w(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_infer_type():
    assert infer_type("12") == "int"
    assert infer_type("1.5") == "float"
    assert infer_type("2026-11-02") == "date"
    assert infer_type("abc") == "str"
    assert infer_type("  ") == "null"
    assert infer_type("N/A") == "null"


def test_column_type_mixed_and_numeric():
    assert column_type({"int", "float", "null"}) == "float"
    assert column_type({"int", "str"}) == "mixed"
    assert column_type({"null"}) == "empty"


def test_profile(tmp_path):
    p = profile_csv(w(tmp_path, "a.csv", "id,x\n1,\n2,5\n2,6\n"), key="id")
    assert p.rows == 3
    assert p.types == {"id": "int", "x": "int"}
    assert round(p.null_rate["x"], 2) == 0.33
    assert p.duplicate_keys == 1


def test_missing_key_column(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        profile_csv(w(tmp_path, "a.csv", "id\n1\n"), key="nope")


def test_compare_schema_and_types(tmp_path):
    a = profile_csv(w(tmp_path, "a.csv", "id,n,gone\n1,1,x\n2,2,y\n"))
    b = profile_csv(w(tmp_path, "b.csv", "id,n,new\n1,abc,x\n2,2,y\n"))
    msgs = {(f.severity, f.message) for f in compare(a, b)}
    assert ("error", "column removed: gone") in msgs
    assert ("warn", "column added: new") in msgs
    assert ("error", "type changed in 'n': int -> mixed") in msgs


def test_null_jump_and_row_change(tmp_path):
    a = profile_csv(w(tmp_path, "a.csv", "id,v\n1,a\n2,b\n3,c\n4,d\n"))
    b = profile_csv(w(tmp_path, "b.csv", "id,v\n1,\n2,\n"))
    text = " ".join(f.message for f in compare(a, b))
    assert "null rate up in 'v'" in text
    assert "row count changed -50%" in text


def test_no_drift(tmp_path):
    a = profile_csv(w(tmp_path, "a.csv", "id,v\n1,a\n2,b\n"), key="id")
    b = profile_csv(w(tmp_path, "b.csv", "id,v\n1,a\n2,b\n"), key="id")
    assert compare(a, b) == []


def test_cli_exit_codes(tmp_path, capsys):
    a = w(tmp_path, "a.csv", "id\n1\n2\n")
    assert main([a, a, "--key", "id"]) == 0
    b = w(tmp_path, "b.csv", "id\n1\n1\n")
    assert main([a, b, "--key", "id"]) == 1
    assert "duplicate" in capsys.readouterr().out
    assert main([a, a, "--key", "zzz"]) == 2
    assert main([a, str(tmp_path / "missing.csv")]) == 2


def test_example_files():
    from pathlib import Path
    ex = Path(__file__).parent.parent / "examples"
    old = profile_csv(str(ex / "orders_monday.csv"), "order_id")
    new = profile_csv(str(ex / "orders_tuesday.csv"), "order_id")
    msgs = [f.message for f in compare(old, new)]
    assert "1 duplicate value(s) in key 'order_id'" in msgs
    assert "type changed in 'amount': float -> mixed" in msgs
    assert "1 key(s) from the old snapshot are missing" in msgs
