"""Internal data model: the clean objects every other module works with."""

from dataclasses import dataclass, field

ERROR = "ERROR"
WARNING = "WARNING"
INFO = "INFO"


@dataclass
class Package:
    """One component or library found by the scanner."""

    id: str
    name: str
    version: str | None = None
    supplier: str | None = None
    origin: str | None = None
    declared_license: str | None = None
    concluded_license: str | None = None
    copyright: str | None = None


@dataclass
class File:
    """One scanned file, belonging to a package."""

    package_id: str
    path: str
    sha1: str
    found_license: str | None = None
    concluded_license: str | None = None
    copyright: str | None = None


@dataclass
class Relationship:
    """A link between two packages, e.g. app DEPENDS_ON libfoo."""

    from_id: str
    type: str
    to_id: str


@dataclass
class Diagnostic:
    """One line of the gap report."""

    severity: str  # ERROR, WARNING or INFO
    location: str  # where in the input, e.g. "files[3]"
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.severity:<8} {self.location:<16} {self.field:<18} {self.message}"


@dataclass
class ScanData:
    """Everything read from one scan file, plus any problems found."""

    document_name: str | None = None
    packages: list[Package] = field(default_factory=list)
    files: list[File] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(d.severity == ERROR for d in self.diagnostics)
