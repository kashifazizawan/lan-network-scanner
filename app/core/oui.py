"""MAC vendor (OUI) lookup.

Includes a small embedded table of common vendors; a full IEEE OUI file
(oui.txt) can be dropped next to the config to extend it.
"""
from __future__ import annotations

import os

# Common OUI prefixes (first 3 octets). Extend by loading an IEEE oui.txt.
EMBEDDED_OUI: dict[str, str] = {
    "00-00-0C": "Cisco Systems",
    "00-1A-A1": "Cisco Systems",
    "00-1B-0C": "Cisco Systems",
    "00-23-EB": "Cisco Systems",
    "00-25-45": "Cisco Systems",
    "58-97-1E": "Cisco Systems",
    "00-50-56": "VMware",
    "00-0C-29": "VMware",
    "00-05-69": "VMware",
    "00-1C-14": "VMware",
    "00-1C-42": "Parallels",
    "08-00-27": "Oracle VirtualBox",
    "0A-00-27": "Oracle VirtualBox",
    "00-15-5D": "Microsoft Hyper-V",
    "00-03-FF": "Microsoft",
    "00-0C-A3": "Dell Inc.",
    "00-14-22": "Dell Inc.",
    "00-1C-23": "Dell Inc.",
    "00-21-70": "Dell Inc.",
    "00-23-AE": "Dell Inc.",
    "00-24-E8": "Dell Inc.",
    "00-E0-4C": "Realtek",
    "00-1B-21": "D-Link",
    "00-05-5D": "D-Link",
    "14-CC-20": "D-Link",
    "00-14-6C": "Netgear",
    "00-24-B2": "Netgear",
    "9C-3D-CF": "Netgear",
    "00-1D-7E": "Cisco-Linksys",
    "00-23-69": "Cisco-Linksys",
    "C0-56-A3": "Cisco-Linksys",
    "00-25-9C": "Cisco-Linksys",
    "54-A0-50": "TP-Link",
    "50-C7-BF": "TP-Link",
    "14-CC-20A": "TP-Link",
    "A4-2B-B0": "TP-Link",
    "D8-07-B6": "TP-Link",
    "00-0E-2A": "Fujitsu",
    "00-11-25": "Fujitsu",
    "00-0B-A0": "Elitegroup",
    "00-1A-92": "Intel Corporate",
    "00-1B-21X": "Intel Corporate",
    "00-1C-BF": "Intel Corporate",
    "00-1D-E0": "Intel Corporate",
    "00-21-5C": "Intel Corporate",
    "00-22-FA": "Intel Corporate",
    "00-24-D6": "Intel Corporate",
    "3C-A9-F4": "Intel Corporate",
    "8C-EC-4B": "Intel Corporate",
    "F8-34-41": "Intel Corporate",
    "00-0B-DB": "Intel Corporate",
    "00-02-B3": "Intel Corporate",
    "00-04-23": "Intel Corporate",
    "00-07-E9": "Intel Corporate",
    "00-0D-56": "Intel Corporate",
    "00-0D-87": "Intel Corporate",
    "3C-D9-2B": "Hewlett Packard",
    "00-1F-29": "Hewlett Packard",
    "00-21-5AX": "Hewlett Packard",
    "00-23-7D": "Hewlett Packard",
    "10-1F-74": "Hewlett Packard",
    "28-80-88": "Hewlett Packard",
    "00-26-99": "Samsung Electronics",
    "14-49-E0": "Samsung Electronics",
    "5C-3A-16": "Samsung Electronics",
    "78-47-1D": "Raspberry Pi Trading",
    "B8-27-EB": "Raspberry Pi Foundation",
    "DC-A6-32": "Raspberry Pi Trading",
    "E4-5F-01": "Raspberry Pi Trading",
    "00-1E-58": "Apple",
    "AC-DE-48": "Apple",
    "F0-18-98": "Apple",
    "A4-83-E7": "Apple",
    "3C-07-54": "Apple",
    "D0-03-4B": "Apple",
    "00-1A-11": "Google",
    "F4-F5-D8": "Google",
    "00-0D-3A": "Microsoft Azure",
    "52-54-00": "QEMU/KVM",
    "08-00-06": "XiJiao (legacy)",
    "00-50-F2": "Microsoft",
    "00-16-EA": "Wistron",
    "00-1E-C9": "Quanta",
    "00-21-86": "Pegatron",
    "00-24-8C": "Micro-Star Intl",
    "D8-CB-8A": "Unknown",
    "00-1B-44": "Realtek",
    "00-60-2F": "SUN",
    "00-16-3E": "Xen",
    "10-00-00": "Unknown",
    "00-26-BB": "ASUSTek",
    "04-D9-F5": "ASUSTek",
    "2C-4D-54": "ASUSTek",
    "00-1D-60": "Cisco",
    "00-40-96": "Cisco",
    "B8-27-EBX": "Raspberry Pi",
}

_external: dict[str, str] = {}


def load_external_oui(path: str) -> int:
    """Load an IEEE oui.txt file (lines like 'AA-BB-CC   (hex)\tVendor Name')."""
    count = 0
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                m = line.split("(hex)")
                if len(m) == 2:
                    oui = m[0].strip().upper().replace(":", "-")
                    vendor = m[1].strip()
                    if re_valid_oui(oui):
                        _external[oui] = vendor
                        count += 1
    except OSError:
        pass
    return count


def re_valid_oui(oui: str) -> bool:
    return len(oui) == 8 and all(
        c in "0123456789ABCDEF-" for c in oui
    )


def normalize(mac: str) -> str:
    return mac.strip().replace(":", "-").upper()


def lookup_vendor(mac: str) -> str:
    """Return the vendor name for a MAC address, or 'Unknown'."""
    mac = normalize(mac)
    if len(mac) < 8:
        return "Unknown"
    oui = mac[:8]
    if oui in _external:
        return _external[oui]
    return EMBEDDED_OUI.get(oui, "Unknown")
