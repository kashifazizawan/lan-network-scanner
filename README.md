# LAN Network Scanner (Windows Desktop)

A professional Windows desktop LAN scanner for IT administrators and network
engineers: automatic device discovery, port scanning, vendor identification,
scan history with diffing, network map, and multi-format export.

> **Intended use:** authorized network administration, troubleshooting and
> asset discovery on networks you are permitted to scan. The app uses only
> normal ICMP pings, OS ARP tables and plain TCP connection checks — no
> stealth scanning, no credential attacks, no vulnerability exploitation.

---

## Features

- **Device discovery** — ICMP ping sweep, ARP discovery, TCP connect probing
- **Device details** — IP, MAC, hostname (DNS/NetBIOS), vendor (MAC OUI),
  status, latency, open ports, first seen / last seen
- **Port scanner** — common ports, custom port lists and ranges, with service
  identification (HTTP, HTTPS, RDP, SMB, VNC, …)
- **Responsive GUI** — all scanning runs in background threads; the window
  never freezes. Start / Stop / Pause / Resume / Rescan controls.
- **Sortable, filterable results table** — global search across IP, MAC,
  hostname, vendor, ports and status
- **Network map** — gateway-to-devices topology view; click a node for details
- **Scan history** — SQLite storage; compare the current scan with any
  previous scan (new devices, disappearances, IP/MAC/ports changes)
- **Export** — CSV, Excel XLSX, JSON, PDF, TXT
- **Notifications** — new device, device gone, new/closed ports, IP/MAC changes
- **Dark / light themes**, settings persisted, full logging
- **Sample data mode** — try the UI with `--sample` without scanning anything

## Screens of the app

1. **Devices tab** — toolbar (interface picker, CIDR input, Scan/Stop/Pause,
   Refresh, Settings), network info panel (local IP, mask, gateway, CIDR,
   interface, device count, progress), search + status filter, results table.
2. **Network Map tab** — topology of gateway and discovered devices.
3. **Scan > Scan History** — previous scans and comparisons.
4. **Double-click a device** — full details window with open ports and ARP info.

## Requirements

- **Runtime:** Windows 10 / 11 (64-bit) — no Python needed if you use the
  built `.exe`. Linux/macOS work for development.
- **Development:** Python 3.10+

## Quick start (from source)

```powershell
python -m pip install -r requirements.txt
python main.py            # normal launch
python main.py --sample   # load sample data instead of scanning
```

## Run the tests

```powershell
python -m pip install pytest
python -m pytest tests -v
```

Tests cover CIDR validation, port-spec parsing, service mapping, MAC/OUI
lookup, ARP parsing helpers, export (CSV/JSON/TXT/XLSX), scan-history storage
and scan-comparison diffing.

## Building the standalone .exe (Windows)

Option A — one command:

```powershell
.\build_windows.ps1
```

Option B — manual:

```powershell
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --clean --noconfirm LanScanner.spec
```

Result: `dist\LanScanner.exe` — a single file you can copy to any
Windows 10/11 64-bit machine. To add an icon, drop `assets\icon.ico` in place
before building (it is picked up automatically).

## Project structure

```text
lanscanner/
├── main.py                  # entry point
├── app/
│   ├── config.py            # JSON-backed settings
│   ├── logger.py           # logging + global exception hook
│   ├── core/
│   │   ├── models.py       # Device / PortResult / ScanSummary
│   │   ├── network_utils.py# CIDR validation, adapters, gateway
│   │   ├── discovery.py    # discovery engine (ping/ARP/TCP, pause/stop)
│   │   ├── ports.py        # TCP connect port scanner + service map
│   │   ├── hostname.py     # reverse DNS + NetBIOS
│   │   ├── arp.py          # ARP table parsing
│   │   └── oui.py          # MAC vendor lookup
│   ├── db/
│   │   └── history.py      # SQLite scan history + comparison
│   ├── export/
│   │   └── exporter.py     # CSV / XLSX / JSON / PDF / TXT
│   └── ui/
│       ├── main_window.py  # dashboard, table, toolbar, menus
│       ├── workers.py      # QThread scan/port/rescan workers
│       ├── device_details.py
│       ├── settings_dialog.py
│       ├── history_dialog.py
│       ├── topology.py     # network map view
│       └── theme.py       # dark/light QSS
├── tests/                  # pytest unit tests
├── sample_data/sample_scan.json
├── LanScanner.spec         # PyInstaller spec
├── build_windows.ps1       # one-command Windows build
└── requirements.txt
```

## Configuration

Settings are stored in `%APPDATA%\LanScanner\settings.json`, scan history in
`%APPDATA%\LanScanner\history.db`, logs in `%APPDATA%\LanScanner\lanscanner_YYYYMMDD.log`.
To extend the vendor database, place an IEEE `oui.txt` next to `main.py` —
or drop it next to the app and load it via `app.core.oui.load_external_oui(path)`.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+S | Start scan |
| Esc | Stop scan |
| Ctrl+P | Pause / resume scan |
| Ctrl+R | Rescan selected device |
| Ctrl+F | Focus search box |
| Ctrl+E | Export (CSV) |
| Ctrl+D | Load sample data |
| Ctrl+T | Toggle dark/light theme |
| Ctrl+H | Scan history |
| F5 | Refresh adapters |

## Safety design

- The target range is shown and must be **explicitly confirmed** before every scan.
- No stealth/SYN scanning; TCP connect checks only.
- No password guessing, no exploits.
- Concurrency is capped (default 100 threads) to avoid disrupting the network.
- MAC vendor lookup is offline; no scan data leaves the machine.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Invalid network range" warning | Use CIDR form like `192.168.1.0/24` |
| No adapters detected | Check that your Ethernet/Wi-Fi is enabled |
| Few devices found | Some hosts block ping; enable TCP method in Settings |
| Missing MAC addresses | Normal for off-subnet devices; ARP only covers the local segment |
| Firewall prompts | Allow the app — it needs to send pings/TCP probes |
| Excel/PDF export error | `pip install openpyxl reportlab` (bundled in the .exe) |

## License

Provided as-is for authorized network administration use.
