"""
Pydantic Schemas - Request/Response models for the Power Grid Monitoring API
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SubstationStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    FAULT = "fault"


# ─── Substation ───────────────────────────────────────────────────────────────

class SubstationBase(BaseModel):
    name: str
    region: str
    province: str
    latitude: float
    longitude: float
    capacity_mw: float
    voltage_level_kv: float
    status: SubstationStatus = SubstationStatus.ONLINE


class SubstationCreate(SubstationBase):
    pass


class SubstationResponse(SubstationBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Grid Reading ─────────────────────────────────────────────────────────────

class GridReadingBase(BaseModel):
    timestamp: datetime
    load_mw: float
    voltage_kv: float
    frequency_hz: float
    power_factor: float
    current_amps: float
    load_percentage: float
    reactive_power_mvar: Optional[float] = None
    apparent_power_mva: Optional[float] = None
    temperature_celsius: Optional[float] = None
    humidity_percent: Optional[float] = None


class GridReadingCreate(GridReadingBase):
    substation_id: int


class GridReadingResponse(GridReadingBase):
    id: int
    substation_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Alert ────────────────────────────────────────────────────────────────────

class AlertBase(BaseModel):
    severity: AlertSeverity
    alert_type: str
    message: str
    metric_value: Optional[float] = None
    threshold_value: Optional[float] = None


class AlertCreate(AlertBase):
    substation_id: int


class AlertResolve(BaseModel):
    resolved_by: str = "Operator"


class AlertResponse(AlertBase):
    id: int
    substation_id: int
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Load Prediction ──────────────────────────────────────────────────────────

class LoadPredictionResponse(BaseModel):
    id: int
    substation_id: int
    predicted_at: datetime
    prediction_for: datetime
    predicted_load_mw: float
    predicted_load_pct: float
    overload_risk: float
    confidence: float
    ml_version: str

    model_config = {"from_attributes": True}


# ─── Load Shedding ────────────────────────────────────────────────────────────

class LoadSheddingEventResponse(BaseModel):
    id: int
    stage: int
    region: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_hours: Optional[float] = None
    affected_mw: Optional[float] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Dashboard Summary ────────────────────────────────────────────────────────

class GridSummary(BaseModel):
    total_substations: int
    online_count: int
    fault_count: int
    total_capacity_mw: float
    total_load_mw: float
    avg_load_percentage: float
    active_alerts: int
    critical_alerts: int
    overload_risk_score: float     # 0-100
    grid_frequency_avg: float
    timestamp: datetime


class SubstationWithLatestReading(BaseModel):
    substation: SubstationResponse
    latest_reading: Optional[GridReadingResponse] = None
    overload_risk: Optional[float] = None
    active_alerts: int = 0

    model_config = {"from_attributes": True}
