import pytest

from app import formats
from app.main import main

DEVICES = [
    formats.normalize_device({"hostname": "R1", "type": "router",
                              "management_ip": "10.0.0.1", "status": "reachable"}),
    formats.normalize_device({"hostname": "SW1", "type": "switch",
                              "management_ip": "10.0.0.2", "status": "unreachable"}),
]


@pytest.mark.parametrize("fmt", formats.SUPPORTED_FORMATS)
def test_each_format_round_trip(tmp_path, fmt):
    paths = formats.export_all(DEVICES, tmp_path, metadata={"source": "test"})

    assert formats.read_devices(paths[fmt]) == DEVICES


def test_from_catalyst_center_maps_fields():
    raw = {"hostname": "sw1", "platformId": "C9KV-UADP-8P",
           "managementIpAddress": "10.10.20.175", "reachabilityStatus": "Reachable"}

    assert formats.from_catalyst_center(raw) == {
        "hostname": "sw1", "type": "C9KV-UADP-8P",
        "management_ip": "10.10.20.175", "status": "Reachable"}


def test_missing_fields_become_dash():
    assert formats.normalize_device({"hostname": "X"})["management_ip"] == "-"


def test_summarize_counts_by_type_and_status():
    summary = formats.summarize(DEVICES)

    assert summary["total"] == 2
    assert summary["by_status"] == {"reachable": 1, "unreachable": 1}


def test_unsupported_extension_raises(tmp_path):
    with pytest.raises(ValueError):
        formats.read_devices(tmp_path / "inventario.txt")


def test_main_reads_yaml_and_writes_four_formats(tmp_path):
    source = tmp_path / "in.yaml"
    formats.write_yaml(DEVICES, source)

    code = main(["--source", str(source), "--output-dir", str(tmp_path / "out")])

    assert code == 0
    for fmt in formats.SUPPORTED_FORMATS:
        assert (tmp_path / "out" / ("inventory." + fmt)).exists()
