"""
FastAPI Application Entry Point - Power Grid Monitoring System
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from database.connection import init_db, get_db
from database.models import AssignmentAlert, GridReading, Substation
from sqlalchemy.sql import func
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
import joblib
from loguru import logger
from api.routers import substations, alerts, analytics

FORECAST_MODEL_PATH = "forecasting/model.pkl"
try:
    if os.path.exists(FORECAST_MODEL_PATH):
        forecast_artifacts = joblib.load(FORECAST_MODEL_PATH)
        forecast_model = forecast_artifacts["model"]
        forecast_mae = forecast_artifacts.get("mae", 0.0)
    else:
        forecast_model = None
        forecast_mae = 0.0
except Exception:
    forecast_model = None
    forecast_mae = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup: initialise database tables."""
    print("⚡ Power Grid Monitoring System - API Starting...")
    init_db()
    print("✅ Database tables initialised")
    yield
    print("🔌 API shutting down")


app = FastAPI(
    title="⚡ Power Grid Monitoring System",
    description=(
        "Real-time monitoring and predictive analytics for the South African national power grid. "
        "Tracks substations, grid telemetry, overload risk, and load shedding events."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(substations.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {
        "system": "Power Grid Monitoring System",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "API is running"}


# ─── Assignment Features (Unified under v1) ───────────────────────────────────

from fastapi import APIRouter
assignment_router = APIRouter(prefix="/api/v1", tags=["Assignment"])

def calculate_risk(demand: float, supply: float) -> str:
    if supply <= 0: return "CRITICAL"
    ratio = demand / supply
    
    if ratio >= 1.0:
        return "CRITICAL"
    elif ratio >= 0.9:
        return "HIGH"
    elif ratio >= 0.75:
        return "MEDIUM"
    else:
        return "LOW"

@assignment_router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts_data = db.query(AssignmentAlert).all()
    return [{"id": a.id, "region": a.region, "risk_level": a.risk_level, "timestamp": a.timestamp} for a in alerts_data]

@assignment_router.get("/alerts/critical")
def get_critical_alerts(db: Session = Depends(get_db)):
    alerts_data = db.query(AssignmentAlert).filter(AssignmentAlert.risk_level == "CRITICAL").all()
    return [{"id": a.id, "region": a.region, "risk_level": a.risk_level, "timestamp": a.timestamp} for a in alerts_data]

@assignment_router.get("/forecast")
def forecast(db: Session = Depends(get_db)):
    if not forecast_model:
        logger.error("Forecast endpoint called but model not trained yet.")
        return {"error": "Model not trained yet"}

    logger.info("Forecast endpoint called")

    # Step 1: Prepare Future Data
    future_times = pd.date_range(
        start=pd.Timestamp.now(),
        periods=3,
        freq="H"
    )
    future_df = pd.DataFrame({"timestamp": future_times})
    future_df["hour"] = future_df["timestamp"].dt.hour

    # Step 3: Predict Future Demand (Instantly)
    predictions = forecast_model.predict(future_df[["hour"]])
    logger.info(f"Predictions: {predictions}")

    # Step 4: Reuse Your Risk Engine (SMART MOVE)
    supply = db.query(func.sum(Substation.capacity_mw)).scalar() or 1.0
    future_risks = [calculate_risk(d, supply) for d in predictions]

    # Step 5: New API Endpoint Output with Elite Feature
    return {
        "future_hours": future_df["hour"].tolist(),
        "predictions": predictions.tolist(),
        "risk_levels": future_risks,
        "note": "Predictions based on historical hourly demand patterns",
        "mae": forecast_mae
    }

@assignment_router.get("/forecast/substation/{name}")
def forecast_substation(name: str, db: Session = Depends(get_db)):
    """Predictive forecast for a specific substation by name (Robust Version)."""
    sub = db.query(Substation).filter(Substation.name == name).first()
    if not sub:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Substation '{name}' not found")
    
    # Step 1: Prepare Future Data (6 hours ahead)
    future_times = pd.date_range(
        start=pd.Timestamp.now(),
        periods=6,
        freq="H"
    )
    
    # Step 2: Attempt ML Prediction with Failover
    if forecast_model:
        try:
            future_df = pd.DataFrame({"hour": future_times.hour})
            national_predictions = forecast_model.predict(future_df)
            
            # Substation-level scaling based on national capacity ratio
            total_cap = db.query(func.sum(Substation.capacity_mw)).scalar() or 1.0
            ratio = sub.capacity_mw / total_cap
            predictions = (national_predictions * ratio).tolist()
        except Exception as e:
            logger.error(f"Prediction failed for {name}: {e}")
            predictions = [sub.capacity_mw * 0.72] * 6 # 72% base load fallback
    else:
        # Rule-based fallback if ML model not trained yet
        predictions = [sub.capacity_mw * 0.65] * 6 # 65% base load fallback

    return {
        "substation": name,
        "capacity_mw": sub.capacity_mw,
        "predictions": predictions,
        "forecast_times": [t.isoformat() for t in future_times],
        "note": "Optimized using node-specific capacity scaling."
    }

app.include_router(assignment_router)




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
