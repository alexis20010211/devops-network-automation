import pytest
import requests

from app import network_status
from app.network_status import DnacError, load_config


def test_load_config_without_variables_raises_error(monkeypatch):
    for name in ("DNAC_URL", "DNAC_USERNAME", "DNAC_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(DnacError) as error:
        load_config()

    assert "DNAC_URL" in str(error.value)


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("DNAC_URL", "https://example.test/")
    monkeypatch.setenv("DNAC_USERNAME", "user")
    monkeypatch.setenv("DNAC_PASSWORD", "secret")
    monkeypatch.delenv("DNAC_VERIFY_SSL", raising=False)

    config = load_config()

    assert config["base_url"] == "https://example.test"
    assert config["verify"] is True


def test_ssl_verification_can_be_disabled(monkeypatch):
    monkeypatch.setenv("DNAC_URL", "https://example.test")
    monkeypatch.setenv("DNAC_USERNAME", "user")
    monkeypatch.setenv("DNAC_PASSWORD", "secret")
    monkeypatch.setenv("DNAC_VERIFY_SSL", "false")

    assert load_config()["verify"] is False


def test_get_devices_returns_simulated_response(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": [{"hostname": "sw-simulado"}]}

    monkeypatch.setattr(network_status.requests, "get",
                        lambda *args, **kwargs: FakeResponse())
    config = {"base_url": "https://example.test", "verify": True}

    devices = network_status.get_devices(config, "token-falso")

    assert devices == [{"hostname": "sw-simulado"}]


def test_get_token_connection_error_is_reported(monkeypatch):
    def fail(*args, **kwargs):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(network_status.requests, "post", fail)
    config = {"base_url": "https://example.test", "username": "u",
              "password": "p", "verify": True}

    with pytest.raises(DnacError):
        network_status.get_token(config)
