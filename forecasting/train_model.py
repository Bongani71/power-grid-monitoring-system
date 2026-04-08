import sys
import os
import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import SessionLocal
from database.models import GridReading

def load_data():
    db = SessionLocal()
    try:
        readings = db.query(GridReading).order_by(GridReading.timestamp.desc()).limit(1500).all()
        df = pd.DataFrame([{"timestamp": r.timestamp, "demand": r.load_mw} for r in readings])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.groupby(["timestamp"])["demand"].sum().reset_index()
        df["hour"] = df["timestamp"].dt.hour
        return df
    finally:
        db.close()

def train_model(df):
    X = df[["hour"]]
    y = df["demand"]
    model = LinearRegression()
    model.fit(X, y)
    
    # Calculate Mean Absolute Error (MAE) for Elite touch
    predictions = model.predict(X)
    mae = mean_absolute_error(y, predictions)
    return model, mae

if __name__ == "__main__":
    df = load_data()
    if not df.empty:
        model, mae = train_model(df)
        os.makedirs("forecasting", exist_ok=True)
        
        # Save model and metrics
        joblib.dump({"model": model, "mae": mae}, "forecasting/model.pkl")
        print(f"✅ Model trained successfully. MAE: {mae:.2f}")
    else:
        print("❌ No data available in database to train model.")
