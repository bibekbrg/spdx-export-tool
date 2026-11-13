import json

from conftest import FIXED_TIME
from spdx_export.pipeline import convert
from spdx_export.serializer import to_json, write_json


def test_output_is_deterministic(samples):
    a, _ = convert(samples / "valid_scan.json", created=FIXED_TIME)
    b, _ = convert(samples / "valid_scan.json", created=FIXED_TIME)
    assert to_json(a) == to_json(b)


def test_matches_expected_output(samples):
    doc, _ = convert(samples / "valid_scan.json", created=FIXED_TIME, creator_person="Bibek Roy")
    expected = (samples / "expected" / "valid_scan.spdx.json").read_text(encoding="utf-8")
    assert to_json(doc) == expected


def test_keys_are_sorted_and_file_ends_with_newline():
    text = to_json({"b": 1, "a": {"d": 2, "c": 3}})
    assert text.index('"a"') < text.index('"b"')
    assert text.index('"c"') < text.index('"d"')
    assert text.endswith("\n")


def test_unicode_is_kept(tmp_path):
    out = tmp_path / "out.json"
    write_json({"copyrightText": "© 2026 Ünïcode"}, out)
    assert "© 2026 Ünïcode" in out.read_text(encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["copyrightText"] == "© 2026 Ünïcode"
