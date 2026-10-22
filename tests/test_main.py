import json

from app.main import generate_report, get_devices


def test_get_devices_returns_router_and_switch():
    devices = get_devices()

    assert len(devices) == 2
    assert devices[0]["type"] == "router"
    assert devices[1]["type"] == "switch"


def test_generate_report_creates_valid_json(tmp_path):
    output = tmp_path / "inventory.json"

    report = generate_report(output_path=output)

    assert output.exists()
    assert report["total_devices"] == 2

    with output.open(encoding="utf-8") as file:
        saved_report = json.load(file)

    assert saved_report["total_devices"] == 2
    assert len(saved_report["devices"]) == 2


def test_generate_report_with_empty_inventory(tmp_path):
    output = tmp_path / "empty_inventory.json"

    report = generate_report(devices=[], output_path=output)

    assert report["total_devices"] == 0
    assert report["devices"] == []
