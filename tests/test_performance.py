"""PRD target: 1,000 files and 50 packages processed and validated in under 3 seconds."""

import json

from spdx_export.benchmark import TARGET_SECONDS, make_scan, run, write_scan_csv


def test_1000_files_json_under_target(tmp_path):
    src = tmp_path / "scan.json"
    src.write_text(json.dumps(make_scan(50, 20)), encoding="utf-8")
    result = run(src, tmp_path / "out.json")
    assert result["_packages"] == 50
    assert result["_files"] == 1000
    assert result["total"] < TARGET_SECONDS


def test_1000_files_csv_under_target(tmp_path):
    src = tmp_path / "scan.csv"
    write_scan_csv(make_scan(50, 20), src)
    result = run(src, tmp_path / "out.json")
    assert result["_files"] == 1000
    assert result["total"] < TARGET_SECONDS


def test_benchmark_command_passes(capsys):
    from spdx_export.benchmark import main
    assert main(["--packages", "5", "--files-per-package", "4"]) == 0
    assert "PASS" in capsys.readouterr().out
