# SPDX Export Tool

A Python command-line tool that converts compliance scan records (JSON/CSV) into validated SPDX 2.3 JSON reports.

It maps scan results (packages, files, licenses, checksums, relationships) into an SPDX 2.3 document, checks it against the official SPDX schema, and lists any missing data in a gap report. **It never makes up missing values.**

> Built as part of an Open Source Developer OJT (Project G370).

## Status

🚧 **Week 1: Requirements & Setup (done)**

| Week | Focus | Status |
|---|---|---|
| 1 | SPDX version, input format, field mapping, missing-data policy, sample files, repo setup | ✅ |
| 2 | Data model, input adapters, JSON serializer, SPDXID generator, unit tests | ⏳ |
| 3 | Schema validation, gap report, CLI, GitHub Actions | ⏳ |
| 4 | More tests (≥85% coverage), performance check, docs, demo | ⏳ |

## Planned usage

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
src/          application code
tests/        pytest tests
samples/      sample scan inputs
docs/         design documents
requirements.txt
```

## Tech stack

Python 3.10+, jsonschema, pytest, coverage.py, GitHub Actions.

## Limitations

This tool produces technical SBOM documents for review. It does not give legal approval of license compliance.
