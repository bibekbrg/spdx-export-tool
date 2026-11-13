# SPDX Export Tool

![tests](https://github.com/bibekbrg/spdx-export-tool/actions/workflows/ci.yml/badge.svg)

A Python command-line tool that converts compliance scan records (JSON/CSV) into validated SPDX 2.3 JSON reports.

It maps scan results (packages, files, licenses, checksums, relationships) into an SPDX 2.3 document, checks it against the official SPDX schema, and lists any missing data in a gap report. **It never makes up missing values.**

> Built as part of an Open Source Developer OJT (Project G370).

## Status

🚧 **Week 3: Integration (in progress)**: working CLI, official schema validation, gap report, CI. 41 tests passing, 94% coverage.

| Week | Focus | Status |
|---|---|---|
| 1 | SPDX version, input format, field mapping, missing-data policy, sample files, repo setup | ✅ |
| 2 | Data model, input adapters, JSON serializer, SPDXID generator, unit tests | ✅ |
| 3 | Schema validation, gap report, CLI, GitHub Actions | ✅ core done |
| 4 | More tests (≥85% coverage), performance check, docs, demo | ⏳ |

## Quick demo (Windows)

Double-click **`demo.bat`**. It sets itself up on the first run, then shows 4 live cases:
valid JSON → SPDX created · same data as CSV · missing fields → NOASSERTION + gap report · broken scan → refused with every error listed.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
pip install -e .
```

## Usage

```bash
spdx-export --input samples/valid_scan.json --output bom.spdx.json
```

```
SPDX Export Tool 0.1.0
  Input   : samples/valid_scan.json
  Read    : 3 packages, 5 files, 2 relationships
  Schema  : valid against official SPDX 2.3 schema
  Gaps    : 0 errors, 0 warnings, 0 info
  Output  : bom.spdx.json
  Result  : SUCCESS
```

| Option | Meaning |
|---|---|
| `-i, --input` | scan file (`.json` or `.csv`) |
| `-o, --output` | where to write the SPDX JSON |
| `--created` | fixed creation time `YYYY-MM-DDThh:mm:ssZ`, for byte-identical repeat runs |
| `--creator` | person added to `creators`, e.g. `"Bibek Roy"` |
| `--namespace-base` | base URL for `documentNamespace` |
| `--gap-report` | also save the gap report to a text file |
| `-q, --quiet` | summary only |

**Exit codes:** `0` success · `1` input errors (no file written) · `2` schema validation failed · `3` bad usage / unreadable input

Example output: [`samples/expected/valid_scan.spdx.json`](samples/expected/valid_scan.spdx.json)

## Run the tests

```bash
python -m pytest
python -m coverage run --source=src -m pytest && python -m coverage report
```

Tests also run automatically on every push (GitHub Actions, Python 3.10 and 3.12).

## Documentation

| Document | What's in it |
|---|---|
| [Architecture](docs/ARCHITECTURE.md) | Project overview, tech stack, folder structure, workflow diagram |
| [Input format](docs/INPUT_FORMAT.md) | What the JSON/CSV scan file must look like |
| [Field mapping](docs/FIELD_MAPPING.md) | How each input field becomes an SPDX 2.3 field |
| [Missing-data policy](docs/MISSING_DATA_POLICY.md) | What happens when a field is missing: NOASSERTION, omit, or error |
| [Sample files](samples/README.md) | Example inputs: valid, missing fields, broken |

## Project structure

```
src/spdx_export/
  model.py       data classes: Package, File, Relationship, Diagnostic
  adapters.py    read JSON/CSV, reject bad records (never guess)
  spdxid.py      deterministic SPDXRef-... IDs
  mapper.py      build the SPDX 2.3 document, apply missing-data policy
  serializer.py  write stable, pretty UTF-8 JSON
  validator.py   check against the official SPDX 2.3 JSON schema
  cli.py         the spdx-export command
  pipeline.py    the steps in order, for use from Python
  schemas/       official SPDX 2.3 JSON schema (from github.com/spdx/spdx-spec)
tests/           pytest tests
samples/         sample scan inputs + expected output
docs/            design documents
demo.bat         one-click live demo
```

## Tech stack

Python 3.10+, jsonschema, pytest, coverage.py, GitHub Actions.

## Limitations

This tool produces technical SBOM documents for review. It does not give legal approval of license compliance.
