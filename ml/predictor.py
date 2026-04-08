"""
ML Predictor - Overload Risk & Load Forecasting
Uses an Isolation Forest for anomaly detection and a Ridge Regression for load forecasting.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from datetime import datetime, timedelta
import pickle
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
os.makedirs(MODEL_DIR, exist_ok=True)

ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_model.pkl")
FORECAST_MODEL_PATH = os.path.join(MODEL_DIR, "forecast_model.pkl")


# ─── Feature Engineering ─────────────────────────────────────────────────────

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract time-series features from a readings DataFrame.
    Expects columns: timestamp, load_mw, voltage_kv, frequency_hz,
                     power_factor, load_percentage, temperature_celsius
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["dayofweek"] = df["timestamp"].dt.dayofweek
    df["month"] = df["timestamp"].dt.month
    df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)

    # Rolling statistics (if enough data)
    if len(df) >= 4:
        df["load_rolling_mean_1h"] = df["load_percentage"].rolling(4, min_periods=1).mean()
        df["load_rolling_std_1h"] = df["load_percentage"].rolling(4, min_periods=1).std().fillna(0)
    else:
        df["load_rolling_mean_1h"] = df["load_percentage"]
        df["load_rolling_std_1h"] = 0.0

    df["freq_deviation"] = abs(df["frequency_hz"] - 50.0)
    df["voltage_deviation_pct"] = abs(df["voltage_kv"] - df["voltage_kv"].mean()) / (df["voltage_kv"].mean() + 1e-9) * 100

    feature_cols = [
        "load_percentage", "voltage_kv", "frequency_hz", "power_factor",
        "hour", "dayofweek", "month", "is_weekend",
        "load_rolling_mean_1h", "load_rolling_std_1h",
        "freq_deviation", "voltage_deviation_pct"
    ]
    if "temperature_celsius" in df.columns:
        feature_cols.append("temperature_celsius")

    return df[feature_cols].fillna(0)


# ─── Anomaly / Overload Risk Model ───────────────────────────────────────────

def train_anomaly_model(df: pd.DataFrame) -> IsolationForest:
    """Train an Isolation Forest on historical readings."""
    X = extract_features(df)
    model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
    model.fit(X)
    with open(ANOMALY_MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    return model


def load_anomaly_model():
    if os.path.exists(ANOMALY_MODEL_PATH):
        with open(ANOMALY_MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None


def predict_overload_risk(df: pd.DataFrame, model=None) -> np.ndarray:
    """
    Returns overload risk scores (0.0 - 1.0) for each row.
    Uses Isolation Forest anomaly scores normalised against thresholds.
    """
    if model is None:
        model = load_anomaly_model()

    if model is None:
        # Fallback: rule-based risk
        risks = []
        for _, row in df.iterrows():
            risk = 0.0
            if row.get("load_percentage", 0) > 90:
                risk += 0.5
            if row.get("load_percentage", 0) > 100:
                risk += 0.3
            if abs(row.get("frequency_hz", 50) - 50) > 0.2:
                risk += 0.1
            if row.get("power_factor", 1) < 0.80:
                risk += 0.1
            risks.append(min(risk, 1.0))
        return np.array(risks)

    X = extract_features(df)
    # Isolation Forest: lower score = more anomalous
    raw_scores = model.decision_function(X)
    # Normalize: -0.5 (very anomalous) → 1.0 risk, +0.5 (normal) → 0.0 risk
    risk = np.clip((-raw_scores + 0.1) / 0.6, 0.0, 1.0)

    # Boost risk for explicit overload
    load_boost = np.clip((df["load_percentage"].values - 80) / 40, 0, 0.5)
    return np.clip(risk + load_boost, 0.0, 1.0)


# ─── Load Forecasting Model ──────────────────────────────────────────────────

def train_forecast_model(df: pd.DataFrame) -> Pipeline:
    """Train a GradientBoosting regressor to forecast load_percentage."""
    X = extract_features(df)
    y = df["load_percentage"].values

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("model", GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42))
    ])
    pipe.fit(X, y)

    with open(FORECAST_MODEL_PATH, "wb") as f:
        pickle.dump(pipe, f)
    return pipe


def load_forecast_model():
    if os.path.exists(FORECAST_MODEL_PATH):
        with open(FORECAST_MODEL_PATH, "rb") as f:
            return pickle.load(f)
    return None


def forecast_next_hours(
    recent_df: pd.DataFrame,
    capacity_mw: float,
    hours_ahead: int = 6,
    interval_minutes: int = 15,
) -> list[dict]:
    """
    Generate load forecasts for the next N hours at given interval.

    Returns a list of dicts: {prediction_for, predicted_load_pct, predicted_load_mw, overload_risk, confidence}
    """
    model = load_forecast_model()
    anomaly_model = load_anomaly_model()

    forecasts = []
    steps = int((hours_ahead * 60) / interval_minutes)
    now = datetime.utcnow()

    for i in range(1, steps + 1):
        future_ts = now + timedelta(minutes=i * interval_minutes)

        # Build a synthetic row for the future timestamp based on recent trends
        synthetic_row = {
            "timestamp": future_ts.isoformat(),
            "load_percentage": recent_df["load_percentage"].mean() if len(recent_df) else 65.0,
            "voltage_kv": recent_df["voltage_kv"].mean() if len(recent_df) else 400.0,
            "frequency_hz": 50.0,
            "power_factor": recent_df["power_factor"].mean() if len(recent_df) else 0.92,
            "temperature_celsius": recent_df["temperature_celsius"].mean() if "temperature_celsius" in recent_df.columns else 22.0,
        }
        future_df = pd.DataFrame([synthetic_row])
        X_pred = extract_features(future_df)

        if model:
            predicted_pct = float(np.clip(model.predict(X_pred)[0], 0, 120))
            confidence = 0.85
        else:
            # Rule-based fallback
            hour = future_ts.hour
            if 18 <= hour < 22:
                predicted_pct = 82 + np.random.normal(0, 3)
            elif 7 <= hour < 10:
                predicted_pct = 78 + np.random.normal(0, 3)
            elif 1 <= hour < 5:
                predicted_pct = 40 + np.random.normal(0, 4)
            else:
                predicted_pct = 65 + np.random.normal(0, 4)
            predicted_pct = float(np.clip(predicted_pct, 0, 120))
            confidence = 0.65

        # Overload risk for prediction
        future_df["load_percentage"] = predicted_pct
        overload_risk = float(predict_overload_risk(future_df, anomaly_model)[0])

        forecasts.append({
            "prediction_for": future_ts.isoformat(),
            "predicted_load_pct": round(predicted_pct, 2),
            "predicted_load_mw": round(capacity_mw * predicted_pct / 100, 2),
            "overload_risk": round(overload_risk, 4),
            "confidence": confidence,
        })

    return forecasts
