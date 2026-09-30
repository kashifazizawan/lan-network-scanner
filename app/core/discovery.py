"""Network discovery engine: asynchronous host discovery.

Methods (all configurable):
  - ICMP ping sweep (OS ping command, no raw sockets / admin rights needed)
  - ARP discovery (populate + read the OS ARP table)
  - TCP connect probing on common ports
  - optional hostname resolution (reverse DNS + NetBIOS)

All scanning is cancelled/pausable through threading.Event objects and runs
in a ThreadPoolExecutor so the GUI stays responsive.
"""
from __future__ import annotations

import logging
import platform
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from .arp import get_arp_table, normalize_mac
from .hostname import resolve_hostname
from .models import Device
from .network_utils import expand_cidr, get_gateway, validate_cidr
from .oui import lookup_vendor
from . import ports as portscanner

log = logging.getLogger("lanscanner.discovery")

IS_WINDOWS = platform.system().lower() == "windows"


@dataclass
class ScanSettings:
    methods: list[str] = field(default_factory=lambda: ["icmp", "arp", "tcp"])
    ping_timeout_ms: int = 800
    port_timeout_s: float = 1.0
    max_concurrent: int = 100
    common_ports: list[int] = field(
        default_factory=lambda: list(portscanner.DEFAULT_COMMON_PORTS)
    )
    resolve_names: bool = True
    netbios: bool = True
    scan_ports_on_discovery: bool = False  # deep scan ports during sweep
    notify: bool = True


@dataclass
class ProgressInfo:
    scanned: int
    total: int
    current_ip: str = ""

    @property
    def percent(self) -> int:
        return int(self.scanned / self.total * 100) if self.total else 0


class DiscoveryEngine:
    """Discovers devices on a network range. Thread-safe cancellation."""

    def __init__(
        self,
        settings: ScanSettings | None = None,
        progress_cb=None,
        device_cb=None,
    ):
        self.settings = settings or ScanSettings()
        self.progress_cb = progress_cb  # cb(ProgressInfo)
        self.device_cb = device_cb  # cb(Device) when each device is confirmed
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._known: dict[str, Device] = {}

    # -- control ------------------------------------------------------------
    def stop(self) -> None:
        self._cancel.set()
        self._pause.clear()

    def pause(self) -> None:
        self._pause.set()

    def resume(self) -> None:
        self._pause.clear()

    @property
    def paused(self) -> bool:
        return self._pause.is_set()

    def _wait_if_paused(self) -> None:
        while self._pause.is_set() and not self._cancel.is_set():
            time.sleep(0.1)

    # -- scanning ------------------------------------------------------------
    def scan_range(self, cidr: str, interface: str = "", known: dict[str, Device] | None = None) -> list[Device]:
        """Scan a CIDR range and return the list of discovered devices."""
        net = validate_cidr(cidr)  # raises ValueError with friendly message
        hosts = expand_cidr(str(net))
        if known:
            self._known = known
        gateway = get_gateway()
        log.info("Scan start: %s (%d hosts), methods=%s", cidr, len(hosts), self.settings.methods)

        arp_first: dict[str, str] = {}
        if "arp" in self.settings.methods:
            arp_first = get_arp_table()

        devices: dict[str, Device] = {}
        scanned = 0
        lock = threading.Lock()

        def check_host(ip: str) -> None:
            if self._cancel.is_set():
                return
            self._wait_if_paused()
            dev = self._probe_host(ip, arp_first, gateway, interface)
            with lock:
                scanned += 1
                if dev is not None:
                    devices[ip] = dev
                    if self.device_cb:
                        try:
                            self.device_cb(dev)
                        except Exception:  # never let a UI callback kill the scan
                            log.exception("device callback failed")
                if self.progress_cb:
                    self.progress_cb(ProgressInfo(scanned, len(hosts), ip))

        with ThreadPoolExecutor(max_workers=max(1, self.settings.max_concurrent)) as pool:
            list(pool.map(check_host, hosts))

        if self._cancel.is_set():
            log.info("Scan cancelled at %d/%d hosts", scanned, len(hosts))
        log.info("Scan done: %d devices found", len(devices))
        return list(devices.values())

    def scan_single(self, ip: str, interface: str = "") -> Device | None:
        """Rescan a single device."""
        arp = get_arp_table() if "arp" in self.settings.methods else {}
        return self._probe_host(ip, arp, get_gateway(), interface)

    # -- internals -----------------------------------------------------------
    def _probe_host(
        self, ip: str, arp_table: dict[str, str], gateway: str, interface: str
    ) -> Device | None:
        methods: list[str] = []
        latency = 0.0

        alive = False
        if "icmp" in self.settings.methods:
            ok, ms = self._ping(ip)
            if ok:
                alive = True
                latency = ms
                methods.append("icmp")
        if not alive and "tcp" in self.settings.methods:
            r = portscanner.is_tcp_alive(ip, self.settings.common_ports[:6])
            if r is not None:
                alive = True
                latency = r.response_ms
                methods.append("tcp")
        if not alive and not "arp" in self.settings.methods:
            return None

        mac = arp_table.get(ip, "")
        if not mac and "arp" in self.settings.methods:
            # host may have appeared since we snapshotted the table
            mac = get_arp_table().get(ip, "")
        if mac:
            methods.append("arp")

        # ARP knowledge counts as alive evidence (device responded recently)
        if not alive and not mac:
            return None

        hostname = "Unknown"
        if self.settings.resolve_names:
            hostname = resolve_hostname(ip, self.settings.netbios)

        dev = Device(
            ip=ip,
            mac=normalize_mac(mac) if mac else "",
            hostname=hostname,
            vendor=lookup_vendor(mac) if mac else "Unknown",
            status="Online",
            latency_ms=latency,
            interface=interface,
            source_methods=sorted(set(methods)),
        )
        if ip == gateway:
            dev.hostname = dev.hostname if dev.hostname != "Unknown" else "Gateway"
            dev.reverse_dns = "gateway"

        # preserve first_seen across rescans
        old = self._known.get(ip)
        if old:
            dev.first_seen = old.first_seen
            if not dev.mac and old.mac:
                dev.mac = old.mac
                dev.vendor = old.vendor

        if self.settings.scan_ports_on_discovery:
            results = portscanner.scan_ports(
                ip, self.settings.common_ports, self.settings.port_timeout_s
            )
            dev.port_results = [r for r in results if r.state == "OPEN"]
            dev.open_ports = [r.number for r in dev.port_results]
        return dev

    def _ping(self, ip: str) -> tuple[bool, float]:
        """ICMP ping via the OS command. Returns (alive, latency_ms)."""
        timeout_s = max(1, int(self.settings.ping_timeout_ms / 1000))
        if IS_WINDOWS:
            cmd = ["ping", "-n", "1", "-w", str(self.settings.ping_timeout_ms), "-4", ip]
        else:
            cmd = ["ping", "-c", "1", "-W", str(timeout_s), ip]
        start = time.perf_counter()
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_s + 2, errors="replace"
            )
        except (subprocess.TimeoutExpired, OSError):
            return False, 0.0
        elapsed = (time.perf_counter() - start) * 1000
        if out.returncode != 0:
            return False, 0.0
        text = out.stdout.lower()
        if "ttl=" in text or "ttl<1" in text:
            return True, elapsed
        return False, 0.0
