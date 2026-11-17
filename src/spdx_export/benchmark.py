"""Speed test: generate a big scan (default 50 packages x 20 files = 1,000 files)
and time every step of the real pipeline. PRD target: under 3.0 seconds.

Run:  spdx-export-benchmark            (or: python -m spdx_export.benchmark)
"""

import argparse
import csv
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

from .adapters import file_sha256, load_scan
from .mapper import build_document
from .serializer import write_json
from .validator import validate

TARGET_SECONDS = 3.0
LICENSES = ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-2.0-only", "ISC"]


def make_scan(packages: int = 50, files_per_package: int = 20) -> dict:
    """A realistic, repeatable scan: every value is derived from its index."""
    pkgs, files, rels = [], [], []
    for p in range(packages):
        pid = f"pkg-{p:03d}"
        lic = LICENSES[p % len(LICENSES)]
        pkgs.append({
            "id": pid, "name": f"library-{p:03d}", "version": f"{1 + p % 4}.{p % 10}.0",
            "supplier": f"Vendor {p % 7}", "origin": f"https://example.com/lib/{p:03d}",
            "declared_license": lic, "concluded_license": lic,
            "copyright": f"Copyright 2026 Vendor {p % 7}",
        })
        if p > 0:
            rels.append({"from": "pkg-000", "type": "DEPENDS_ON", "to": pid})
        for f in range(files_per_package):
            path = f"src/module_{f // 5}/file_{f:02d}.c"
            files.append({
                "package_id": pid, "path": path,
                "sha1": hashlib.sha1(f"{pid}/{path}".encode()).hexdigest(),
                "found_license": lic, "concluded_license": lic,
                "copyright": f"Copyright 2026 Vendor {p % 7}",
            })
    return {"document_name": f"benchmark-{packages}x{files_per_package}",
            "packages": pkgs, "files": files, "relationships": rels}


def write_scan_csv(scan: dict, path: Path) -> None:
    deps: dict[str, list[str]] = {}
    for r in scan["relationships"]:
        deps.setdefault(r["from"], []).append(r["to"])
    pkgs = {p["id"]: p for p in scan["packages"]}
    cols = ["package_id", "package_name", "version", "supplier", "origin", "declared_license",
            "concluded_license", "package_copyright", "file_path", "sha1", "found_license",
            "file_concluded_license", "file_copyright", "depends_on"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for f in scan["files"]:
            p = pkgs[f["package_id"]]
            w.writerow([p["id"], p["name"], p["version"], p["supplier"], p["origin"],
                        p["declared_license"], p["concluded_license"], p["copyright"],
                        f["path"], f["sha1"], f["found_license"], f["concluded_license"],
                        f["copyright"], ";".join(deps.get(p["id"], []))])


def run(input_path: Path, output_path: Path) -> dict:
    """Time each pipeline step. Returns {step: seconds, ..., 'total': seconds}."""
    t = {}
    start = time.perf_counter()

    s = time.perf_counter(); scan = load_scan(input_path); t["read + check input"] = time.perf_counter() - s
    if scan.has_errors:
        raise RuntimeError("benchmark input has errors")
    s = time.perf_counter()
    doc, _ = build_document(scan, fallback_name=input_path.stem, input_digest=file_sha256(input_path),
                            created="2026-01-01T00:00:00Z")
    t["map to SPDX 2.3"] = time.perf_counter() - s
    s = time.perf_counter(); errors = validate(doc); t["schema validation"] = time.perf_counter() - s
    if errors:
        raise RuntimeError(f"benchmark output invalid: {errors[0]}")
    s = time.perf_counter(); write_json(doc, output_path); t["write JSON"] = time.perf_counter() - s

    t["total"] = time.perf_counter() - start
    t["_packages"], t["_files"] = len(doc["packages"]), len(doc["files"])
    return t


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="spdx-export-benchmark", description=__doc__.splitlines()[0])
    ap.add_argument("--packages", type=int, default=50)
    ap.add_argument("--files-per-package", type=int, default=20)
    args = ap.parse_args(argv)

    scan = make_scan(args.packages, args.files_per_package)
    worst = 0.0
    print(f"Speed test: {args.packages} packages, {args.packages * args.files_per_package} files "
          f"(target under {TARGET_SECONDS:.1f} s)")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "scan.json").write_text(json.dumps(scan), encoding="utf-8")
        write_scan_csv(scan, tmp / "scan.csv")
        for fmt in ("json", "csv"):
            r = run(tmp / f"scan.{fmt}", tmp / f"out_{fmt}.spdx.json")
            print(f"\n  {fmt.upper()} input -> {r['_packages']} packages, {r['_files']} files")
            for step, sec in r.items():
                if not step.startswith("_") and step != "total":
                    print(f"    {step:<20} {sec:7.3f} s")
            print(f"    {'TOTAL':<20} {r['total']:7.3f} s")
            worst = max(worst, r["total"])

    ok = worst < TARGET_SECONDS
    print(f"\n  Result: {'PASS' if ok else 'FAIL'}: slowest run {worst:.3f} s "
          f"({'under' if ok else 'over'} the {TARGET_SECONDS:.1f} s target)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
