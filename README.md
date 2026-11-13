# SPDX Export Tool

A Python command-line tool that converts compliance scan records (JSON/CSV) into validated SPDX 2.3 JSON reports.

It maps scan results (packages, files, licenses, checksums, relationships) into an SPDX 2.3 document, checks it against the official SPDX schema, and lists any missing data in a gap report. **It never makes up missing values.**

> Built as part of an Open Source Developer OJT (Project G370).

## Status

🚧 **Week 2: Core Development (done)**: 31 unit tests passing, 93% coverage

| Week | Focus | Status |
|---|---|---|
| 1 | SPDX version, input format, field mapping, missing-data policy, sample files, repo setup | ✅ |
| 2 | Data model, input adapters, JSON serializer, SPDXID generator, unit tests | ✅ |
| 3 | Schema validation, gap report, CLI, GitHub Actions | ⏳ |
| 4 | More tests (≥85% coverage), performance check, docs, demo | ⏳ |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

## Try it (Week 2)

```bash
python -c "import sys; sys.path.insert(0, 'src'); from spdx_export.pipeline import convert; from spdx_export.serializer import to_json; doc, gaps = convert('samples/valid_scan.json'); print(to_json(doc))"
```

Example output: [`samples/expected/valid_scan.spdx.json`](samples/expected/valid_scan.spdx.json)

## Run the tests

```bash
python -m pytest
python -m coverage run --source=src -m pytest && python -m coverage report
```

## Planned CLI (Week 3)

```bash
spdx-export --input samples/valid_scan.json --output bom.spdx.json
```

Options (planned): `--created` (fixed timestamp for repeatable output), `--creator`, `--namespace-base`.

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
  pipeline.py    runs the steps in order
tests/           pytest unit tests
samples/         sample scan inputs + expected output
docs/            design documents
```

## Tech stack

Python 3.10+, jsonschema, pytest, coverage.py, GitHub Actions.

## Limitations

This tool produces technical SBOM documents for review. It does not give legal approval of license compliance.
