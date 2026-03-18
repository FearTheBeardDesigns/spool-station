"""PrusaLink + ESP32 configuration persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

_CONFIG_DIR = os.path.join(
    os.environ.get("SPOOL_STATION_DATA", os.path.expanduser("~/.spool-station"))
)
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "prusalink.json")


@dataclass
class PrinterConfig:
    """PrusaLink + ESP32 printer tracking configuration."""

    prusalink_host: str = ""
    prusalink_api_key: str = ""
    esp32_host: str = ""
    poll_interval: int = 30
    auto_sync: bool = True
    enabled: bool = False


def load_config() -> PrinterConfig:
    """Load printer config from disk."""
    try:
        with open(_CONFIG_PATH, "r") as f:
            data = json.load(f)
        return PrinterConfig(**{k: v for k, v in data.items() if k in PrinterConfig.__dataclass_fields__})
    except (FileNotFoundError, json.JSONDecodeError):
        return PrinterConfig()


def save_config(config: PrinterConfig) -> None:
    """Save printer config to disk."""
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(asdict(config), f, indent=2)
