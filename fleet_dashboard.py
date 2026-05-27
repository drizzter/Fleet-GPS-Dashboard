"""
Fleet GPS Dashboard Generator
Reads fleet_status.csv and generates an interactive HTML dashboard.
"""

import csv
import json
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


def human_ago(dt, ref):
    """Return human-readable time difference like '5 min ago'."""
    mins = int((ref - dt).total_seconds() // 60)
    if mins < 60:
        return f"{mins} min ago"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs} hr ago"
    return f"{hrs // 24} days ago"


# --- Read CSV ---
if not CSV_PATH.exists():
    print(f"ERROR: {CSV_PATH} not found!")
    print("Make sure fleet_status.csv is in the same folder as this script.")
    exit(1)

with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
    devices = list(csv.DictReader(f))

print(f"Loaded {len(devices)} devices from {CSV_PATH.name}")

# --- Process data ---
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
<style>
body{{margin:0;font-family:Arial,sans-serif;background:#f1f5f9;color:#0f172a}}
header{{background:#0f172a;color:white;padding:24px 32px}}
h1{{margin:0;font-size:28px}} p{{margin:6px 0 0;color:#cbd5e1}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;padding:24px 32px}}
.card{{background:white;border-radius:16px;padding:18px;box-shadow:0 8px 20px #0001}}
.card b{{font-size:30px;display:block;margin-top:6px}}
.main{{display:grid;grid-template-columns:1.2fr 1fr;gap:24px;padding:0 32px 32px}}
.panel{{background:white;border-radius:18px;padding:18px;box-shadow:0 8px 20px #0001}}
#map{{height:560px;background:#e0f2fe;border-radius:16px;position:relative;overflow:hidden}}
.marker{{position:absolute;width:16px;height:16px;border-radius:50%;border:3px solid white;transform:translate(-50%,-50%);box-shadow:0 3px 10px #0005;cursor:pointer}}
.marker:hover::after{{content:attr(data-tip);position:absolute;left:18px;top:-8px;background:#0f172a;color:white;padding:8px 10px;border-radius:8px;white-space:nowrap;z-index:5}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{padding:10px;border-bottom:1px solid #e2e8f0;text-align:left}}
th{{font-size:12px;text-transform:uppercase;color:#64748b}}
.badge{{color:white;border-radius:999px;padding:4px 9px;font-size:12px;font-weight:bold}}
.legend{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px}}
.dot{{width:11px;height:11px;border-radius:50%;display:inline-block;margin-right:5px}}
@media(max-width:900px){{.main{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header>
<h1>Fleet GPS Dashboard</h1>
<p>{len(devices)} GPS tracking devices across Australia &middot; Snapshot based on latest CSV ping</p>
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
<table>
<thead><tr><th>Device</th><th>Status</th><th>Battery</th><th>Last Seen</th><th>Location</th></tr></thead>
<tbody id="rows"></tbody>
</table>
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

const summaryEl = document.getElementById("summary");
Object.keys(colors).forEach(s => {{
  summaryEl.innerHTML += `<div class="card">${{labels[s]}}<b>${{summary[s] || 0}}</b></div>`;
}});

const legend = document.getElementById("legend");
Object.keys(colors).forEach(s => {{
  legend.innerHTML += `<span><i class="dot" style="background:${{colors[s]}}"></i>${{labels[s]}}</span>`;
}});

const map = document.getElementById("map");
const minLat = -44, maxLat = -10, minLon = 112, maxLon = 154;

devices.forEach(d => {{
  const x = ((d.lon - minLon) / (maxLon - minLon)) * 100;
  const y = ((maxLat - d.lat) / (maxLat - minLat)) * 100;

  const m = document.createElement("div");
  m.className = "marker";
  m.style.left = x + "%";
  m.style.top = y + "%";
  m.style.background = d.color;
  m.dataset.tip = `${{d.device_id}} &middot; ${{d.name}} &middot; ${{labels[d.status]}} &middot; ${{d.location}}`;
  map.appendChild(m);

  document.getElementById("rows").innerHTML += `
    <tr>
      <td><b>${{d.device_id}}</b><br>${{d.name}}</td>
      <td><span class="badge" style="background:${{d.color}}">${{labels[d.status]}}</span></td>
      <td>${{d.battery_pct}}%</td>
      <td>${{d.seen_ago}}<br><small>${{d.last_seen}}</small></td>
      <td>${{d.location}}</td>
    </tr>`;
}});
</script>
</body>
</html>
"""

OUT_PATH.write_text(html, encoding="utf-8")
print(f"Created {OUT_PATH.name} ({len(html):,} bytes)")
