"""Consulta y cambia la configuración de un router IOS-XE por NETCONF (SSH 830).

La respuesta de NETCONF es XML; se procesa con xml.etree.

Uso:
    python3 -m app.netconf_config get
    python3 -m app.netconf_config set --loopback 102 --ip 10.102.1.1

Variables de entorno: IOSXE_HOST, IOSXE_USERNAME, IOSXE_PASSWORD,
IOSXE_NETCONF_PORT (830 por defecto).
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET

NS = {"if": "urn:ietf:params:xml:ns:yang:ietf-interfaces",
      "ip": "urn:ietf:params:xml:ns:yang:ietf-ip"}

INTERFACES_FILTER = """
<filter>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces"/>
</filter>
"""

LOOPBACK_TEMPLATE = """
<config>
  <interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
    <interface>
      <name>Loopback{number}</name>
      <description>{description}</description>
      <type xmlns:ianaift="urn:ietf:params:xml:ns:yang:iana-if-type">ianaift:softwareLoopback</type>
      <enabled>true</enabled>
      <ipv4 xmlns="urn:ietf:params:xml:ns:yang:ietf-ip">
        <address>
          <ip>{ip}</ip>
          <netmask>{mask}</netmask>
        </address>
      </ipv4>
    </interface>
  </interfaces>
</config>
"""


class NetconfError(Exception):
    """Error al usar NETCONF."""


def load_config():
    values = {name: os.environ.get(name, "")
              for name in ("IOSXE_HOST", "IOSXE_USERNAME", "IOSXE_PASSWORD")}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise NetconfError("Faltan variables de entorno: " + ", ".join(missing))
    return {
        "host": values["IOSXE_HOST"],
        "port": int(os.environ.get("IOSXE_NETCONF_PORT", "830")),
        "username": values["IOSXE_USERNAME"],
        "password": values["IOSXE_PASSWORD"],
    }


def connect(config):
    from ncclient import manager  # import aquí para que las pruebas no lo exijan
    try:
        return manager.connect(
            host=config["host"], port=config["port"],
            username=config["username"], password=config["password"],
            hostkey_verify=False, allow_agent=False, look_for_keys=False,
            timeout=20,
        )
    except Exception as exc:
        raise NetconfError("No se pudo conectar por NETCONF ({}): revisar VPN, "
                           "puerto 830 y 'netconf-yang'.".format(exc.__class__.__name__))


def parse_interfaces(xml_text):
    """Extrae nombre, descripción, estado e IP de la respuesta XML."""
    root = ET.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
    result = []
    for itf in root.iter("{%s}interface" % NS["if"]):
        ip_node = itf.find("ip:ipv4/ip:address/ip:ip", NS)
        result.append({
            "name": itf.findtext("if:name", "-", NS),
            "description": itf.findtext("if:description", "-", NS),
            "enabled": itf.findtext("if:enabled", "-", NS),
            "ip": ip_node.text if ip_node is not None else "-",
        })
    return result


def build_loopback(number, ip, mask, description):
    return LOOPBACK_TEMPLATE.format(number=number, ip=ip, mask=mask,
                                    description=description)


def print_interfaces(interfaces):
    print("{:<22} {:<8} {:<18} {}".format("Interfaz", "Activa", "IPv4", "Descripción"))
    print("-" * 75)
    for itf in interfaces:
        print("{:<22} {:<8} {:<18} {}".format(
            itf["name"], itf["enabled"], itf["ip"], itf["description"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description="NETCONF sobre IOS-XE")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("get", help="listar interfaces")
    setp = sub.add_parser("set", help="crear o actualizar una loopback")
    setp.add_argument("--loopback", type=int, default=102)
    setp.add_argument("--ip", default="10.102.1.1")
    setp.add_argument("--mask", default="255.255.255.0")
    setp.add_argument("--description", default="Configurado por NETCONF")
    args = parser.parse_args(argv)

    try:
        config = load_config()
        with connect(config) as session:
            if args.action == "set":
                payload = build_loopback(args.loopback, args.ip, args.mask,
                                         args.description)
                reply = session.edit_config(target="running", config=payload)
                print("Loopback{} aplicada: {}".format(
                    args.loopback, "OK" if reply.ok else reply.errors))
            reply = session.get_config(source="running", filter=INTERFACES_FILTER)
            print_interfaces(parse_interfaces(reply.xml))
    except NetconfError as error:
        print("Error:", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
