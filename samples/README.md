# Sample scan files

Test inputs for the tool. The format is described in [docs/INPUT_FORMAT.md](../docs/INPUT_FORMAT.md).

| File | What it is | Expected result |
|---|---|---|
| `valid_scan.json` | 3 packages (app → libfoo, libbar), 5 files, all fields filled | Valid SPDX file, no warnings, exit code `0` |
| `valid_scan.csv` | Same data as `valid_scan.json`, in CSV | Same SPDX output as the JSON version |
| `missing_fields_scan.json` | Optional fields left out (supplier, origin, licenses, copyright, version, document name) | Valid SPDX file with `NOASSERTION` values and warnings in the gap report, exit code `0` |
| `broken_scan.json` | Missing SHA1, invalid SHA1, package without name, duplicate package id, file with unknown package, file without path, relationship to unknown package, unknown relationship type, package depending on itself | No SPDX file written, every problem listed as an error, exit code `1` |
