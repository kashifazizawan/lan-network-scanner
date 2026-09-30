"""Tests for the port scanner logic (no live network needed)."""
import pytest

from app.core.ports import (
    DEFAULT_COMMON_PORTS,
    SERVICE_MAP,
    PortResult,
    parse_port_spec,
    scan_tcp_port,
)


class TestParsePortSpec:
    def test_simple_list(self):
        assert parse_port_spec("80,443,22") == [22, 80, 443]

    def test_range(self):
        assert parse_port_spec("100-104") == [100, 101, 102, 103, 104]

    def test_mixed(self):
        assert parse_port_spec("80, 100-102, 3389") == [80, 100, 101, 102, 3389]

    def test_dedup_and_sort(self):
        assert parse_port_spec("443,80,443") == [80, 443]

    def test_invalid_ignored(self):
        assert parse_port_spec("abc, 0, 70000, , 80") == [80]

    def test_empty(self):
        assert parse_port_spec("") == []

    def test_out_of_order_range_ignored(self):
        assert parse_port_spec("100-50") == []


class TestServiceMap:
    def test_common_ports_have_services(self):
        for p in DEFAULT_COMMON_PORTS:
            assert p in SERVICE_MAP, f"port {p} missing a service name"

    def test_known_mappings(self):
        assert SERVICE_MAP[80] == "HTTP"
        assert SERVICE_MAP[443] == "HTTPS"
        assert SERVICE_MAP[3389] == "RDP"
        assert SERVICE_MAP[5900] == "VNC"


class TestScanTcpPort:
    def test_closed_port(self):
        # port 1 on loopback: connection refused -> CLOSED (loopback is instant)
        r = scan_tcp_port("127.0.0.1", 1, timeout=0.3)
        assert r.state in ("CLOSED", "FILTERED")
        assert r.protocol == "TCP"

    def test_result_fields(self):
        r = PortResult(number=80, state="OPEN", service="HTTP")
        d = r.to_dict()
        assert d["port"] == 80
        assert d["service"] == "HTTP"
        assert d["response_ms"] == 0.0
