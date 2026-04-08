"""
FastAPI Routers - Alerts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from database.models import Alert, Substation
from api.schemas import AlertCreate, AlertResponse, AlertResolve

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=List[AlertResponse])
def get_alerts(
    severity: Optional[str] = None,
    is_resolved: Optional[bool] = None,
    substation_id: Optional[int] = None,
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db)
):
    """Get alerts with optional filters."""
    query = db.query(Alert)
    if severity:
        query = query.filter(Alert.severity == severity)
    if is_resolved is not None:
        query = query.filter(Alert.is_resolved == is_resolved)
    if substation_id:
        query = query.filter(Alert.substation_id == substation_id)

    return query.order_by(desc(Alert.created_at)).limit(limit).all()


@router.get("/active", response_model=List[AlertResponse])
def get_active_alerts(db: Session = Depends(get_db)):
    """Get all unresolved alerts ordered by severity."""
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts = (
        db.query(Alert)
        .filter(Alert.is_resolved == False)
        .order_by(desc(Alert.created_at))
        .all()
    )
    return sorted(alerts, key=lambda a: severity_order.get(a.severity, 9))


@router.get("/summary")
def get_alert_summary(db: Session = Depends(get_db)):
    """Return count of active alerts grouped by severity."""
    active = db.query(Alert).filter(Alert.is_resolved == False).all()
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": len(active)}
    for a in active:
        if a.severity in summary:
            summary[a.severity] += 1
    return summary


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(
    alert_id: int,
    payload: AlertResolve,
    db: Session = Depends(get_db)
):
    """Mark an alert as resolved."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = payload.resolved_by
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/resolve-all")
def resolve_all_alerts(db: Session = Depends(get_db)):
    """Resolve all active alerts (bulk action)."""
    count = (
        db.query(Alert)
        .filter(Alert.is_resolved == False)
        .update({"is_resolved": True, "resolved_at": datetime.utcnow(), "resolved_by": "Bulk Action"})
    )
    db.commit()
    return {"message": f"Resolved {count} alerts"}
