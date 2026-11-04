"""Lectura y escritura del inventario de red en JSON, CSV, YAML y XML.

Todas las funciones trabajan con una lista de diccionarios con los campos
definidos en FIELDS, de modo que cualquier formato se puede convertir en otro.
"""
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

FIELDS = ["hostname", "type", "management_ip", "status"]
SUPPORTED_FORMATS = ("json", "csv", "yaml", "xml")


def normalize_device(device):
    """Deja un dispositivo solo con los campos de FIELDS, como texto."""
    return {field: str(device.get(field) or "-") for field in FIELDS}


def from_catalyst_center(raw_device):
    """Convierte un dispositivo de Catalyst Center al formato del inventario."""
    return normalize_device({
        "hostname": raw_device.get("hostname"),
        "type": raw_device.get("platformId") or raw_device.get("family"),
        "management_ip": raw_device.get("managementIpAddress"),
        "status": raw_device.get("reachabilityStatus"),
    })


def summarize(devices):
    """Cuenta dispositivos por tipo y por estado."""
    by_type = {}
    by_status = {}
    for device in devices:
        by_type[device["type"]] = by_type.get(device["type"], 0) + 1
        by_status[device["status"]] = by_status.get(device["status"], 0) + 1
    return {"total": len(devices), "by_type": by_type, "by_status": by_status}


# --- Escritura ---------------------------------------------------------------

def write_json(devices, path, metadata=None):
    data = dict(metadata or {})
    data["devices"] = devices
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def write_csv(devices, path, metadata=None):
    with Path(path).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(devices)


def write_yaml(devices, path, metadata=None):
    data = dict(metadata or {})
    data["devices"] = devices
    with Path(path).open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)


def write_xml(devices, path, metadata=None):
    root = ET.Element("inventory")
    for key, value in (metadata or {}).items():
        root.set(key, str(value))
    for device in devices:
        node = ET.SubElement(root, "device")
        for field in FIELDS:
            ET.SubElement(node, field).text = device[field]
    tree = ET.ElementTree(root)
    if hasattr(ET, "indent"):  # Python 3.9+
        ET.indent(tree)
    tree.write(str(path), encoding="utf-8", xml_declaration=True)


WRITERS = {"json": write_json, "csv": write_csv,
           "yaml": write_yaml, "xml": write_xml}


def export_all(devices, output_dir, basename="inventory", metadata=None):
    """Escribe el inventario en todos los formatos y devuelve las rutas."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for fmt, writer in WRITERS.items():
        path = output_dir / (basename + "." + fmt)
        writer(devices, path, metadata)
        paths[fmt] = path
    return paths


# --- Lectura -----------------------------------------------------------------

def read_devices(path):
    """Lee un inventario según la extensión del archivo."""
    path = Path(path)
    ext = path.suffix.lower().lstrip(".")
    if ext == "yml":
        ext = "yaml"
    if ext not in SUPPORTED_FORMATS:
        raise ValueError("Formato no soportado: " + path.suffix)

    if ext == "json":
        with path.open(encoding="utf-8") as file:
            devices = json.load(file).get("devices", [])
    elif ext == "yaml":
        with path.open(encoding="utf-8") as file:
            devices = (yaml.safe_load(file) or {}).get("devices", [])
    elif ext == "csv":
        with path.open(encoding="utf-8", newline="") as file:
            devices = list(csv.DictReader(file))
    else:
        root = ET.parse(str(path)).getroot()
        devices = [{child.tag: child.text for child in node}
                   for node in root.findall("device")]

    return [normalize_device(device) for device in devices]
