import os
import time

from flask import Flask, Response, jsonify, render_template, request

from algorithms import PredictiveAllocator
from db_layer import DBLayer
from ml_predictor import MLPredictor
from os_layer import OSLayer, get_system_memory_snapshot

app = Flask(__name__)

# Initialize components
os_layer = OSLayer(total_memory=1024)
db = DBLayer()
predictor = MLPredictor()
allocator = PredictiveAllocator(os_layer, predictor)

# Simple training cache: retrain only when sample count changes
_last_trained_sample_count = 0


def _ensure_trained() -> tuple[bool, dict]:
    """
    Ensure predictor is trained using recent samples.
    Returns (ok, payload). On failure, payload is an error JSON.
    """
    global _last_trained_sample_count
    sample_count = db.count_system_samples()
    if sample_count < 2:
        return False, {"error": "need more samples; click Sample RAM Now at least twice", "samples": sample_count}

    if sample_count == _last_trained_sample_count:
        return True, {"status": "already trained", "samples": sample_count}

    # Train on a recent window for better relevance
    recent = db.fetch_system_history_recent(limit=int(os.environ.get("TRAIN_WINDOW", "300")))
    ok = predictor.train([(t, "SYSTEM", used) for (t, used) in recent])
    if not ok:
        return False, {"error": "training failed (insufficient/invalid data)", "samples": sample_count}

    _last_trained_sample_count = sample_count
    return True, {"status": "trained", "samples": sample_count}


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/model")
def model_page():
    return render_template("model.html")

@app.route("/logs")
def logs_page():
    return render_template("logs.html")

@app.route("/health")
def health():
    return jsonify({"ok": True})

@app.route("/status")
def status():
    return jsonify(
        {
            "samples": db.count_system_samples(),
            "latest": db.fetch_latest_system_snapshot(),
            "train_window": int(os.environ.get("TRAIN_WINDOW", "300")),
        }
    )


@app.route("/sample")
def sample():
    now = int(time.time())
    snap = get_system_memory_snapshot(now)
    db.upsert_system_snapshot(time=snap.time, used_mb=snap.used_mb, total_mb=snap.total_mb, percent=snap.percent)
    return jsonify(
        {
            "status": "sampled",
            "time": snap.time,
            "used_mb": snap.used_mb,
            "total_mb": snap.total_mb,
            "percent": snap.percent,
        }
    )


@app.route("/train")
def train_model():
    ok, payload = _ensure_trained()
    if not ok:
        return jsonify(payload), 400

    # Return grouped history for the chart code
    grouped = db.fetch_system_grouped_for_chart()
    return jsonify({"status": "Model trained", "history": grouped, "meta": payload})


@app.route("/predict/<int:time_value>")
def predict_usage(time_value: int):
    # Interpret small numbers as "seconds ahead" to keep the old UI working (/predict/6)
    if time_value < 10_000_000:
        target_time = int(time.time()) + int(time_value)
    else:
        target_time = int(time_value)

    ok, payload = _ensure_trained()
    if not ok:
        return jsonify(payload), 400

    prediction = predictor.predict(target_time)

    # Keep allocator call (demo only)
    allocator.allocate(target_time, prediction)

    return jsonify({"time": target_time, "predicted_usage": prediction, "units": "MB", "meta": payload})


@app.route("/data")
def get_data():
    # Keep the same response shape the table code expects
    data = db.fetch_system_rows_for_table(limit=200)
    return jsonify(data)

@app.route("/reset", methods=["POST"])
def reset():
    # Basic safety: require an explicit query param like ?confirm=YES
    if request.args.get("confirm") != "YES":
        return jsonify({"error": "confirmation required: POST /reset?confirm=YES"}), 400

    db.clear_system_samples()
    global _last_trained_sample_count
    _last_trained_sample_count = 0
    return jsonify({"status": "cleared", "samples": 0})

@app.route("/export.csv")
def export_csv():
    rows = db.conn.execute(
        "SELECT time, used_mb, total_mb, percent FROM system_memory_logs ORDER BY time ASC"
    ).fetchall()
    out = ["time,used_mb,total_mb,percent"]
    out.extend([f"{int(t)},{int(u)},{int(total)},{float(p)}" for (t, u, total, p) in rows])
    csv_text = "\n".join(out) + "\n"
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=system_memory_logs.csv"},
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
