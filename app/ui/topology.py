"""Network topology / map view (gateway at top, devices as nodes)."""
from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsScene, QGraphicsTextItem,
    QGraphicsView, QMenu,
)
from PySide6.QtGui import QBrush, QColor, QPen

from ..core.models import Device
from .theme import ONLINE_COLOR, OFFLINE_COLOR


class _Node(QGraphicsEllipseItem):
    def __init__(self, device: Device, x: float, y: float, r: float = 26):
        super().__init__(x - r, y - r, r * 2, r * 2)
        self.device = device
        color = QColor(ONLINE_COLOR) if device.status == "Online" else QColor(OFFLINE_COLOR)
        self.setBrush(QBrush(color))
        self.setPen(QPen(QColor("#1e2127"), 2))
        self.setAcceptHoverEvents(True)
        self.setToolTip(
            f"{device.ip}\n{device.hostname}\n{device.mac or 'MAC unknown'}\n"
            f"{device.vendor} · {device.latency_display}"
        )


class TopologyView(QGraphicsView):
    """Simple gateway -> devices tree map. Click a node to open details."""

    device_selected = Signal(object)  # Device

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(self.renderHints().Antialiasing, True) if hasattr(self, "renderHints") else None
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.devices: list[Device] = []

    def set_devices(self, devices: list[Device], gateway_ip: str = ""):
        self.devices = devices
        scene = self.scene()
        scene.clear()
        if not devices:
            scene.addText("No devices discovered yet. Run a scan to build the network map.")
            return

        # Gateway node at top
        gw_x, gw_y = 0, -160
        gw_color = QColor(ONLINE_COLOR if not gateway_ip or any(d.ip == gateway_ip for d in devices) else OFFLINE_COLOR)
        gw = scene.addEllipse(gw_x - 34, gw_y - 22, 68, 44)
        gw.setBrush(QBrush(QColor("#2b6cb0")))
        gw.setToolTip("Gateway / Internet uplink")
        label = scene.addText("Gateway", self.font())
        label.setPos(gw_x - label.boundingRect().width() / 2, gw_y + 24)

        # Devices laid out in a grid below
        cols = max(4, int(len(devices) ** 0.5))
        for i, dev in enumerate(devices):
            col = i % cols
            row = i // cols
            x = (col - (cols - 1) / 2) * 90
            y = 40 + row * 80
            # line gateway -> device
            pen = QPen(QColor(OFFLINE_COLOR if dev.status != "Online" else ONLINE_COLOR), 1.4)
            scene.addLine(gw_x, gw_y + 22, x, y - 26, pen)
            node = _Node(dev, x, y)
            node.device_clicked = None
            scene.addItem(node)
            text = scene.addText(dev.hostname if dev.hostname not in ("Unknown", "") else dev.ip, self.font())
            if text.boundingRect().width() > 82:
                t = text.toPlainText()[:10] + "…"
                text.setPlainText(t)
            text.setPos(x - text.boundingRect().width() / 2, y + 28)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, _Node):
            self.device_selected.emit(item.device)
            return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, _Node):
            menu = QMenu(self)
            act = menu.addAction(f"Open details for {item.device.ip}")
            if menu.exec(event.globalPos()) == act:
                self.device_selected.emit(item.device)
            return
        super().contextMenuEvent(event)
