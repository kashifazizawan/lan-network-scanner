"""Main window: toolbar, network info panel, results table, topology, history."""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
    QStatusBar, QTableWidget, QTableWidgetItem, QTabWidget, QToolBar,
    QVBoxLayout, QWidget, QInputDialog,
    QSystemTrayIcon,
)

from .. import db
from ..config import Settings, load_settings, save_settings
from ..core.discovery import ScanSettings
from ..core.models import Device
from ..core.network_utils import get_adapters, get_gateway, get_local_ip, validate_cidr
from ..core.ports import parse_port_spec, DEFAULT_COMMON_PORTS
from ..export import exporter
from .theme import apply_theme, ONLINE_COLOR, OFFLINE_COLOR
from ..logger import setup_logging  # noqa: F401
from .device_details import DeviceDetailsDialog
from .history_dialog import HistoryDialog
from .settings_dialog import SettingsDialog
from .topology import TopologyView
from .workers import PortScanWorker, RescanWorker, ScanWorker

TABLE_COLUMNS = ["Status", "IP Address", "MAC Address", "Hostname", "Vendor",
                 "Open Ports", "Latency", "Last Seen"]


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or load_settings()
        self.devices: dict[str, Device] = {}
        self.scan_worker: ScanWorker | None = None
        self.port_worker: PortScanWorker | None = None
        self.rescan_worker: RescanWorker | None = None
        self.gateway_ip = ""
        self.selected_adapter = None

        self.setWindowTitle("LAN Network Scanner")
        self.resize(1280, 780)
        self._build_menu()
        self._build_ui()
        self._refresh_adapters()
        self._build_statusbar()
        self.apply_theme()

        # keyboard shortcuts
        self._add_shortcut("F5", self._refresh_adapters)
        self._add_shortcut("Ctrl+F", lambda: self.search.setFocus())
        self._add_shortcut("Ctrl+E", self._export_dialog)

    # ------------------------------------------------------------------ UI
    def _build_menu(self):
        m_file = self.menuBar().addMenu("&File")
        m_file.addAction("&Load Sample Data", self._load_sample_data, QKeySequence("Ctrl+D"))
        exp = m_file.addMenu("&Export Results")
        for fmt, label in [("csv", "CSV"), ("xlsx", "Excel XLSX"), ("json", "JSON"), ("pdf", "PDF"), ("txt", "TXT")]:
            exp.addAction(label, lambda f=fmt: self._export_dialog(f))
        m_file.addSeparator()
        m_file.addAction("E&xit", self.close, QKeySequence("Ctrl+Q"))

        m_scan = self.menuBar().addMenu("&Scan")
        m_scan.addAction("&Start Scan", self._start_scan, QKeySequence("Ctrl+S"))
        m_scan.addAction("S&top Scan", self._stop_scan, QKeySequence("Esc"))
        m_scan.addAction("&Pause / Resume", self._toggle_pause, QKeySequence("Ctrl+P"))
        m_scan.addAction("&Rescan Selected Device", self._rescan_selected, QKeySequence("Ctrl+R"))
        m_scan.addAction("Scan &All Devices", self._scan_all)
        m_scan.addSeparator()
        m_scan.addAction("Scan &History…", self._open_history, QKeySequence("Ctrl+H"))

        m_view = self.menuBar().addMenu("&View")
        act_theme = QAction("&Toggle Dark/Light Theme", self)
        act_theme.setShortcut(QKeySequence("Ctrl+T"))
        act_theme.triggered.connect(self._toggle_theme)
        m_view.addAction(act_theme)

        m_help = self.menuBar().addMenu("&Help")
        m_help.addAction("&About", self._about)

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)

        # ---- toolbar ----
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.cb_interface = QComboBox()
        self.cb_interface.setMinimumWidth(200)
        self.cb_interface.currentIndexChanged.connect(self._adapter_changed)
        toolbar.addWidget(QLabel(" Interface: "))
        toolbar.addWidget(self.cb_interface)

        self.edit_cidr = QLineEdit()
        self.edit_cidr.setPlaceholderText("192.168.1.0/24")
        self.edit_cidr.setMinimumWidth(160)
        self.edit_cidr.setToolTip("Target network range (CIDR). Only scan networks you are authorized to scan.")
        toolbar.addWidget(QLabel(" Range: "))
        toolbar.addWidget(self.edit_cidr)

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.setToolTip("Start scanning the selected network range (Ctrl+S)")
        self.btn_scan.clicked.connect(self._start_scan)
        toolbar.addWidget(self.btn_scan)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setProperty("accent", "danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_scan)
        toolbar.addWidget(self.btn_stop)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)
        toolbar.addWidget(self.btn_pause)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setToolTip("Refresh adapter / network info (F5)")
        btn_refresh.clicked.connect(self._refresh_adapters)
        toolbar.addWidget(btn_refresh)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.clicked.connect(self._open_settings)
        toolbar.addWidget(self.btn_settings)

        # ---- network info panel ----
        self.info_panel = QWidget()
        info_layout = QHBoxLayout(self.info_panel)
        info_layout.setContentsMargins(4, 4, 4, 4)
        self._info_labels: dict[str, QLabel] = {}
        for key, title in [
            ("local_ip", "Local IP"), ("mask", "Subnet Mask"), ("gateway", "Gateway"),
            ("cidr", "CIDR"), ("iface", "Interface"), ("count", "Devices Found"),
            ("progress", "Scan Progress"),
        ]:
            box = QVBoxLayout()
            t = QLabel(title)
            t.setObjectName("infoTitle")
            v = QLabel("-")
            v.setObjectName("infoValue")
            box.addWidget(t)
            box.addWidget(v)
            info_layout.addLayout(box)
            self._info_labels[key] = v
        root.addWidget(self.info_panel)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        # ---- search row ----
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Search / filter devices by IP, MAC, hostname, vendor, port or service (Ctrl+F)…"
        )
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self.search)

        self.cb_status_filter = QComboBox()
        self.cb_status_filter.addItems(["All", "Online", "Offline"])
        self.cb_status_filter.currentTextChanged.connect(self._apply_filter)
        search_row.addWidget(self.cb_status_filter)
        root.addLayout(search_row)

        # ---- tabs ----
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, stretch=1)

        # Devices table
        self.table = QTableWidget(0, len(TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(TABLE_COLUMNS)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.cellDoubleClicked.connect(self._open_details)
        self.tabs.addTab(self.table, "Devices")

        # Topology
        self.topology = TopologyView()
        self.topology.device_selected.connect(self._show_device_details)
        self.tabs.addTab(self.topology, "Network Map")

        self.setCentralWidget(central)

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.lbl_status = QLabel("Ready.")
        sb.addWidget(self.lbl_status)
        self.lbl_scan_info = QLabel("")
        sb.addPermanentWidget(self.lbl_scan_info)

    def _add_shortcut(self, key, handler):
        from PySide6.QtGui import QShortcut
        QShortcut(QKeySequence(key), self, handler)

    def apply_theme(self):
        apply_theme(QApplication.instance(), self.settings.theme)
        compact = "44px" if self.settings.compact_table else "default"
        self.table.verticalHeader().setDefaultSectionSize(26 if self.settings.compact_table else 34)
        self.table.resizeRowsToContents() if compact == "default" else None

    def _toggle_theme(self):
        self.settings.theme = "light" if self.settings.theme == "dark" else "dark"
        save_settings(self.settings)
        self.apply_theme()

    # ------------------------------------------------------------- adapters
    def _refresh_adapters(self):
        try:
            adapters = get_adapters()
        except Exception:
            adapters = []
        self.cb_interface.blockSignals(True)
        self.cb_interface.clear()
        if adapters:
            for a in adapters:
                self.cb_interface.addItem(f"{a.name}  ({a.ipv4}/{a.cidr.split('/')[-1]})", a)
            self.cb_interface.blockSignals(False)
            self.cb_interface.setCurrentIndex(0)
            self._adapter_changed(0)
        else:
            self.cb_interface.blockSignals(False)
            # no adapter detected: minimal info from local IP
            ip = get_local_ip()
            self._set_info("local_ip", ip)
            self._set_info("mask", "-")
            self._set_info("gateway", get_gateway() or "-")
            self._set_info("cidr", f"{ip.rsplit('.', 1)[0]}.0/24")
            self._set_info("iface", "-")
            self.edit_cidr.setText(f"{ip.rsplit('.', 1)[0]}.0/24")

    def _adapter_changed(self, index: int):
        data = self.cb_interface.itemData(index)
        if not data:
            return
        self.selected_adapter = data
        self.gateway_ip = data.gateway or ""
        self._set_info("local_ip", data.ipv4)
        self._set_info("mask", data.netmask)
        self._set_info("gateway", data.gateway or "Unknown")
        self._set_info("cidr", data.cidr)
        self._set_info("iface", data.name)
        self.edit_cidr.setText(data.cidr)

    def _set_info(self, key: str, value: str):
        self._info_labels[key].setText(str(value))

    # -------------------------------------------------------------- scanning
    def _scan_settings(self) -> ScanSettings:
        s = self.settings
        ports = list(s.common_ports)
        if s.custom_ports:
            ports = sorted(set(ports) | set(parse_port_spec(s.custom_ports)))
        return ScanSettings(
            methods=list(s.scan_methods),
            ping_timeout_ms=s.ping_timeout_ms,
            port_timeout_s=s.port_timeout_s,
            max_concurrent=s.max_concurrent,
            common_ports=ports or list(DEFAULT_COMMON_PORTS),
            resolve_names=s.dns_lookup,
            netbios=s.netbios_lookup,
            scan_ports_on_discovery=s.scan_ports_on_discovery,
        )

    def _start_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            QMessageBox.information(self, "Scan in progress", "A scan is already running. Stop it first.")
            return
        cidr = self.edit_cidr.text().strip()
        try:
            validate_cidr(cidr)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid network range", str(exc))
            return
        if not cidr:
            QMessageBox.warning(self, "Missing range", "Enter a network range such as 192.168.1.0/24.")
            return

        answer = QMessageBox.question(
            self, "Confirm scan",
            f"Start an authorized scan of the selected network range?\n\nTarget: {cidr}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        iface = self.selected_adapter.name if self.selected_adapter else ""
        self.scan_worker = ScanWorker(cidr, self._scan_settings(), iface, known=dict(self.devices))
        self.scan_worker.progress.connect(self._on_progress)
        self.scan_worker.device_found.connect(self._on_device_found)
        self.scan_worker.finished_ok.connect(self._on_scan_finished)
        self.scan_worker.failed.connect(self._on_scan_failed)
        self._set_scan_running(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"Scanning {cidr}…")
        self.scan_worker.start()

    def _set_scan_running(self, running: bool):
        self.btn_scan.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.btn_pause.setEnabled(running)
        if not running:
            self.btn_pause.setText("Pause")

    def _stop_scan(self):
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
            self.lbl_status.setText("Stopping scan…")

    def _toggle_pause(self):
        if not (self.scan_worker and self.scan_worker.isRunning()):
            return
        if self.scan_worker.paused:
            self.scan_worker.resume()
            self.btn_pause.setText("Pause")
            self.lbl_status.setText("Scan resumed.")
        else:
            self.scan_worker.pause()
            self.btn_pause.setText("Resume")
            self.lbl_status.setText("Scan paused.")

    def _on_progress(self, scanned: int, total: int, ip: str):
        pct = int(scanned / total * 100) if total else 0
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(scanned)
        self._set_info("progress", f"{pct}%")
        self.lbl_status.setText(f"Scanning {scanned} / {total} hosts — {pct}%")

    def _on_device_found(self, dev: Device):
        # live diff notifications against previous knowledge
        old = self.devices.get(dev.ip)
        self.devices[dev.ip] = dev
        self._notify_diff(old, dev)
        self._rebuild_table()
        self._set_info("count", str(len(self.devices)))
        self.topology.set_devices(sorted(self.devices.values(), key=lambda d: tuple(map(int, d.ip.split(".")))), self.gateway_ip)

    def _notify_diff(self, old: Device | None, new: Device):
        s = self.settings
        msgs: list[str] = []
        if old is None and s.notify_new_device:
            msgs.append(f"New device: {new.ip} ({new.hostname})")
        if old:
            if s.notify_new_port:
                opened = set(new.open_ports) - set(old.open_ports)
                for p in opened:
                    msgs.append(f"New open port on {new.ip}: {p}")
            if s.notify_port_closed:
                closed = set(old.open_ports) - set(new.open_ports)
                for p in closed:
                    msgs.append(f"Port {p} on {new.ip} is no longer open")
            if s.notify_mac_ip_change and old.mac and new.mac and old.mac != new.mac:
                msgs.append(f"MAC changed on {new.ip}: {old.mac} → {new.mac}")
        for m in msgs:
            self.lbl_status.setText(m)
            QApplication.beep() if False else None
            self.statusBar().showMessage(m, 8000)
            QApplication.processEvents()

    def _on_scan_finished(self, devices: list):
        self._set_scan_running(False)
        self.progress_bar.setVisible(False)
        self.devices = {d.ip: d for d in devices}
        self._rebuild_table()
        self.topology.set_devices(sorted(devices, key=lambda d: tuple(map(int, d.ip.split(".")))), self.gateway_ip)
        self._set_info("count", str(len(devices)))
        self._set_info("progress", "100%" if devices else "Done")
        duration = ""
        if devices:
            self.lbl_status.setText(f"Scan complete: {len(devices)} devices found.")
            self.lbl_scan_info.setText(f"{len(devices)} devices · {sum(len(d.open_ports) for d in devices)} open ports")
        try:
            from ..core.models import ScanSummary
            started = devices[0].first_seen if devices else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            summary = ScanSummary(cidr=self.edit_cidr.text().strip(), started=started,
                                 finished=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 device_count=len(devices), duration_seconds=0)
            db.save_scan(summary, list(self.devices.values()))
        except Exception:
            traceback.print_exc()

    def _on_scan_failed(self, message: str):
        self._set_scan_running(False)
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("Scan failed.")
        QMessageBox.critical(self, "Scan failed", message)

    # ------------------------------------------------------------ rescan/ports
    def _selected_devices(self) -> list[Device]:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        result = []
        for r in rows:
            ip = self.table.item(r, 1).text()
            if ip in self.devices:
                result.append(self.devices[ip])
        return result

    def _rescan_selected(self):
        devs = self._selected_devices()
        if not devs:
            QMessageBox.information(self, "Rescan", "Select a device in the table first.")
            return
        if self.rescan_worker and self.rescan_worker.isRunning():
            return
        self.lbl_status.setText(f"Rescanning {devs[0].ip}…")
        self.rescan_worker = RescanWorker(devs[0].ip, self._scan_settings(),
                                          self.selected_adapter.name if self.selected_adapter else "")
        self.rescan_worker.device_ready.connect(self._on_rescan_done)
        self.rescan_worker.start()

    def _on_rescan_done(self, dev):
        if dev is not None:
            old = self.devices.get(dev.ip)
            dev.first_seen = old.first_seen if old else dev.first_seen
            self.devices[dev.ip] = dev
            self._notify_diff(old, dev)
            self._rebuild_table()
        self.lbl_status.setText("Rescan complete.")

    def _scan_all(self):
        if not self.devices:
            QMessageBox.information(self, "Scan all", "No devices discovered yet. Run a network scan first.")
            return
        for dev in list(self.devices.values()):
            self._port_scan_device(dev)

    def _port_scan_device(self, dev: Device, ports: list[int] | None = None):
        if self.port_worker and self.port_worker.isRunning():
            QMessageBox.information(self, "Port scanner", "A port scan is already running.")
            return
        port_list = ports or list(self.settings.common_ports)
        if self.settings.custom_ports:
            port_list = sorted(set(port_list) | set(parse_port_spec(self.settings.custom_ports)))
        self.lbl_status.setText(f"Port scanning {dev.ip} ({len(port_list)} ports)…")
        self.port_worker = PortScanWorker(dev.ip, port_list, self.settings.port_timeout_s)
        self.port_worker.ports_ready.connect(self._on_ports_ready)
        self.port_worker.start()

    def _on_ports_ready(self, ip: str, results, error: str):
        if error:
            QMessageBox.warning(self, "Port scan", error)
            return
        dev = self.devices.get(ip)
        if dev is None:
            return
        open_results = [r for r in results if r.state == "OPEN"]
        old = set(dev.open_ports)
        dev.port_results = open_results
        dev.open_ports = [r.number for r in open_results]
        self._rebuild_table()
        newly = sorted(set(dev.open_ports) - old)
        if newly and self.settings.notify_new_port:
            self.statusBar().showMessage(f"{ip}: new open ports {','.join(map(str, newly))}", 8000)
        self.lbl_status.setText(f"Port scan of {ip} complete: {len(dev.open_ports)} open.")

    # ------------------------------------------------------------- table ops
    def _rebuild_table(self):
        self.table.setSortingEnabled(False)
        rows = self._filtered_devices()
        self.table.setRowCount(len(rows))
        for r, d in enumerate(rows):
            status = QTableWidgetItem("🟢 Online" if d.status == "Online" else "🔴 Offline")
            status.setForeground(Qt.green if d.status == "Online" else Qt.red)
            items = [
                status,
                QTableWidgetItem(d.ip),
                QTableWidgetItem(d.mac or "-"),
                QTableWidgetItem(d.hostname),
                QTableWidgetItem(d.vendor),
                QTableWidgetItem(d.ports_display),
                QTableWidgetItem(d.latency_display),
                QTableWidgetItem(d.last_seen.split(" ")[-1]),
            ]
            for c, it in enumerate(items):
                it.setData(Qt.UserRole, d.ip)
                self.table.setItem(r, c, it)
        self.table.setSortingEnabled(True)

    def _filter_matches(self, d: Device, text: str) -> bool:
        if not text:
            return True
        t = text.lower()
        return any(
            t in str(x).lower()
            for x in [d.ip, d.mac, d.hostname, d.vendor, d.ports_display, d.status]
        )

    def _filtered_devices(self) -> list[Device]:
        status = self.cb_status_filter.currentText() if hasattr(self, "cb_status_filter") else "All"
        text = self.search.text().strip() if hasattr(self, "search") else ""
        out = []
        for d in self.devices.values():
            if status != "All" and d.status != status:
                continue
            if not self._filter_matches(d, text):
                continue
            out.append(d)
        return sorted(out, key=lambda d: tuple(map(int, d.ip.split("."))))

    def _apply_filter(self, *_):
        self._rebuild_table()

    def _open_details(self, row: int, col: int):
        ip = self.table.item(row, 1).text()
        dev = self.devices.get(ip)
        if dev:
            self._show_device_details(dev)

    def _show_device_details(self, dev: Device):
        dlg = DeviceDetailsDialog(dev, self)
        dlg.show()

    def _context_menu(self, pos):
        devs = self._selected_devices()
        if not devs:
            return
        menu = QMenu(self)
        act_details = menu.addAction(f"Open details ({devs[0].ip})")
        act_rescan = menu.addAction("Rescan device")
        act_ports = menu.addAction("Port scan (common ports)")
        act_custom = menu.addAction("Port scan (custom ports…)")
        menu.addSeparator()
        act_copy_ip = menu.addAction("Copy IP address")
        act_copy_mac = menu.addAction("Copy MAC address")
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == act_details:
            self._show_device_details(devs[0])
        elif chosen == act_rescan:
            self._rescan_selected()
        elif chosen == act_ports:
            for d in devs:
                self._port_scan_device(d)
        elif chosen == act_custom:
            spec, ok = QInputDialog.getText(
                self, "Custom ports", "Ports (e.g. 80,443,9000-9010):",
                text=self.settings.custom_ports or "80,443,8080")
            if ok:
                ports = parse_port_spec(spec)
                if ports:
                    for d in devs:
                        self._port_scan_device(d, ports)
                else:
                    QMessageBox.warning(self, "Invalid ports", "Could not parse that port specification.")
        elif chosen == act_copy_ip:
            QApplication.clipboard().setText(", ".join(d.ip for d in devs))
        elif chosen == act_copy_mac:
            QApplication.clipboard().setText(", ".join(d.mac for d in devs if d.mac))

    # ---------------------------------------------------------------- export
    def _export_dialog(self, fmt: str = "csv"):
        devices = self._filtered_devices()
        if not devices:
            QMessageBox.information(self, "Export", "Nothing to export. Scan a network first.")
            return
        ext = {"csv": "CSV files (*.csv)", "xlsx": "Excel files (*.xlsx)",
               "json": "JSON files (*.json)", "pdf": "PDF files (*.pdf)", "txt": "Text files (*.txt)"}
        default = f"scan_{datetime.now():%Y%m%d_%H%M%S}.{fmt}"
        path, _ = QFileDialog.getSaveFileName(self, "Export results", default, ext.get(fmt))
        if not path:
            return
        try:
            exporter.export(devices, path, fmt)
            QMessageBox.information(self, "Export", f"Exported {len(devices)} devices to:\n{path}")
        except RuntimeError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
        except Exception as exc:
            QMessageBox.warning(self, "Export failed", f"Could not export: {exc}")

    # ---------------------------------------------------------------- sample
    def _load_sample_data(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                            "sample_data", "sample_scan.json")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except OSError:
            QMessageBox.warning(self, "Sample data", f"Sample file not found:\n{path}")
            return
        self.devices = {d["ip"]: Device.from_dict(d) for d in data.get("devices", [])}
        self.gateway_ip = data.get("gateway", "")
        self._rebuild_table()
        self.topology.set_devices(list(self.devices.values()), self.gateway_ip)
        self._set_info("count", str(len(self.devices)))
        self.lbl_status.setText(f"Loaded sample data: {len(self.devices)} devices.")

    # ---------------------------------------------------------------- history
    def _open_history(self):
        dlg = HistoryDialog(list(self.devices.values()), self)
        dlg.devices_loaded.connect(self._on_history_loaded)
        dlg.exec()

    def _on_history_loaded(self, devices: list):
        self.devices = {d.ip: d for d in devices}
        self._rebuild_table()
        self.topology.set_devices(devices, self.gateway_ip)
        self.lbl_status.setText(f"Loaded historical scan: {len(devices)} devices.")

    def _open_settings(self):
        before = self.settings.theme
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            save_settings(self.settings)
            if self.settings.theme != before:
                self.apply_theme()

    def _about(self):
        QMessageBox.about(
            self, "About LAN Network Scanner",
            "LAN Network Scanner 1.0\n\n"
            "A professional network discovery and port scanning tool for IT "
            "administrators, for use on networks you are authorized to scan.\n\n"
            "Discovery methods: ICMP ping, ARP table, TCP connect.\n"
            "Ports are checked with normal TCP connections only."
        )

    # ---------------------------------------------------------------- close
    def closeEvent(self, event):
        if self.scan_worker and self.scan_worker.isRunning():
            if QMessageBox.question(
                self, "Scan running",
                "A scan is in progress. Stop it and exit?",
                QMessageBox.Yes | QMessageBox.No,
            ) == QMessageBox.Yes:
                self.scan_worker.stop()
                self.scan_worker.wait(3000)
            else:
                event.ignore()
                return
        if self.port_worker and self.port_worker.isRunning():
            self.port_worker.stop()
            self.port_worker.wait(2000)
        event.accept()
