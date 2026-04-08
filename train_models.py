"""
ML Model Trainer
Trains the Isolation Forest (anomaly/overload) and GBM (load forecast) models
on the seeded historical data and saves them to the models/ directory.

Usage (run AFTER seed.py):
    python train_models.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta

from database.connection import SessionLocal, init_db
from database.models import GridReading, Substation
from ml.predictor import train_anomaly_model, train_forecast_model


def fetch_training_data(db, hours_back: int = 72) -> pd.DataFrame:
    """Pull all readings from the last N hours into a DataFrame."""
    since = datetime.utcnow() - timedelta(hours=hours_back)
    rows = (
        db.query(GridReading)
        .filter(GridReading.timestamp >= since)
        .order_by(GridReading.timestamp)
        .all()
    )
    print(f"  📦 Fetched {len(rows)} readings for training")
    return pd.DataFrame([{
        "timestamp":          r.timestamp,
        "load_mw":            r.load_mw,
        "load_percentage":    r.load_percentage,
        "voltage_kv":         r.voltage_kv,
        "frequency_hz":       r.frequency_hz,
        "power_factor":       r.power_factor,
        "temperature_celsius": r.temperature_celsius or 22.0,
    } for r in rows])


def main():
    print("\n🤖 Power Grid ML Model Trainer")
    print("=" * 45)
    init_db()
    db = SessionLocal()

    try:
        df = fetch_training_data(db, hours_back=72)
        if len(df) < 50:
            print("  ⚠️  Not enough data to train — run seed.py first.")
            return

        print("  🔍 Training Isolation Forest (anomaly/overload detection)...")
        model_anomaly = train_anomaly_model(df)
        print("  ✅ Anomaly model saved → models/anomaly_model.pkl")

        print("  📈 Training GBM Forecast model (load prediction)...")
        model_forecast = train_forecast_model(df)
        print("  ✅ Forecast model saved → models/forecast_model.pkl")

        print(f"\n🎉 Training complete!")
        print("  Models will be used automatically by the /analytics/forecast endpoint.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
