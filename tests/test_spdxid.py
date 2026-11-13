import re

from spdx_export.model import File, Package
from spdx_export.spdxid import file_spdxid, package_spdxid, slug

VALID_ID = re.compile(r"^SPDXRef-[A-Za-z0-9.-]+$")


def test_same_input_same_id():
    p = Package(id="pkg-1", name="libfoo", version="1.0")
    assert package_spdxid(p) == package_spdxid(Package(id="pkg-1", name="libfoo", version="1.0"))


def test_package_id_format():
    sid = package_spdxid(Package(id="pkg-1", name="libfoo", version="1.0"))
    assert sid.startswith("SPDXRef-Package-libfoo-1.0-")
    assert VALID_ID.match(sid)


def test_different_ids_never_collide():
    a = package_spdxid(Package(id="pkg-1", name="libfoo", version="1.0"))
    b = package_spdxid(Package(id="pkg-2", name="libfoo", version="1.0"))
    assert a != b


def test_special_characters_are_sanitized():
    sid = package_spdxid(Package(id="x", name="@scope/my pkg!", version="1.0+build_7"))
    assert VALID_ID.match(sid)
    assert slug("@scope/my pkg!") == "scope-my-pkg"


def test_file_id_format():
    sid = file_spdxid(File(package_id="pkg-1", path="src/foo.c", sha1="0" * 40))
    assert sid.startswith("SPDXRef-File-src-foo.c-")
    assert VALID_ID.match(sid)


def test_empty_name_still_valid():
    assert slug("!!!") == "x"
