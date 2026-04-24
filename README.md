## Predictive Memory Management Dashboard (pmms_web)

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
cd C:\Users\DELL\OneDrive\Desktop\pmms_web
python -m pip install -r requirements.txt
```

### Run

Use a custom port if `5000` is already taken:

```powershell
$env:PORT=5052
python app.py
```

Open the dashboard:

- `http://127.0.0.1:5052/`

### How to use the dashboard

- **Sample RAM Now**: captures one real snapshot into SQLite
- **Auto-sample**: captures every N seconds
- **Train Model**: trains using the most recent samples (default window: 300)
- **Predict (60s ahead)**: predicts used RAM in MB 60 seconds from now
- **Reset Samples**: clears all captured system samples (requires confirmation)
- **Export CSV**: downloads `system_memory_logs.csv`

### Useful endpoints

- `GET /health`
- `GET /status`
- `GET /sample`
- `GET /train`
- `GET /predict/<seconds_ahead>` (e.g. `/predict/60`)
- `POST /reset?confirm=YES`
- `GET /export.csv`

### Configuration (optional)

Environment variables:

- **`PORT`**: server port (default `5000`)
- **`FLASK_DEBUG`**: `1` for debug (default `1`)
- **`TRAIN_WINDOW`**: number of recent samples to train on (default `300`)

### Troubleshooting

- **`/train` says need more samples**: click **Sample RAM Now** at least twice (or enable auto-sample).
- **Port already in use**: set `PORT` to something else (e.g. `5052`).

