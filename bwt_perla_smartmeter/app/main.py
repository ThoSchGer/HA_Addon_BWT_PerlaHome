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

    mqtt_address: str
    mqtt_port: int
    mqtt_user: str
    mqtt_password: str

    mqtt_topic_throughput: str
    mqtt_topic_volume: str
    mqtt_topic_status: str

    interval_seconds: int

    throughput_region: Tuple[int, int, int, int]
    throughput_pattern: str
    volume_region: Tuple[int, int, int, int]
    volume_pattern: str

    discovery_prefix: str
    discovery_node_id: str

    tesseract_config: str
    debug_screenshots: bool


def _parse_region(s: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Region muss 'x,y,w,h' sein, erhalten: {s!r}")
    return int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])


def read_config() -> Config:
    raw = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))

    return Config(
        bwt_ipaddress=str(raw["bwt_ipaddress"]),
        bwt_password=str(raw.get("bwt_password", "")),
        vnc_timeout_seconds=int(raw.get("vnc_timeout_seconds", 60)),
        vnc_connect_delay=int(raw.get("vnc_connect_delay", 2)),

        mqtt_address=str(raw["mqtt_address"]),
        mqtt_port=int(raw.get("mqtt_port", 1883)),
        mqtt_user=str(raw.get("mqtt_user", "")),
        mqtt_password=str(raw.get("mqtt_password", "")),

        mqtt_topic_throughput=str(raw["mqtt_topic_throughput"]),
        mqtt_topic_volume=str(raw["mqtt_topic_volume"]),
        mqtt_topic_status=str(raw["mqtt_topic_status"]),

        interval_seconds=int(raw.get("interval_seconds", 10)),

        # Default-Koordinaten aus deinem ursprünglichen Script
        throughput_region=_parse_region(str(raw.get("throughput_region", "60,70,80,25"))),
        throughput_pattern=str(raw.get("throughput_pattern", r"(.*)\|*./h")),
        volume_region=_parse_region(str(raw.get("volume_region", "70,150,60,24"))),
        volume_pattern=str(raw.get("volume_pattern", r"(.*)\|*.")),


        # MQTT Discovery
        discovery_prefix=str(raw.get("discovery_prefix", "homeassistant")),
        discovery_node_id=str(raw.get("discovery_node_id", "bwt_perla")),

        tesseract_config=str(raw.get("tesseract_config", '-c page_separator=""')),
        debug_screenshots=bool(raw.get("debug_screenshots", True)),
    )


def mqtt_connect(cfg: Config) -> mqtt.Client:
    # Paho MQTT 2.x: Use VERSION2 (current stable)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if cfg.mqtt_user or cfg.mqtt_password:
        client.username_pw_set(cfg.mqtt_user, cfg.mqtt_password)

    client.reconnect_delay_set(min_delay=1, max_delay=120)
    client.connect(cfg.mqtt_address, cfg.mqtt_port, keepalive=20)
    client.loop_start()
    return client


def mqtt_set_status(client: mqtt.Client, cfg: Config, status: str) -> None:
    try:
        client.publish(cfg.mqtt_topic_status, payload=status, qos=1, retain=True)
    except Exception as e:
        print(f"[WARN] Status publish failed ({status}): {e}")


def publish_discovery(client: mqtt.Client, cfg: Config) -> None:
    """
    MQTT Discovery für Home Assistant:
    - sensor.bwt_perla_throughput
    - sensor.bwt_perla_volume
    """
    device = {
        "identifiers": [cfg.discovery_node_id],
        "manufacturer": "BWT",
        "model": "Perla",
        "name": "BWT Perla",
    }

    sensors = [
        {
            "object_id": "throughput",
            "name": "BWT Perla Durchfluss",
            "state_topic": cfg.mqtt_topic_throughput,
            "unique_id": f"{cfg.discovery_node_id}_throughput",
            "unit": "l/h",
            "state_class": "measurement",
            "device_class": "water",
            "icon": "mdi:water-pump",
        },
        {
            "object_id": "volume",
            "name": "BWT Perla Volumen",
            "state_topic": cfg.mqtt_topic_volume,
            "unique_id": f"{cfg.discovery_node_id}_volume",
            "unit": "l",
            "state_class": "total_increasing",
            "device_class": "water",
            "icon": "mdi:water",
        },
    ]

    for s in sensors:
        topic = f"{cfg.discovery_prefix}/sensor/{cfg.discovery_node_id}/{s['object_id']}/config"
        payload = {
            "name": s["name"],
            "state_topic": s["state_topic"],
            "availability_topic": cfg.mqtt_topic_status,
            "payload_available": "online",
            "payload_not_available": "offline",
            "unique_id": s["unique_id"],
            "device": device,
            "unit_of_measurement": s["unit"],
            "state_class": s["state_class"],
            "device_class": s["device_class"],
            "icon": s["icon"],
        }
        client.publish(topic, json.dumps(payload), qos=1, retain=True)

    print("[INFO] MQTT Discovery published.")


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

    mqttc = mqtt_connect(cfg)
    mqtt_set_status(mqttc, cfg, "online")
    publish_discovery(mqttc, cfg)

    if cfg.debug_screenshots:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Service started.")
    print(f"[INFO] BWT={cfg.bwt_ipaddress}, interval={cfg.interval_seconds}s")

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
                mqttc.publish(cfg.mqtt_topic_throughput, payload=tp_val, qos=1, retain=False)
                throughput_old = tp_val

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
                    mqttc.publish(cfg.mqtt_topic_volume, payload=vol_val, qos=1, retain=False)
                else:
                    diff = vol_val - volume_old
                    if diff < 50 or vol_val == 0:
                        mqttc.publish(cfg.mqtt_topic_volume, payload=vol_val, qos=1, retain=False)
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
    mqtt_set_status(mqttc, cfg, "offline")
    try:
        mqttc.loop_stop()
    except Exception:
        pass
    try:
        mqttc.disconnect()
    except Exception:
        pass
    print("[INFO] Stopped.")


if __name__ == "__main__":
    main()
