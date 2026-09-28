"""The built pages are served from web_dir and nowhere else, and a missing API route is a 404."""

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from tests.api.conftest import make_settings


def _client_with_pages(tmp_path: Path) -> TestClient:
    web = tmp_path / "web"
    (web / "assets").mkdir(parents=True)
    (web / "index.html").write_text("<!doctype html><title>Provette</title>", encoding="utf-8")
    (web / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    settings = replace(make_settings(tmp_path, sets=()), web_dir=web)
    return TestClient(create_app(settings))


def test_a_deep_link_gets_the_page_and_a_real_file_gets_the_file(tmp_path: Path) -> None:
    client = _client_with_pages(tmp_path)
    assert "<title>Provette</title>" in client.get("/runs/abc").text
    assert client.get("/favicon.svg").text == "<svg/>"


def test_a_path_outside_the_pages_is_never_served(tmp_path: Path) -> None:
    client = _client_with_pages(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("the key", encoding="utf-8")
    for path in ("//etc/hostname", "/../secret.txt", "../secret.txt", f"/{secret}"):
        body = client.get(path).text
        assert "the key" not in body and "<title>Provette</title>" in body, path


def test_a_missing_api_route_is_a_404_not_the_page(tmp_path: Path) -> None:
    client = _client_with_pages(tmp_path)
    answer = client.get("/api/no-such-route")
    assert answer.status_code == 404
    assert answer.json()["detail"] == "there is no such API route"


def test_the_route_documentation_is_off_unless_asked_for(tmp_path: Path) -> None:
    # As deployed the page is off: it would list every route to anyone. The dev server asks.
    assert _client_with_pages(tmp_path).get("/api/docs").status_code == 404
    settings = replace(make_settings(tmp_path, sets=()), api_docs=True)
    assert TestClient(create_app(settings)).get("/api/docs").status_code == 200
