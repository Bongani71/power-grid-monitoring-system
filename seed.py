"""
Database Seeder - Populates PostgreSQL with substations and 72 hours of grid readings.
Run once after `init_db()` creates the tables.

Usage:
    python seed.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from database.connection import init_db, SessionLocal
from database.models import Substation, GridReading, Alert, LoadSheddingEvent, AssignmentAlert
from data_pipeline.generator import SUBSTATIONS, generate_reading
from main import calculate_risk
import random


def seed_substations(db) -> list:
    """Insert all SA substations if not already present."""
    existing = {s.name for s in db.query(Substation).all()}
    added = []
    for s in SUBSTATIONS:
        if s["name"] not in existing:
            sub = Substation(
                name=s["name"],
                region=s["region"],
                province=s["province"],
                latitude=s["lat"],
                longitude=s["lon"],
                capacity_mw=s["capacity_mw"],
                voltage_level_kv=s["voltage_kv"],
                status="online",
                commissioned_date=datetime(2005, 1, 1) + timedelta(days=random.randint(0, 4000)),
            )
            db.add(sub)
            added.append(sub)
    db.commit()
    for sub in added:
        db.refresh(sub)
    all_subs = db.query(Substation).all()
    print(f"  ✅ Substations: {len(all_subs)} total ({len(added)} new)")
    return all_subs


def seed_readings(db, substations: list, hours_back: int = 72, interval_min: int = 15):
    """Insert historical readings for all substations."""
    if db.query(GridReading).count() > 100:
        print("  ⏭  Readings already seeded - skipping")
        return

    now = datetime.utcnow()
    steps = int((hours_back * 60) / interval_min)
    sub_map = {s.name: s for s in substations}
    batch = []

    for step in range(steps):
        ts = now - timedelta(minutes=(steps - step) * interval_min)
        for sub_data in SUBSTATIONS:
            sub = sub_map.get(sub_data["name"])
            if not sub:
                continue
            raw = generate_reading(sub_data, ts, fault_chance=0.015)
            batch.append(GridReading(
                substation_id=sub.id,
                timestamp=ts,
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
            ))
            
            # Assignment Core Logic Processing
            risk_level = calculate_risk(demand=raw["load_mw"], supply=sub.capacity_mw)
            if risk_level in ["HIGH", "CRITICAL"]:
                db.add(AssignmentAlert(
                    region=sub.region,
                    risk_level=risk_level,
                    timestamp=ts
                ))


        if len(batch) >= 500:
            db.bulk_save_objects(batch)
            db.commit()
            batch.clear()

    if batch:
        db.bulk_save_objects(batch)
        db.commit()

    total = db.query(GridReading).count()
    print(f"  ✅ Grid readings: {total} rows inserted")


def seed_alerts(db, substations: list):
    """Create sample alerts for high-load substations."""
    if db.query(Alert).count() > 5:
        print("  ⏭  Alerts already seeded - skipping")
        return

    high_load_subs = substations[:6]
    alert_templates = [
        ("critical", "OVERLOAD",       "Load exceeds 100% of rated capacity!",     105.0, 100.0),
        ("high",     "HIGH_LOAD",      "Load above 90% – approaching capacity",      92.0,  90.0),
        ("medium",   "FREQ_DEVIATION", "Frequency deviation > 0.3 Hz from 50 Hz",    50.35,  50.2),
        ("low",      "LOW_POWER_FACTOR","Power factor dropped below 0.80",             0.76,  0.80),
        ("high",     "VOLTAGE_SAG",    "Voltage sag detected – below nominal -5%",   380.0, 400.0),
    ]

    for sub in high_load_subs:
        for sev, atype, msg, val, thresh in alert_templates:
            alert = Alert(
                substation_id=sub.id,
                severity=sev,
                alert_type=atype,
                message=f"[{sub.name}] {msg}",
                metric_value=val,
                threshold_value=thresh,
                is_resolved=random.random() < 0.3,  # 30% already resolved
            )
            db.add(alert)
    db.commit()
    total = db.query(Alert).count()
    print(f"  ✅ Alerts: {total} seeded")


def seed_load_shedding(db):
    """Seed sample load shedding events."""
    if db.query(LoadSheddingEvent).count() > 0:
        print("  ⏭  Load-shedding events already seeded - skipping")
        return

    events = [
        {"stage": 4, "region": "Gauteng",      "hours_ago_start": 48, "duration": 2.5,
         "affected_mw": 2600, "reason": "Unplanned unit trip at Kendal PS"},
        {"stage": 2, "region": "Western Cape",  "hours_ago_start": 36, "duration": 2.0,
         "affected_mw": 1200, "reason": "High demand evening peak – insufficient reserves"},
        {"stage": 6, "region": "National",       "hours_ago_start": 24, "duration": 4.0,
         "affected_mw": 6000, "reason": "Multiple unit outages: Tutuka, Majuba, Arnot"},
        {"stage": 3, "region": "Mpumalanga",    "hours_ago_start": 12, "duration": 3.0,
         "affected_mw": 3200, "reason": "Transmission line fault – Hendrina–Maputo"},
        {"stage": 2, "region": "KwaZulu-Natal", "hours_ago_start": 6,  "duration": 2.0,
         "affected_mw": 1400, "reason": "High demand, delayed unit return"},
    ]

    now = datetime.utcnow()
    for e in events:
        started = now - timedelta(hours=e["hours_ago_start"])
        ended = started + timedelta(hours=e["duration"])
        db.add(LoadSheddingEvent(
            stage=e["stage"],
            region=e["region"],
            started_at=started,
            ended_at=ended if ended < now else None,
            duration_hours=e["duration"],
            affected_mw=e["affected_mw"],
            reason=e["reason"],
        ))
    db.commit()
    print(f"  ✅ Load shedding events: {db.query(LoadSheddingEvent).count()} seeded")


def main():
    print("\n🌍 Power Grid Monitoring System - Database Seeder")
    print("=" * 55)
    init_db()
    print("  ✅ Tables created")

    db = SessionLocal()
    try:
        substations = seed_substations(db)
        seed_readings(db, substations)
        seed_alerts(db, substations)
        seed_load_shedding(db)
        print("\n🎉 Seeding complete! Start the API with: python main.py")
    finally:
        db.close()


if __name__ == "__main__":
    main()
