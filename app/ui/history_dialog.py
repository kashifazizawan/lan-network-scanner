"""Scan history dialog with compare functionality."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QListWidget,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .. import db
from ..core.models import ScanSummary


class HistoryDialog(QDialog):
    """List previous scans, load one, or compare with the current scan."""

    devices_loaded = Signal(list)  # emits list[Device]

    def __init__(self, current_devices, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scan History")
        self.resize(760, 520)
        self.current_devices = current_devices
        self._scans: list[ScanSummary] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(QLabel("Select a previous scan (newest first):"))
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        self.btn_load = QPushButton("Load Selected Scan")
        self.btn_compare = QPushButton("Compare Selected with Current Scan")
        btn_row.addWidget(self.btn_load)
        btn_row.addWidget(self.btn_compare)
        layout.addLayout(btn_row)

        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(["Change", "Device", "Detail", "Status"])
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.result_table, stretch=1)

        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)

        self.btn_load.clicked.connect(self._load_selected)
        self.btn_compare.clicked.connect(self._compare_selected)
        self._populate()

    def _populate(self):
        self.list_widget.clear()
        self._scans = db.list_scans()
        for s in self._scans:
            self.list_widget.addItem(
                f"#{s.scan_id} — {s.started} — {s.cidr} — {s.device_count} devices, "
                f"{s.open_ports_count} open ports — {s.duration_seconds:.1f}s"
            )

    def _selected_scan(self) -> ScanSummary | None:
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._scans):
            QMessageBox.information(self, "Scan History", "Select a scan from the list first.")
            return None
        return self._scans[row]

    def _load_selected(self):
        s = self._selected_scan()
        if not s:
            return
        devices = db.get_scan_devices(s.scan_id)
        if not devices:
            QMessageBox.information(self, "Scan History", "No device data stored for that scan.")
            return
        self.devices_loaded.emit(devices)
        self.accept()

    def _compare_selected(self):
        s = self._selected_scan()
        if not s:
            return
        old = db.get_scan_devices(s.scan_id)
        diff = db.compare_scans(old, self.current_devices)
        rows = []
        for d in diff["new_devices"]:
            rows.append(("New device", d.ip, f"{d.hostname} / {d.mac or 'no MAC'}", d.status))
        for d in diff["disappeared"]:
            rows.append(("Disappeared", d.ip, f"{d.hostname} (was online)", "Offline"))
        for old_d, new_d in diff["changed_ip"]:
            rows.append(("IP changed", new_d.ip, f"{new_d.mac}: {old_d.ip} → {new_d.ip}", new_d.status))
        for old_d, new_d in diff["changed_mac"]:
            rows.append(("MAC changed", new_d.ip, f"{old_d.mac} → {new_d.mac}", new_d.status))
        for d, opened, closed in diff["port_changes"]:
            detail = ""
            if opened:
                detail += f"newly open: {','.join(map(str, opened))}"
            if closed:
                detail += ("; " if detail else "") + f"now closed: {','.join(map(str, closed))}"
            rows.append(("Ports changed", d.ip, detail, d.status))
        self.result_table.setRowCount(len(rows))
        for r, (a, b, c, dd) in enumerate(rows):
            for col, val in enumerate((a, b, c, dd)):
                self.result_table.setItem(r, col, QTableWidgetItem(str(val)))
        if not rows:
            self.result_table.setRowCount(1)
            for col, val in enumerate(("No differences found", "", "", "")):
                self.result_table.setItem(0, col, QTableWidgetItem(val))
