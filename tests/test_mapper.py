import hashlib

from conftest import FIXED_TIME
from spdx_export.pipeline import convert


def _rels(doc, rtype):
    return [r for r in doc["relationships"] if r["relationshipType"] == rtype]


def test_document_header(samples):
    doc, _ = convert(samples / "valid_scan.json", created=FIXED_TIME, creator_person="Bibek Roy")
    assert doc["spdxVersion"] == "SPDX-2.3"
    assert doc["dataLicense"] == "CC0-1.0"
    assert doc["SPDXID"] == "SPDXRef-DOCUMENT"
    assert doc["name"] == "demo-app-1.0"
    assert doc["documentNamespace"].startswith("https://spdx.org/spdxdocs/demo-app-1.0-")
    assert doc["creationInfo"]["created"] == FIXED_TIME
    assert doc["creationInfo"]["creators"] == ["Tool: spdx-export-0.1.0", "Person: Bibek Roy"]


def test_packages_and_files_are_mapped(samples):
    doc, diags = convert(samples / "valid_scan.json", created=FIXED_TIME)
    assert diags == []
    assert len(doc["packages"]) == 3
    assert len(doc["files"]) == 5
    libfoo = next(p for p in doc["packages"] if p["name"] == "libfoo")
    assert libfoo["versionInfo"] == "1.2.0"
    assert libfoo["supplier"] == "Organization: Acme Corp"
    assert libfoo["licenseDeclared"] == "MIT"
    assert libfoo["filesAnalyzed"] is True
    main_c = next(f for f in doc["files"] if f["fileName"] == "./app/main.c")
    assert main_c["checksums"] == [{"algorithm": "SHA1", "checksumValue": "8c9d14b64da9026abd3b1fce520de54cf757f084"}]


def test_verification_code_follows_spdx_rule(samples):
    doc, _ = convert(samples / "valid_scan.json", created=FIXED_TIME)
    libfoo = next(p for p in doc["packages"] if p["name"] == "libfoo")
    sha1s = sorted([
        "219ae878d2877fc176e05830ab919104d0852352",
        "e33afa0fa0c1849b1a86f75977f5ad134f1bfd35",
        "d09cf782f6a47209227be47c32263cd68547d765",
    ])
    expected = hashlib.sha1("".join(sha1s).encode()).hexdigest()
    assert libfoo["packageVerificationCode"]["packageVerificationCodeValue"] == expected


def test_relationships(samples):
    doc, _ = convert(samples / "valid_scan.json", created=FIXED_TIME)
    describes = _rels(doc, "DESCRIBES")
    assert len(describes) == 1  # only the app is top level
    assert describes[0]["relatedSpdxElement"].startswith("SPDXRef-Package-demo-app")
    assert len(_rels(doc, "CONTAINS")) == 5
    assert len(_rels(doc, "DEPENDS_ON")) == 2


def test_every_relationship_points_to_a_real_element(samples):
    doc, _ = convert(samples / "valid_scan.json", created=FIXED_TIME)
    ids = {"SPDXRef-DOCUMENT"} | {p["SPDXID"] for p in doc["packages"]} | {f["SPDXID"] for f in doc["files"]}
    for r in doc["relationships"]:
        assert r["spdxElementId"] in ids
        assert r["relatedSpdxElement"] in ids


def test_missing_values_become_noassertion_never_guessed(samples):
    doc, diags = convert(samples / "missing_fields_scan.json", created=FIXED_TIME)
    libbar = next(p for p in doc["packages"] if p["name"] == "libbar")
    assert libbar["supplier"] == "NOASSERTION"
    assert libbar["downloadLocation"] == "NOASSERTION"
    assert libbar["licenseDeclared"] == "NOASSERTION"
    assert "versionInfo" not in libbar
    assert any(d.field == "supplier" and d.severity == "WARNING" for d in diags)
    assert any(d.field == "version" and d.severity == "INFO" for d in diags)
    assert doc["name"] == "missing_fields_scan"


def test_explicit_none_is_kept(samples):
    doc, _ = convert(samples / "missing_fields_scan.json", created=FIXED_TIME)
    util = next(f for f in doc["files"] if f["fileName"] == "./src/bar_util.c")
    assert util["copyrightText"] == "NONE"


def test_broken_input_produces_no_document(samples):
    doc, diags = convert(samples / "broken_scan.json", created=FIXED_TIME)
    assert doc is None
    assert any(d.severity == "ERROR" for d in diags)
