"""Check a generated document against the official SPDX 2.3 JSON schema.

The schema file is bundled from github.com/spdx/spdx-spec (branch support/2.3).
"""

import json
from functools import lru_cache
from importlib import resources

from jsonschema.validators import validator_for

from .model import ERROR, Diagnostic

SCHEMA_FILE = "spdx-schema-2.3.json"


@lru_cache(maxsize=1)
def _validator():
    text = resources.files("spdx_export").joinpath("schemas", SCHEMA_FILE).read_text(encoding="utf-8")
    schema = json.loads(text)
    cls = validator_for(schema)
    return cls(schema)


def validate(document: dict) -> list[Diagnostic]:
    """Return one ERROR diagnostic per schema violation (empty list = valid)."""
    errors = sorted(_validator().iter_errors(document), key=lambda e: list(e.absolute_path))
    return [
        Diagnostic(ERROR, _where(e.absolute_path), "schema", e.message)
        for e in errors
    ]


def _where(path) -> str:
    parts = [f"[{p}]" if isinstance(p, int) else (("." if i else "") + str(p))
             for i, p in enumerate(path)]
    return "".join(parts) or "document"
