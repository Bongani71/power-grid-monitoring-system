"""
FastAPI Routers - Analytics & ML Predictions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List
from datetime import datetime, timedelta
import pandas as pd

from database.connection import get_db
from database.models import GridReading, Substation, LoadPrediction, LoadSheddingEvent
from api.schemas import LoadPredictionResponse, GridSummary, LoadSheddingEventResponse
from ml.predictor import predict_overload_risk, forecast_next_hours

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=GridSummary)
def get_grid_summary(db: Session = Depends(get_db)):
    """
    Returns a real-time snapshot of the national grid:
    total substations, load, active alerts, frequency, overload risk.
    """
    substations = db.query(Substation).all()
    since = datetime.utcnow() - timedelta(minutes=30)

    total_capacity = sum(s.capacity_mw for s in substations)
    total_load = 0.0
    freqs = []
    load_pcts = []
    risks = []
    online_count = 0
    fault_count = 0

    for sub in substations:
        # Fetch the absolute latest reading to ensure we don't show 0 MW if there's a minor telemetry lag
        latest = (
            db.query(GridReading)
            .filter(GridReading.substation_id == sub.id)
            .order_by(desc(GridReading.timestamp))
            .first()
        )
        if sub.status == "online":
            online_count += 1
        if sub.status in ("fault", "offline"):
            fault_count += 1

        if latest:
            total_load += latest.load_mw
            freqs.append(latest.frequency_hz)
            load_pcts.append(latest.load_percentage)
            # System risk score contribution
            risk = 0.0
            if latest.load_percentage > 90: risk += 0.5
            if latest.load_percentage > 100: risk += 0.3
            if abs(latest.frequency_hz - 50.0) > 0.2: risk += 0.1
            risks.append(min(risk, 1.0))

    from database.models import Alert
    active_alerts = db.query(Alert).filter(Alert.is_resolved == False).count()
    critical_alerts = db.query(Alert).filter(Alert.is_resolved == False, Alert.severity == "critical").count()

    return GridSummary(
        total_substations=len(substations),
        online_count=online_count,
        fault_count=fault_count,
        total_capacity_mw=round(total_capacity, 2),
        total_load_mw=round(total_load, 2),
        avg_load_percentage=round(sum(load_pcts) / len(load_pcts), 2) if load_pcts else 0.0,
        active_alerts=active_alerts,
        critical_alerts=critical_alerts,
        overload_risk_score=round(sum(risks) / len(risks) * 100, 1) if risks else 0.0,
        grid_frequency_avg=round(sum(freqs) / len(freqs), 3) if freqs else 50.0,
        timestamp=datetime.utcnow(),
    )


@router.get("/substation/{substation_id}/forecast", response_model=List[LoadPredictionResponse])
def get_forecast(
    substation_id: int,
    hours_ahead: int = Query(default=6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    """Run ML load forecast for a specific substation."""
    sub = db.query(Substation).filter(Substation.id == substation_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substation not found")

    # Fetch recent readings as DataFrame
    since = datetime.utcnow() - timedelta(hours=48)
    readings = (
        db.query(GridReading)
        .filter(GridReading.substation_id == substation_id, GridReading.timestamp >= since)
        .order_by(GridReading.timestamp)
        .all()
    )

    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "load_mw": r.load_mw,
        "load_percentage": r.load_percentage,
        "voltage_kv": r.voltage_kv,
        "frequency_hz": r.frequency_hz,
        "power_factor": r.power_factor,
        "temperature_celsius": r.temperature_celsius or 22.0,
    } for r in readings])

    forecasts = forecast_next_hours(df, capacity_mw=sub.capacity_mw, hours_ahead=hours_ahead)

    # Persist predictions
    new_preds = []
    for f in forecasts:
        pred = LoadPrediction(
            substation_id=substation_id,
            prediction_for=datetime.fromisoformat(f["prediction_for"]),
            predicted_load_mw=f["predicted_load_mw"],
            predicted_load_pct=f["predicted_load_pct"],
            overload_risk=f["overload_risk"],
            confidence=f["confidence"],
        )
        db.add(pred)
        new_preds.append(pred)

    db.commit()
    for p in new_preds:
        db.refresh(p)

    return new_preds


@router.get("/load-curve")
def get_national_load_curve(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Aggregate national load curve: total_load_mw vs timestamp for the past N hours.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = (
        db.query(
            GridReading.timestamp,
            func.sum(GridReading.load_mw).label("total_load_mw"),
            func.avg(GridReading.load_percentage).label("avg_load_pct"),
            func.avg(GridReading.frequency_hz).label("avg_frequency"),
        )
        .filter(GridReading.timestamp >= since)
        .group_by(GridReading.timestamp)
        .order_by(GridReading.timestamp)
        .all()
    )

    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "total_load_mw": round(r.total_load_mw or 0, 2),
            "avg_load_pct": round(r.avg_load_pct or 0, 2),
            "avg_frequency": round(r.avg_frequency or 50, 3),
        }
        for r in rows
    ]


@router.get("/load-shedding", response_model=List[LoadSheddingEventResponse])
def get_load_shedding(db: Session = Depends(get_db)):
    """Get all load shedding events ordered by most recent first."""
    return db.query(LoadSheddingEvent).order_by(desc(LoadSheddingEvent.started_at)).all()


@router.get("/province-heatmap")
def get_province_heatmap(db: Session = Depends(get_db)):
    """Average load percentage grouped by province for heatmap visualisation."""
    since = datetime.utcnow() - timedelta(hours=2)

    substations = db.query(Substation).all()
    result = {}

    for sub in substations:
        latest = (
            db.query(GridReading)
            .filter(GridReading.substation_id == sub.id, GridReading.timestamp >= since)
            .order_by(desc(GridReading.timestamp))
            .first()
        )
        if latest:
            prov = sub.province
            if prov not in result:
                result[prov] = {"load_pcts": [], "total_capacity_mw": 0, "total_load_mw": 0}
            result[prov]["load_pcts"].append(latest.load_percentage)
            result[prov]["total_capacity_mw"] += sub.capacity_mw
            result[prov]["total_load_mw"] += latest.load_mw

    return {
        prov: {
            "avg_load_pct": round(sum(v["load_pcts"]) / len(v["load_pcts"]), 2),
            "total_capacity_mw": round(v["total_capacity_mw"], 2),
            "total_load_mw": round(v["total_load_mw"], 2),
        }
        for prov, v in result.items()
    }
