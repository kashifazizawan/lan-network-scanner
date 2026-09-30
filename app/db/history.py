"""Scan history storage (SQLite) and scan-to-scan comparison."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime

from ..core.models import Device, ScanSummary

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cidr TEXT NOT NULL,
    started TEXT NOT NULL,
    finished TEXT NOT NULL,
    device_count INTEGER NOT NULL,
    duration_seconds REAL NOT NULL,
    open_ports_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    ip TEXT NOT NULL,
    mac TEXT,
    hostname TEXT,
    vendor TEXT,
    status TEXT,
    latency_ms REAL,
    open_ports TEXT,
    ports_detail TEXT,
    interface TEXT,
    first_seen TEXT,
    last_seen TEXT,
    sources TEXT
);
CREATE INDEX IF NOT EXISTS idx_devices_scan ON devices(scan_id);
"""


def _db_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.local/share")
    folder = os.path.join(base, "LanScanner")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "history.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.executescript(SCHEMA)
    return conn


def save_scan(summary: ScanSummary, devices: list[Device]) -> int:
    """Persist a completed scan; returns the scan id."""
    conn = _connect()
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO scans (cidr, started, finished, device_count, duration_seconds, open_ports_count) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    summary.cidr,
                    summary.started,
                    summary.finished or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    summary.device_count or len(devices),
                    summary.duration_seconds,
                    sum(len(d.open_ports) for d in devices),
                ),
            )
            scan_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO devices (scan_id, ip, mac, hostname, vendor, status, latency_ms, "
                "open_ports, ports_detail, interface, first_seen, last_seen, sources) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        scan_id,
                        d.ip,
                        d.mac,
                        d.hostname,
                        d.vendor,
                        d.status,
                        d.latency_ms,
                        json.dumps(d.open_ports),
                        json.dumps([p.to_dict() for p in d.port_results]),
                        d.interface,
                        d.first_seen,
                        d.last_seen,
                        json.dumps(d.source_methods),
                    )
                    for d in devices
                ],
            )
        return scan_id
    finally:
        conn.close()


def list_scans(limit: int = 100) -> list[ScanSummary]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, cidr, started, finished, device_count, duration_seconds, open_ports_count "
            "FROM scans ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        ScanSummary(
            scan_id=r[0],
            cidr=r[1],
            started=r[2],
            finished=r[3],
            device_count=r[4],
            duration_seconds=r[5],
            open_ports_count=r[6],
        )
        for r in rows
    ]


def get_scan_devices(scan_id: int) -> list[Device]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT ip, mac, hostname, vendor, status, latency_ms, open_ports, ports_detail, "
            "interface, first_seen, last_seen, sources FROM devices WHERE scan_id = ?",
            (scan_id,),
        ).fetchall()
    finally:
        conn.close()
    devices = []
    for r in rows:
        d = Device(
            ip=r[0],
            mac=r[1] or "",
            hostname=r[2] or "Unknown",
            vendor=r[3] or "Unknown",
            status=r[4] or "Offline",
            latency_ms=r[5] or 0.0,
            open_ports=json.loads(r[6]) if r[6] else [],
            interface=r[8] or "",
            first_seen=r[9] or "",
            last_seen=r[10] or "",
            source_methods=json.loads(r[11]) if r[11] else [],
        )
        detail = json.loads(r[7]) if r[7] else []
        from ..core.models import PortResult

        d.port_results = [
            PortResult(p["port"], p["state"], p.get("protocol", "TCP"),
                       p.get("service", "Unknown"), p.get("response_ms", 0.0))
            for p in detail
        ]
        devices.append(d)
    return devices


def delete_scan(scan_id: int) -> None:
    conn = _connect()
    try:
        with conn:
            conn.execute("DELETE FROM devices WHERE scan_id = ?", (scan_id,))
            conn.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
    finally:
        conn.close()


def compare_scans(old: list[Device], new: list[Device]) -> dict:
    """Compare two scans and categorize differences."""
    old_by_ip = {d.ip: d for d in old}
    new_by_ip = {d.ip: d for d in new}
    old_by_mac = {d.mac: d for d in old if d.mac}
    new_by_mac = {d.mac: d for d in new if d.mac}

    new_devices = [new_by_ip[ip] for ip in new_by_ip if ip not in old_by_ip]
    disappeared = [old_by_ip[ip] for ip in old_by_ip if ip not in new_by_ip]

    changed_ip: list[tuple[Device, Device]] = []  # (old, new) same MAC new IP
    for mac, nd in new_by_mac.items():
        od = old_by_mac.get(mac)
        if od and od.ip != nd.ip:
            changed_ip.append((od, nd))

    changed_mac: list[tuple[Device, Device]] = []  # (old, new) same IP new MAC
    for ip, nd in new_by_ip.items():
        od = old_by_ip.get(ip)
        if od and od.mac and nd.mac and od.mac != nd.mac:
            changed_mac.append((od, nd))

    port_changes: list[tuple[Device, list[int], list[int]]] = []  # (new, opened, closed)
    for ip, nd in new_by_ip.items():
        od = old_by_ip.get(ip)
        if not od:
            continue
        opened = sorted(set(nd.open_ports) - set(od.open_ports))
        closed = sorted(set(od.open_ports) - set(nd.open_ports))
        if opened or closed:
            port_changes.append((nd, opened, closed))

    return {
        "new_devices": new_devices,
        "disappeared": disappeared,
        "changed_ip": changed_ip,
        "changed_mac": changed_mac,
        "port_changes": port_changes,
    }
