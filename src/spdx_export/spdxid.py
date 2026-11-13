"""Deterministic SPDXID generator.

Same input always gives the same ID. A short hash is added so two items
with similar names never collide. SPDX only allows letters, digits, '.' and '-'.
"""

import hashlib
import re

from .model import File, Package

_UNSAFE = re.compile(r"[^A-Za-z0-9.]+")


def slug(text: str) -> str:
    """Replace every unsafe character run with '-'."""
    return _UNSAFE.sub("-", text).strip("-") or "x"


def short_hash(text: str, length: int = 6) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def package_spdxid(package: Package) -> str:
    parts = [slug(package.name)]
    if package.version:
        parts.append(slug(package.version))
    return f"SPDXRef-Package-{'-'.join(parts)}-{short_hash(package.id)}"


def file_spdxid(file: File) -> str:
    return f"SPDXRef-File-{slug(file.path)}-{short_hash(file.package_id + '/' + file.path)}"
