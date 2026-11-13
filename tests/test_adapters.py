import json

import pytest

from spdx_export.adapters import load_csv, load_json, load_scan, normalize_path


def test_valid_json_loads_everything(samples):
    scan = load_json(samples / "valid_scan.json")
    assert not scan.diagnostics
    assert scan.document_name == "demo-app-1.0"
    assert len(scan.packages) == 3
    assert len(scan.files) == 5
    assert len(scan.relationships) == 2


def test_csv_gives_same_data_as_json(samples):
    from_json = load_json(samples / "valid_scan.json")
    from_csv = load_csv(samples / "valid_scan.csv")
    assert not from_csv.has_errors
    key = lambda x: str(x)
    assert sorted(from_csv.packages, key=key) == sorted(from_json.packages, key=key)
    assert sorted(from_csv.files, key=key) == sorted(from_json.files, key=key)
    assert sorted(from_csv.relationships, key=key) == sorted(from_json.relationships, key=key)


def test_missing_optional_fields_are_not_errors(samples):
    scan = load_json(samples / "missing_fields_scan.json")
    assert not scan.has_errors
    assert scan.packages[1].version is None
    assert scan.packages[1].supplier is None


def test_broken_scan_reports_every_problem(samples):
    scan = load_json(samples / "broken_scan.json")
    assert scan.has_errors
    text = "\n".join(str(d) for d in scan.diagnostics)
    for expected in [
        "missing for 'pkg-noname'",
        "duplicate id 'pkg-dup'",
        "SPDX 2.3 requires a SHA1",
        "must be 40 hex characters",
        "unknown package 'pkg-does-not-exist'",
        "path               missing",
        "unknown package 'pkg-ghost'",
        "'USES' not allowed",
        "cannot relate to itself",
    ]:
        assert expected in text, expected
    # Good records are still kept; nothing is invented for bad ones.
    assert [p.id for p in scan.packages] == ["pkg-libfoo"]
    assert scan.files == []


def test_invalid_json_is_reported_not_crashed(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    scan = load_json(bad)
    assert scan.has_errors
    assert "invalid JSON" in scan.diagnostics[0].message


def test_empty_object_has_no_packages(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    scan = load_json(empty)
    assert scan.has_errors
    assert "no valid packages" in scan.diagnostics[-1].message


def test_csv_conflicting_package_details(tmp_path):
    f = tmp_path / "conflict.csv"
    f.write_text(
        "package_id,package_name,version,file_path,sha1\n"
        "p1,libfoo,1.0,a.c,da39a3ee5e6b4b0d3255bfef95601890afd80709\n"
        "p1,libfoo,2.0,b.c,da39a3ee5e6b4b0d3255bfef95601890afd80709\n",
        encoding="utf-8",
    )
    scan = load_csv(f)
    assert scan.has_errors
    assert "different details" in scan.diagnostics[0].message


def test_sha1_is_stored_lowercase(tmp_path):
    f = tmp_path / "upper.json"
    f.write_text(json.dumps({
        "packages": [{"id": "p1", "name": "x"}],
        "files": [{"package_id": "p1", "path": "a.c", "sha1": "DA39A3EE5E6B4B0D3255BFEF95601890AFD80709"}],
    }), encoding="utf-8")
    assert load_json(f).files[0].sha1 == "da39a3ee5e6b4b0d3255bfef95601890afd80709"


def test_unsupported_extension():
    with pytest.raises(ValueError):
        load_scan("scan.xml")


@pytest.mark.parametrize("raw, expected", [
    ("src/foo.c", "src/foo.c"),
    ("./src/foo.c", "src/foo.c"),
    ("/src/foo.c", "src/foo.c"),
    ("src\\win\\foo.c", "src/win/foo.c"),
])
def test_normalize_path(raw, expected):
    assert normalize_path(raw) == expected
