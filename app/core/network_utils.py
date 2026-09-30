"""Network utilities: CIDR handling, adapter/interface detection, gateway lookup.

Cross-platform (Windows 10/11 primary target, Linux works for development/testing).
"""
from __future__ import annotations

import ipaddress
import platform
import re
import socket
import subprocess
import sys
from dataclasses import dataclass

IS_WINDOWS = platform.system().lower() == "windows"


@dataclass
class AdapterInfo:
    name: str
    ipv4: str
    netmask: str
    gateway: str
    cidr: str


def validate_cidr(cidr: str) -> ipaddress.IPv4Network:
    """Validate a CIDR string and return an IPv4Network.

    Accepts bare IPs (treated as /32) and plain networks like 192.168.1.0
    (treated as /24 by default? No: strict=False allows host bits set).
    Raises ValueError with a user-friendly message on invalid input.
    """
    if not cidr or not cidr.strip():
        raise ValueError("Network range cannot be empty.")
    cidr = cidr.strip()
    try:
        if "/" not in cidr:
            return ipaddress.ip_network(cidr, strict=False)
        return ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        raise ValueError(
            f"'{cidr}' is not a valid network range.\n"
            f"Use a CIDR such as 192.168.1.0/24, 10.0.0.0/24 or 172.16.1.0/24.\n"
            f"Details: {exc}"
        ) from exc


def cidr_of(ip: str, netmask: str) -> str:
    """Return the CIDR string (e.g. 192.168.1.0/24) for an ip/netmask pair."""
    try:
        iface = ipaddress.ip_interface(f"{ip}/{netmask}")
        return str(iface.network)
    except ValueError:
        # Fall back to a /24 assumption for private IPv4 ranges
        return f"{ip.rsplit('.', 1)[0]}.0/24"


def expand_cidr(cidr: str) -> list[str]:
    """Return the list of usable host IPs in the given CIDR."""
    net = validate_cidr(cidr)
    if net.num_addresses <= 2:
        return [str(ip) for ip in net.hosts()] or [str(net.network_address)]
    return [str(ip) for ip in net.hosts()]


def get_local_ip() -> str:
    """Best-effort local IPv4 (does not send traffic; uses a UDP connect trick)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


def _run(cmd: list[str], timeout: int = 10) -> str:
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        return out.stdout or ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def get_adapters() -> list[AdapterInfo]:
    """Detect local network adapters with IPv4, mask, gateway and CIDR."""
    if IS_WINDOWS:
        return _adapters_windows()
    return _adapters_linux()


def _adapters_windows() -> list[AdapterInfo]:
    text = _run(["ipconfig", "/all"])
    adapters: list[AdapterInfo] = []
    current: dict | None = None
    name_re = re.compile(r"^(.+?) adapter (.+?):")
    for raw in text.splitlines():
        line = raw.rstrip()
        m = name_re.match(line)
        if m:
            if current and current.get("ipv4"):
                adapters.append(_mk_adapter(current))
            current = {"name": f"{m.group(1)}: {m.group(2)}".strip(": ")}
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.lower().startswith("ipv4"):
            ip = stripped.split(":", 1)[-1].split("%")[0].strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip):
                current["ipv4"] = ip
        elif "subnet mask" in stripped.lower():
            current["mask"] = stripped.split(":", 1)[-1].strip()
        elif "default gateway" in stripped.lower():
            gw = stripped.split(":", 1)[-1].strip()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", gw):
                current["gw"] = gw
        elif "media disconnected" in stripped.lower() or "media state" in stripped.lower():
            current["down"] = True
    if current and current.get("ipv4") and not current.get("down"):
        adapters.append(_mk_adapter(current))
    return adapters


def _mk_adapter(d: dict) -> AdapterInfo:
    ip = d.get("ipv4", "")
    mask = d.get("mask", "255.255.255.0")
    return AdapterInfo(
        name=d.get("name", "Unknown"),
        ipv4=ip,
        netmask=mask,
        gateway=d.get("gw", ""),
        cidr=cidr_of(ip, mask),
    )


def _adapters_linux() -> list[AdapterInfo]:
    text = _run(["ip", "-4", "-o", "addr", "show"])
    adapters: list[AdapterInfo] = []
    for line in text.splitlines():
        # 2: eth0    inet 192.168.1.10/24 brd ...
        m = re.match(r"\d+:\s+(\S+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/(\d+)", line)
        if not m:
            continue
        name, ip, prefix = m.groups()
        if name == "lo":
            continue
        mask = str(ipaddress.ip_network(f"0.0.0.0/{prefix}").netmask)
        adapters.append(AdapterInfo(name, ip, mask, get_gateway(), f"{ip.rsplit('.', 1)[0]}.0/{prefix}"))
    return adapters


def get_gateway() -> str:
    """Detect the default gateway."""
    if IS_WINDOWS:
        text = _run(["route", "print", "-4", "0.0.0.0"])
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == "0.0.0.0":
                if re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[1]) and parts[1] != "0.0.0.0":
                    return parts[1]
    else:
        try:
            with open("/proc/net/route") as fh:
                next(fh)
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) > 2 and parts[1] == "00000000":
                        gw_hex = parts[2]
                        gw = ".".join(
                            str(int(gw_hex[i : i + 2], 16)) for i in (6, 4, 2, 0)
                        )
                        return gw
        except OSError:
            pass
    return ""


def friendly_error(exc: Exception) -> str:
    """Map common low-level errors to friendly messages."""
    msg = str(exc)
    if isinstance(exc, PermissionError):
        return "Permission denied. Try running the application as Administrator."
    if "timed out" in msg or isinstance(exc, TimeoutError):
        return "The operation timed out. Check your network connection and try again."
    if isinstance(exc, OSError) and exc.errno == 10065:
        return "The network is unreachable. Check that you are connected to a network."
    return f"{type(exc).__name__}: {msg}"
