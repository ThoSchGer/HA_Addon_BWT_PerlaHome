# BWT Perla Smartmeter – Home Assistant Add-on

Dieses Repository enthält ein **Home-Assistant-Add-on (HAOS / Supervisor-konform)** zur Auslesung eines **BWT Perla Wasserenthärters** über **VNC + OCR**.

Die Messwerte werden als **native Sensor-Zustände** über **MQTT Discovery** in Home Assistant geschrieben.

**Voraussetzung**: Mosquitto MQTT Broker Add-on muss installiert und gestartet sein.

## ✨ Features

- Native Sensoren via MQTT Discovery (erfordert Mosquitto Broker Add-on)
- Konfigurierbar über die Home-Assistant-UI
- VNC + OCR (Tesseract) zum Auslesen
- Optional: Debug-Screenshots bei OCR-Fehlern (`/data/debug`)

## 📦 Installation

1. **Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories**
2. Repository-URL hinzufügen: <https://github.com/ThoSchGer/HA_Addon_BWT_PerlaHome>
3. Add-on installieren und starten

## ⚙️ Konfiguration

Alle Parameter werden über die Add-on-Konfiguration gesetzt (`/data/options.json`).

Wichtige Optionen:

- `bwt_ipaddress`: IP-Adresse des BWT Perla (VNC Server)
- `bwt_password`: Passwort für das BWT UI-Login
- `interval_seconds`: Abfrageintervall
- `vnc_timeout_seconds`, `vnc_connect_delay`: VNC-Verhalten
- `throughput_region`, `volume_region`: OCR-Regionen im Format `x,y,w,h`
- `throughput_pattern`, `volume_pattern`: Regex zum Extrahieren der Werte
- `tesseract_config`: Tesseract OCR-Konfiguration
- `debug_screenshots`: Debug-Bilder nach `/data/debug`

## 🧩 Sensor-IDs (bestehende Entitäten beibehalten)

Standardmäßig aktualisiert das Add-on diese Entity-IDs:

- `sensor.<entity_prefix>_throughput` (Default: `sensor.bwt_perla_throughput`)
- `sensor.<entity_prefix>_volume` (Default: `sensor.bwt_perla_volume`)

Wenn du **bereits existierende Entitäten** in Home Assistant hast und deren IDs beibehalten willst, setze in der Add-on Konfiguration:

- `throughput_entity_id`: z.B. `sensor.wasserdurchfluss`
- `volume_entity_id`: z.B. `sensor.wasserverbrauch`

Hinweis: Du kannst auch ohne `sensor.` eintragen (z.B. `wasserdurchfluss`), das Add-on normalisiert das automatisch zu `sensor.wasserdurchfluss`.

## 👤 Maintainer

Thomas Schnee
