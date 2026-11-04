"""Genera el inventario de red en JSON, CSV, YAML y XML.

Uso (desde la raíz del proyecto):
    python3 -m app.main                 # datos de ejemplo
    python3 -m app.main --source api    # Catalyst Center (requiere .env)
    python3 -m app.main --source data/devices.yaml
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app import formats

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"


def get_devices():
    """Devuelve dispositivos de ejemplo para la demostración."""
    return [
        {
            "hostname": "R1",
            "type": "router",
            "management_ip": "192.168.1.1",
            "status": "simulado",
        },
        {
            "hostname": "SW1",
            "type": "switch",
            "management_ip": "192.168.1.2",
            "status": "simulado",
        },
    ]


def get_devices_from_api():
    """Consulta Catalyst Center y convierte la respuesta al inventario."""
    from app import network_status

    config = network_status.load_config()
    if not config["verify"]:
        network_status.disable_ssl_warnings()
    token = network_status.get_token(config)
    raw_devices = network_status.get_devices(config, token)
    return [formats.from_catalyst_center(device) for device in raw_devices]


def generate_report(devices=None, output_path=None):
    """Genera un reporte JSON del inventario de red."""
    if devices is None:
        devices = get_devices()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_devices": len(devices),
        "devices": devices,
    }

    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / "inventory.json"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    return report


def load_source(source):
    """Obtiene los dispositivos según el origen elegido."""
    if source == "demo":
        return [formats.normalize_device(d) for d in get_devices()]
    if source == "api":
        return get_devices_from_api()
    return formats.read_devices(source)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Inventario de red")
    parser.add_argument(
        "--source", default="demo",
        help="demo, api o la ruta de un archivo .json/.csv/.yaml/.xml")
    parser.add_argument(
        "--output-dir", default=str(REPORTS_DIR),
        help="carpeta donde se guardan los reportes")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        devices = load_source(args.source)
    except Exception as error:  # se informa y se sale con código 1
        print("Error al obtener el inventario:", error)
        return 1

    summary = formats.summarize(devices)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "total_devices": summary["total"],
    }
    paths = formats.export_all(devices, args.output_dir, metadata=metadata)

    print("Reporte generado correctamente.")
    print("Origen:", args.source)
    print("Total de dispositivos:", summary["total"])
    print("Por tipo:", summary["by_type"])
    print("Por estado:", summary["by_status"])
    for fmt, path in paths.items():
        print("  {:<5} {}".format(fmt.upper(), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
