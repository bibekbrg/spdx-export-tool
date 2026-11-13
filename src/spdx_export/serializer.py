"""Write the SPDX document as pretty, stable UTF-8 JSON."""

import json
from pathlib import Path


def to_json(document: dict) -> str:
    """Sorted keys + fixed indent = same input always gives byte-identical output."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(document: dict, path: str | Path) -> None:
    Path(path).write_text(to_json(document), encoding="utf-8", newline="\n")
