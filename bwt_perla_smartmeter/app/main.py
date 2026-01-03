import json, time, signal
from pathlib import Path
import paho.mqtt.client as mqtt

OPTIONS = Path("/data/options.json")
run = True

def handle(sig, frame):
    global run
    run = False

signal.signal(signal.SIGTERM, handle)
signal.signal(signal.SIGINT, handle)

def publish_discovery(c, cfg):
    device = {"identifiers":["bwt_perla"],"name":"BWT Perla"}
    sensors=[("throughput","Durchfluss",cfg["mqtt_topic_throughput"],"l/h"),
             ("volume","Volumen",cfg["mqtt_topic_volume"],"l")]
    for sid,name,topic,unit in sensors:
        payload={
            "name":f"BWT Perla {name}",
            "state_topic":topic,
            "availability_topic":cfg["mqtt_topic_status"],
            "unit_of_measurement":unit,
            "unique_id":f"bwt_perla_{sid}",
            "device":device
        }
        c.publish(f"homeassistant/sensor/bwt_perla/{sid}/config",
                  json.dumps(payload),retain=True)

def main():
    cfg=json.loads(OPTIONS.read_text())
    c=mqtt.Client()
    c.connect(cfg["mqtt_address"],cfg["mqtt_port"],20)
    c.loop_start()
    publish_discovery(c,cfg)
    c.publish(cfg["mqtt_topic_status"],"online",retain=True)
    while run:
        time.sleep(cfg["interval_seconds"])
    c.publish(cfg["mqtt_topic_status"],"offline",retain=True)
    c.loop_stop(); c.disconnect()

if __name__=="__main__":
    main()
