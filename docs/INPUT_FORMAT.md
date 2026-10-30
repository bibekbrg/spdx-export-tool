# Input Format (Source Scan Schema)

This file describes what the tool expects as input. The tool reads scan results in **JSON** or **CSV**. Both formats carry the same information.

Example files are in [`samples/`](../samples).

---

## 1. JSON format

A JSON scan file is one object with four parts:

```json
{
  "document_name": "my-app-1.0",
  "packages": [ ... ],
  "files": [ ... ],
  "relationships": [ ... ]
}
```

### `document_name` (optional)
A name for the SBOM. If it is missing, the tool uses the input file name (without extension) and logs a warning.

### `packages`
One entry per component or library.

| Field | Type | Required | Example | Notes |
|---|---|---|---|---|
| `id` | string | **yes** | `pkg-1` | Must be unique inside the file. Used to link files and relationships to this package. |
| `name` | string | **yes** | `libfoo` | |
| `version` | string | no | `1.0.0` | |
| `supplier` | string | no | `Acme Corp` | Organization or person that provides the package. |
| `origin` | string | no | `https://github.com/acme/libfoo` | Where the package can be downloaded from. |
| `declared_license` | string | no | `MIT` | License the package author states. SPDX license ID or expression. |
| `concluded_license` | string | no | `MIT` | License concluded by the scanner or reviewer. |
| `copyright` | string | no | `Copyright 2024 Acme Corp` | |

### `files`
One entry per scanned file.

| Field | Type | Required | Example | Notes |
|---|---|---|---|---|
| `package_id` | string | **yes** | `pkg-1` | Must match a package `id`. |
| `path` | string | **yes** | `src/foo.c` | Path relative to the package root. |
| `sha1` | string | **yes** | `219ae878...` | 40 hex characters. SPDX 2.3 requires a SHA1 for every file. |
| `found_license` | string | no | `MIT` | License(s) the scanner found written inside the file. |
| `concluded_license` | string | no | `MIT` | |
| `copyright` | string | no | `Copyright 2024 Acme Corp` | |

### `relationships` (optional)
Extra links between packages.

| Field | Type | Required | Example | Notes |
|---|---|---|---|---|
| `from` | string | **yes** | `pkg-1` | Package `id` |
| `type` | string | **yes** | `DEPENDS_ON` | Allowed: `DEPENDS_ON`, `CONTAINS` |
| `to` | string | **yes** | `pkg-2` | Package `id` |

> **CONTAINS between a package and its files is automatic.** Every file with `package_id: pkg-1` becomes `pkg-1 CONTAINS <file>`. You don't need to list these.

---

## 2. CSV format

CSV is a flat table, so it uses **one row per file**. Package details repeat on each row of the same package.

| Column | Maps to |
|---|---|
| `package_id` | package `id` |
| `package_name` | package `name` |
| `version` | package `version` |
| `supplier` | package `supplier` |
| `origin` | package `origin` |
| `declared_license` | package `declared_license` |
| `concluded_license` | package `concluded_license` |
| `package_copyright` | package `copyright` |
| `file_path` | file `path` |
| `sha1` | file `sha1` |
| `found_license` | file `found_license` |
| `file_concluded_license` | file `concluded_license` |
| `file_copyright` | file `copyright` |
| `depends_on` | `DEPENDS_ON` relationships. Several package IDs separated by `;` |

Rules for CSV:
- The first row must be the header.
- Encoding is UTF-8.
- If rows of the same `package_id` have different package details, the tool reports an error instead of picking one.
- A package with no files can be written as a row with empty `file_path` and `sha1`.

---

## 3. Special values

| Value in input | Meaning |
|---|---|
| empty / missing | Unknown. Handled by the [missing-data policy](MISSING_DATA_POLICY.md). |
| `NONE` | We checked and there is none (e.g. no license, no copyright). Passed to SPDX as `NONE`. |
| `NOASSERTION` | We did not check / can't say. Passed to SPDX as `NOASSERTION`. |

---

## 4. What counts as a malformed record

These records are set aside and listed in the gap report, instead of crashing the tool:
- a package without `id` or `name`
- two packages with the same `id`
- a file without `path` or with a `package_id` that doesn't exist
- a file whose `sha1` is missing or is not 40 hex characters
- a relationship pointing to an `id` that doesn't exist, or with a type not in the allowed list
