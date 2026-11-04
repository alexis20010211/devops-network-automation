# devops-network-automation

Automatización de inventario y configuración de una red Cisco: consulta por API REST (HTTPS) a Catalyst Center, cambios con RESTCONF, NETCONF y Ansible sobre IOS-XE, notificaciones a Webex, reportes en JSON/CSV/YAML/XML, contenedor Docker y pipeline Jenkins.

Probado en la **DEVASC VM** (Python 3.8).

## Estructura

```
app/
  main.py             inventario -> reportes JSON, CSV, YAML y XML
  formats.py          lectura/escritura de los 4 formatos
  network_status.py   API REST de Catalyst Center (token + network-device)
  restconf_config.py  RESTCONF: listar interfaces / crear loopback
  netconf_config.py   NETCONF: listar interfaces (XML) / crear loopback
  webex_notify.py     envía el resumen del inventario a una sala de Webex
ansible/              inventario YAML y playbook para IOS-XE
config/.env.example   plantilla de variables (sin secretos)
data/devices.yaml     inventario de entrada de ejemplo
reports/              reportes generados
tests/                pruebas con pytest (sin red, usando mocks)
Dockerfile, Jenkinsfile
```

## Instalación

```bash
git clone https://github.com/alexis20010211/devops-network-automation.git
cd devops-network-automation
python3 -m pip install --user -r requirements.txt
cp config/.env.example config/.env
nano config/.env           # completar con los datos reales
chmod 600 config/.env      # solo el dueño puede leer los secretos
set -a; . config/.env; set +a   # cargar las variables en la sesión
```

## Uso

| Tarea | Comando |
|---|---|
| Pruebas | `python3 -m pytest -v` |
| Inventario de ejemplo | `python3 -m app.main` |
| Inventario desde un archivo | `python3 -m app.main --source data/devices.yaml` |
| Inventario desde Catalyst Center | `python3 -m app.main --source api` |
| Estado de la red (tabla) | `python3 -m app.network_status` |
| RESTCONF | `python3 -m app.restconf_config get` / `set --loopback 101 --ip 10.101.1.1` |
| NETCONF | `python3 -m app.netconf_config get` / `set --loopback 102 --ip 10.102.1.1` |
| Ansible | `cd ansible && ansible-playbook playbook.yml` |
| Webex | `python3 -m app.webex_notify` |
| Docker | `docker build -t devops-network-automation:1.0 .` y `docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)/reports:/app/reports" devops-network-automation:1.0` |

## Troubleshooting de REST API

| Síntoma | Causa probable | Solución |
|---|---|---|
| HTTP 401 | Usuario, contraseña o token incorrecto o vencido | Revisar `.env`; pedir un token nuevo |
| HTTP 403 | Usuario sin privilegios | Usar una cuenta con privilege 15 / rol admin |
| HTTP 404 | Ruta o recurso mal escrito | Revisar el endpoint y el modelo YANG |
| HTTP 415 | Content-Type incorrecto | `application/yang-data+json` en RESTCONF |
| HTTP 429 | Demasiadas peticiones | Esperar lo que indique `Retry-After` |
| HTTP 5xx | Error del servidor | Reintentar; revisar estado del sandbox |
| `SSLError` | Certificado autofirmado | `*_VERIFY_SSL=false` **solo** en laboratorio |
| `Timeout` / `ConnectionError` | Sin VPN, IP o puerto errado, servicio apagado | Conectar VPN, `ping`, `curl -vk https://host`, habilitar `restconf` / `netconf-yang` |

Los scripts traducen estos errores a mensajes claros, sin mostrar credenciales.

## Seguridad

- Las credenciales solo viven en `config/.env` (ignorado por Git) o en las credenciales de Jenkins.
- El contenedor se ejecuta con un usuario sin privilegios (`appuser`).
- La verificación SSL está activada por defecto.
