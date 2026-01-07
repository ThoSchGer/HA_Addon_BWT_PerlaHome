# BWT Perla Smartmeter – Home Assistant Add-on

Dieses Repository enthält ein **Home-Assistant-Add-on (HAOS / Supervisor-konform)** zur Auslesung eines **BWT Perla Wasserenthärters** über **VNC + OCR**.

Die Messwerte werden per **MQTT** veröffentlicht mit optionaler **MQTT Discovery** für automatische Sensor-Registrierung.

**Voraussetzung**: MQTT Broker (z.B. Mosquitto Add-on) muss verfügbar sein.

## ✨ Features

- MQTT-Veröffentlichung mit konfigurierbaren Topics
- MQTT Discovery für automatische Sensor-Registrierung in Home Assistant
- Konfigurierbar über die Home-Assistant-UI
- VNC + OCR (Tesseract) zum Auslesen
- MQTT-Status-Topic (online/offline, retained)
- Umfassende Debug-Logs und optionale Screenshots (`/data/debug`)

## 📦 Installation

1. **Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories**
2. Repository-URL hinzufügen: <https://github.com/ThoSchGer/HA_Addon_BWT_PerlaHome>
3. Add-on installieren und starten

## ⚙️ Konfiguration

Alle Parameter werden über die Add-on-Konfiguration gesetzt (`/data/options.json`).

### BWT / VNC

- `bwt_ipaddress`: IP-Adresse des BWT Perla (VNC Server)
- `bwt_password`: Passwort für das BWT UI-Login
- `vnc_timeout_seconds`: Timeout für VNC-Verbindung (Standard: 60)
- `vnc_connect_delay`: Wartezeit vor VNC-Verbindungsaufbau in Sekunden (Standard: 2)

### MQTT

- `mqtt_address`: MQTT Broker Adresse (z.B. `homeassistant.local` oder `core-mosquitto`)
- `mqtt_port`: MQTT Port (Standard: 1883)
- `mqtt_user`: MQTT Benutzername (optional)
- `mqtt_password`: MQTT Passwort (optional)
- `mqtt_topic_throughput`: Topic für Durchflusswerte (Standard: `home/wasser/durchfluss`)
- `mqtt_topic_volume`: Topic für Volumenwerte (Standard: `home/wasser/volumen`)
- `mqtt_topic_status`: Status-Topic für online/offline (Standard: `home/wasser/status`)

### MQTT Discovery

- `discovery_prefix`: MQTT Discovery Prefix (Standard: `homeassistant`)
- `discovery_node_id`: Node-ID für das Device (Standard: `bwt_perla`)

### OCR

- `throughput_region`: OCR-Region Durchfluss im Format `x,y,w,h` (Standard: `60,70,80,25`)
- `throughput_pattern`: Regex zum Extrahieren des Durchflusswerts (Standard: `(.*)|*./h`)
- `volume_region`: OCR-Region Volumen im Format `x,y,w,h` (Standard: `70,150,60,24`)
- `volume_pattern`: Regex zum Extrahieren des Volumenwerts (Standard: `(.*)|*.`)
- `tesseract_config`: Tesseract OCR-Konfiguration (Standard: `-c page_separator=""`)

### Sonstiges

- `interval_seconds`: Abfrageintervall in Sekunden (Standard: 10)
- `debug_screenshots`: Debug-Screenshots nach `/data/debug` schreiben (Standard: true)

## 📡 MQTT Topics

Standardmäßig verwendet das Add-on folgende Topics:

- **Durchfluss**: `home/wasser/durchfluss` (Payload: Integer, QoS: 1)
- **Volumen**: `home/wasser/volumen` (Payload: Integer, QoS: 1)
- **Status**: `home/wasser/status` (Payload: `online`/`offline`, QoS: 1, retained)

## 🔍 MQTT Discovery

Bei aktivierter MQTT Discovery werden automatisch folgende Sensoren in Home Assistant registriert:

- `sensor.bwt_perla_throughput` (Durchfluss in l/h)
- `sensor.bwt_perla_volume` (Volumen in l)

Das Device wird als "BWT Perla" mit Hersteller "BWT" angezeigt.

**Discovery-Topics**:

- `homeassistant/sensor/bwt_perla/throughput/config`
- `homeassistant/sensor/bwt_perla/volume/config`

## 📋 Manuelle Sensor-Konfiguration (ohne Discovery)

Falls du MQTT Discovery nicht nutzen möchtest, kannst du die Sensoren manuell in Home Assistant konfigurieren:

**In `configuration.yaml`:**

```yaml
mqtt: !include mqtt.yaml
```

**In `mqtt.yaml`:**

```yaml
sensor:
  - name: "Wasserdurchfluss"
    unique_id: home_wasser_durchfluss_1
    state_topic: "home/wasser/durchfluss"
    unit_of_measurement: "L/h"
    value_template: "{{ value }}"
    state_class: measurement
  - name: "Wasserverbrauch"
    unique_id: home_wasser_volumen_1
    state_topic: "home/wasser/volumen"
    unit_of_measurement: L
    value_template: "{{ value }}"
    state_class: total_increasing
    device_class: water
```

**Hinweis**: Passe die `state_topic` Werte an deine Add-on Konfiguration an (`mqtt_topic_throughput` und `mqtt_topic_volume`).

## 🧪 Debugging

Siehe [DEBUGGING.md](DEBUGGING.md) für eine ausführliche Anleitung zur Fehlersuche.

### Quick-Tipps

- **Logs**: Home Assistant → Add-ons → BWT Perla Smartmeter → Logs
- **Screenshots**: Bei `debug_screenshots: true` werden Bilder nach `/data/debug/` geschrieben
- **MQTT-Test**: Mit MQTT Explorer oder `mosquitto_sub` kannst du die Topics überwachen

## 👤 Maintainer

Thomas Schnee
