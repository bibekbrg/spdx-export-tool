# User Guide

How to install and use the SPDX Export Tool.

## 1. What it does

It reads a compliance scan file (**JSON** or **CSV**) and writes an **SPDX 2.3 JSON** document that passes the official SPDX schema. Missing data is never invented: unknown values become `NOASSERTION`, and missing required data stops the export with a clear error.

## 2. Install

Needs Python 3.10 or newer.

```bash
git clone https://github.com/bibekbrg/spdx-export-tool.git
cd spdx-export-tool
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

This installs three commands: `spdx-export`, `spdx-export-benchmark` and `spdx-export-web`.

**Windows shortcut:** double-click `demo.bat`. It installs everything on the first run and shows a live demo.

## 3. Convert a scan

```bash
spdx-export --input samples/valid_scan.json --output bom.spdx.json
```

Output:

```
SPDX Export Tool 0.1.0
  Input   : samples/valid_scan.json
  Read    : 3 packages, 5 files, 2 relationships
  Schema  : valid against official SPDX 2.3 schema
  Gaps    : 0 errors, 0 warnings, 0 info
  Output  : bom.spdx.json
  Result  : SUCCESS
```

### Options

| Option | Meaning |
|---|---|
| `-i`, `--input` | Scan file, `.json` or `.csv` (format: [INPUT_FORMAT.md](INPUT_FORMAT.md)) |
| `-o`, `--output` | Where to write the SPDX JSON |
| `--created` | Fixed creation time `YYYY-MM-DDThh:mm:ssZ`. Use it when you need byte-identical output on every run. |
| `--creator` | Adds `Person: <name>` to the document creators |
| `--namespace-base` | Base URL for `documentNamespace` (default `https://spdx.org/spdxdocs`) |
| `--gap-report FILE` | Also save the gap report as a text file |
| `-q`, `--quiet` | Print only the summary (errors are always shown) |
| `--version` | Show the tool version |

### Exit codes

| Code | Meaning | Output file written? |
|---|---|---|
| `0` | Success (warnings are allowed) | Yes |
| `1` | Input has errors (e.g. missing SHA1, unknown package, circular CONTAINS) | No |
| `2` | Generated document failed the official schema check | No |
| `3` | Wrong command-line usage, or input file missing/unreadable/unsupported type | No |

Scripts and CI pipelines can use the exit code to stop a release when the SBOM is not valid.

## 4. Reading the gap report

Each line is: **severity**, **where** in the input, **field**, **message**.

```
WARNING  packages[1]      supplier           missing: written as NOASSERTION
INFO     packages[1]      version            missing: versionInfo omitted
ERROR    files[0]         sha1               missing: SPDX 2.3 requires a SHA1 for every file; never invented
```

| Severity | Meaning | Export continues? |
|---|---|---|
| `INFO` | Something was left out or merged, nothing wrong | Yes |
| `WARNING` | Unknown value written as `NOASSERTION`, or a dependency loop | Yes |
| `ERROR` | Required data missing or invalid | **No** |

The full rules are in [MISSING_DATA_POLICY.md](MISSING_DATA_POLICY.md).

## 5. Speed test

```bash
spdx-export-benchmark                       # 50 packages x 20 files = 1,000 files
spdx-export-benchmark --packages 200 --files-per-package 50
```

It generates a realistic scan, runs every step of the real pipeline on both JSON and CSV versions, and prints the time per step. PRD target: under 3.0 seconds for 1,000 files. Measured: about **0.15 s**.

## 6. Web preview

```bash
spdx-export-web                 # opens http://127.0.0.1:8000
spdx-export-web --port 8010     # if 8000 is busy
```

On Windows, double-click `web.bat`. Drop in a `.json` or `.csv` scan (or click a sample) to see the result banner, the package tree with files and licenses, relationships, the gap report with filters, and the SPDX JSON with a download button. The page also runs the 1,000-file speed test. It only listens on your own computer (127.0.0.1); uploads are limited to 20 MB.

## 6b. Use from Python

```python
from spdx_export.pipeline import convert
from spdx_export.serializer import write_json
from spdx_export.validator import validate

doc, gaps = convert("samples/valid_scan.json", created="2026-01-01T00:00:00Z")
if doc is not None and not validate(doc):
    write_json(doc, "bom.spdx.json")
for g in gaps:
    print(g)
```

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `input file not found` | Check the path; use quotes if it has spaces |
| `Unsupported input type` | Only `.json` and `.csv` are supported |
| `missing required column(s)` | The CSV header must include at least `package_id` and `package_name` |
| `invalid JSON` | The file isn't valid JSON; the message shows the line and column |
| CSV from Excel looks odd | Save as **CSV UTF-8**. A BOM at the start is handled automatically. |
| `'spdx-export' is not recognized` | Activate the virtual environment, or run `python -m spdx_export ...` |

## 8. Limitations

- Output format is SPDX 2.3 JSON only (Tag:Value and SPDX 3.0 are possible future work).
- License strings are copied as given. Checking them against the SPDX License List and handling custom `LicenseRef-` licenses is pending the mentor's decision.
- The tool documents what the scan says. It does not give legal approval of license compliance.
