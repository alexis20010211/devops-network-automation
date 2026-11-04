"""Consulta y cambia la configuración de un router IOS-XE por RESTCONF (HTTPS).

Uso:
    python3 -m app.restconf_config get
    python3 -m app.restconf_config set --loopback 101 --ip 10.101.1.1 \
        --description "Configurado por RESTCONF"

Variables de entorno: IOSXE_HOST, IOSXE_USERNAME, IOSXE_PASSWORD,
IOSXE_PORT (443 por defecto), IOSXE_VERIFY_SSL.
"""
import argparse
import json
import os
import sys

import requests

TIMEOUT = 15
HEADERS = {
    "Accept": "application/yang-data+json",
    "Content-Type": "application/yang-data+json",
}
INTERFACES_PATH = "/restconf/data/ietf-interfaces:interfaces"

# Explicación de errores frecuentes, usada para el troubleshooting.
HTTP_HINTS = {
    400: "Petición mal formada: revisar el JSON y el modelo YANG.",
    401: "Credenciales incorrectas: revisar IOSXE_USERNAME/IOSXE_PASSWORD.",
    403: "Usuario sin privilegios suficientes (se necesita privilege 15).",
    404: "Recurso inexistente: revisar la ruta YANG o el nombre de interfaz.",
    405: "Método no permitido en ese recurso.",
    409: "Conflicto: el recurso ya existe o está bloqueado.",
    415: "Content-Type incorrecto: usar application/yang-data+json.",
}


class RestconfError(Exception):
    """Error al usar RESTCONF."""


def load_config():
    host = os.environ.get("IOSXE_HOST", "")
    username = os.environ.get("IOSXE_USERNAME", "")
    password = os.environ.get("IOSXE_PASSWORD", "")
    missing = [n for n, v in (("IOSXE_HOST", host),
                              ("IOSXE_USERNAME", username),
                              ("IOSXE_PASSWORD", password)) if not v]
    if missing:
        raise RestconfError("Faltan variables de entorno: " + ", ".join(missing))
    port = os.environ.get("IOSXE_PORT", "443")
    return {
        "base_url": "https://{}:{}".format(host, port),
        "auth": (username, password),
        "verify": os.environ.get("IOSXE_VERIFY_SSL", "true").lower() != "false",
    }


def explain_http_error(status):
    hint = HTTP_HINTS.get(status)
    if hint is None and status >= 500:
        hint = "Error interno del dispositivo: reintentar o revisar logs."
    return "HTTP {}: {}".format(status, hint or "respuesta inesperada.")


def request(config, method, path, payload=None):
    """Hace la petición y traduce los errores a mensajes claros."""
    try:
        response = requests.request(
            method,
            config["base_url"] + path,
            auth=config["auth"],
            headers=HEADERS,
            data=json.dumps(payload) if payload is not None else None,
            verify=config["verify"],
            timeout=TIMEOUT,
        )
    except requests.exceptions.SSLError:
        raise RestconfError("Certificado no válido (usar IOSXE_VERIFY_SSL=false "
                            "solo en laboratorio).")
    except requests.exceptions.Timeout:
        raise RestconfError("Tiempo de espera agotado: revisar VPN e IP.")
    except requests.exceptions.ConnectionError:
        raise RestconfError("No hay conexión: revisar VPN, IP, puerto y "
                            "que 'restconf' esté habilitado.")
    if response.status_code >= 400:
        raise RestconfError(explain_http_error(response.status_code))
    return response


def get_interfaces(config):
    response = request(config, "GET", INTERFACES_PATH)
    return response.json()["ietf-interfaces:interfaces"]["interface"]


def build_loopback(number, ip, mask, description):
    return {
        "ietf-interfaces:interface": {
            "name": "Loopback{}".format(number),
            "description": description,
            "type": "iana-if-type:softwareLoopback",
            "enabled": True,
            "ietf-ip:ipv4": {"address": [{"ip": ip, "netmask": mask}]},
        }
    }


def set_loopback(config, number, ip, mask, description):
    payload = build_loopback(number, ip, mask, description)
    path = INTERFACES_PATH + "/interface=Loopback{}".format(number)
    return request(config, "PUT", path, payload).status_code


def print_interfaces(interfaces):
    print("{:<22} {:<8} {:<18} {}".format("Interfaz", "Activa", "IPv4", "Descripción"))
    print("-" * 75)
    for itf in interfaces:
        addresses = itf.get("ietf-ip:ipv4", {}).get("address", [])
        ip = addresses[0]["ip"] if addresses else "-"
        print("{:<22} {:<8} {:<18} {}".format(
            itf.get("name", "-"), str(itf.get("enabled", "-")), ip,
            itf.get("description", "-")))


def main(argv=None):
    parser = argparse.ArgumentParser(description="RESTCONF sobre IOS-XE")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("get", help="listar interfaces")
    setp = sub.add_parser("set", help="crear o actualizar una loopback")
    setp.add_argument("--loopback", type=int, default=101)
    setp.add_argument("--ip", default="10.101.1.1")
    setp.add_argument("--mask", default="255.255.255.0")
    setp.add_argument("--description", default="Configurado por RESTCONF")
    args = parser.parse_args(argv)

    try:
        config = load_config()
        if not config["verify"]:
            print("AVISO: verificación SSL desactivada (solo laboratorio).")
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        if args.action == "set":
            status = set_loopback(config, args.loopback, args.ip,
                                  args.mask, args.description)
            print("Loopback{} aplicada (HTTP {}).".format(args.loopback, status))
        print_interfaces(get_interfaces(config))
    except RestconfError as error:
        print("Error:", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
