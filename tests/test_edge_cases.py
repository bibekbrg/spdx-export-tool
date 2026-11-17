"""Edge cases: unusual but realistic inputs must never crash or produce wrong SPDX."""

import json

from conftest import FIXED_TIME
from spdx_export.adapters import find_cycles, load_csv, load_json
from spdx_export.pipeline import convert
from spdx_export.validator import validate

SHA_A = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
SHA_B = "a9993e364706816aba3e25717850c26c9cd0d89d"


def write_json(tmp_path, data, name="scan.json", bom=False):
    p = tmp_path / name
    text = json.dumps(data, ensure_ascii=False)
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))
    return p


def write_csv(tmp_path, text, name="scan.csv", bom=False):
    p = tmp_path / name
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))
    return p


def pkg(pid, name=None, **extra):
    return {"id": pid, "name": name or pid, **extra}


def rel(a, t, b):
    return {"from": a, "type": t, "to": b}


# ---------------------------------------------------------------- file format quirks

def test_json_with_bom_is_read(tmp_path):
    scan = load_json(write_json(tmp_path, {"packages": [pkg("p1")]}, bom=True))
    assert not scan.has_errors


def test_csv_with_bom_from_excel_is_read(tmp_path):
    scan = load_csv(write_csv(tmp_path, f"package_id,package_name,file_path,sha1\np1,lib,a.c,{SHA_A}\n", bom=True))
    assert not scan.has_errors
    assert scan.packages[0].id == "p1"


def test_csv_header_case_and_spaces_are_tolerated(tmp_path):
    scan = load_csv(write_csv(tmp_path, f" Package_ID , PACKAGE_NAME ,file_path,sha1\np1,lib,a.c,{SHA_A}\n"))
    assert not scan.has_errors


def test_csv_missing_required_column(tmp_path):
    scan = load_csv(write_csv(tmp_path, "id,name\np1,lib\n"))
    assert scan.has_errors
    assert "missing required column" in scan.diagnostics[0].message


def test_csv_header_only_has_no_packages(tmp_path):
    scan = load_csv(write_csv(tmp_path, "package_id,package_name\n"))
    assert scan.has_errors
    assert "no valid packages" in scan.diagnostics[-1].message


def test_empty_csv_file(tmp_path):
    scan = load_csv(write_csv(tmp_path, ""))
    assert scan.has_errors


def test_packages_must_be_a_list(tmp_path):
    scan = load_json(write_json(tmp_path, {"packages": {"id": "p1"}}))
    assert scan.has_errors
    assert "'packages' must be a list" in scan.diagnostics[0].message


def test_top_level_list_is_rejected(tmp_path):
    assert load_json(write_json(tmp_path, [1, 2])).has_errors


# ---------------------------------------------------------------- values

def test_whitespace_only_values_count_as_missing(tmp_path):
    scan = load_json(write_json(tmp_path, {"packages": [pkg("p1", "lib", supplier="   ", version="  ")]}))
    assert scan.packages[0].supplier is None
    assert scan.packages[0].version is None


def test_numeric_version_becomes_text(tmp_path):
    scan = load_json(write_json(tmp_path, {"packages": [pkg("p1", "lib", version=2.5)]}))
    assert scan.packages[0].version == "2.5"


def test_unicode_names_and_paths_give_valid_spdx(tmp_path):
    f = write_json(tmp_path, {
        "packages": [pkg("p1", "bibliothèque-日本", copyright="© 2026 Société")],
        "files": [{"package_id": "p1", "path": "src/fichier été.c", "sha1": SHA_A}],
    })
    doc, _ = convert(f, created=FIXED_TIME)
    assert validate(doc) == []
    assert doc["packages"][0]["name"] == "bibliothèque-日本"
    assert doc["files"][0]["fileName"] == "./src/fichier été.c"


def test_package_without_files(tmp_path):
    doc, _ = convert(write_json(tmp_path, {"packages": [pkg("p1", "lib")]}), created=FIXED_TIME)
    p = doc["packages"][0]
    assert p["filesAnalyzed"] is False
    assert "packageVerificationCode" not in p
    assert validate(doc) == []


def test_lowercase_relationship_type_accepted(tmp_path):
    scan = load_json(write_json(tmp_path, {
        "packages": [pkg("a"), pkg("b")], "relationships": [rel("a", "depends_on", "b")]}))
    assert scan.relationships[0].type == "DEPENDS_ON"


def test_unknown_extra_fields_are_ignored(tmp_path):
    scan = load_json(write_json(tmp_path, {"packages": [pkg("p1", "lib", colour="blue")], "extra": 1}))
    assert not scan.has_errors


# ---------------------------------------------------------------- duplicates

def test_identical_duplicate_file_is_merged(tmp_path):
    f = {"package_id": "p1", "path": "a.c", "sha1": SHA_A}
    scan = load_json(write_json(tmp_path, {"packages": [pkg("p1")], "files": [f, dict(f, path="./a.c")]}))
    assert not scan.has_errors
    assert len(scan.files) == 1


def test_conflicting_duplicate_file_is_an_error(tmp_path):
    scan = load_json(write_json(tmp_path, {"packages": [pkg("p1")], "files": [
        {"package_id": "p1", "path": "a.c", "sha1": SHA_A},
        {"package_id": "p1", "path": "a.c", "sha1": SHA_B},
    ]}))
    assert scan.has_errors
    assert "different SHA1" in str(scan.diagnostics)


def test_same_path_in_two_packages_is_fine(tmp_path):
    doc, _ = convert(write_json(tmp_path, {"packages": [pkg("p1"), pkg("p2")], "files": [
        {"package_id": "p1", "path": "LICENSE", "sha1": SHA_A},
        {"package_id": "p2", "path": "LICENSE", "sha1": SHA_B},
    ]}), created=FIXED_TIME)
    ids = [f["SPDXID"] for f in doc["files"]]
    assert len(set(ids)) == 2
    assert validate(doc) == []


def test_duplicate_relationship_is_ignored(tmp_path):
    scan = load_json(write_json(tmp_path, {
        "packages": [pkg("a"), pkg("b")], "relationships": [rel("a", "DEPENDS_ON", "b")] * 2}))
    assert len(scan.relationships) == 1
    assert not scan.has_errors


# ---------------------------------------------------------------- circular relationships

def test_find_cycles():
    assert find_cycles({"a": ["b"], "b": ["c"], "c": ["a"]}) == [["a", "b", "c"]]
    assert find_cycles({"a": ["b"], "b": ["c"]}) == []
    assert find_cycles({"b": ["a"], "a": ["b"], "x": ["y"], "y": ["x"]}) == [["a", "b"], ["x", "y"]]


def test_contains_loop_is_an_error(tmp_path):
    scan = load_json(write_json(tmp_path, {
        "packages": [pkg("a"), pkg("b")],
        "relationships": [rel("a", "CONTAINS", "b"), rel("b", "CONTAINS", "a")]}))
    assert scan.has_errors
    assert "circular CONTAINS: a -> b -> a" in str(scan.diagnostics)


def test_depends_on_loop_is_a_warning_and_still_converts(tmp_path):
    f = write_json(tmp_path, {
        "packages": [pkg("a"), pkg("b"), pkg("c")],
        "relationships": [rel("a", "DEPENDS_ON", "b"), rel("b", "DEPENDS_ON", "c"), rel("c", "DEPENDS_ON", "a")]})
    doc, diags = convert(f, created=FIXED_TIME)
    assert doc is not None
    assert any(d.severity == "WARNING" and "circular DEPENDS_ON: a -> b -> c -> a" in d.message for d in diags)
    assert validate(doc) == []
    # no package is "top level" in a loop, so the document must still describe something
    assert len([r for r in doc["relationships"] if r["relationshipType"] == "DESCRIBES"]) == 3
