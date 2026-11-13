"""Input adapters: read a JSON or CSV scan file into clean model objects.

Bad records are never fixed or guessed. They are set aside and reported
as ERROR diagnostics (see docs/MISSING_DATA_POLICY.md).
"""

import csv
import hashlib
import json
import re
from pathlib import Path

from .model import ERROR, Diagnostic, File, Package, Relationship, ScanData

ALLOWED_RELATIONSHIPS = {"DEPENDS_ON", "CONTAINS"}
SHA1_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def load_scan(path: str | Path) -> ScanData:
    """Read a scan file, choosing the reader from the file extension."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_json(path)
    if suffix == ".csv":
        return load_csv(path)
    raise ValueError(f"Unsupported input type '{suffix}': use .json or .csv")


def file_sha256(path: str | Path) -> str:
    """Fingerprint of the input file (used to make the document namespace unique).

    Line endings are normalised so Windows (CRLF) and Linux (LF) copies match.
    """
    data = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- JSON

def load_json(path: str | Path) -> ScanData:
    with open(path, encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            return ScanData(diagnostics=[Diagnostic(ERROR, "file", "-", f"invalid JSON: {e}")])

    if not isinstance(data, dict):
        return ScanData(diagnostics=[Diagnostic(ERROR, "file", "-", "top level must be a JSON object")])

    return build_scan(
        document_name=data.get("document_name"),
        raw_packages=_as_list(data.get("packages")),
        raw_files=_as_list(data.get("files")),
        raw_relationships=_as_list(data.get("relationships")),
    )


# ---------------------------------------------------------------- CSV

def load_csv(path: str | Path) -> ScanData:
    """CSV has one row per file; package details repeat on each row."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    raw_packages: dict[str, dict] = {}
    raw_files: list[dict] = []
    raw_relationships: list[dict] = []
    conflicts: list[Diagnostic] = []

    for i, row in enumerate(rows, start=2):  # row 1 is the header
        pid = _clean(row.get("package_id"))
        package = {
            "id": pid,
            "name": row.get("package_name"),
            "version": row.get("version"),
            "supplier": row.get("supplier"),
            "origin": row.get("origin"),
            "declared_license": row.get("declared_license"),
            "concluded_license": row.get("concluded_license"),
            "copyright": row.get("package_copyright"),
        }
        key = pid or f"__row{i}"
        if key in raw_packages and _cleaned(raw_packages[key]) != _cleaned(package):
            conflicts.append(Diagnostic(ERROR, f"row {i}", "package_id",
                                        f"package '{pid}' has different details on different rows"))
        raw_packages.setdefault(key, package)

        if _clean(row.get("file_path")) or _clean(row.get("sha1")):
            raw_files.append({
                "package_id": pid,
                "path": row.get("file_path"),
                "sha1": row.get("sha1"),
                "found_license": row.get("found_license"),
                "concluded_license": row.get("file_concluded_license"),
                "copyright": row.get("file_copyright"),
            })

        for target in (row.get("depends_on") or "").split(";"):
            if _clean(target):
                raw_relationships.append({"from": pid, "type": "DEPENDS_ON", "to": target})

    scan = build_scan(None, list(raw_packages.values()), raw_files, _unique(raw_relationships))
    scan.diagnostics[:0] = conflicts
    return scan


# ---------------------------------------------------------------- shared checks

def build_scan(document_name, raw_packages, raw_files, raw_relationships) -> ScanData:
    """Turn raw dictionaries into model objects, rejecting bad records."""
    scan = ScanData(document_name=_clean(document_name))
    diags = scan.diagnostics

    # Packages: id and name are required, ids must be unique.
    id_count: dict[str, int] = {}
    for p in raw_packages:
        if isinstance(p, dict) and _clean(p.get("id")):
            id_count[_clean(p["id"])] = id_count.get(_clean(p["id"]), 0) + 1

    for i, p in enumerate(raw_packages):
        loc = f"packages[{i}]"
        if not isinstance(p, dict):
            diags.append(Diagnostic(ERROR, loc, "-", "record must be an object"))
            continue
        pid, name = _clean(p.get("id")), _clean(p.get("name"))
        if not pid:
            diags.append(Diagnostic(ERROR, loc, "id", "missing: package rejected"))
            continue
        if not name:
            diags.append(Diagnostic(ERROR, loc, "name", f"missing for '{pid}': package rejected"))
            continue
        if id_count[pid] > 1:
            diags.append(Diagnostic(ERROR, loc, "id", f"duplicate id '{pid}': package rejected"))
            continue
        scan.packages.append(Package(
            id=pid, name=name,
            version=_clean(p.get("version")),
            supplier=_clean(p.get("supplier")),
            origin=_clean(p.get("origin")),
            declared_license=_clean(p.get("declared_license")),
            concluded_license=_clean(p.get("concluded_license")),
            copyright=_clean(p.get("copyright")),
        ))

    known_ids = {p.id for p in scan.packages}
    if not scan.packages:
        diags.append(Diagnostic(ERROR, "packages", "-", "no valid packages found"))

    # Files: package_id, path and a valid SHA1 are required.
    for i, f in enumerate(raw_files):
        loc = f"files[{i}]"
        if not isinstance(f, dict):
            diags.append(Diagnostic(ERROR, loc, "-", "record must be an object"))
            continue
        pid, path, sha1 = _clean(f.get("package_id")), _clean(f.get("path")), _clean(f.get("sha1"))
        if not pid:
            diags.append(Diagnostic(ERROR, loc, "package_id", "missing: file rejected"))
            continue
        if pid not in known_ids:
            diags.append(Diagnostic(ERROR, loc, "package_id", f"unknown package '{pid}': file rejected"))
            continue
        if not path:
            diags.append(Diagnostic(ERROR, loc, "path", "missing: file rejected"))
            continue
        if not sha1:
            diags.append(Diagnostic(ERROR, loc, "sha1",
                                    "missing: SPDX 2.3 requires a SHA1 for every file; never invented"))
            continue
        if not SHA1_PATTERN.match(sha1):
            diags.append(Diagnostic(ERROR, loc, "sha1", f"invalid value '{sha1}': must be 40 hex characters"))
            continue
        scan.files.append(File(
            package_id=pid, path=normalize_path(path), sha1=sha1.lower(),
            found_license=_clean(f.get("found_license")),
            concluded_license=_clean(f.get("concluded_license")),
            copyright=_clean(f.get("copyright")),
        ))

    # Relationships: both ends must exist, type must be allowed, no self-links.
    for i, r in enumerate(raw_relationships):
        loc = f"relationships[{i}]"
        if not isinstance(r, dict):
            diags.append(Diagnostic(ERROR, loc, "-", "record must be an object"))
            continue
        src, rtype, dst = _clean(r.get("from")), _clean(r.get("type")), _clean(r.get("to"))
        if rtype:
            rtype = rtype.upper()
        if not (src and rtype and dst):
            diags.append(Diagnostic(ERROR, loc, "-", "from, type and to are all required"))
            continue
        if rtype not in ALLOWED_RELATIONSHIPS:
            diags.append(Diagnostic(ERROR, loc, "type", f"'{rtype}' not allowed (use DEPENDS_ON or CONTAINS)"))
            continue
        missing = [x for x in (src, dst) if x not in known_ids]
        if missing:
            diags.append(Diagnostic(ERROR, loc, "-", f"orphaned reference to unknown package '{missing[0]}'"))
            continue
        if src == dst:
            diags.append(Diagnostic(ERROR, loc, "-", f"package '{src}' cannot relate to itself"))
            continue
        scan.relationships.append(Relationship(src, rtype, dst))

    return scan


def normalize_path(path: str) -> str:
    """Use forward slashes and strip a leading './' or '/'."""
    path = path.replace("\\", "/")
    while path.startswith("./") or path.startswith("/"):
        path = path[2:] if path.startswith("./") else path[1:]
    return path


def _clean(value) -> str | None:
    """Trim text; treat empty values as missing (None)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _cleaned(record: dict) -> dict:
    return {k: _clean(v) for k, v in record.items()}


def _as_list(value) -> list:
    return value if isinstance(value, list) else []


def _unique(records: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in records:
        key = tuple(sorted((k, _clean(v)) for k, v in r.items()))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out
