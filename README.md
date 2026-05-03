## Predictive Memory Management Dashboard (pmms)

This is a Flask + SQLite + scikit-learn dashboard that:

- **Samples your laptop's real RAM usage** (OS-reported metrics via `psutil`)
- Stores snapshots in SQLite (`memory_logs.db`)
- Trains a simple regression model to **predict used RAM (MB)** into the future
- Visualizes the history in a Chart.js graph + table

### What it does (and does NOT do)

- **Does**: read OS-level RAM stats like used/total/percent.
- **Does NOT**: access raw RAM contents (unsafe + not needed).

### Setup

From PowerShell:

```powershell
cd C:\Users\kevin\OneDrive\Desktop\rfid\clone\pmms
python -m pip install -r requirements.txt