import pytest

from app import webex_notify

DEVICES = [
    {"hostname": "sw1", "type": "switch", "management_ip": "1.1.1.1", "status": "Reachable"},
    {"hostname": "sw2", "type": "switch", "management_ip": "1.1.1.2", "status": "Unreachable"},
]


class FakeResponse:
    def __init__(self, status):
        self.status_code = status

    def json(self):
        return {"id": "msg-1"}


def test_message_includes_total_and_alert():
    message = webex_notify.build_message(DEVICES)

    assert "2 dispositivos" in message
    assert "sw2" in message.split("Alerta")[1]


def test_send_message_ok(monkeypatch):
    monkeypatch.setattr(webex_notify.requests, "post", lambda *a, **k: FakeResponse(200))

    assert webex_notify.send_message({"token": "t", "room_id": "r"}, "hola") == "msg-1"


def test_send_message_invalid_token(monkeypatch):
    monkeypatch.setattr(webex_notify.requests, "post", lambda *a, **k: FakeResponse(401))

    with pytest.raises(webex_notify.WebexError) as error:
        webex_notify.send_message({"token": "t", "room_id": "r"}, "hola")

    assert "401" in str(error.value)


def test_load_config_requires_token(monkeypatch):
    monkeypatch.delenv("WEBEX_TOKEN", raising=False)
    monkeypatch.setenv("WEBEX_ROOM_ID", "r")

    with pytest.raises(webex_notify.WebexError):
        webex_notify.load_config()
