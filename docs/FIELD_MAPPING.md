# Field Mapping Matrix (Input → SPDX 2.3)

How every input field becomes an SPDX 2.3 JSON field. Every value in the output comes from either the input file or a documented constant/rule below. Nothing is guessed.

Input format: [INPUT_FORMAT.md](INPUT_FORMAT.md) · Missing values: [MISSING_DATA_POLICY.md](MISSING_DATA_POLICY.md)

**Source column legend:** `input` = copied from the scan file · `constant` = fixed value from the SPDX spec · `generated` = calculated by a fixed rule (same input → same result)

---

## 1. Document Creation Information

| SPDX field | Required in SPDX | Source | Value / rule |
|---|---|---|---|
| `spdxVersion` | yes | constant | `SPDX-2.3` |
| `dataLicense` | yes | constant | `CC0-1.0` |
| `SPDXID` | yes | constant | `SPDXRef-DOCUMENT` |
| `name` | yes | input | `document_name`; if missing, input file name without extension |
| `documentNamespace` | yes | generated | `<namespace-base>/<name>-<first 12 chars of SHA256 of the input file>`. Default base `https://spdx.org/spdxdocs`, can be changed with `--namespace-base` |
| `creationInfo.created` | yes | input / generated | `--created` CLI option if given (keeps output deterministic); otherwise current UTC time. Format `YYYY-MM-DDThh:mm:ssZ` |
| `creationInfo.creators` | yes | constant + input | `Tool: spdx-export-<tool version>`, plus `Person: <name>` if `--creator` is given |

## 2. Package Information

| SPDX field | Required in SPDX | Source | Input field | Rule |
|---|---|---|---|---|
| `SPDXID` | yes | generated | `id`, `name`, `version` | `SPDXRef-Package-<name>-<version>-<6-char hash of id>`. Unsafe characters replaced by `-` |
| `name` | yes | input | `name` | copied as is |
| `versionInfo` | no | input | `version` | left out if missing |
| `supplier` | no | input | `supplier` | written as `Organization: <supplier>`; `NOASSERTION` if missing |
| `downloadLocation` | yes | input | `origin` | `NOASSERTION` if missing |
| `filesAnalyzed` | no | generated | — | `true` if the package has at least one file, else `false` |
| `packageVerificationCode` | if `filesAnalyzed` is true | generated | file `sha1`s | SPDX algorithm: sort the package's file SHA1s, join them, take the SHA1 of the result |
| `licenseDeclared` | no | input | `declared_license` | `NOASSERTION` if missing |
| `licenseConcluded` | no | input | `concluded_license` | `NOASSERTION` if missing |
| `copyrightText` | no | input | `copyright` | `NOASSERTION` if missing |

## 3. File Information

| SPDX field | Required in SPDX | Source | Input field | Rule |
|---|---|---|---|---|
| `SPDXID` | yes | generated | `package_id`, `path` | `SPDXRef-File-<path>-<6-char hash of package_id + path>` |
| `fileName` | yes | input | `path` | forward slashes, prefixed with `./` (e.g. `./src/foo.c`) |
| `checksums` | yes (SHA1) | input | `sha1` | `[{"algorithm": "SHA1", "checksumValue": <sha1 in lowercase>}]`. **Error if missing** |
| `licenseInfoInFiles` | no | input | `found_license` | list of license IDs; `NOASSERTION` if missing |
| `licenseConcluded` | no | input | `concluded_license` | `NOASSERTION` if missing |
| `copyrightText` | no | input | `copyright` | `NOASSERTION` if missing |

## 4. Relationships

| SPDX relationship | Source | Rule |
|---|---|---|
| `SPDXRef-DOCUMENT DESCRIBES <package>` | generated | for every package that is not the target of another package's `DEPENDS_ON` or `CONTAINS` (the top-level packages) |
| `<package> CONTAINS <file>` | generated | for every file, from its `package_id` |
| `<package> DEPENDS_ON <package>` | input | from `relationships` (JSON) or `depends_on` (CSV) |
| `<package> CONTAINS <package>` | input | from `relationships` with type `CONTAINS` |

Both ends of every relationship must exist in the document. Otherwise it is an orphaned reference and is reported as an error.

## 5. Output ordering (deterministic)

- packages sorted by SPDXID
- files sorted by SPDXID
- relationships sorted by (`spdxElementId`, `relationshipType`, `relatedSpdxElement`)
- JSON keys sorted, 2-space indent, UTF-8

## 6. Open questions for mentor

- **Custom licenses** not on the SPDX License List: plan is to use `LicenseRef-<name>`, but SPDX then needs the license text (`extractedText`), which the scan may not have. Waiting for the approved policy.
- **Validator choice**: `jsonschema` as the main check, `spdx-tools` as an extra check?
