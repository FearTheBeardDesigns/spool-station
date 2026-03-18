"""PrusaLink API client for MicroPython."""

import ujson
import urequests


def get_status(host, api_key):
    """GET /api/v1/status — returns printer status dict or None."""
    try:
        url = f"http://{host}/api/v1/status"
        headers = {"X-Api-Key": api_key}
        resp = urequests.get(url, headers=headers)
        if resp.status_code == 200:
            data = ujson.loads(resp.text)
            resp.close()
            return data
        resp.close()
    except Exception as e:
        print(f"PrusaLink error: {e}")
    return None


def get_printer_state(status):
    """Extract printer state string from status response."""
    if status and "printer" in status:
        return status["printer"].get("state", "UNKNOWN")
    return "UNKNOWN"


def get_job_info(status):
    """Extract job info (gcode path, storage) from status response."""
    if not status:
        return None, None
    job = status.get("job", {})
    storage = status.get("storage", {})
    gcode_path = None
    storage_name = storage.get("path", "/usb/")

    if job and job.get("id"):
        return storage_name, job.get("id")
    return storage_name, None


def get_printer_info(host, api_key):
    """GET /api/v1/info — returns printer info dict or None."""
    try:
        url = f"http://{host}/api/v1/info"
        headers = {"X-Api-Key": api_key}
        resp = urequests.get(url, headers=headers)
        if resp.status_code == 200:
            data = ujson.loads(resp.text)
            resp.close()
            return data
        resp.close()
    except Exception as e:
        print(f"PrusaLink info error: {e}")
    return None
