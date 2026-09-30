"""Unit tests for network utilities (CIDR parsing, adapter helpers)."""
import ipaddress

import pytest

from app.core.network_utils import (
    cidr_of,
    expand_cidr,
    get_local_ip,
    validate_cidr,
    friendly_error,
)


class TestValidateCidr:
    def test_valid_cidr(self):
        net = validate_cidr("192.168.1.0/24")
        assert net == ipaddress.ip_network("192.168.1.0/24")

    def test_valid_cidr_hosts_set(self):
        # host bits set should be tolerated (strict=False)
        assert validate_cidr("192.168.1.10/24") == ipaddress.ip_network("192.168.1.0/24")

    def test_private_ranges(self):
        for cidr in ["192.168.1.0/24", "10.0.0.0/24", "172.16.1.0/24"]:
            assert validate_cidr(cidr)

    def test_invalid_cidr(self):
        for bad in ["", "  ", "abc", "999.999.999.999/24", "10.0.0.0/33", "10.0.0.0/-1"]:
            with pytest.raises(ValueError):
                validate_cidr(bad)

    def test_error_message_is_friendly(self):
        with pytest.raises(ValueError, match="not a valid network range"):
            validate_cidr("banana")

    def test_bare_ip_treated_as_network(self):
        assert validate_cidr("10.0.0.5") == ipaddress.ip_network("10.0.0.5/32")


class TestExpandCidr:
    def test_24_hosts(self):
        hosts = expand_cidr("192.168.1.0/24")
        assert len(hosts) == 254
        assert "192.168.1.1" in hosts
        assert "192.168.1.0" not in hosts
        assert "192.168.1.255" not in hosts

    def test_32(self):
        assert expand_cidr("10.0.0.7/32") == ["10.0.0.7"]

    def test_31(self):
        assert set(expand_cidr("10.0.0.0/31")) == {"10.0.0.0", "10.0.0.1"}

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            expand_cidr("nope/24")


class TestCidrOf:
    def test_class_c(self):
        assert cidr_of("192.168.1.10", "255.255.255.0") == "192.168.1.0/24"

    def test_invalid_mask_fallback(self):
        assert cidr_of("192.168.1.10", "bad") == "192.168.1.0/24"


class TestLocalIp:
    def test_returns_something(self):
        ip = get_local_ip()
        assert ip
        ipaddress.ip_address(ip)  # does not raise


class TestFriendlyError:
    def test_permission(self):
        assert "Administrator" in friendly_error(PermissionError("denied"))

    def test_timeout(self):
        assert "timed out" in friendly_error(TimeoutError())

    def test_generic(self):
        assert "ValueError" in friendly_error(ValueError("x"))
