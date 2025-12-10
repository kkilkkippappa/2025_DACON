# -*- coding: utf-8 -*-

# =========================
# 0. Pre-training setup
# =========================

import os
from pathlib import Path
import time
import threading
import json
from collections import deque

import numpy as np
import pandas as pd
import requests
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import pickle

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_EVENTS_URL = "http://127.0.0.1:8000/dashboard/events"


def send_event_to_dashboard(event: dict):
    """Send anomaly event to FastAPI dashboard endpoint."""
    try:
        payload = json.loads(json.dumps(event, default=float))
    except (TypeError, ValueError):
        payload = event
    try:
        resp = requests.post(DASHBOARD_EVENTS_URL, json=payload, timeout=5)
        if resp.status_code >= 400:
            print(f"[Dashboard] Failed to send event ({resp.status_code}): {resp.text}")
        else:
            print(f"[Dashboard] Event sent ({resp.status_code})")
    except requests.RequestException as exc:
        print(f"[Dashboard] Error sending event: {exc}")


def compute_spe(pca, scaled_x):
    x_pca = pca.transform(scaled_x)
    x_recon = pca.inverse_transform(x_pca)
    residual = scaled_x - x_recon
    spe = np.sum(residual**2)
    return float(spe)


def compute_risk_pca(pca, scaled_x):
    x_pca = pca.transform(scaled_x)
    lambdas = pca.explained_variance_
    t2 = np.sum((x_pca[0] ** 2) / lambdas)
    return float(t2)


def get_feature_contributions(pca, scaled_x):
    x_pca = pca.transform(scaled_x)[0]
    loadings = pca.components_.T
    raw_contrib = np.abs(loadings * x_pca).sum(axis=1)
    norm_contrib = raw_contrib / raw_contrib.sum()
    return norm_contrib


def get_spe_contributions(pca, scaled_x):
    x_pca = pca.transform(scaled_x)
    x_recon = pca.inverse_transform(x_pca)
    residual = (scaled_x - x_recon)[0]
    raw = residual**2
    norm = raw / raw.sum()
    return norm


def get_top3_features_with_scores(pca, scaled_x):
    contrib = get_feature_contributions(pca, scaled_x)
    top3_idx = contrib.argsort()[-3:][::-1]
    results = []
    for idx in top3_idx:
        results.append({"sensor": int(idx + 1), "score": float(contrib[idx])})
    return results


def get_top3_spe_features(pca, scaled_x):
    contrib = get_spe_contributions(pca, scaled_x)
    top3_idx = contrib.argsort()[-3:][::-1]
    results = []
    for idx in top3_idx:
        results.append({"sensor": int(idx + 1), "score": float(contrib[idx])})
    return results


class EventLog:
    def __init__(self):
        self.logs = []

    def add(self, event_dict: dict):
        self.logs.append(event_dict)


def train_models(normal_csv: str = "normal.csv"):
    """Train scaler/PCA models and persist thresholds."""
    print(f"Loading {normal_csv}...")
    csv_path = (BASE_DIR / normal_csv).resolve()
    df = pd.read_csv(csv_path)
    df_features = df.select_dtypes(include=[np.number]).copy()
    df_features = df_features.fillna(method="ffill").fillna(method="bfill")

    print("Data shape:", df_features.shape)

    print("Fitting StandardScaler...")
    scaler = StandardScaler()
    scaled = scaler.fit_transform(df_features)

    print("Fitting PCA (90% explained variance)...")
    pca = PCA(n_components=0.90)
    pca.fit(scaled)
    print(f"PCA components learned: {pca.n_components_}")

    spe_scores = [compute_spe(pca, scaled[i : i + 1]) for i in range(len(scaled))]
    spe_threshold = np.percentile(spe_scores, 99)
    print("SPE Threshold:", spe_threshold)
    with open(BASE_DIR / "threshold_spe.txt", "w") as f:
        f.write(str(spe_threshold))

    print("Computing threshold...")
    t2_scores = [compute_risk_pca(pca, scaled[i : i + 1]) for i in range(len(scaled))]
    threshold = np.percentile(t2_scores, 95)
    print("Threshold :", threshold)

    print("Saving scaler.pkl and pca.pkl ...")
    with open(BASE_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(BASE_DIR / "pca.pkl", "wb") as f:
        pickle.dump(pca, f)
    with open(BASE_DIR / "threshold.txt", "w") as f:
        f.write(str(threshold))

    print("Training complete!")
    print("Generated files: scaler.pkl, pca.pkl, threshold.txt, threshold_spe.txt")


def load_trained_artifacts():
    with open(BASE_DIR / "scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    with open(BASE_DIR / "pca.pkl", "rb") as f:
        pca = pickle.load(f)
    with open(BASE_DIR / "threshold.txt") as f:
        threshold = float(f.read().strip())
    with open(BASE_DIR / "threshold_spe.txt") as f:
        spe_threshold = float(f.read().strip())
    return scaler, pca, threshold, spe_threshold


def load_sensor_data(test_csv: str = "test2.csv"):
    csv_path = (BASE_DIR / test_csv).resolve()
    df = pd.read_csv(csv_path)
    return df.select_dtypes(include=[np.number]).values


def make_snapshot_reader(sensor_cols):
    cursor = 0

    def _reader():
        nonlocal cursor
        if len(sensor_cols) == 0:
            raise RuntimeError("Sensor dataset is empty.")
        if cursor >= len(sensor_cols):
            cursor = 0
        snap = sensor_cols[cursor]
        cursor += 1
        return snap

    return _reader


def warn_loop(get_snapshot, history_buffer, scaler, pca, log, threshold_t2, threshold_spe):
    while True:
        snap = get_snapshot()
        history_buffer.append(snap.tolist())
        snap_scaled = scaler.transform(snap.reshape(1, -1))

        risk_t2 = compute_risk_pca(pca, snap_scaled)
        risk_spe = compute_spe(pca, snap_scaled)
        print(f"[T2] {risk_t2:.4f}   [SPE] {risk_spe:.4f}")

        if (risk_t2 > threshold_t2) or (risk_spe > threshold_spe):
            top3_t2 = get_top3_features_with_scores(pca, snap_scaled)
            top3_spe = get_top3_spe_features(pca, snap_scaled)
            event = {
                "event_type": "WARN",
                "timestamp": time.time(),
                "risk": float(risk_t2),
                "spe": float(risk_spe),
                "top3_t2": top3_t2,
                "top3_spe": top3_spe,
                "history": list(history_buffer),
                "alarm_code": "Warning",
                "raw_data": snap.tolist(),
                "source": "sensor",
            }
            event = json.loads(json.dumps(event, default=float))
            log.add(event)
            send_event_to_dashboard(event)

        time.sleep(3)


def analyze_alarm_snapshot(pca, scaler, history_buffer):
    snap = np.array(history_buffer[-1]).reshape(1, -1)
    snap_scaled = scaler.transform(snap)
    t2 = compute_risk_pca(pca, snap_scaled)
    spe = compute_spe(pca, snap_scaled)
    top3_t2 = get_top3_features_with_scores(pca, snap_scaled)
    top3_spe = get_top3_spe_features(pca, snap_scaled)
    return {"risk": float(t2), "spe": float(spe), "top3_t2": top3_t2, "top3_spe": top3_spe}


def trigger_alarm(code, log: EventLog, history_buffer, scaler, pca):
    if not history_buffer:
        raise ValueError("history_buffer is empty")
    latest_snap = np.array(history_buffer[-1]).reshape(1, -1)
    analysis = analyze_alarm_snapshot(pca, scaler, history_buffer)
    event = {
        "event_type": "ALARM",
        "timestamp": time.time(),
        "risk": analysis["risk"],
        "spe": analysis["spe"],
        "top3_t2": analysis["top3_t2"],
        "top3_spe": analysis["top3_spe"],
        "history": list(history_buffer),
        "alarm_code": code,
        "raw_data": latest_snap.tolist(),
        "source": "machine",
    }
    event = json.loads(json.dumps(event, default=float))
    log.add(event)
    send_event_to_dashboard(event)
    return event


def run_pipeline(normal_csv: str = "normal.csv", test_csv: str = "test2.csv"):
    train_models(normal_csv)
    scaler, pca, threshold_t2, threshold_spe = load_trained_artifacts()
    sensor_cols = load_sensor_data(test_csv)
    history_buffer = deque(maxlen=5)
    get_snapshot = make_snapshot_reader(sensor_cols)
    log = EventLog()

    warn_thread = threading.Thread(
        target=warn_loop,
        args=(get_snapshot, history_buffer, scaler, pca, log, threshold_t2, threshold_spe),
    )
    warn_thread.daemon = True
    warn_thread.start()

    try:
        warn_thread.join()
    except KeyboardInterrupt:
        print("Stopping warn loop...")

    return log, history_buffer, scaler, pca


def main():
    run_pipeline()


if __name__ == "__main__":
    main()
