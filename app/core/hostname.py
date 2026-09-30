"""Hostname resolution: reverse DNS, Windows resolution, NetBIOS."""
from __future__ import annotations

import platform
import re
import socket
import subprocess

IS_WINDOWS = platform.system().lower() == "windows"


def resolve_hostname(ip: str, enable_netbios: bool = True) -> str:
    """Try reverse DNS, then NetBIOS (Windows only). Returns 'Unknown' on failure."""
    name = _reverse_dns(ip)
    if name and name != ip:
        return name
    if enable_netbios and IS_WINDOWS:
        name = _netbios(ip)
        if name:
            return name
    return "Unknown"


def _reverse_dns(ip: str) -> str:
    try:
        name = socket.gethostbyaddr(ip)[0]
        return name.split(".")[0]
    except (socket.herror, socket.gaierror, OSError, UnicodeError):
        return ""


def _netbios(ip: str) -> str:
    """Use `nbtstat -A <ip>` (Windows) and take the <00> UNIQUE machine name."""
    try:
        out = subprocess.run(
            ["nbtstat", "-A", ip],
            capture_output=True,
            text=True,
            timeout=6,
            errors="replace",
        )
        for line in out.stdout.splitlines():
            m = re.search(
                r"^\s*([A-Za-z0-9_-]{1,15})\s+<00>\s+UNIQUE", line, re.IGNORECASE
            )
            if m:
                return m.group(1)
    except (subprocess.TimeoutExpired, OSError):
        pass
    return ""
