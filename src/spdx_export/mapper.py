"""Map clean scan data to an SPDX 2.3 document (a Python dict).

Rules come from docs/FIELD_MAPPING.md and docs/MISSING_DATA_POLICY.md.
Every missing value becomes NOASSERTION or is left out, and is logged.
"""

import hashlib
from datetime import datetime, timezone

from . import TOOL_NAME, __version__
from .model import ERROR, INFO, WARNING, Diagnostic, ScanData
from .spdxid import file_spdxid, package_spdxid, slug

NOASSERTION = "NOASSERTION"
DEFAULT_NAMESPACE_BASE = "https://spdx.org/spdxdocs"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def verification_code(sha1s: list[str]) -> str:
    """SPDX package verification code: SHA1 of all file SHA1s, sorted and joined."""
    return hashlib.sha1("".join(sorted(sha1s)).encode("ascii")).hexdigest()


def build_document(
    scan: ScanData,
    *,
    fallback_name: str,
    input_digest: str,
    created: str | None = None,
    creator_person: str | None = None,
    namespace_base: str = DEFAULT_NAMESPACE_BASE,
) -> tuple[dict, list[Diagnostic]]:
    """Return (spdx_document, diagnostics)."""
    diags: list[Diagnostic] = []

    name = scan.document_name
    if not name:
        name = fallback_name
        diags.append(Diagnostic(WARNING, "document", "document_name", f"missing: using input file name '{name}'"))

    creators = [f"Tool: {TOOL_NAME}-{__version__}"]
    if creator_person:
        creators.append(f"Person: {creator_person}")

    # ---- packages
    pkg_ids = {p.id: package_spdxid(p) for p in scan.packages}
    if len(set(pkg_ids.values())) != len(pkg_ids):
        diags.append(Diagnostic(ERROR, "packages", "SPDXID", "two packages produced the same SPDXID"))

    files_by_pkg: dict[str, list] = {}
    for f in scan.files:
        files_by_pkg.setdefault(f.package_id, []).append(f)

    packages = []
    for i, p in enumerate(scan.packages):
        loc = f"packages[{i}]"
        pkg_files = files_by_pkg.get(p.id, [])
        entry = {
            "SPDXID": pkg_ids[p.id],
            "name": p.name,
            "supplier": _supplier(p.supplier, loc, diags),
            "downloadLocation": _or_noassertion(p.origin, loc, "origin", diags),
            "filesAnalyzed": bool(pkg_files),
            "licenseDeclared": _or_noassertion(p.declared_license, loc, "declared_license", diags),
            "licenseConcluded": _or_noassertion(p.concluded_license, loc, "concluded_license", diags),
            "copyrightText": _or_noassertion(p.copyright, loc, "copyright", diags),
        }
        if p.version:
            entry["versionInfo"] = p.version
        else:
            diags.append(Diagnostic(INFO, loc, "version", "missing: versionInfo omitted"))
        if pkg_files:
            entry["packageVerificationCode"] = {
                "packageVerificationCodeValue": verification_code([f.sha1 for f in pkg_files])
            }
        packages.append(entry)

    # ---- files
    files = []
    file_owner = {}
    for i, f in enumerate(scan.files):
        loc = f"files[{i}]"
        sid = file_spdxid(f)
        file_owner[sid] = pkg_ids[f.package_id]
        files.append({
            "SPDXID": sid,
            "fileName": "./" + f.path,
            "checksums": [{"algorithm": "SHA1", "checksumValue": f.sha1}],
            "licenseInfoInFiles": [_or_noassertion(f.found_license, loc, "found_license", diags)],
            "licenseConcluded": _or_noassertion(f.concluded_license, loc, "concluded_license", diags),
            "copyrightText": _or_noassertion(f.copyright, loc, "copyright", diags),
        })

    # ---- relationships
    relationships = []
    targets = set()
    for r in scan.relationships:
        relationships.append(_rel(pkg_ids[r.from_id], r.type, pkg_ids[r.to_id]))
        targets.add(r.to_id)
    for sid, owner in file_owner.items():
        relationships.append(_rel(owner, "CONTAINS", sid))
    top_level = [p for p in scan.packages if p.id not in targets]
    if not top_level:  # everything depends on something (a loop): describe all packages
        top_level = scan.packages
    for p in top_level:
        relationships.append(_rel("SPDXRef-DOCUMENT", "DESCRIBES", pkg_ids[p.id]))

    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": name,
        "documentNamespace": f"{namespace_base.rstrip('/')}/{slug(name)}-{input_digest[:12]}",
        "creationInfo": {"created": created or utc_now(), "creators": creators},
        "packages": sorted(packages, key=lambda x: x["SPDXID"]),
        "files": sorted(files, key=lambda x: x["SPDXID"]),
        "relationships": sorted(relationships, key=lambda x: (
            x["spdxElementId"], x["relationshipType"], x["relatedSpdxElement"])),
    }
    return document, diags


def _rel(a: str, rtype: str, b: str) -> dict:
    return {"spdxElementId": a, "relationshipType": rtype, "relatedSpdxElement": b}


def _or_noassertion(value, loc, field, diags) -> str:
    if value:
        return value
    diags.append(Diagnostic(WARNING, loc, field, "missing: written as NOASSERTION"))
    return NOASSERTION


def _supplier(value, loc, diags) -> str:
    if not value:
        diags.append(Diagnostic(WARNING, loc, "supplier", "missing: written as NOASSERTION"))
        return NOASSERTION
    if value == NOASSERTION:
        return value
    if value.startswith(("Organization:", "Person:")):
        return value
    return f"Organization: {value}"
