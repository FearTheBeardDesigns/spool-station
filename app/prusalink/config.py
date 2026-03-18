"""PrusaLink + ESP32 configuration persistence — multi-printer support."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field

_CONFIG_DIR = os.path.join(
    os.environ.get("SPOOL_STATION_DATA", os.path.expanduser("~/.spool-station"))
)
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "prusalink.json")


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class PrinterConfig:
    """PrusaLink + ESP32 printer tracking configuration."""

    id: str = ""
    name: str = ""
    prusalink_host: str = ""
    prusalink_api_key: str = ""
    esp32_host: str = ""
    poll_interval: int = 30
    auto_sync: bool = True
    enabled: bool = True

    def __post_init__(self):
        if not self.id:
            self.id = _new_id()


def load_all_configs() -> list[PrinterConfig]:
    """Load all printer configs from disk."""
    try:
        with open(_CONFIG_PATH, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    # Migration: old single-printer format → wrap in list
    if isinstance(data, dict) and "printers" not in data:
        # Old format: single PrinterConfig dict
        fields = PrinterConfig.__dataclass_fields__
        config = PrinterConfig(**{k: v for k, v in data.items() if k in fields})
        if not config.name:
            config.name = "Printer 1"
        return [config]

    printers = data.get("printers", [])
    result = []
    fields = PrinterConfig.__dataclass_fields__
    for p in printers:
        config = PrinterConfig(**{k: v for k, v in p.items() if k in fields})
        result.append(config)
    return result


def save_all_configs(configs: list[PrinterConfig]) -> None:
    """Save all printer configs to disk."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    data = {"printers": [asdict(c) for c in configs]}
    with open(_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_config() -> PrinterConfig:
    """Load first printer config (backward compat)."""
    configs = load_all_configs()
    return configs[0] if configs else PrinterConfig()


def save_config(config: PrinterConfig) -> None:
    """Save single printer config (backward compat — replaces matching id or appends)."""
    configs = load_all_configs()
    found = False
    for i, c in enumerate(configs):
        if c.id == config.id:
            configs[i] = config
            found = True
            break
    if not found:
        configs.append(config)
    save_all_configs(configs)
