# Testing & Verification

## How to run

```bash
python -m pytest                                              # all tests
python -m coverage run --source=src -m pytest && python -m coverage report
spdx-export-benchmark                                         # speed test
```

Tests also run automatically on every push with GitHub Actions on Python 3.10 and 3.12. The build fails if coverage drops below 85%.

## Results

| Metric (from the PRD) | Target | Result |
|---|---|---|
| Official SPDX 2.3 schema conformance | 100% | **100%**: every generated document passes |
| Test coverage | ≥ 85% | **91%** (76 tests) |
| Speed: 1,000 files + 50 packages | < 3.0 s | **~0.15 s** (JSON and CSV) |
| Fabricated licenses, hashes, links | 0 | **0**: missing values become NOASSERTION or errors |
| Deterministic output | same input → same output | **Yes**: byte-for-byte check against `samples/expected/valid_scan.spdx.json` |

## What is tested

| Test file | Covers |
|---|---|
| `test_adapters.py` | Reading JSON and CSV, CSV = JSON, every kind of broken record, path cleaning |
| `test_spdxid.py` | IDs are repeatable, unique, and use only SPDX-allowed characters |
| `test_mapper.py` | Header, packages, files, verification code, relationships, NOASSERTION policy |
| `test_serializer.py` | Deterministic output, sorted keys, Unicode, exact match with the expected file |
| `test_validator.py` | Generated documents pass the official schema; broken documents are caught |
| `test_cli.py` | The `spdx-export` command: success, warnings, all exit codes, gap report file |
| `test_edge_cases.py` | BOM files from Excel, header case/spaces, empty files, wrong types, whitespace values, numeric versions, Unicode names, packages without files, duplicates, circular relationships |
| `test_performance.py` | 1,000 files from JSON and CSV under 3 seconds |
| `test_web.py` | Web preview over real HTTP: page, samples, upload, wrong type, too-large file, speed test |

## Edge cases handled

| Case | Behaviour |
|---|---|
| File saved with a BOM (Excel, Notepad) | Read normally |
| CSV header with different case/spaces | Accepted |
| CSV missing `package_id`/`package_name` columns | ERROR, names the missing columns |
| Empty file / header only / `{}` | ERROR "no valid packages found" |
| `packages` is not a list | ERROR |
| Value is only spaces | Treated as missing |
| Version written as a number (`2.5`) | Converted to text `"2.5"` |
| Unicode names, paths and copyright | Kept as is, output still valid |
| Package with no files | `filesAnalyzed: false`, no verification code |
| Same file listed twice, same SHA1 | Merged (INFO) |
| Same file listed twice, different SHA1 | ERROR |
| Same path in two different packages | Allowed, different SPDXIDs |
| Duplicate relationship | Ignored (INFO) |
| Lower-case relationship type | Accepted |
| `CONTAINS` loop (A contains B contains A) | ERROR, impossible in reality |
| `DEPENDS_ON` loop (A → B → C → A) | WARNING, exported, all packages described |
| Package relating to itself | ERROR |

## Sample fixtures

See [samples/README.md](../samples/README.md): a valid scan (JSON and CSV), a scan with missing fields, and a broken scan that triggers every error type.
