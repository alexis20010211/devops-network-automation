import pytest
import requests

from app import netconf_config, restconf_config

CONFIG = {"base_url": "https://router.test:443", "auth": ("u", "p"), "verify": True}


class FakeResponse:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


def test_restconf_load_config_requires_variables(monkeypatch):
    for name in ("IOSXE_HOST", "IOSXE_USERNAME", "IOSXE_PASSWORD"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(restconf_config.RestconfError):
        restconf_config.load_config()


def test_restconf_get_interfaces(monkeypatch):
    data = {"ietf-interfaces:interfaces": {"interface": [{"name": "Loopback0"}]}}
    monkeypatch.setattr(restconf_config.requests, "request",
                        lambda *a, **k: FakeResponse(200, data))

    assert restconf_config.get_interfaces(CONFIG) == [{"name": "Loopback0"}]


@pytest.mark.parametrize("status,text", [(401, "Credenciales"), (404, "inexistente"),
                                         (503, "interno")])
def test_restconf_http_errors_are_explained(monkeypatch, status, text):
    monkeypatch.setattr(restconf_config.requests, "request",
                        lambda *a, **k: FakeResponse(status))

    with pytest.raises(restconf_config.RestconfError) as error:
        restconf_config.get_interfaces(CONFIG)

    assert text in str(error.value)


def test_restconf_timeout_is_explained(monkeypatch):
    def fail(*a, **k):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(restconf_config.requests, "request", fail)

    with pytest.raises(restconf_config.RestconfError) as error:
        restconf_config.get_interfaces(CONFIG)

    assert "VPN" in str(error.value)


def test_restconf_loopback_payload():
    payload = restconf_config.build_loopback(101, "10.1.1.1", "255.255.255.0", "x")
    itf = payload["ietf-interfaces:interface"]

    assert itf["name"] == "Loopback101"
    assert itf["ietf-ip:ipv4"]["address"][0]["ip"] == "10.1.1.1"


def test_netconf_parse_interfaces_xml():
    xml = """<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"><data>
      <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
        <interface><name>Loopback102</name><description>NC</description>
          <enabled>true</enabled>
          <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
            <address><ip>10.102.1.1</ip><netmask>255.255.255.0</netmask></address>
          </ipv4></interface>
      </interfaces></data></rpc-reply>"""

    assert netconf_config.parse_interfaces(xml) == [
        {"name": "Loopback102", "description": "NC", "enabled": "true", "ip": "10.102.1.1"}]


def test_netconf_loopback_template_is_valid_xml():
    import xml.etree.ElementTree as ET

    root = ET.fromstring(netconf_config.build_loopback(5, "10.5.5.5", "255.255.255.0", "d"))

    assert root.tag == "config"
