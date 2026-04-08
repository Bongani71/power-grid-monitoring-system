"""
SQLAlchemy ORM Models - Power Grid Monitoring System
"""

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SubstationStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    FAULT = "fault"


class Substation(Base):
    __tablename__ = "substations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    region = Column(String(80), nullable=False)
    province = Column(String(80), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_mw = Column(Float, nullable=False)           # Maximum capacity in MW
    voltage_level_kv = Column(Float, nullable=False)      # Operating voltage in kV
    status = Column(String(20), default=SubstationStatus.ONLINE)
    commissioned_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    readings = relationship("GridReading", back_populates="substation", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="substation", cascade="all, delete-orphan")
    predictions = relationship("LoadPrediction", back_populates="substation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Substation(id={self.id}, name={self.name}, region={self.region})>"


class GridReading(Base):
    __tablename__ = "grid_readings"

    id = Column(Integer, primary_key=True, index=True)
    substation_id = Column(Integer, ForeignKey("substations.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # Power Metrics
    load_mw = Column(Float, nullable=False)               # Current load in MW
    voltage_kv = Column(Float, nullable=False)            # Current voltage in kV
    frequency_hz = Column(Float, nullable=False)          # Grid frequency in Hz
    power_factor = Column(Float, nullable=False)          # Power factor (0-1)
    current_amps = Column(Float, nullable=False)          # Current in Amperes

    # Calculated fields
    load_percentage = Column(Float, nullable=False)       # % of capacity used
    reactive_power_mvar = Column(Float, nullable=True)    # Reactive power in MVAR
    apparent_power_mva = Column(Float, nullable=True)     # Apparent power in MVA

    # Environmental
    temperature_celsius = Column(Float, nullable=True)
    humidity_percent = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    substation = relationship("Substation", back_populates="readings")

    def __repr__(self):
        return f"<GridReading(id={self.id}, substation_id={self.substation_id}, load_mw={self.load_mw})>"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    substation_id = Column(Integer, ForeignKey("substations.id", ondelete="CASCADE"), nullable=False)
    severity = Column(String(20), nullable=False)
    alert_type = Column(String(80), nullable=False)
    message = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(120), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    substation = relationship("Substation", back_populates="alerts")

    def __repr__(self):
        return f"<Alert(id={self.id}, severity={self.severity}, type={self.alert_type})>"


class LoadPrediction(Base):
    __tablename__ = "load_predictions"

    id = Column(Integer, primary_key=True, index=True)
    substation_id = Column(Integer, ForeignKey("substations.id", ondelete="CASCADE"), nullable=False)
    predicted_at = Column(DateTime, server_default=func.now())
    prediction_for = Column(DateTime, nullable=False)    # Future timestamp of prediction
    predicted_load_mw = Column(Float, nullable=False)
    predicted_load_pct = Column(Float, nullable=False)
    overload_risk = Column(Float, nullable=False)         # 0.0 - 1.0 probability
    confidence = Column(Float, nullable=False)            # Model confidence score
    model_version = Column(String(40), default="v1.0.0")

    # Relationships
    substation = relationship("Substation", back_populates="predictions")

    def __repr__(self):
        return f"<LoadPrediction(id={self.id}, substation_id={self.substation_id}, overload_risk={self.overload_risk})>"


class LoadSheddingEvent(Base):
    __tablename__ = "load_shedding_events"

    id = Column(Integer, primary_key=True, index=True)
    stage = Column(Integer, nullable=False)               # Stage 1-8
    region = Column(String(80), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_hours = Column(Float, nullable=True)
    affected_mw = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<LoadSheddingEvent(id={self.id}, stage={self.stage}, region={self.region})>"


# ─── Assignment Specific Model ───────────────────────────────────────────────

class AssignmentAlert(Base):
    __tablename__ = "assignment_alerts"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String(80), nullable=False)
    risk_level = Column(String(20), nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

