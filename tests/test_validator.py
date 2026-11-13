from conftest import FIXED_TIME
from spdx_export.pipeline import convert
from spdx_export.validator import validate


def test_generated_documents_pass_official_schema(samples):
    for name in ("valid_scan.json", "valid_scan.csv", "missing_fields_scan.json"):
        doc, _ = convert(samples / name, created=FIXED_TIME)
        assert validate(doc) == [], name


def test_schema_catches_broken_document(samples):
    doc, _ = convert(samples / "valid_scan.json", created=FIXED_TIME)
    del doc["spdxVersion"]
    doc["packages"][0]["filesAnalyzed"] = "yes"  # must be a boolean
    errors = validate(doc)
    assert len(errors) >= 2
    assert all(e.severity == "ERROR" for e in errors)
    assert any("spdxVersion" in e.message for e in errors)
    assert any(e.location.startswith("packages[0]") for e in errors)
