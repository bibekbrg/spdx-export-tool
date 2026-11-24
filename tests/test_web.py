"""The local web preview: real HTTP requests against a server on a random port."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from spdx_export.validator import validate
from spdx_export.web import MAX_UPLOAD_BYTES, make_server


@pytest.fixture(scope="module")
def base_url():
    server = make_server(port=0)  # 0 = any free port
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, r.headers.get("Content-Type"), r.read()


def post(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_page_is_served(base_url):
    status, ctype, body = get(base_url + "/")
    assert status == 200
    assert "text/html" in ctype
    assert b"SPDX Export Tool" in body


def test_info_lists_samples(base_url):
    _, _, body = get(base_url + "/api/info")
    info = json.loads(body)
    assert info["version"]
    assert {s["name"] for s in info["samples"]} >= {"valid_scan.json", "broken_scan.json"}


def test_convert_valid_sample(base_url):
    status, r = post(base_url + "/api/convert", {"sample": "valid_scan.json"})
    assert status == 200
    assert r["ok"] is True
    assert r["counts"] == {"packages": 3, "files": 5, "relationships": 2}
    assert validate(r["document"]) == []
    assert r["spdx_text"].startswith("{")


def test_convert_missing_fields_sample(base_url):
    _, r = post(base_url + "/api/convert", {"sample": "missing_fields_scan.json"})
    assert r["ok"] is True
    assert r["gaps"]["WARNING"] == 17


def test_convert_broken_sample_gives_no_document(base_url):
    _, r = post(base_url + "/api/convert", {"sample": "broken_scan.json"})
    assert r["ok"] is False
    assert r["failed_stage"] == "input"
    assert r["document"] is None
    assert r["gaps"]["ERROR"] == 10


def test_upload_csv(base_url):
    content = ("package_id,package_name,file_path,sha1\n"
               "p1,libfoo,src/a.c,da39a3ee5e6b4b0d3255bfef95601890afd80709\n")
    _, r = post(base_url + "/api/convert", {"filename": "my scan.csv", "content": content})
    assert r["ok"] is True
    assert r["input"] == "my scan.csv"
    assert r["document"]["name"] == "my scan"


def test_upload_wrong_type_rejected(base_url):
    status, r = post(base_url + "/api/convert", {"filename": "scan.xml", "content": "<x/>"})
    assert status == 400
    assert "json and .csv" in r["error"]


def test_unknown_sample_rejected(base_url):
    status, _ = post(base_url + "/api/convert", {"sample": "../../secret.json"})
    assert status == 400


def test_upload_too_large(base_url):
    status, r = post(base_url + "/api/convert", {"filename": "big.json", "content": "x" * (MAX_UPLOAD_BYTES + 1)})
    assert status == 413


def test_speed_test(base_url):
    _, r = post(base_url + "/api/speed-test", {})
    assert r["files"] == 1000
    assert r["packages"] == 50
    assert r["passed"] is True


def test_unknown_route(base_url):
    with pytest.raises(urllib.error.HTTPError) as e:
        get(base_url + "/nope")
    assert e.value.code == 404
