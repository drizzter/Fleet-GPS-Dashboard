"""
Fleet GPS Dashboard Generator
Reads fleet_status.csv and generates an interactive HTML dashboard.

Usage:
    python fleet_dashboard.py              # Normal: read CSV → generate HTML
    python fleet_dashboard.py --inject     # Inject noisy rows, then generate
    python fleet_dashboard.py --reset      # Remove noisy rows, then generate
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Resolve paths relative to THIS script (works from anywhere)
SCRIPT_DIR = Path(__file__).parent
CSV_PATH = SCRIPT_DIR / "fleet_status.csv"
OUT_PATH = SCRIPT_DIR / "fleet_dashboard.html"

STATUS_COLORS = {
    "active": "#16a34a",
    "idle": "#f59e0b",
    "offline": "#64748b",
    "low_battery": "#dc2626",
}


def parse_time(value):
    """Parse 'YYYY-MM-DD HH:MM:SS' string into datetime."""
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


# --- Noisy data injection (for testing dashboard robustness) ---

NOISY_ROWS = [
    {
        "device_id": "GPS-031",
        "name": "Ghost Tracker",
        "status": "active",
        "battery_pct": "-5",
        "lat": "-33.87",
        "lon": "151.21",
        "last_seen": "2026-06-15 08:00:00",  # future date
        "location": "Sydney",
    },
    {
        "device_id": "GPS-032",
        "name": "Null Island Unit",
        "status": "idle",
        "battery_pct": "100",
        "lat": "0.0",
        "lon": "0.0",  # Null Island (0,0) — in the ocean
        "last_seen": "2025-01-01 00:00:00",  # very old
        "location": "Null Island",
    },
    {
        "device_id": "GPS-033",
        "name": "Duplicate Alpha",
        "status": "offline",
        "battery_pct": "50",
        "lat": "-37.81",
        "lon": "144.96",
        "last_seen": "2026-05-20 12:00:00",
        "location": "Melbourne",
    },
    {
        "device_id": "GPS-033",
        "name": "Duplicate Alpha COPY",
        "status": "active",
        "battery_pct": "99",
        "lat": "-37.82",
        "lon": "144.97",
        "last_seen": "2026-05-27 09:00:00",
        "location": "Melbourne",
    },
    {
        "device_id": "GPS-034",
        "name": "Arctic Drifter",
        "status": "low_battery",
        "battery_pct": "2",
        "lat": "64.15",
        "lon": "-21.94",  # Reykjavik, Iceland — way outside Australia
        "last_seen": "2026-05-27 10:29:00",
        "location": "Reykjavik",
    },
]


NOISY_IDS = {r["device_id"] for r in NOISY_ROWS}


def inject_noisy_rows():
    """Append edge-case rows to CSV for stress-testing the dashboard."""
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        existing = list(csv.DictReader(f))

    fieldnames = list(existing[0].keys()) if existing else []

    # Remove any previous noisy rows first (exact match)
    clean = [r for r in existing if r["device_id"] not in NOISY_IDS]

    # Add noisy rows
    clean.extend(NOISY_ROWS)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean)

    print(f"Injected {len(NOISY_ROWS)} noisy rows → {CSV_PATH.name}")
    print("  • Negative battery (GPS-031)")
    print("  • Null Island 0,0 coords (GPS-032)")
    print("  • Duplicate device ID (GPS-033 x2)")
    print("  • Off-map coordinates (GPS-034)")
    print("  • Future timestamp (GPS-031)")
    return clean


def reset_noisy_rows():
    """Remove all injected noisy rows from CSV."""
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        existing = list(csv.DictReader(f))

    clean = [r for r in existing if r["device_id"] not in NOISY_IDS]
    removed = len(existing) - len(clean)

    fieldnames = list(existing[0].keys()) if existing else []
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean)

    print(f"Removed {removed} noisy rows from {CSV_PATH.name}")
    return clean


# --- CLI handling ---

if "--inject" in sys.argv:
    devices_raw = inject_noisy_rows()
elif "--reset" in sys.argv:
    devices_raw = reset_noisy_rows()
else:
    # --- Read CSV (normal mode) ---
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found!")
        print("Make sure fleet_status.csv is in the same folder as this script.")
        exit(1)
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        devices_raw = list(csv.DictReader(f))

print(f"Loaded {len(devices_raw)} devices from {CSV_PATH.name}")


def human_ago(dt, ref):
    """Return human-readable time difference like '5 min ago'."""
    mins = int((ref - dt).total_seconds() // 60)
    if mins < 60:
        return f"{mins} min ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} hr ago"
    return f"{hrs // 24} days ago"


# --- Process data ---
devices = devices_raw
for d in devices:
    d["battery_pct"] = int(d["battery_pct"])
    d["lat"] = float(d["lat"])
    d["lon"] = float(d["lon"])
    d["_seen_dt"] = parse_time(d["last_seen"])

snapshot_time = max(d["_seen_dt"] for d in devices)

summary = {s: 0 for s in STATUS_COLORS}
for d in devices:
    summary[d["status"]] += 1
    d["seen_ago"] = human_ago(d["_seen_dt"], snapshot_time)
    d["color"] = STATUS_COLORS.get(d["status"], "#334155")
    del d["_seen_dt"]

data_json = json.dumps(devices)
summary_json = json.dumps(summary)

# --- Build HTML ---
from html import escape

html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Fleet Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f1f5f9;color:#0f172a}}
header{{background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);color:white;padding:28px 32px}}
h1{{margin:0;font-size:26px;font-weight:700;letter-spacing:-0.5px}}
header p{{margin:6px 0 0;color:#94a3b8;font-size:14px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px;padding:24px 32px}}
.card{{background:white;border-radius:14px;padding:18px 20px;box-shadow:0 1px 3px #0001,0 8px 24px #0000000a;border:1px solid #e2e8f0}}
.card .label{{font-size:13px;color:#64748b;font-weight:500;text-transform:uppercase;letter-spacing:0.5px}}
.card b{{font-size:32px;display:block;margin-top:4px;font-weight:700}}
.main{{display:grid;grid-template-columns:1.3fr 1fr;gap:24px;padding:0 32px 32px}}
.panel{{background:white;border-radius:18px;padding:20px;box-shadow:0 1px 3px #0001,0 8px 24px #0000000a;border:1px solid #e2e8f0}}
.panel h2{{font-size:16px;font-weight:600;margin-bottom:14px;color:#334155}}
#map{{height:580px;border-radius:14px;z-index:1}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px}}
.legend-item{{display:flex;align-items:center;gap:6px;font-size:13px;color:#475569;font-weight:500}}
.legend-dot{{width:12px;height:12px;border-radius:50%;border:2px solid white;box-shadow:0 1px 3px #0003}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{padding:10px 12px;border-bottom:1px solid #f1f5f9;text-align:left}}
th{{font-size:11px;text-transform:uppercase;color:#94a3b8;font-weight:600;letter-spacing:0.5px}}
tr:hover{{background:#f8fafc}}
.badge{{color:white;border-radius:999px;padding:3px 10px;font-size:11px;font-weight:600;display:inline-block}}
.device-id{{font-weight:700;color:#0f172a;font-size:13px}}
.device-name{{color:#64748b;font-size:12px}}
.time-ago{{font-weight:500;color:#334155;font-size:13px}}
.time-full{{color:#94a3b8;font-size:11px}}
.battery-bar{{width:50px;height:6px;background:#e2e8f0;border-radius:3px;overflow:hidden;display:inline-block;vertical-align:middle;margin-right:6px}}
.battery-fill{{height:100%;border-radius:3px}}
@media(max-width:960px){{.main{{grid-template-columns:1fr}}#map{{height:400px}}}}
</style>
</head>
<body>
<header>
<h1>&#x1F69A; Fleet GPS Dashboard</h1>
<p>{len(devices)} GPS tracking devices across Australia &middot; Real-time map &middot; Last updated from CSV snapshot</p>
</header>

<section class="cards" id="summary"></section>

<section class="main">
<div class="panel">
<h2>Device Map</h2>
<div class="legend" id="legend"></div>
<div id="map"></div>
</div>

<div class="panel">
<h2>Device List</h2>
<div style="overflow-x:auto;max-height:580px;overflow-y:auto">
<table>
<thead style="position:sticky;top:0;background:white;z-index:2"><tr><th>Device</th><th>Status</th><th>Battery</th><th>Last Seen</th><th>Location</th></tr></thead>
<tbody id="rows"></tbody>
</table>
</div>
</div>
</section>

<script>
const devices = {data_json};
const summary = {summary_json};
const colors = {json.dumps(STATUS_COLORS)};

const labels = {{
  active: "Active",
  idle: "Idle",
  offline: "Offline",
  low_battery: "Low Battery"
}};

// Summary cards
const summaryEl = document.getElementById("summary");
Object.keys(colors).forEach(s => {{
  summaryEl.innerHTML += `<div class="card"><div class="label">${{labels[s]}}</div><b style="color:${{colors[s]}}">${{summary[s] || 0}}</b></div>`;
}});

// Legend
const legend = document.getElementById("legend");
Object.keys(colors).forEach(s => {{
  legend.innerHTML += `<span class="legend-item"><span class="legend-dot" style="background:${{colors[s]}}"></span>${{labels[s]}}</span>`;
}});

// Leaflet map
const map = L.map("map", {{
  zoomControl: true,
  scrollWheelZoom: true
}}).setView([-25.5, 134], 4);

L.tileLayer("https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
  subdomains: "abcd",
  maxZoom: 19
}}).addTo(map);

// Add markers
devices.forEach(d => {{
  const marker = L.circleMarker([d.lat, d.lon], {{
    radius: 8,
    fillColor: d.color,
    color: "#fff",
    weight: 2.5,
    opacity: 1,
    fillOpacity: 0.9
  }}).addTo(map);

  marker.bindPopup(`
    <div style="font-family:Segoe UI,Arial,sans-serif;min-width:180px">
      <div style="font-weight:700;font-size:14px;margin-bottom:4px">${{d.device_id}} &middot; ${{d.name}}</div>
      <div style="margin-bottom:3px"><span style="background:${{d.color}};color:white;padding:2px 8px;border-radius:99px;font-size:11px;font-weight:600">${{labels[d.status]}}</span></div>
      <div style="font-size:12px;color:#64748b;margin-top:6px">
        Battery: <b>${{d.battery_pct}}%</b><br>
        Last seen: ${{d.seen_ago}}<br>
        Location: ${{d.location}}
      </div>
    </div>
  `);

  marker.bindTooltip(`${{d.device_id}} &middot; ${{d.name}}`, {{
    direction: "top",
    offset: [0, -8]
  }});
}});

// Fit map to markers
if (devices.length > 0) {{
  const bounds = L.latLngBounds(devices.map(d => [d.lat, d.lon]));
  map.fitBounds(bounds, {{ padding: [40, 40] }});
}}

// Device table
function batteryColor(pct) {{
  if (pct >= 60) return "#16a34a";
  if (pct >= 30) return "#f59e0b";
  return "#dc2626";
}}

devices.forEach(d => {{
  document.getElementById("rows").innerHTML += `
    <tr>
      <td><span class="device-id">${{d.device_id}}</span><br><span class="device-name">${{d.name}}</span></td>
      <td><span class="badge" style="background:${{d.color}}">${{labels[d.status]}}</span></td>
      <td><span class="battery-bar"><span class="battery-fill" style="width:${{d.battery_pct}}%;background:${{batteryColor(d.battery_pct)}}"></span></span>${{d.battery_pct}}%</td>
      <td><span class="time-ago">${{d.seen_ago}}</span><br><span class="time-full">${{d.last_seen}}</span></td>
      <td>${{d.location}}</td>
    </tr>`;
}});
</script>
</body>
</html>
"""

OUT_PATH.write_text(html, encoding="utf-8")
print(f"Created {OUT_PATH.name} ({len(html):,} bytes)")
