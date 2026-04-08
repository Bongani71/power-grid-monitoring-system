"""
FastAPI Routers - Substations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta

from database.connection import get_db
from database.models import Substation, GridReading, Alert
from api.schemas import (
    SubstationCreate, SubstationResponse, SubstationWithLatestReading
)

router = APIRouter(prefix="/substations", tags=["Substations"])


@router.get("/", response_model=List[SubstationWithLatestReading])
def get_substations(
    province: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all substations with their latest readings and active alert count."""
    query = db.query(Substation)
    if province:
        query = query.filter(Substation.province.ilike(f"%{province}%"))
    if status:
        query = query.filter(Substation.status == status)

    substations = query.all()
    result = []

    for sub in substations:
        latest = (
            db.query(GridReading)
            .filter(GridReading.substation_id == sub.id)
            .order_by(desc(GridReading.timestamp))
            .first()
        )
        active_alerts = (
            db.query(Alert)
            .filter(Alert.substation_id == sub.id, Alert.is_resolved == False)
            .count()
        )

        overload_risk = None
        if latest:
            load_pct = latest.load_percentage
            freq_dev = abs(latest.frequency_hz - 50.0)
            pf = latest.power_factor
            risk = 0.0
            if load_pct > 90:  risk += 0.5
            if load_pct > 100: risk += 0.3
            if freq_dev > 0.2: risk += 0.1
            if pf < 0.80:      risk += 0.1
            overload_risk = min(risk, 1.0)

        result.append(SubstationWithLatestReading(
            substation=SubstationResponse.model_validate(sub),
            latest_reading=latest,
            overload_risk=overload_risk,
            active_alerts=active_alerts,
        ))

    return result


@router.get("/{substation_id}", response_model=SubstationResponse)
def get_substation(substation_id: int, db: Session = Depends(get_db)):
    sub = db.query(Substation).filter(Substation.id == substation_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substation not found")
    return sub


@router.get("/{substation_id}/readings")
def get_readings(
    substation_id: int,
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get time-series readings for a substation over the past N hours."""
    sub = db.query(Substation).filter(Substation.id == substation_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substation not found")

    since = datetime.utcnow() - timedelta(hours=hours)
    readings = (
        db.query(GridReading)
        .filter(GridReading.substation_id == substation_id, GridReading.timestamp >= since)
        .order_by(GridReading.timestamp)
        .all()
    )
    return readings


@router.patch("/{substation_id}/status")
def update_status(substation_id: int, status: str, db: Session = Depends(get_db)):
    """Update a substation's operational status."""
    valid = {"online", "offline", "maintenance", "fault"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")

    sub = db.query(Substation).filter(Substation.id == substation_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Substation not found")

    sub.status = status
    db.commit()
    db.refresh(sub)
    return {"message": f"Status updated to '{status}'", "substation_id": substation_id}
