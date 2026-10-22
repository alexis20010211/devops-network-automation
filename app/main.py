
import json
from datetime import datetime, timezone
from pathlib import Path

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


def main():
    output = REPORTS_DIR / "inventory.json"
    report = generate_report(output_path=output)

    print("Reporte generado correctamente.")
    print("Total de dispositivos:", report["total_devices"])
    print("Archivo:", output)


if __name__ == "__main__":
    main()
