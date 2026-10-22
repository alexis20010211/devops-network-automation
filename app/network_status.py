"""Consulta el estado de los dispositivos en Cisco Catalyst Center (DNA Center).

La configuración se lee de variables de entorno:
    DNAC_URL, DNAC_USERNAME, DNAC_PASSWORD
    DNAC_VERIFY_SSL (opcional, "false" solo en laboratorio)
"""
import os
import sys

import requests

TIMEOUT = 15


class DnacError(Exception):
    """Error al consultar Catalyst Center."""


def load_config():
    """Lee la configuración desde variables de entorno."""
    base_url = os.environ.get("DNAC_URL", "").rstrip("/")
    username = os.environ.get("DNAC_USERNAME", "")
    password = os.environ.get("DNAC_PASSWORD", "")
    verify = os.environ.get("DNAC_VERIFY_SSL", "true").lower() != "false"

    missing = [
        name
        for name, value in (
            ("DNAC_URL", base_url),
            ("DNAC_USERNAME", username),
            ("DNAC_PASSWORD", password),
        )
        if not value
    ]
    if missing:
        raise DnacError("Faltan variables de entorno: " + ", ".join(missing))

    return {
        "base_url": base_url,
        "username": username,
        "password": password,
        "verify": verify,
    }


def get_token(config):
    """Solicita un token de autenticación."""
    url = config["base_url"] + "/dna/system/api/v1/auth/token"
    try:
        response = requests.post(
            url,
            auth=(config["username"], config["password"]),
            verify=config["verify"],
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["Token"]
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise DnacError("Autenticación rechazada (HTTP " + str(status) + ").")
    except requests.exceptions.RequestException as exc:
        raise DnacError("No se pudo conectar: " + exc.__class__.__name__)
    except (KeyError, ValueError):
        raise DnacError("Respuesta de autenticación inesperada.")


def get_devices(config, token):
    """Devuelve la lista de dispositivos de red."""
    url = config["base_url"] + "/dna/intent/api/v1/network-device"
    try:
        response = requests.get(
            url,
            headers={"X-Auth-Token": token},
            verify=config["verify"],
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("response", [])
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        raise DnacError("Consulta rechazada (HTTP " + str(status) + ").")
    except requests.exceptions.RequestException as exc:
        raise DnacError("No se pudo consultar: " + exc.__class__.__name__)
    except ValueError:
        raise DnacError("Respuesta de dispositivos inesperada.")


def print_devices(devices):
    """Muestra los dispositivos en una tabla sencilla."""
    print("{:<28} {:<16} {:<20} {}".format(
        "Hostname", "IP gestión", "Plataforma", "Alcanzable"))
    print("-" * 78)
    for device in devices:
        print("{:<28} {:<16} {:<20} {}".format(
            str(device.get("hostname") or "-"),
            str(device.get("managementIpAddress") or "-"),
            str(device.get("platformId") or "-"),
            str(device.get("reachabilityStatus") or "-"),
        ))


def main():
    try:
        config = load_config()
        if not config["verify"]:
            print("AVISO: verificación SSL desactivada (solo laboratorio).")
            requests.packages.urllib3.disable_warnings()
        print("Consultando:", config["base_url"])
        token = get_token(config)
        devices = get_devices(config, token)
    except DnacError as error:
        print("Error:", error)
        return 1

    print("Total de dispositivos:", len(devices))
    print_devices(devices)
    return 0


if __name__ == "__main__":
    sys.exit(main())
