"""Background workers so the GUI never freezes during scans."""
from __future__ import annotations

import traceback
from datetime import datetime

from PySide6.QtCore import QThread, Signal

from ..core.discovery import DiscoveryEngine, ProgressInfo, ScanSettings
from ..core.models import Device, ScanSummary, PortResult
from ..core import ports as portscanner
from ..core.arp import get_arp_table
from ..core.hostname import resolve_hostname
from ..core.oui import lookup_vendor


class ScanWorker(QThread):
    """Runs a full network discovery in the background."""

    progress = Signal(int, int, str)          # scanned, total, current ip
    device_found = Signal(object)             # Device
    finished_ok = Signal(object)              # list[Device]
    failed = Signal(str)                      # friendly error

    def __init__(self, cidr: str, settings: ScanSettings, interface: str, known: dict, parent=None):
        super().__init__(parent)
        self.cidr = cidr
        self.settings = settings
        self.interface = interface
        self.known = known
        self.engine = DiscoveryEngine(settings)

    # control from the GUI thread
    def stop(self): self.engine.stop()
    def pause(self): self.engine.pause()
    def resume(self): self.engine.resume()
    @property
    def paused(self): return self.engine.paused

    def run(self):
        started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        import time as _t
        t0 = _t.perf_counter()

        def on_progress(info: ProgressInfo):
            self.progress.emit(info.scanned, info.total, info.current_ip)

        def on_device(dev: Device):
            self.device_found.emit(dev)

        self.engine.progress_cb = on_progress
        self.engine.device_cb = on_device
        try:
            devices = self.engine.scan_range(self.cidr, self.interface, self.known)
            duration = _t.perf_counter() - t0
            summary = ScanSummary(
                cidr=self.cidr, started=started,
                finished=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                device_count=len(devices), duration_seconds=duration,
            )
            self.finished_ok.emit(devices)
        except ValueError as exc:
            self.failed.emit(str(exc))
        except Exception:
            traceback.print_exc()
            self.failed.emit("The scan failed unexpectedly. See the log for details.")


class RescanWorker(QThread):
    """Rescans a single device."""

    device_ready = Signal(object)  # Device (or None if offline now)

    def __init__(self, ip: str, settings: ScanSettings, interface: str, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.settings = settings
        self.interface = interface

    def run(self):
        try:
            engine = DiscoveryEngine(self.settings)
            dev = engine.scan_single(self.ip, self.interface)
            self.device_ready.emit(dev)
        except Exception:
            traceback.print_exc()
            self.device_ready.emit(None)


class PortScanWorker(QThread):
    """Runs a TCP port scan for one host in the background."""

    ports_ready = Signal(str, object, str)  # ip, list[PortResult], error

    def __init__(self, ip: str, port_list: list[int], timeout: float, max_workers: int = 64, parent=None):
        super().__init__(parent)
        self.ip = ip
        self.port_list = port_list
        self.timeout = timeout
        self.max_workers = max_workers
        self._cancel = False

    def stop(self):
        self._cancel = True

    def run(self):
        try:
            if self._cancel:
                return
            results = portscanner.scan_ports(
                self.ip, self.port_list, self.timeout, self.max_workers
            )
            if self._cancel:
                return
            self.ports_ready.emit(self.ip, results, "")
        except Exception as exc:
            self.ports_ready.emit(self.ip, [], f"Port scan failed: {exc}")
