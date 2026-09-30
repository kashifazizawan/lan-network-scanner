"""Tests for scan history storage and comparison logic."""
import json
import os

import pytest

from app.core.models import Device, ScanSummary
from app import db
from app.db import history


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    p = str(tmp_path / "history.db")
    monkeypatch.setattr(history, "_db_path", lambda: p)
    yield


def mk_devices():
    return [
        Device(ip="192.168.1.1", mac="AA-BB-CC-DD-EE-FF", hostname="Router",
               vendor="TP-Link", status="Online", open_ports=[80]),
        Device(ip="192.168.1.20", mac="11-22-33-44-55-66", hostname="PC",
               vendor="Dell", status="Online", open_ports=[135, 445]),
    ]


class TestSaveAndList:
    def test_save_and_list(self):
        summary = ScanSummary(cidr="192.168.1.0/24", started="2026-01-01 10:00:00",
                              finished="2026-01-01 10:00:10", device_count=2,
                              duration_seconds=10.0, open_ports_count=3)
        scan_id = db.save_scan(summary, mk_devices())
        scans = db.list_scans()
        assert len(scans) == 1
        assert scans[0].scan_id == scan_id
        assert scans[0].cidr == "192.168.1.0/24"
        assert scans[0].device_count == 2
        assert scans[0].open_ports_count == 3

    def test_get_scan_devices(self):
        summary = ScanSummary(cidr="192.168.1.0/24", started="x", finished="y",
                              device_count=2, duration_seconds=1, open_ports_count=0)
        scan_id = db.save_scan(summary, mk_devices())
        devs = db.get_scan_devices(scan_id)
        assert {d.ip for d in devs} == {"192.168.1.1", "192.168.1.20"}
        by_ip = {d.ip: d for d in devs}
        assert by_ip["192.168.1.1"].mac == "AA-BB-CC-DD-EE-FF"
        assert by_ip["192.168.1.20"].open_ports == [135, 445]

    def test_delete_scan(self):
        summary = ScanSummary(cidr="c", started="s", finished="f", device_count=0,
                              duration_seconds=0, open_ports_count=0)
        scan_id = db.save_scan(summary, mk_devices())
        db.delete_scan(scan_id)
        assert db.list_scans() == []
        assert db.get_scan_devices(scan_id) == []


class TestCompare:
    def test_compare_scans(self):
        old = [
            Device(ip="192.168.1.1", mac="AA-AA", status="Online", open_ports=[80]),
            Device(ip="192.168.1.20", mac="BB-BB", status="Online", open_ports=[135, 445]),
            Device(ip="192.168.1.99", mac="CC-CC", status="Online", open_ports=[]),
        ]
        new = [
            Device(ip="192.168.1.1", mac="AA-AA", status="Online", open_ports=[80, 443]),
            Device(ip="192.168.1.20", mac="BB-BB", status="Online", open_ports=[135]),
            Device(ip="192.168.1.30", mac="DD-DD", status="Online", open_ports=[]),
            Device(ip="192.168.1.40", mac="CC-CC", status="Online", open_ports=[]),
        ]
        diff = db.compare_scans(old, new)
        # new by IP: .30 (brand new) and .40 (CC-CC moved from .99)
        assert [d.ip for d in diff["new_devices"]] == ["192.168.1.30", "192.168.1.40"]
        assert [d.ip for d in diff["disappeared"]] == ["192.168.1.99"]
        # CC-CC moved from .99 to .40 -> also flagged as an IP change
        assert [(o.ip, n.ip) for o, n in diff["changed_ip"]] == [("192.168.1.99", "192.168.1.40")]
        assert diff["changed_mac"] == []
        changes = {d.ip: (opened, closed) for d, opened, closed in diff["port_changes"]}
        assert changes["192.168.1.1"] == ([443], [])
        assert changes["192.168.1.20"] == ([], [445])

    def test_compare_mac_change(self):
        old = [Device(ip="10.0.0.1", mac="AA-AA", status="Online")]
        new = [Device(ip="10.0.0.1", mac="BB-BB", status="Online")]
        diff = db.compare_scans(old, new)
        assert len(diff["changed_mac"]) == 1
        assert diff["new_devices"] == []
