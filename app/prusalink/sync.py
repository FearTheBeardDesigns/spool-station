"""Sync engine — fetch pending prints from ESP32, parse G-code, deduct spool usage."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.db.engine import get_session
from app.db.models import Spool, UsageLog
from app.prusalink.config import PrinterConfig
from app.prusalink.gcode_parser import parse_filament_usage_g, parse_project_name


@dataclass
class SyncResult:
    """Summary of a sync operation."""

    prints_synced: int = 0
    total_grams: float = 0.0
    spool_names: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    _printer_names: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.prints_synced == 0 and not self.errors:
            return "No pending prints to sync"
        parts = []
        if self.prints_synced:
            msg = f"Synced {self.prints_synced} print(s): {self.total_grams:.1f}g total"
            if self._printer_names:
                msg += f" from {', '.join(self._printer_names)}"
            parts.append(msg)
        if self.spool_names:
            parts.append(f"Spools: {', '.join(self.spool_names)}")
        if self.errors:
            parts.append(f"Errors: {len(self.errors)}")
        return " | ".join(parts)


def _http_get(url: str, timeout: int = 10) -> dict | list | None:
    """Simple HTTP GET returning parsed JSON."""
    req = urllib.request.Request(url, headers={"User-Agent": "SpoolStation/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _http_delete(url: str, timeout: int = 10) -> bool:
    """Simple HTTP DELETE."""
    req = urllib.request.Request(url, method="DELETE", headers={"User-Agent": "SpoolStation/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _http_get_text(url: str, headers: dict | None = None, timeout: int = 30) -> str | None:
    """HTTP GET returning raw text (for G-code download)."""
    h = {"User-Agent": "SpoolStation/1.0"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # Only read first 100KB — filament comments are in the header
            return resp.read(100_000).decode("utf-8", errors="replace")
    except Exception:
        return None


def _download_gcode_header(config: PrinterConfig, gcode_path: str) -> str | None:
    """Download the first ~100KB of a G-code file from PrusaLink."""
    url = f"http://{config.prusalink_host}/api/v1/files{gcode_path}"
    headers = {"X-Api-Key": config.prusalink_api_key}
    return _http_get_text(url, headers=headers)


def sync_pending_prints(config: PrinterConfig) -> SyncResult:
    """Sync all pending prints from ESP32, deduct spool usage.

    Flow:
    1. GET http://{esp32}/pending → list of completed prints
    2. For each: download G-code from PrusaLink, parse filament used [g]
    3. Deduct from spool, create UsageLog
    4. DELETE http://{esp32}/pending/{index} to mark processed
    """
    result = SyncResult()

    # Fetch pending prints from ESP32
    pending = _http_get(f"http://{config.esp32_host}:8080/pending")
    if pending is None:
        result.errors.append("Could not connect to ESP32")
        return result
    if not pending:
        return result  # Nothing to sync

    session = get_session()
    try:
        # Process in reverse order so index deletion works correctly
        for idx in range(len(pending) - 1, -1, -1):
            entry = pending[idx]
            spool_id = entry.get("spool_id")
            gcode_path = entry.get("gcode_path")

            if not spool_id:
                result.errors.append(f"Print {idx}: missing spool_id")
                continue

            # Find spool in DB
            spool = session.get(Spool, spool_id)
            if not spool:
                result.errors.append(f"Print {idx}: spool {spool_id} not found")
                _http_delete(f"http://{config.esp32_host}:8080/pending/{idx}")
                continue

            # Try to get filament usage from G-code
            used_g = 0.0
            project_name = "Unknown"

            if gcode_path:
                gcode_text = _download_gcode_header(config, gcode_path)
                if gcode_text:
                    usages = parse_filament_usage_g(gcode_text)
                    if usages:
                        used_g = sum(usages)  # Total across all tools
                    project_name = parse_project_name(gcode_text)

            if used_g <= 0:
                result.errors.append(
                    f"Print {idx}: could not parse filament usage from G-code"
                )
                _http_delete(f"http://{config.esp32_host}:8080/pending/{idx}")
                continue

            # Deduct usage
            spool.used_weight_g += used_g
            spool.last_used = datetime.utcnow()
            if spool.first_used is None:
                spool.first_used = datetime.utcnow()

            log = UsageLog(
                spool_id=spool_id,
                used_weight_g=used_g,
                source="prusaslicer",
                project_name=project_name,
            )
            session.add(log)

            # Get spool display name
            fil_name = spool.filament.name if spool.filament else f"Spool #{spool_id}"
            result.prints_synced += 1
            result.total_grams += used_g
            result.spool_names.append(f"{fil_name} (-{used_g:.1f}g)")

            # Mark as processed on ESP32
            _http_delete(f"http://{config.esp32_host}:8080/pending/{idx}")

        session.commit()
    except Exception as e:
        session.rollback()
        result.errors.append(str(e))
    finally:
        session.close()

    return result


def sync_all_printers(configs: list[PrinterConfig]) -> SyncResult:
    """Sync pending prints from all configured printers.

    Aggregates results across all printers into a single SyncResult.
    """
    combined = SyncResult()
    printer_names = []

    for config in configs:
        if not config.esp32_host:
            continue
        result = sync_pending_prints(config)
        combined.prints_synced += result.prints_synced
        combined.total_grams += result.total_grams
        combined.spool_names.extend(result.spool_names)
        if result.errors:
            label = config.name or config.esp32_host
            combined.errors.extend(f"[{label}] {e}" for e in result.errors)
        if result.prints_synced > 0:
            printer_names.append(config.name or config.esp32_host)

    # Override summary for multi-printer context
    if printer_names and len(configs) > 1:
        combined._printer_names = printer_names
    return combined


def test_esp32_connection(esp32_host: str) -> dict | None:
    """Test ESP32 connection. Returns status dict or None."""
    return _http_get(f"http://{esp32_host}:8080/status")


def test_prusalink_connection(host: str, api_key: str) -> dict | None:
    """Test PrusaLink connection. Returns printer info or None."""
    url = f"http://{host}/api/v1/info"
    req = urllib.request.Request(url, headers={
        "User-Agent": "SpoolStation/1.0",
        "X-Api-Key": api_key,
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
