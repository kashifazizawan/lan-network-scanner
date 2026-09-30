"""Tests for OUI (MAC vendor) lookup and ARP parsing."""
from app.core.arp import normalize_mac
from app.core.oui import lookup_vendor, normalize, load_external_oui


class TestNormalizeMac:
    def test_colon_to_dash(self):
        assert normalize_mac("aa:bb:cc:dd:ee:ff") == "AA-BB-CC-DD-EE-FF"

    def test_already_dash(self):
        assert normalize_mac("AA-BB-CC-DD-EE-FF") == "AA-BB-CC-DD-EE-FF"

    def test_invalid(self):
        assert normalize_mac("not-a-mac") == ""
        assert normalize_mac("aa:bb") == ""
        assert normalize_mac("") == ""


class TestLookupVendor:
    def test_dell(self):
        assert lookup_vendor("00:14:22:AA:BB:CC") == "Dell Inc."

    def test_cisco(self):
        assert lookup_vendor("00-00-0C-11-22-33") == "Cisco Systems"

    def test_raspberry_pi(self):
        assert lookup_vendor("B8:27:EB:12:34:56") == "Raspberry Pi Foundation"

    def test_unknown(self):
        assert lookup_vendor("FF-EE-DD-11-22-33") == "Unknown"
        assert lookup_vendor("") == "Unknown"
        assert lookup_vendor("short") == "Unknown"

    def test_intel(self):
        assert "Intel" in lookup_vendor("00-1C-BF-12-34-56")


class TestExternalOui:
    def test_load(self, tmp_path):
        p = tmp_path / "oui.txt"
        p.write_text("DE-AD-BE   (hex)\t\tTestVendor Inc.\n", encoding="utf-8")
        assert load_external_oui(str(p)) == 1
        assert lookup_vendor("DE:AD:BE:00:00:01") == "TestVendor Inc."

    def test_missing_file(self):
        assert load_external_oui("does/not/exist.txt") == 0
