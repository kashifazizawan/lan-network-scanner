"""TCP port scanner: connect scan with service identification.

Uses normal TCP connection checks only (no stealth/ SYN scanning),
per the application's safety constraints.
"""
from __future__ import annotations

import socket
import time
from concurrent.futures import ThreadPoolExecutor

from .models import PortResult

SERVICE_MAP: dict[int, str] = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 67: "DHCP", 68: "DHCP", 69: "TFTP", 80: "HTTP", 110: "POP3",
    111: "RPC", 123: "NTP", 135: "MSRPC", 137: "NetBIOS-NS", 138: "NetBIOS-DGM",
    139: "NetBIOS-SSN", 143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS",
    445: "SMB", 465: "SMTPS", 514: "Syslog", 548: "AFP", 554: "RTSP",
    587: "SMTP", 631: "IPP", 636: "LDAPS", 993: "IMAPS", 995: "POP3S",
    1080: "SOCKS", 1433: "MSSQL", 1521: "Oracle", 1723: "PPTP", 3306: "MySQL",
    3389: "RDP", 4443: "HTTPS-Alt", 4848: "AppSrv", 5060: "SIP", 5432: "PostgreSQL",
    5900: "VNC", 5985: "WinRM-HTTP", 5986: "WinRM-HTTPS", 6379: "Redis",
    6443: "Kubernetes", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt", 8888: "HTTP-Alt",
    9000: "HTTP-Alt", 9090: "Web", 9200: "Elasticsearch", 11211: "Memcached",
    27017: "MongoDB", 32400: "Plex", 49152: "Unknown",
}

DEFAULT_COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 3389, 5900, 8080]


def parse_port_spec(spec: str) -> list[int]:
    """Parse '80,443,1000-1010' into a sorted unique port list (1-65535)."""
    ports: set[int] = set()
    for part in spec.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, _, hi = part.partition("-")
            if lo.isdigit() and hi.isdigit():
                lo_i, hi_i = int(lo), int(hi)
                if 1 <= lo_i <= hi_i <= 65535:
                    ports.update(range(lo_i, min(hi_i, lo_i + 5000) + 1))
        elif part.isdigit():
            p = int(part)
            if 1 <= p <= 65535:
                ports.add(p)
    return sorted(ports)


def scan_tcp_port(ip: str, port: int, timeout: float = 1.0) -> PortResult:
    """Connect-scan a single TCP port."""
    start = time.perf_counter()
    state = "CLOSED"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if s.connect_ex((ip, port)) == 0:
                state = "OPEN"
    except (socket.timeout, OSError):
        state = "FILTERED"
    elapsed = (time.perf_counter() - start) * 1000
    return PortResult(
        number=port,
        state=state,
        protocol="TCP",
        service=SERVICE_MAP.get(port, "Unknown"),
        response_ms=elapsed if state == "OPEN" else 0.0,
    )


def scan_ports(
    ip: str,
    ports: list[int],
    timeout: float = 1.0,
    max_workers: int = 64,
    cancel_event=None,
    progress_cb=None,
) -> list[PortResult]:
    """Scan a list of TCP ports on one host. Returns only OPEN results list
    of all results is returned; caller filters as needed."""
    results: list[PortResult] = []
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 512))) as pool:
        futures = {pool.submit(scan_tcp_port, ip, p, timeout): p for p in ports}
        for fut in futures:
            # Check cancellation before consuming
            if cancel_event is not None and cancel_event.is_set():
                for f in futures:
                    f.cancel()
                break
            results.append(fut.result())
            done += 1
            if progress_cb:
                progress_cb(done, len(ports))
    return sorted(results, key=lambda r: r.number)


def is_tcp_alive(ip: str, ports: list[int] | None = None, timeout: float = 0.7) -> PortResult | None:
    """Quick liveness check: any of the given ports accepting connections."""
    for port in ports or DEFAULT_COMMON_PORTS:
        r = scan_tcp_port(ip, port, timeout)
        if r.state == "OPEN":
            return r
    return None
