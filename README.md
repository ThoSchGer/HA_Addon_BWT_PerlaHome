# BWT Perla Smartmeter – Home Assistant Add-on

Dieses Repository enthält ein **Home-Assistant-Add-on (HAOS / Supervisor-konform)** zur Auslesung eines **BWT Perla Wasserenthärters** über **VNC + OCR** und zur Veröffentlichung der Messwerte via **MQTT**.

Die Auslesung erfolgt durch:

- Aufbau einer VNC-Verbindung zum BWT-Display
- Screenshot definierter Bildschirmbereiche
- OCR (Tesseract)
- Veröffentlichung der Werte über MQTT

---

## ✨ Features

- HA-konformes Add-on (Supervisor verwaltet Lifecycle)
- Vollständig **konfigurierbar über die Home-Assistant-UI**
- **MQTT Discovery**: Automatische Sensor-Registrierung in Home Assistant
- Multi-Arch (Raspberry Pi, x86, etc.)
- Sauberes Shutdown-Handling (SIGTERM)
- Robuste OCR-Nachbearbeitung
- Optional: Debug-Screenshots bei OCR-Fehlern (`/data/debug`)
- MQTT-Status-Topic (online/offline, retained)
- Konfigurierbare OCR-Parameter und VNC-Einstellungen

---

## 📦 Installation

### 1. Add-on Repository hinzufügen

In Home Assistant:

**Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories**

Repository-URL eintragen:

<https://github.com/ThoSchGer/HA_Addon_BWT_PerlaHome>

### 2. Add-on installieren

- Add-on **„BWT Perla Smartmeter (VNC OCR MQTT)“** auswählen
- **Installieren**
- Konfiguration ausfüllen
- **Starten**

---

## ⚙️ Konfiguration

Alle Parameter werden über die Add-on-Konfiguration gesetzt (`/data/options.json`).

### BWT / VNC

| Option | Beschreibung |
|------|--------------|
| `bwt_ipaddress` | IP-Adresse des BWT Perla |
| `bwt_password` | Passwort für das BWT UI |
| `vnc_timeout_seconds` | Timeout für VNC-Verbindung || `vnc_connect_delay` | Wartezeit vor VNC-Verbindungsaufbau (Sekunden) |
### MQTT

| Option | Beschreibung |
|------|--------------|
| `mqtt_address` | MQTT Broker (Hostname/IP) |
| `mqtt_port` | MQTT Port |
| `mqtt_user` | MQTT Benutzer |
| `mqtt_password` | MQTT Passwort |
| `mqtt_topic_throughput` | Topic für Durchfluss |
| `mqtt_topic_volume` | Topic für Volumen |
| `mqtt_topic_status` | Status-Topic (online/offline, retained) |

### Intervall

| Option | Beschreibung |
|------|--------------|
| `interval_seconds` | Abfrageintervall in Sekunden |

### OCR (optional anpassbar)

| Option | Beschreibung |
|------|--------------|
| `throughput_region` | OCR-Region Durchfluss (`x,y,w,h`) |
| `throughput_pattern` | Regex für Durchfluss |
| `volume_region` | OCR-Region Volumen |
| `volume_pattern` | Regex für Volumen || `tesseract_config` | Tesseract OCR-Konfiguration |

### MQTT Discovery (optional)

| Option | Beschreibung |
|------|------------|
| `discovery_prefix` | MQTT Discovery Prefix (Standard: `homeassistant`) |
| `discovery_node_id` | Node-ID für das Device (Standard: `bwt_perla`) |
### Debug

| Option | Beschreibung |
|------|--------------|
| `debug_screenshots` | Bei OCR-Fehlern Screenshots nach `/data/debug` schreiben |

---

## 📡 MQTT Topics

### Durchfluss

```home/wasser/durchfluss```

- Payload: Integer
- QoS: 1
- Retain: false

### Volumen

```home/wasser/volumen```

- Payload: Integer
- QoS: 1
- Retain: false

### Status

```home/wasser/status```

- Payload: `online` / `offline`
- QoS: 1
- Retain: true

---

## 🧪 Debugging

### Logs

- Home Assistant → Add-on → **Logs**
- OCR-Rohwerte und Parsing-Ergebnisse werden geloggt

### Screenshots

Wenn `debug_screenshots=true`:

- OCR-Ausschnitte und ggf. Fullscreen unter:
```/data/debug/```
- Verfügbar über **Add-on → Dateisystem** oder Backup-Export

---

## 🛑 Bekannte Einschränkungen

- OCR ist abhängig von Display-Helligkeit, Schrift und UI-Layout
- VNC-Koordinaten sind **geräte- und firmwareabhängig**
- Kein offizielles BWT-API (reines Reverse-Engineering)

---

## ⚠️ Haftungsausschluss

Dieses Projekt steht **in keiner Verbindung zu BWT** und wird nicht offiziell unterstützt.  
Die Nutzung erfolgt auf eigene Verantwortung.

---

## 👤 Maintainer

**Thomas Schnee**  
GitHub: <https://github.com/ThoSchGer>
