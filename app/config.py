"""Application settings (JSON-backed)."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

from .core.ports import DEFAULT_COMMON_PORTS


@dataclass
class Settings:
    # Scanning
    ping_timeout_ms: int = 800
    max_concurrent: int = 100
    port_timeout_s: float = 1.0
    scan_methods: list[str] = field(default_factory=lambda: ["icmp", "arp", "tcp"])
    dns_lookup: bool = True
    netbios_lookup: bool = True
    scan_ports_on_discovery: bool = False
    # Ports
    common_ports: list[int] = field(default_factory=lambda: list(DEFAULT_COMMON_PORTS))
    custom_ports: str = ""
    # Appearance
    theme: str = "dark"  # dark | light
    compact_table: bool = False
    auto_refresh: bool = False
    # Notifications
    notify_new_device: bool = True
    notify_device_gone: bool = True
    notify_new_port: bool = True
    notify_port_closed: bool = True
    notify_mac_ip_change: bool = True


DEFAULTS = Settings()


def _settings_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.local/share")
    folder = os.path.join(base, "LanScanner")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "settings.json")


def load_settings() -> Settings:
    """Load settings from disk, falling back to defaults per missing key."""
    s = Settings()
    try:
        with open(_settings_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            for key, value in data.items():
                if hasattr(s, key):
                    setattr(s, key, value)
    except (OSError, json.JSONDecodeError):
        pass
    return s


def save_settings(s: Settings) -> bool:
    try:
        with open(_settings_path(), "w", encoding="utf-8") as fh:
            json.dump(asdict(s), fh, indent=2)
        return True
    except OSError:
        return False
