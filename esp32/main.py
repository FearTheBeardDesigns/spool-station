"""Spool Station ESP32 Print Logger — NFC + PrusaLink monitor.

Monitors PrusaLink printer status and NFC tag reader.
When a spool is tapped, stores its ID as the active spool.
When a print finishes, records {spool_id, gcode_path, timestamp} to flash.
Exposes HTTP API for Spool Station desktop to sync completed prints.

Hardware:
  - ESP32-WROOM-32 dev board
  - RC522 NFC module (SPI: SCK=18, MISO=19, MOSI=23, SDA=5, RST=22)
"""

import gc
import time
import network
import ujson
import machine

from nfc import RC522
from prusalink import get_status, get_printer_state
from server import start_server, handle_request


def load_config():
    """Load configuration from config.json."""
    try:
        with open("config.json", "r") as f:
            return ujson.load(f)
    except Exception:
        print("ERROR: config.json not found or invalid")
        return {}


def load_pending():
    """Load pending prints from flash."""
    try:
        with open("pending.json", "r") as f:
            return ujson.load(f)
    except Exception:
        return []


def save_pending(pending):
    """Save pending prints to flash."""
    with open("pending.json", "w") as f:
        ujson.dump(pending, f)


def connect_wifi(ssid, password):
    """Connect to WiFi and return IP address."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to WiFi: {ssid}")
        wlan.connect(ssid, password)
        for _ in range(30):
            if wlan.isconnected():
                break
            time.sleep(1)
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"WiFi connected: {ip}")
        return ip
    else:
        print("WiFi connection failed")
        return None


def get_timestamp():
    """Get current time as ISO string (approximate, no RTC sync)."""
    t = time.localtime()
    return f"{t[0]:04d}-{t[1]:02d}-{t[2]:02d}T{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"


def main():
    config = load_config()
    if not config:
        return

    # Connect WiFi
    ip = connect_wifi(config["wifi_ssid"], config["wifi_pass"])
    if not ip:
        return

    # Init NFC reader
    try:
        nfc = RC522()
        print("NFC reader initialized")
    except Exception as e:
        print(f"NFC init failed: {e}")
        nfc = None

    # Shared state
    state = {
        "active_spool_id": None,
        "printer_state": "UNKNOWN",
        "prusalink_connected": False,
        "printer_name": config.get("printer_name", ""),
        "pending": load_pending(),
        "prev_state": "UNKNOWN",
    }

    # Start HTTP server
    srv = start_server(state, nfc)
    print(f"Spool Station Logger ready at http://{ip}:8080")

    poll_interval = config.get("poll_interval", 30)
    last_poll = 0
    last_nfc_check = 0

    # Main loop
    while True:
        now = time.time()

        # Check for HTTP requests (non-blocking)
        try:
            client, _ = srv.accept()
            handle_request(client, state, nfc)
        except OSError:
            pass  # timeout, no connection

        # Poll NFC reader every 2 seconds
        if nfc and (now - last_nfc_check) >= 2:
            last_nfc_check = now
            spool_id = nfc.read_spool_id()
            if spool_id is not None and spool_id > 0:
                if spool_id != state["active_spool_id"]:
                    state["active_spool_id"] = spool_id
                    print(f"NFC: Active spool = {spool_id}")

        # Poll PrusaLink
        if (now - last_poll) >= poll_interval:
            last_poll = now
            status = get_status(
                config["prusalink_host"],
                config["prusalink_api_key"],
            )
            if status:
                state["prusalink_connected"] = True
                new_state = get_printer_state(status)
                prev = state["prev_state"]

                # Detect print completion
                if prev == "PRINTING" and new_state in ("FINISHED", "PRINTING FINISHED", "IDLE"):
                    if state["active_spool_id"]:
                        # Extract gcode path from job info
                        storage = status.get("storage", {})
                        job = status.get("job", {})
                        gcode_path = None

                        # Try to get the file path from storage
                        if storage.get("path"):
                            gcode_path = storage.get("path", "")

                        entry = {
                            "spool_id": state["active_spool_id"],
                            "gcode_path": gcode_path,
                            "storage": storage.get("name", "usb"),
                            "timestamp": get_timestamp(),
                        }
                        state["pending"].append(entry)
                        save_pending(state["pending"])
                        print(f"Print finished! Logged: spool={entry['spool_id']}")
                    else:
                        print("Print finished but no active spool tagged")

                state["printer_state"] = new_state
                state["prev_state"] = new_state
            else:
                state["prusalink_connected"] = False

            gc.collect()

        time.sleep_ms(100)


if __name__ == "__main__":
    main()
