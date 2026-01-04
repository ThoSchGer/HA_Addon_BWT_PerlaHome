from __future__ import annotations

import json
import os
import re
import signal
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import paho.mqtt.client as mqtt
import pytesseract
from PIL import Image
from vncdotool import api

OPTIONS_PATH = Path("/data/options.json")
DEBUG_DIR = Path("/data/debug")
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")

run = True
vncclient = None
throughput_old: Optional[int] = None
volume_old: Optional[int] = None


def handle_sigterm(signum, frame):
    global run
    print("[INFO] SIGTERM/SIGINT empfangen, beende...")
    run = False


signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)


@dataclass(frozen=True)
class Config:
    bwt_ipaddress: str
    bwt_password: str
    vnc_timeout_seconds: int
    vnc_connect_delay: int

    interval_seconds: int

    throughput_region: Tuple[int, int, int, int]
    throughput_pattern: str
    volume_region: Tuple[int, int, int, int]
    volume_pattern: str

    entity_prefix: str
    throughput_entity_id: Optional[str]
    volume_entity_id: Optional[str]
    tesseract_config: str
    debug_screenshots: bool


def _parse_region(s: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Region muss 'x,y,w,h' sein, erhalten: {s!r}")
    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])


def read_config() -> Config:
    raw = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))

    throughput_entity_id_raw = str(raw.get("throughput_entity_id", "")).strip()
    volume_entity_id_raw = str(raw.get("volume_entity_id", "")).strip()

    return Config(
        bwt_ipaddress=str(raw["bwt_ipaddress"]),
        bwt_password=str(raw.get("bwt_password", "")),
        vnc_timeout_seconds=int(raw.get("vnc_timeout_seconds", 60)),
        vnc_connect_delay=int(raw.get("vnc_connect_delay", 2)),

        interval_seconds=int(raw.get("interval_seconds", 10)),

        throughput_region=_parse_region(str(raw.get("throughput_region", "60,70,80,25"))),
        throughput_pattern=str(raw.get("throughput_pattern", r"(.*)\|*./h")),
        volume_region=_parse_region(str(raw.get("volume_region", "70,150,60,24"))),
        volume_pattern=str(raw.get("volume_pattern", r"(.*)\|*.")),

        entity_prefix=str(raw.get("entity_prefix", "bwt_perla")),
        throughput_entity_id=throughput_entity_id_raw or None,
        volume_entity_id=volume_entity_id_raw or None,
        tesseract_config=str(raw.get("tesseract_config", '-c page_separator=""')),
        debug_screenshots=bool(raw.get("debug_screenshots", True)),
    )


def _normalize_entity_id(value: Optional[str], default: str) -> str:
    if not value:
        return default
    v = value.strip()
    if not v:
        return default
    if "." not in v:
        return f"sensor.{v}"
    return v


def _throughput_entity_id(cfg: Config) -> str:
    return _normalize_entity_id(cfg.throughput_entity_id, f"sensor.{cfg.entity_prefix}_throughput")


def _volume_entity_id(cfg: Config) -> str:
    return _normalize_entity_id(cfg.volume_entity_id, f"sensor.{cfg.entity_prefix}_volume")


mqtt_client: Optional[mqtt.Client] = None


def mqtt_on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[INFO] MQTT connected successfully")
    else:
        print(f"[WARN] MQTT connection failed with code {rc}")


def setup_mqtt() -> mqtt.Client:
    """Initialize MQTT client for embedded Mosquitto add-on."""
    client = mqtt.Client()
    client.on_connect = mqtt_on_connect
    
    # Connect to Home Assistant's embedded MQTT broker
    try:
        client.connect("core-mosquitto", 1883, 60)
        client.loop_start()
        print("[INFO] MQTT client started")
        return client
    except Exception as e:
        print(f"[ERROR] Failed to connect to MQTT: {e}")
        return client


def publish_mqtt_discovery(client: mqtt.Client, entity_id: str, name: str, unit: str, device_class: str, state_class: str, icon: str):
    """Publish MQTT discovery config for a sensor."""
    # Extract sensor name from entity_id
    object_id = entity_id.replace("sensor.", "")
    
    discovery_topic = f"homeassistant/sensor/{object_id}/config"
    state_topic = f"homeassistant/sensor/{object_id}/state"
    
    config = {
        "name": name,
        "unique_id": entity_id,
        "state_topic": state_topic,
        "unit_of_measurement": unit,
        "device_class": device_class,
        "state_class": state_class,
        "icon": icon,
        "device": {
            "identifiers": ["bwt_perla_smartmeter"],
            "name": "BWT Perla",
            "manufacturer": "BWT",
            "model": "Perla Smartmeter"
        }
    }
    
    client.publish(discovery_topic, json.dumps(config), qos=1, retain=True)
    print(f"[INFO] Published MQTT discovery for {entity_id}")


def setup_sensors(cfg: Config) -> None:
    """Initialize MQTT discovery for sensors."""
    global mqtt_client
    
    mqtt_client = setup_mqtt()
    time.sleep(2)  # Allow MQTT to connect
    
    throughput_entity = _throughput_entity_id(cfg)
    volume_entity = _volume_entity_id(cfg)
    
    publish_mqtt_discovery(
        mqtt_client,
        throughput_entity,
        "BWT Perla Durchfluss",
        "L/h",
        "water",
        "measurement",
        "mdi:water-pump"
    )
    
    publish_mqtt_discovery(
        mqtt_client,
        volume_entity,
        "BWT Perla Volumen",
        "L",
        "water",
        "total_increasing",
        "mdi:water"
    )
    
    print(f"[INFO] MQTT Discovery configured for {throughput_entity}, {volume_entity}")


def create_or_update_sensor(entity_id: str, state: int, attributes: dict) -> bool:
    """Update sensor state via MQTT."""
    if not mqtt_client:
        return False
    
    object_id = entity_id.replace("sensor.", "")
    state_topic = f"homeassistant/sensor/{object_id}/state"
    
    try:
        mqtt_client.publish(state_topic, str(state), qos=1, retain=False)
        return True
    except Exception as e:
        print(f"[ERROR] MQTT publish failed: {e}")
        return False


def bwt_login(vnc, password: str) -> None:
    """
    UI-Login-Sequenz (Koordinaten aus deinem Originalscript).
    """
    print("[INFO] Login via VNC UI...")
    vnc.mouseMove(160, 100)
    vnc.mouseDown(1); vnc.mouseUp(1)
    vnc.mouseMove(160, 50)
    vnc.mouseDown(1); vnc.mouseUp(1)

    for ch in password:
        vnc.keyPress(ch)

    vnc.mouseMove(290, 217)
    vnc.mouseDown(1); vnc.mouseUp(1)
    vnc.mouseMove(250, 210)
    vnc.mouseDown(1); vnc.mouseUp(1)
    time.sleep(1)
    print("[INFO] Login sequence done.")


def capture_region(vnc, region: Tuple[int, int, int, int], persist_path: Optional[Path]) -> Path:
    x, y, w, h = region
    if persist_path is None:
        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        path = Path(tmp)
    else:
        persist_path.parent.mkdir(parents=True, exist_ok=True)
        path = persist_path

    print(f"[DEBUG] Capturing region: x={x}, y={y}, w={w}, h={h} -> {path}")
    vnc.captureRegion(str(path), x, y, w, h)
    print(f"[DEBUG] Screenshot saved to: {path} (exists={path.exists()}, size={path.stat().st_size if path.exists() else 0} bytes)")
    return path


def ocr_image(path: Path, tesseract_config: str) -> str:
    print(f"[DEBUG] Running OCR on: {path}")
    with Image.open(path) as img:
        print(f"[DEBUG] Image size: {img.size}, mode: {img.mode}")
        result = pytesseract.image_to_string(img, lang="eng", config=tesseract_config).strip()
        print(f"[DEBUG] OCR raw result length: {len(result)} chars")
        return result


def parse_ocr_value(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text)
    if not m:
        return None
    result = m.group(1).strip()
    if result in {"O", "o"}:
        result = "0"
    # Minimale Bereinigung: nur Pipe-Zeichen entfernen, Komma zu Punkt
    result = result.replace("|", "").replace(",", ".").strip()
    return result if result else None


def to_int_value(s: str) -> Optional[int]:
    try:
        return int(float(s))
    except Exception:
        return None


def main() -> None:
    global vncclient, throughput_old, volume_old, run

    cfg = read_config()

    setup_sensors(cfg)

    if cfg.debug_screenshots:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Service started.")
    print(f"[INFO] BWT={cfg.bwt_ipaddress}, interval={cfg.interval_seconds}s")
    print(f"[INFO] Entity prefix={cfg.entity_prefix}")
    print(f"[INFO] Throughput entity={_throughput_entity_id(cfg)}")
    print(f"[INFO] Volume entity={_volume_entity_id(cfg)}")

    while run:
        tp_path = None
        vol_path = None
        try:
            if vncclient is None:
                print("[INFO] Connecting VNC...")
                time.sleep(cfg.vnc_connect_delay)
                vncclient = api.connect(cfg.bwt_ipaddress, password=None, timeout=cfg.vnc_timeout_seconds)
                print("[INFO] VNC connected successfully.")
                bwt_login(vncclient, cfg.bwt_password)
                
                # Fullscreen-Capture direkt nach Login (Debug)
                if cfg.debug_screenshots:
                    print("[DEBUG] Capturing fullscreen after login...")
                    vncclient.captureScreen(str(DEBUG_DIR / "fullscreen_after_login.png"))

            # Durchfluss
            tp_path = capture_region(
                vncclient,
                cfg.throughput_region,
                (DEBUG_DIR / f"throughput_{int(time.time())}.png") if cfg.debug_screenshots else None
            )
            tp_raw = ocr_image(tp_path, cfg.tesseract_config)
            tp_str = parse_ocr_value(tp_raw, cfg.throughput_pattern)
            print(f"[DEBUG] throughput raw={tp_raw!r} parsed={tp_str!r}")

            if tp_str is None:
                print("[WARN] Throughput OCR failed -> re-login.")
                if cfg.debug_screenshots:
                    vncclient.captureScreen(str(DEBUG_DIR / "fullscreen.png"))
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            tp_val = to_int_value(tp_str)
            if tp_val is None:
                print("[WARN] Throughput not numeric -> re-login.")
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            if throughput_old is None or tp_val != throughput_old:
                entity_id = _throughput_entity_id(cfg)
                success = create_or_update_sensor(
                    entity_id,
                    tp_val,
                    {
                        "friendly_name": "BWT Perla Durchfluss",
                        "unit_of_measurement": "l/h",
                        "device_class": "water",
                        "state_class": "measurement",
                        "icon": "mdi:water-pump",
                    }
                )
                if success:
                    print(f"[INFO] Updated throughput: {tp_val} l/h")
                    throughput_old = tp_val
                else:
                    print("[WARN] Failed to update throughput sensor")

            # Volumen
            vol_path = capture_region(
                vncclient,
                cfg.volume_region,
                (DEBUG_DIR / f"volume_{int(time.time())}.png") if cfg.debug_screenshots else None
            )
            vol_raw = ocr_image(vol_path, cfg.tesseract_config)
            vol_str = parse_ocr_value(vol_raw, cfg.volume_pattern)
            print(f"[DEBUG] volume raw={vol_raw!r} parsed={vol_str!r}")

            if vol_str is None:
                print("[WARN] Volume OCR failed -> re-login.")
                if cfg.debug_screenshots:
                    vncclient.captureScreen(str(DEBUG_DIR / "fullscreen.png"))
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            vol_val = to_int_value(vol_str)
            if vol_val is None:
                print("[WARN] Volume not numeric -> re-login.")
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            # VNC keep-alive (wie im Originalscript)
            vncclient.mouseMove(400, 0)
            vncclient.mouseDown(1); vncclient.mouseUp(1)

            # Publish Volume nur bei Änderung + “Jump”-Filter (wie zuvor)
            if volume_old is None or vol_val != volume_old:
                if volume_old is None:
                    should_update = True
                else:
                    diff = vol_val - volume_old
                    should_update = diff < 50 or vol_val == 0
                
                if should_update:
                    entity_id = _volume_entity_id(cfg)
                    success = create_or_update_sensor(
                        entity_id,
                        vol_val,
                        {
                            "friendly_name": "BWT Perla Volumen",
                            "unit_of_measurement": "l",
                            "device_class": "water",
                            "state_class": "total_increasing",
                            "icon": "mdi:water",
                        }
                    )
                    if success:
                        print(f"[INFO] Updated volume: {vol_val} l")
                    else:
                        print("[WARN] Failed to update volume sensor")
                volume_old = vol_val

        except Exception as e:
            print(f"[ERROR] Loop exception: {e}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            vncclient = None
        finally:
            # temporäre Dateien löschen, falls nicht persistent
            try:
                if tp_path and not cfg.debug_screenshots:
                    tp_path.unlink(missing_ok=True)
                if vol_path and not cfg.debug_screenshots:
                    vol_path.unlink(missing_ok=True)
            except Exception:
                pass

        time.sleep(cfg.interval_seconds)

    print("[INFO] Stopping...")
    print("[INFO] Stopped.")


if __name__ == "__main__":
    main()
