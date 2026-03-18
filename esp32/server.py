"""Tiny HTTP server for ESP32 — exposes NFC + print tracking API."""

import ujson
import usocket


def start_server(state, nfc_reader, port=8080):
    """Start blocking HTTP server. `state` is the shared app state dict."""
    addr = usocket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = usocket.socket()
    s.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(2)
    s.settimeout(1)  # non-blocking so main loop can also poll
    print(f"HTTP server on port {port}")
    return s


def handle_request(client, state, nfc_reader):
    """Handle a single HTTP request."""
    try:
        data = client.recv(1024).decode("utf-8")
        if not data:
            client.close()
            return

        # Parse method and path
        first_line = data.split("\r\n")[0]
        parts = first_line.split(" ")
        if len(parts) < 2:
            client.close()
            return
        method, path = parts[0], parts[1]

        # Parse body for POST/PUT
        body = None
        if "\r\n\r\n" in data:
            body_str = data.split("\r\n\r\n", 1)[1]
            if body_str.strip():
                try:
                    body = ujson.loads(body_str)
                except Exception:
                    pass

        # Route requests
        if method == "GET" and path == "/status":
            _respond_json(client, {
                "wifi": True,
                "prusalink_connected": state.get("prusalink_connected", False),
                "active_spool_id": state.get("active_spool_id"),
                "printer_state": state.get("printer_state", "UNKNOWN"),
                "printer_name": state.get("printer_name", ""),
                "version": "1.0.0",
            })

        elif method == "GET" and path == "/pending":
            _respond_json(client, state.get("pending", []))

        elif method == "DELETE" and path.startswith("/pending/"):
            try:
                idx = int(path.split("/")[-1])
                pending = state.get("pending", [])
                if 0 <= idx < len(pending):
                    pending.pop(idx)
                    _save_pending(state)
                    _respond_json(client, {"ok": True})
                else:
                    _respond_json(client, {"error": "Index out of range"}, 404)
            except ValueError:
                _respond_json(client, {"error": "Invalid index"}, 400)

        elif method == "GET" and path == "/nfc/read":
            spool_id = nfc_reader.read_spool_id() if nfc_reader else None
            _respond_json(client, {"spool_id": spool_id})

        elif method == "POST" and path == "/nfc/write":
            if body and "spool_id" in body:
                spool_id = int(body["spool_id"])
                ok = nfc_reader.write_spool_id(spool_id) if nfc_reader else False
                _respond_json(client, {"ok": ok, "spool_id": spool_id})
            else:
                _respond_json(client, {"error": "Missing spool_id"}, 400)

        else:
            _respond_json(client, {"error": "Not found"}, 404)

    except Exception as e:
        print(f"Request error: {e}")
        try:
            _respond_json(client, {"error": str(e)}, 500)
        except Exception:
            pass
    finally:
        client.close()


def _respond_json(client, data, status=200):
    body = ujson.dumps(data)
    status_text = "OK" if status == 200 else "Error"
    client.send(f"HTTP/1.0 {status} {status_text}\r\n")
    client.send("Content-Type: application/json\r\n")
    client.send("Access-Control-Allow-Origin: *\r\n")
    client.send(f"Content-Length: {len(body)}\r\n")
    client.send("\r\n")
    client.send(body)


def _save_pending(state):
    """Persist pending list to flash."""
    try:
        with open("pending.json", "w") as f:
            ujson.dump(state.get("pending", []), f)
    except Exception as e:
        print(f"Save pending error: {e}")
