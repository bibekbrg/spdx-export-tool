"""Command-line interface: spdx-export --input scan.json --output bom.spdx.json

Exit codes
  0  SPDX file written and valid (warnings allowed)
  1  input has errors; no file written
  2  output failed SPDX schema validation; no file written
  3  bad command-line usage or input file can't be read
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .adapters import file_sha256, load_scan
from .mapper import DEFAULT_NAMESPACE_BASE, build_document
from .model import ERROR, INFO, WARNING
from .serializer import write_json
from .validator import validate

OK, INPUT_ERRORS, SCHEMA_ERRORS, USAGE_ERROR = 0, 1, 2, 3


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse would exit with 2; we reserve 2 for schema errors
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        sys.exit(USAGE_ERROR)


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(
        prog="spdx-export",
        description="Convert a compliance scan (JSON/CSV) into a validated SPDX 2.3 JSON document.",
    )
    p.add_argument("-i", "--input", required=True, help="scan file (.json or .csv)")
    p.add_argument("-o", "--output", required=True, help="where to write the SPDX JSON file")
    p.add_argument("--created", help="fixed creation time YYYY-MM-DDThh:mm:ssZ (for repeatable output)")
    p.add_argument("--creator", help="person name added to creators, e.g. 'Bibek Roy'")
    p.add_argument("--namespace-base", default=DEFAULT_NAMESPACE_BASE, help="base URL for documentNamespace")
    p.add_argument("--gap-report", help="also save the gap report to this text file")
    p.add_argument("-q", "--quiet", action="store_true", help="only print the summary, not each warning")
    p.add_argument("--version", action="version", version=f"spdx-export {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    args = build_parser().parse_args(argv)
    src, out = Path(args.input), Path(args.output)

    print(f"SPDX Export Tool {__version__}")
    print(f"  Input   : {src}")
    if not src.is_file():
        print(f"  [FAIL]  input file not found: {src}")
        return USAGE_ERROR
    try:
        scan = load_scan(src)
    except (ValueError, OSError, UnicodeDecodeError) as e:
        print(f"  [FAIL]  cannot read input: {e}")
        return USAGE_ERROR

    print(f"  Read    : {len(scan.packages)} packages, {len(scan.files)} files, "
          f"{len(scan.relationships)} relationships")

    if scan.has_errors:
        _report(scan.diagnostics, args)
        print("  Result  : FAILED: input has errors, no SPDX file written (nothing is guessed)")
        return INPUT_ERRORS

    document, map_diags = build_document(
        scan,
        fallback_name=src.stem,
        input_digest=file_sha256(src),
        created=args.created,
        creator_person=args.creator,
        namespace_base=args.namespace_base,
    )
    diagnostics = scan.diagnostics + map_diags
    if any(d.severity == ERROR for d in diagnostics):
        _report(diagnostics, args)
        print("  Result  : FAILED: mapping errors, no SPDX file written")
        return INPUT_ERRORS

    schema_errors = validate(document)
    if schema_errors:
        _report(diagnostics + schema_errors, args)
        print("  Schema  : INVALID against official SPDX 2.3 schema")
        print("  Result  : FAILED: no SPDX file written")
        return SCHEMA_ERRORS
    print("  Schema  : valid against official SPDX 2.3 schema")

    out.parent.mkdir(parents=True, exist_ok=True)
    write_json(document, out)
    _report(diagnostics, args)
    print(f"  Output  : {out}")
    print("  Result  : SUCCESS")
    return OK


def _report(diagnostics, args) -> None:
    counts = {s: sum(d.severity == s for d in diagnostics) for s in (ERROR, WARNING, INFO)}
    print(f"  Gaps    : {counts[ERROR]} errors, {counts[WARNING]} warnings, {counts[INFO]} info")
    lines = [str(d) for d in diagnostics]
    if lines and not (args.quiet and counts[ERROR] == 0):
        print("  ---- gap report ----")
        for line in lines:
            print("  " + line)
        print("  --------------------")
    if args.gap_report:
        Path(args.gap_report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.gap_report).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        print(f"  Report  : {args.gap_report}")


if __name__ == "__main__":
    sys.exit(main())
