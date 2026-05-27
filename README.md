# Fleet GPS Dashboard

A Python script that reads GPS tracking data from a CSV file and generates an interactive HTML dashboard showing device locations on a map of Australia.

## What It Does

- Reads `fleet_status.csv` with 30 GPS device records
- Processes status, battery, location, and last-seen timestamps
- Generates `fleet_dashboard.html` with:
  - Status summary cards (Active, Idle, Offline, Low Battery)
  - Interactive device map with hover tooltips
  - Sortable device list table

## How to Run

```bash
python fleet_dashboard.py
```

Then open `fleet_dashboard.html` in your browser.

## CSV Format

| Column | Description |
|--------|-------------|
| device_id | Unique device identifier (e.g. GPS-001) |
| name | Human-readable device name |
| status | active, idle, offline, or low_battery |
| battery_pct | Battery percentage (0-100) |
| lat | Latitude |
| lon | Longitude |
| last_seen | Timestamp (YYYY-MM-DD HH:MM:SS) |
| location | City or area name |

## Requirements

- Python 3.6+
- No external packages (uses only stdlib)
