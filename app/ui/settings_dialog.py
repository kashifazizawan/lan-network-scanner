"""Settings dialog."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
)

from ..config import Settings
from ..core.ports import DEFAULT_COMMON_PORTS


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(520)
        self.settings = settings
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        # --- Scanning ---
        scan_box = QGroupBox("Scanning")
        scan_form = QFormLayout(scan_box)
        self.ping_timeout = QDoubleSpinBox()
        self.ping_timeout.setRange(100, 5000)
        self.ping_timeout.setSuffix(" ms")
        self.ping_timeout.setSingleStep(100)
        scan_form.addRow("Ping timeout", self.ping_timeout)

        self.max_concurrent = QSpinBox_int(1, 500)
        scan_form.addRow("Max concurrent scans", self.max_concurrent)

        self.port_timeout = QDoubleSpinBox()
        self.port_timeout.setRange(0.2, 10.0)
        self.port_timeout.setSuffix(" s")
        self.port_timeout.setSingleStep(0.1)
        scan_form.addRow("Port scan timeout", self.port_timeout)

        self.scan_method = QComboBox()
        self.scan_method.addItems(["ICMP + ARP + TCP", "ICMP only", "ARP only", "TCP only", "ICMP + ARP"])
        scan_form.addRow("Scan method", self.scan_method)

        self.dns_lookup = QCheckBox("Enable DNS / hostname lookup")
        scan_form.addRow(self.dns_lookup)
        self.netbios_lookup = QCheckBox("Enable NetBIOS lookup (Windows)")
        scan_form.addRow(self.netbios_lookup)
        self.ports_on_discovery = QCheckBox("Scan common ports during discovery (slower)")
        scan_form.addRow(self.ports_on_discovery)

        # --- Ports ---
        port_box = QGroupBox("Ports")
        port_form = QFormLayout(port_box)
        self.common_ports = QLineEdit()
        self.common_ports.setPlaceholderText("e.g. 21,22,23,25,53,80,110,135,139,143,443,445,3389,5900,8080")
        port_form.addRow("Common ports", self.common_ports)
        self.custom_ports = QLineEdit()
        self.custom_ports.setPlaceholderText("e.g. 8080,9000-9010")
        port_form.addRow("Custom ports", self.custom_ports)

        # --- Appearance & notifications ---
        app_box = QGroupBox("Appearance & Notifications")
        app_form = QFormLayout(app_box)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        app_form.addRow("Theme", self.theme_combo)
        self.compact = QCheckBox("Compact table rows")
        app_form.addRow(self.compact)
        self.notify_new = QCheckBox("Notify: new device detected")
        self.notify_gone = QCheckBox("Notify: device disappeared")
        self.notify_port = QCheckBox("Notify: new open port")
        self.notify_port_closed = QCheckBox("Notify: previously open port closed")
        self.notify_mac_ip = QCheckBox("Notify: IP/MAC relationship changed")
        app_form.addRow(self.notify_new)
        app_form.addRow(self.notify_gone)
        app_form.addRow(self.notify_port)
        app_form.addRow(self.notify_port_closed)
        app_form.addRow(self.notify_mac_ip)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(scan_box)
        layout.addWidget(port_box)
        layout.addWidget(app_box)
        layout.addWidget(buttons)

    def _load(self):
        s = self.settings
        self.ping_timeout.setValue(s.ping_timeout_ms)
        self.max_concurrent.setValue(s.max_concurrent)
        self.port_timeout.setValue(s.port_timeout_s)
        methods = list(s.scan_methods)
        method_map = {
            "ICMP + ARP + TCP": ["icmp", "arp", "tcp"],
            "ICMP only": ["icmp"],
            "ARP only": ["arp"],
            "TCP only": ["tcp"],
            "ICMP + ARP": ["icmp", "arp"],
        }
        for name, m in method_map.items():
            if m == methods:
                self.scan_method.setCurrentText(name)
                break
        self.dns_lookup.setChecked(s.dns_lookup)
        self.netbios_lookup.setChecked(s.netbios_lookup)
        self.ports_on_discovery.setChecked(s.scan_ports_on_discovery)
        self.common_ports.setText(",".join(map(str, s.common_ports)))
        self.custom_ports.setText(s.custom_ports)
        self.theme_combo.setCurrentText(s.theme)
        self.compact.setChecked(s.compact_table)
        self.notify_new.setChecked(s.notify_new_device)
        self.notify_gone.setChecked(s.notify_device_gone)
        self.notify_port.setChecked(s.notify_new_port)
        self.notify_port_closed.setChecked(s.notify_port_closed)
        self.notify_mac_ip.setChecked(s.notify_mac_ip_change)

    def accept(self):
        s = self.settings
        s.ping_timeout_ms = int(self.ping_timeout.value())
        s.max_concurrent = self.max_concurrent.value()
        s.port_timeout_s = self.port_timeout.value()
        method_map = {
            "ICMP + ARP + TCP": ["icmp", "arp", "tcp"],
            "ICMP only": ["icmp"],
            "ARP only": ["arp"],
            "TCP only": ["tcp"],
            "ICMP + ARP": ["icmp", "arp"],
        }
        s.scan_methods = method_map[self.scan_method.currentText()]
        s.dns_lookup = self.dns_lookup.isChecked()
        s.netbios_lookup = self.netbios_lookup.isChecked()
        s.scan_ports_on_discovery = self.ports_on_discovery.isChecked()
        from ..core.ports import parse_port_spec
        common = parse_port_spec(self.common_ports.text())
        s.common_ports = common if common else list(DEFAULT_COMMON_PORTS)
        s.custom_ports = self.custom_ports.text()
        s.theme = self.theme_combo.currentText()
        s.compact_table = self.compact.isChecked()
        s.notify_new_device = self.notify_new.isChecked()
        s.notify_device_gone = self.notify_gone.isChecked()
        s.notify_port = self.notify_port.isChecked()
        s.notify_port_closed = self.notify_port_closed.isChecked()
        s.notify_mac_ip_change = self.notify_mac_ip.isChecked()
        super().accept()


from PySide6.QtWidgets import QSpinBox  # noqa: E402


def QSpinBox_int(lo, hi):
    sb = QSpinBox()
    sb.setRange(lo, hi)
    return sb
