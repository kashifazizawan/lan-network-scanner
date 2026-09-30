"""ARP table access. Uses the OS `arp` command (works on Windows and Linux)."""
from __future__ import annotations

import re
import subprocess
import platform

IS_WINDOWS = platform.system().lower() == "windows"

_MAC_RE = re.compile(r"([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")
_IP_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")


def normalize_mac(mac: str) -> str:
    """Return a MAC in AA-BB-CC-DD-EE-FF format (or '' if invalid)."""
    cleaned = mac.strip().replace(":", "-").upper()
    if re.fullmatch(r"([0-9A-F]{2}-){5}[0-9A-F]{2}", cleaned):
        return cleaned
    return ""


def get_arp_table() -> dict[str, str]:
    """Parse `arp -a` into {ip: normalized MAC}."""
    try:
        out = subprocess.run(
            ["arp", "-a"],
            capture_output=True,
            text=True,
            timeout=10,
            errors="replace",
        )
        table: dict[str, str] = {}
        for line in out.stdout.splitlines():
            ip_m = _IP_RE.search(line)
            mac_m = _MAC_RE.search(line)
            if ip_m and mac_m:
                mac = normalize_mac(mac_m.group(0))
                if mac:
                    table[ip_m.group(0)] = mac
        return table
    except (subprocess.TimeoutExpired, OSError):
        return {}
