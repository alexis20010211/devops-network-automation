"""Envía a una sala de Webex el resumen del último inventario generado.

Uso:
    python3 -m app.webex_notify                       # usa reports/inventory.json
    python3 -m app.webex_notify --report reports/inventory.yaml

Variables de entorno: WEBEX_TOKEN, WEBEX_ROOM_ID.
"""
import argparse
import os
import sys
from pathlib import Path

import requests

from app import formats

API_URL = "https://webexapis.com/v1/messages"
TIMEOUT = 15
DEFAULT_REPORT = Path(__file__).resolve().parent.parent / "reports" / "inventory.json"


class WebexError(Exception):
    """Error al enviar el mensaje."""


def load_config():
    token = os.environ.get("WEBEX_TOKEN", "")
    room_id = os.environ.get("WEBEX_ROOM_ID", "")
    missing = [n for n, v in (("WEBEX_TOKEN", token), ("WEBEX_ROOM_ID", room_id)) if not v]
    if missing:
        raise WebexError("Faltan variables de entorno: " + ", ".join(missing))
    return {"token": token, "room_id": room_id}


def build_message(devices):
    """Arma el mensaje en Markdown; marca los dispositivos no alcanzables."""
    summary = formats.summarize(devices)
    down = [d for d in devices if d["status"].lower() not in ("reachable", "simulado")]
    lines = [
        "**Inventario de red** - {} dispositivos".format(summary["total"]),
        "",
        "- Por tipo: " + ", ".join("{}: {}".format(k, v) for k, v in summary["by_type"].items()),
        "- Por estado: " + ", ".join("{}: {}".format(k, v) for k, v in summary["by_status"].items()),
    ]
    if down:
        lines.append("")
        lines.append("**Alerta:** no alcanzables: " + ", ".join(d["hostname"] for d in down))
    return "\n".join(lines)


def send_message(config, markdown):
    try:
        response = requests.post(
            API_URL,
            headers={"Authorization": "Bearer " + config["token"]},
            json={"roomId": config["room_id"], "markdown": markdown},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise WebexError("No se pudo conectar con Webex: " + exc.__class__.__name__)
    if response.status_code == 401:
        raise WebexError("HTTP 401: token inválido o vencido.")
    if response.status_code == 404:
        raise WebexError("HTTP 404: la sala no existe o el bot no es miembro.")
    if response.status_code == 429:
        raise WebexError("HTTP 429: demasiadas peticiones, esperar Retry-After.")
    if response.status_code >= 400:
        raise WebexError("HTTP {}: mensaje rechazado.".format(response.status_code))
    return response.json().get("id")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Notificación a Webex")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)
    try:
        config = load_config()
        devices = formats.read_devices(args.report)
        message = build_message(devices)
        send_message(config, message)
    except (WebexError, OSError, ValueError) as error:
        print("Error:", error)
        return 1
    print("Mensaje enviado a Webex:")
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
