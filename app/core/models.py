"""Data models for the LAN Scanner."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class PortResult:
    number: int
    state: str  # OPEN / CLOSED / FILTERED
    protocol: str = "TCP"
    service: str = "Unknown"
    response_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "port": self.number,
            "state": self.state,
            "protocol": self.protocol,
            "service": self.service,
            "response_ms": round(self.response_ms, 2),
        }


@dataclass
class Device:
    ip: str
    mac: str = ""
    hostname: str = "Unknown"
    vendor: str = "Unknown"
    status: str = "Offline"
    latency_ms: float = 0.0
    open_ports: list[int] = field(default_factory=list)
    port_results: list[PortResult] = field(default_factory=list)
    interface: str = ""
    reverse_dns: str = ""
    first_seen: str = field(default_factory=_now)
    last_seen: str = field(default_factory=_now)
    source_methods: list[str] = field(default_factory=list)  # ping / arp / tcp

    @property
    def latency_display(self) -> str:
        if self.status != "Online":
            return "-"
        if self.latency_ms <= 0:
            return "?"
        return f"{self.latency_ms:.0f} ms"

    @property
    def ports_display(self) -> str:
        return ",".join(str(p) for p in sorted(self.open_ports)) if self.open_ports else "-"

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "mac": self.mac,
            "hostname": self.hostname,
            "vendor": self.vendor,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "open_ports": sorted(self.open_ports),
            "ports_detail": [p.to_dict() for p in self.port_results],
            "interface": self.interface,
            "reverse_dns": self.reverse_dns,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "sources": self.source_methods,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Device":
        dev = cls(
            ip=d["ip"],
            mac=d.get("mac", ""),
            hostname=d.get("hostname", "Unknown"),
            vendor=d.get("vendor", "Unknown"),
            status=d.get("status", "Offline"),
            latency_ms=d.get("latency_ms", 0.0),
            open_ports=list(d.get("open_ports", [])),
            interface=d.get("interface", ""),
            reverse_dns=d.get("reverse_dns", ""),
            first_seen=d.get("first_seen", _now()),
            last_seen=d.get("last_seen", _now()),
            source_methods=list(d.get("sources", [])),
        )
        dev.port_results = [
            PortResult(
                number=p["port"],
                state=p["state"],
                protocol=p.get("protocol", "TCP"),
                service=p.get("service", "Unknown"),
                response_ms=p.get("response_ms", 0.0),
            )
            for p in d.get("ports_detail", [])
        ]
        return dev


@dataclass
class ScanSummary:
    cidr: str
    started: str
    finished: str = ""
    device_count: int = 0
    duration_seconds: float = 0.0
    open_ports_count: int = 0
    scan_id: int = 0

    def to_dict(self) -> dict:
        return {
            "cidr": self.cidr,
            "started": self.started,
            "finished": self.finished,
            "device_count": self.device_count,
            "duration_seconds": round(self.duration_seconds, 2),
            "open_ports_count": self.open_ports_count,
        }
