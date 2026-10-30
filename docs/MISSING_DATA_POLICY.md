# Missing-Data Policy

The main rule of this tool: **never make up data.** When a value is missing, the tool does one of three things, depending on what the SPDX 2.3 spec allows for that field.

| Action | When | Effect |
|---|---|---|
| **NOASSERTION** | Field is optional, or SPDX allows "unknown" for it | Value is written as `NOASSERTION` and a **warning** goes in the gap report |
| **Omit** | Field is fully optional and has no "unknown" value | Field is left out of the output; logged as **info** |
| **Error** | Field is required and SPDX does not allow `NOASSERTION` | Record is rejected and an **error** goes in the gap report. If any error exists, no SPDX file is written and the tool exits with a non-zero code |

`NONE` is **never** used to fill a gap. It is only written when the input itself says `NONE` ("we checked, there is none").

---

## Per-field policy

### Document
| Field | If missing |
|---|---|
| `document_name` | Use input file name → **warning** |

### Package
| Input field | SPDX field | If missing |
|---|---|---|
| `id` | (used for SPDXID and links) | **Error**, package rejected |
| `name` | `name` | **Error**, package rejected |
| `version` | `versionInfo` | **Omit**, info |
| `supplier` | `supplier` | **NOASSERTION**, warning |
| `origin` | `downloadLocation` | **NOASSERTION**, warning |
| `declared_license` | `licenseDeclared` | **NOASSERTION**, warning |
| `concluded_license` | `licenseConcluded` | **NOASSERTION**, warning |
| `copyright` | `copyrightText` | **NOASSERTION**, warning |

### File
| Input field | SPDX field | If missing |
|---|---|---|
| `package_id` | (CONTAINS link) | **Error**, file rejected |
| `path` | `fileName` | **Error**, file rejected |
| `sha1` | `checksums` | **Error**, file rejected. A checksum is never invented |
| `found_license` | `licenseInfoInFiles` | **NOASSERTION**, warning |
| `concluded_license` | `licenseConcluded` | **NOASSERTION**, warning |
| `copyright` | `copyrightText` | **NOASSERTION**, warning |

### Relationship
| Problem | Result |
|---|---|
| `from` or `to` missing, or points to an unknown id | **Error** (orphaned reference) |
| `type` not `DEPENDS_ON` / `CONTAINS` | **Error** |
| A package depends on itself, or a `CONTAINS` loop | **Error** (illegal cycle) |

### Invalid values (present but wrong)
| Problem | Result |
|---|---|
| `sha1` not 40 hex characters | **Error** |
| License is not a valid SPDX license ID/expression | **Warning** for now; final rule depends on mentor's decision about custom licenses |
| Duplicate package `id` | **Error**, both records rejected |

---

## Gap report format

Each gap is one line with: severity, record location, field, and message. Example:

```
ERROR    files[3]      sha1      missing: SPDX 2.3 requires a SHA1 checksum for every file
WARNING  packages[1]   supplier  missing: written as NOASSERTION
INFO     packages[1]   version   missing: versionInfo omitted
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | SPDX file written and valid (warnings allowed) |
| `1` | Input has errors (gap report lists them); no file written |
| `2` | Output failed schema validation |
| `3` | Bad CLI usage or input file can't be read |
