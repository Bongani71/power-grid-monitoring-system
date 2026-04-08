"""
Background Data Ingestion Scheduler
Continuously generates new telemetry readings every 15 minutes 
and writes them to the database, simulating live grid telemetry.
Raises alerts when thresholds are breached.

Run alongside the API:
    python data_pipeline/scheduler.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from database.connection import SessionLocal, init_db
from database.models import Substation, GridReading, Alert
from data_pipeline.generator import SUBSTATIONS, generate_reading


# Alert thresholds
THRESHOLDS = {
    "load_critical":   {"load_pct": 100, "severity": "critical", "type": "OVERLOAD"},
    "load_high":       {"load_pct": 90,  "severity": "high",     "type": "HIGH_LOAD"},
    "freq_deviation":  {"freq_dev": 0.3, "severity": "high",     "type": "FREQ_DEVIATION"},
    "low_power_factor":{"pf":       0.80, "severity": "medium",  "type": "LOW_POWER_FACTOR"},
}


def _raise_alert_if_needed(db, substation_id: int, reading: GridReading):
    """Check a reading against thresholds and raise alerts as necessary."""
    checks = []

    if reading.load_percentage >= 100:
        checks.append(("critical", "OVERLOAD",
                        f"Load {reading.load_percentage:.1f}% exceeds rated capacity!",
                        reading.load_percentage, 100.0))
    elif reading.load_percentage >= 90:
        checks.append(("high", "HIGH_LOAD",
                        f"Load {reading.load_percentage:.1f}% approaching capacity",
                        reading.load_percentage, 90.0))

    freq_dev = abs(reading.frequency_hz - 50.0)
    if freq_dev >= 0.3:
        checks.append(("high", "FREQ_DEVIATION",
                        f"Frequency deviation {freq_dev:.3f} Hz from nominal",
                        reading.frequency_hz, 50.0))

    if reading.power_factor < 0.80:
        checks.append(("medium", "LOW_POWER_FACTOR",
                        f"Power factor {reading.power_factor:.3f} below minimum",
                        reading.power_factor, 0.80))

    for severity, atype, message, val, thresh in checks:
        # Only raise if no duplicate open alert exists for this type
        existing = (
            db.query(Alert)
            .filter(
                Alert.substation_id == substation_id,
                Alert.alert_type == atype,
                Alert.is_resolved == False,
            )
            .first()
        )
        if not existing:
            db.add(Alert(
                substation_id=substation_id,
                severity=severity,
                alert_type=atype,
                message=f"[Auto] {message}",
                metric_value=val,
                threshold_value=thresh,
            ))


def ingest_readings():
    """Core ingestion job: generate and persist one reading per substation."""
    db = SessionLocal()
    try:
        sub_records = db.query(Substation).all()
        sub_map = {s.name: s for s in sub_records}
        now = datetime.utcnow()
        count = 0

        for sub_data in SUBSTATIONS:
            sub = sub_map.get(sub_data["name"])
            if not sub or sub.status not in ("online", None):
                continue

            raw = generate_reading(sub_data, now, fault_chance=0.02)
            reading = GridReading(
                substation_id=sub.id,
                timestamp=now,
                load_mw=raw["load_mw"],
                load_percentage=raw["load_percentage"],
                voltage_kv=raw["voltage_kv"],
                frequency_hz=raw["frequency_hz"],
                power_factor=raw["power_factor"],
                current_amps=raw["current_amps"],
                reactive_power_mvar=raw["reactive_power_mvar"],
                apparent_power_mva=raw["apparent_power_mva"],
                temperature_celsius=raw["temperature_celsius"],
                humidity_percent=raw["humidity_percent"],
            )
            db.add(reading)
            db.flush()
            _raise_alert_if_needed(db, sub.id, reading)
            count += 1

        db.commit()
        print(f"[{now.strftime('%H:%M:%S')}] ✅ Ingested {count} readings")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Ingestion failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("⚡ Power Grid Data Scheduler starting...")
    init_db()

    # Run once immediately on start
    ingest_readings()

    scheduler = BlockingScheduler()
    scheduler.add_job(ingest_readings, "interval", minutes=15, id="grid_ingest")
    print("📡 Scheduler running — ingesting every 15 minutes. Press Ctrl+C to stop.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Scheduler stopped.")
