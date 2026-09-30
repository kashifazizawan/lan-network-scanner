"""Device details dialog (opened by double-clicking a device)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QGroupBox, QLabel, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
)

from ..core.models import Device, PortResult


class DeviceDetailsDialog(QDialog):
    """Detailed window for a single discovered device."""

    def __init__(self, device: Device, parent=None):
        super().__init__(parent)
        self.device = device
        self.setWindowTitle(f"Device Details — {device.ip}")
        self.setMinimumWidth(640)
        self.setModal(False)
        self._build()

    def _build(self):
        d = self.device
        layout = QVBoxLayout(self)

        # Device information
        info = QGroupBox("Device Information")
        form = QFormLayout(info)
        status_txt = "🟢 Online" if d.status == "Online" else "🔴 Offline"
        rows = [
            ("IP Address", d.ip),
            ("MAC Address", d.mac or "Unknown"),
            ("Hostname", d.hostname or "Unknown"),
            ("Vendor", d.vendor or "Unknown"),
            ("Interface", d.interface or "Unknown"),
            ("Latency", d.latency_display),
            ("Status", status_txt),
            ("Discovery methods", ", ".join(d.source_methods) or "-"),
            ("First Seen", d.first_seen),
            ("Last Seen", d.last_seen),
        ]
        for label, value in rows:
            form.addRow(QLabel(label), QLabel(str(value)))

        # Open ports
        ports_box = QGroupBox("Open Ports")
        pv = QVBoxLayout(ports_box)
        tree = QTreeWidget()
        tree.setHeaderLabels(["Port", "Protocol", "State", "Service", "Response"])
        tree.setRootIsDecorated(False)
        self._fill_ports(tree, d.port_results, d.open_ports)
        pv.addWidget(tree)

        # Network information
        net = QGroupBox("Network Information")
        nform = QFormLayout(net)
        nform.addRow(QLabel("Reverse DNS"), QLabel(d.reverse_dns or "Unknown"))
        nform.addRow(QLabel("Gateway relationship"),
                     QLabel("Gateway" if d.reverse_dns == "gateway" or d.hostname == "Gateway"
                            else "Regular host"))
        nform.addRow(QLabel("ARP entry"),
                     QLabel(f"{d.ip} → {d.mac}" if d.mac else "No ARP entry"))

        close = QPushButton("Close")
        close.clicked.connect(self.accept)

        layout.addWidget(info)
        layout.addWidget(ports_box)
        layout.addWidget(net)
        layout.addWidget(close, alignment=Qt.AlignRight)

    @staticmethod
    def _fill_ports(tree: QTreeWidget, results: list[PortResult], open_ports: list[int]):
        if results:
            for r in results:
                if r.state != "OPEN":
                    continue
                DeviceDetailsDialog._add_port_row(tree, r.number, r.protocol, r.state, r.service, r.response_ms)
        for p in open_ports:
            if not any(r.number == p for r in results):
                DeviceDetailsDialog._add_port_row(tree, p, "TCP", "OPEN", "Unknown", 0)
        if tree.topLevelItemCount() == 0:
            QTreeWidgetItem(tree, ["No open ports detected", "", "", "", ""])

    @staticmethod
    def _add_port_row(tree, number, protocol, state, service, ms):
        QTreeWidgetItem(tree, [str(number), protocol, state, service, f"{ms:.1f} ms" if ms else "-"])
