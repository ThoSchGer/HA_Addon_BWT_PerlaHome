\
from __future__ import annotations

import json
import os
import re
import signal
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
    # Fix: run must be global, otherwise SIGTERM won't stop the loop reliably
    global run
    print("[INFO] SIGTERM/SIGINT empfangen, beende das Skript...")
    run = False


signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)


@dataclass(frozen=True)
class Config:
    bwt_ipaddress: str
    bwt_password: str
    vnc_timeout_seconds: int

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

    debug_screenshots: bool


def _parse_region(s: str) -> Tuple[int, int, int, int]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise ValueError(f"Region must have 4 integers 'x,y,w,h' but got: {s!r}")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def read_config() -> Config:
    if not OPTIONS_PATH.exists():
        raise RuntimeError("Missing /data/options.json (Supervisor should provide it).")

    raw = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))

    return Config(
        bwt_ipaddress=str(raw["bwt_ipaddress"]),
        bwt_password=str(raw.get("bwt_password", "")),
        vnc_timeout_seconds=int(raw.get("vnc_timeout_seconds", 60)),

        mqtt_address=str(raw["mqtt_address"]),
        mqtt_port=int(raw.get("mqtt_port", 1883)),
        mqtt_user=str(raw.get("mqtt_user", "")),
        mqtt_password=str(raw.get("mqtt_password", "")),

        mqtt_topic_throughput=str(raw["mqtt_topic_throughput"]),
        mqtt_topic_volume=str(raw["mqtt_topic_volume"]),
        mqtt_topic_status=str(raw["mqtt_topic_status"]),

        interval_seconds=int(raw.get("interval_seconds", 10)),

        throughput_region=_parse_region(str(raw.get("throughput_region", "60,70,80,25"))),
        throughput_pattern=str(raw.get("throughput_pattern", r"(.*)\|*\.?/h")),
        volume_region=_parse_region(str(raw.get("volume_region", "70,150,60,24"))),
        volume_pattern=str(raw.get("volume_pattern", r"(.*)\|*\.")),

        debug_screenshots=bool(raw.get("debug_screenshots", True)),
    )


def ensure_debug_dir(enabled: bool) -> None:
    if enabled:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def mqtt_connect(cfg: Config) -> mqtt.Client:
    client = mqtt.Client()
    if cfg.mqtt_user or cfg.mqtt_password:
        client.username_pw_set(cfg.mqtt_user, cfg.mqtt_password)

    # Keep reconnecting; Supervisor may restart networking during boot
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    client.connect(cfg.mqtt_address, cfg.mqtt_port, keepalive=20)
    client.loop_start()
    return client


def mqtt_set_status(client: mqtt.Client, cfg: Config, status: str) -> None:
    # Retained status is useful for availability
    try:
        client.publish(cfg.mqtt_topic_status, payload=status, qos=1, retain=True)
    except Exception as e:
        print(f"[WARN] Failed to publish status '{status}': {e}")


def bwt_login(vnc, password: str) -> None:
    print("[INFO] Attempting BWT login via VNC UI...")

    # NOTE: Coordinates are taken from your original script
    vnc.mouseMove(160, 100)
    vnc.mouseDown(1); vnc.mouseUp(1)
    vnc.mouseMove(160, 50)
    vnc.mouseDown(1); vnc.mouseUp(1)

    for char in password:
        vnc.keyPress(char)

    vnc.mouseMove(290, 217)
    vnc.mouseDown(1); vnc.mouseUp(1)
    vnc.mouseMove(250, 210)
    vnc.mouseDown(1); vnc.mouseUp(1)

    time.sleep(1)
    print("[INFO] Login sequence executed.")


def capture_region(vnc, filepath: Path, region: Tuple[int, int, int, int]) -> None:
    x, y, w, h = region
    vnc.captureRegion(str(filepath), x, y, w, h)


def ocr_image(filepath: Path) -> str:
    with Image.open(filepath) as image:
        # eng is used; adjust if your UI uses other language glyphs
        return pytesseract.image_to_string(
            image,
            lang="eng",
            config='-c page_separator=""'
        ).strip()


def parse_ocr_output(ocr_output: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, ocr_output)
    if not match:
        return None

    result = match.group(1).strip()

    # common OCR confusion: 'O' vs '0'
    if result in {"O", "o"}:
        result = "0"

    # Strip unwanted characters while keeping digits, dot, comma, minus
    cleaned = re.sub(r"[^0-9\.,\-]", "", result)
    cleaned = cleaned.replace(",", ".")
    return cleaned if cleaned else None


def to_int_value(s: str) -> Optional[int]:
    try:
        return int(float(s))
    except Exception:
        return None


def main() -> None:
    global vncclient, throughput_old, volume_old, run

    cfg = read_config()
    ensure_debug_dir(cfg.debug_screenshots)

    mqttclient = mqtt_connect(cfg)
    mqtt_set_status(mqttclient, cfg, "online")

    print("[INFO] Service started.")
    print(f"[INFO] BWT IP: {cfg.bwt_ipaddress}, interval: {cfg.interval_seconds}s, VNC timeout: {cfg.vnc_timeout_seconds}s")

    while run:
        try:
            if vncclient is None:
                print("[INFO] Connecting to VNC server...")
                time.sleep(3)
                vncclient = api.connect(cfg.bwt_ipaddress, password=None, timeout=cfg.vnc_timeout_seconds)
                bwt_login(vncclient, cfg.bwt_password)

            # Capture + OCR throughput
            tp_path = DEBUG_DIR / "throughput.png" if cfg.debug_screenshots else Path("/tmp/throughput.png")
            capture_region(vncclient, tp_path, cfg.throughput_region)
            throughput_ocr = ocr_image(tp_path)
            throughput_str = parse_ocr_output(throughput_ocr, cfg.throughput_pattern)

            print(f"[DEBUG] OCR Throughput raw: {throughput_ocr!r} -> parsed: {throughput_str!r}")

            if throughput_str is None:
                if cfg.debug_screenshots:
                    fs_path = DEBUG_DIR / "fullscreen.png"
                    vncclient.captureScreen(str(fs_path))
                print("[WARN] OCR throughput failed; re-login and retry.")
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            tp_val = to_int_value(throughput_str)
            if tp_val is None:
                print("[WARN] Throughput value not numeric; re-login and retry.")
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            if throughput_old is None or tp_val != throughput_old:
                mqttclient.publish(cfg.mqtt_topic_throughput, payload=tp_val, qos=1, retain=False)
                throughput_old = tp_val

            # Capture + OCR volume
            vol_path = DEBUG_DIR / "volume.png" if cfg.debug_screenshots else Path("/tmp/volume.png")
            capture_region(vncclient, vol_path, cfg.volume_region)
            volume_ocr = ocr_image(vol_path)
            volume_str = parse_ocr_output(volume_ocr, cfg.volume_pattern)

            print(f"[DEBUG] OCR Volume raw: {volume_ocr!r} -> parsed: {volume_str!r}")

            if volume_str is None:
                if cfg.debug_screenshots:
                    fs_path = DEBUG_DIR / "fullscreen.png"
                    vncclient.captureScreen(str(fs_path))
                print("[WARN] OCR volume failed; re-login and retry.")
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            vol_val = to_int_value(volume_str)
            if vol_val is None:
                print("[WARN] Volume value not numeric; re-login and retry.")
                bwt_login(vncclient, cfg.bwt_password)
                time.sleep(cfg.interval_seconds)
                continue

            # Keep VNC connection alive
            vncclient.mouseMove(400, 0)
            vncclient.mouseDown(1); vncclient.mouseUp(1)

            # Publish volume if changed; apply "jump" filter like in your original script
            if volume_old is None or vol_val != volume_old:
                if volume_old is None:
                    # first publish
                    mqttclient.publish(cfg.mqtt_topic_volume, payload=vol_val, qos=1, retain=False)
                else:
                    vol_diff = vol_val - volume_old
                    if vol_diff < 50 or vol_val == 0:
                        mqttclient.publish(cfg.mqtt_topic_volume, payload=vol_val, qos=1, retain=False)
                volume_old = vol_val

        except Exception as e:
            print(f"[ERROR] Loop exception: {e}")
            # Force reconnect on any error
            vncclient = None

        time.sleep(cfg.interval_seconds)

    print("[INFO] Stopping...")
    mqtt_set_status(mqttclient, cfg, "offline")
    try:
        mqttclient.loop_stop()
    except Exception:
        pass
    try:
        mqttclient.disconnect()
    except Exception:
        pass
    print("[INFO] Stopped.")


if __name__ == "__main__":
    main()
