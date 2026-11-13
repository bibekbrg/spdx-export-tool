"""Run the steps in order: read -> check -> map. Used by tests now and by the CLI in Week 3."""

from pathlib import Path

from .adapters import file_sha256, load_scan
from .mapper import DEFAULT_NAMESPACE_BASE, build_document
from .model import Diagnostic


def convert(
    input_path: str | Path,
    *,
    created: str | None = None,
    creator_person: str | None = None,
    namespace_base: str = DEFAULT_NAMESPACE_BASE,
) -> tuple[dict | None, list[Diagnostic]]:
    """Return (spdx_document, diagnostics). The document is None if the input has errors."""
    input_path = Path(input_path)
    scan = load_scan(input_path)
    if scan.has_errors:
        return None, scan.diagnostics

    document, map_diags = build_document(
        scan,
        fallback_name=input_path.stem,
        input_digest=file_sha256(input_path),
        created=created,
        creator_person=creator_person,
        namespace_base=namespace_base,
    )
    diagnostics = scan.diagnostics + map_diags
    if any(d.severity == "ERROR" for d in map_diags):
        return None, diagnostics
    return document, diagnostics
