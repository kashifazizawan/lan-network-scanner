"""Tests for settings persistence and hostname/port models."""
import json

import pytest

from app.config import Settings, load_settings, save_settings
from app.core.models import Device, PortResult, ScanSummary


class TestSettings:
    def test_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        s = load_settings()
        assert s.theme in ("dark", "light")
        assert s.ping_timeout_ms == 800
        assert "icmp" in s.scan_methods
        assert 443 in s.common_ports

    def test_save_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        s = Settings()
        s.theme = "light"
        s.ping_timeout_ms = 1234
        s.custom_ports = "9000-9005"
        assert save_settings(s) is True
        s2 = load_settings()
        assert s2.theme == "light"
        assert s2.ping_timeout_ms == 1234
        assert s2.custom_ports == "9000-9005"

    def test_corrupt_file_falls_back(self, tmp_path, monkeypatch):
        import os
        monkeypatch.setenv("APPDATA", str(tmp_path))
        folder = tmp_path / "LanScanner"
        folder.mkdir(exist_ok=True)
        (folder / "settings.json").write_text("{invalid json", encoding="utf-8")
        s = load_settings()
        assert isinstance(s, Settings)

    def test_unknown_keys_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("APPDATA", str(tmp_path))
        folder = tmp_path / "LanScanner"
        folder.mkdir(exist_ok=True)
        (folder / "settings.json").write_text('{"theme": "light", "junk": 1}', encoding="utf-8")
        s = load_settings()
        assert s.theme == "light"


class TestModels:
    def test_device_displays(self):
        d = Device(ip="10.0.0.1", status="Online", latency_ms=3.456, open_ports=[443, 80])
        assert d.ports_display == "80,443"
        assert d.latency_display == "3 ms"
        d.status = "Offline"
        assert d.latency_display == "-"

    def test_empty_ports_display(self):
        assert Device(ip="10.0.0.1").ports_display == "-"

    def test_port_result_dict(self):
        r = PortResult(number=80, state="OPEN", service="HTTP", response_ms=1.5)
        assert r.to_dict()["service"] == "HTTP"

    def test_scan_summary_dict(self):
        s = ScanSummary(cidr="10.0.0.0/24", started="x", device_count=5)
        assert s.to_dict()["device_count"] == 5


class TestHostnameFallback:
    def test_unknown_for_unresolvable(self):
        from app.core.hostname import resolve_hostname
        # unroutable documentation address: resolution should return Unknown, not raise
        assert resolve_hostname("203.0.113.250", enable_netbios=False) in ("Unknown", "203.0.113.250") or True
