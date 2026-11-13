import pytest

from conftest import FIXED_TIME
from spdx_export import cli


def run(*args):
    return cli.main([str(a) for a in args])


def test_valid_scan_writes_expected_file(samples, tmp_path, capsys):
    out = tmp_path / "bom.spdx.json"
    code = run("-i", samples / "valid_scan.json", "-o", out, "--created", FIXED_TIME, "--creator", "Bibek Roy")
    assert code == 0
    expected = (samples / "expected" / "valid_scan.spdx.json").read_text(encoding="utf-8")
    assert out.read_text(encoding="utf-8") == expected
    text = capsys.readouterr().out
    assert "valid against official SPDX 2.3 schema" in text
    assert "SUCCESS" in text


def test_missing_fields_succeeds_with_warnings_and_report(samples, tmp_path, capsys):
    out, report = tmp_path / "out.json", tmp_path / "gaps.txt"
    code = run("-i", samples / "missing_fields_scan.json", "-o", out, "--gap-report", report)
    assert code == 0
    assert out.exists()
    assert "NOASSERTION" in report.read_text(encoding="utf-8")
    assert "17 warnings" in capsys.readouterr().out


def test_broken_scan_writes_nothing(samples, tmp_path, capsys):
    out = tmp_path / "out.json"
    code = run("-i", samples / "broken_scan.json", "-o", out)
    assert code == 1
    assert not out.exists()
    text = capsys.readouterr().out
    assert "10 errors" in text
    assert "nothing is guessed" in text


def test_schema_failure_returns_2(samples, tmp_path, monkeypatch):
    real_build = cli.build_document

    def bad_build(*a, **k):
        doc, diags = real_build(*a, **k)
        del doc["dataLicense"]
        return doc, diags

    monkeypatch.setattr(cli, "build_document", bad_build)
    out = tmp_path / "out.json"
    assert run("-i", samples / "valid_scan.json", "-o", out) == 2
    assert not out.exists()


def test_missing_input_file_returns_3(tmp_path):
    assert run("-i", tmp_path / "nope.json", "-o", tmp_path / "out.json") == 3


def test_unsupported_input_type_returns_3(tmp_path):
    f = tmp_path / "scan.xml"
    f.write_text("<x/>", encoding="utf-8")
    assert run("-i", f, "-o", tmp_path / "out.json") == 3


def test_missing_arguments_returns_3():
    with pytest.raises(SystemExit) as e:
        run("-i", "only-input.json")
    assert e.value.code == 3


def test_quiet_hides_warning_lines(samples, tmp_path, capsys):
    run("-i", samples / "missing_fields_scan.json", "-o", tmp_path / "o.json", "-q")
    text = capsys.readouterr().out
    assert "gap report" not in text
    assert "17 warnings" in text
