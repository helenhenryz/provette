from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import settings_from_env


def test_health_is_green_and_names_the_simulator() -> None:
    client = TestClient(create_app(settings_from_env()))
    body = client.get("/health").json()
    assert body["ok"] is True
    assert body["opentrons"] == "8.8.2"
    assert body["footer"] == "Provette checks the logic of a protocol, not the physics."
