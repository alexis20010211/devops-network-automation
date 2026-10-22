import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"


def main():
    devices = [
        {
            "hostname": "R1",
            "type": "router",
            "management_ip": "192.168.1.1",
            "status": "simulado"
        },
        {
            "hostname": "SW1",
            "type": "switch",
            "management_ip": "192.168.1.2",
            "status": "simulado"
        }
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_devices": len(devices),
        "devices": devices
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output = REPORTS_DIR / "inventory.json"

    with output.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    print("Reporte generado correctamente.")
    print("Total de dispositivos:", len(devices))
    print("Archivo:", output)


if __name__ == "__main__":
    main()
