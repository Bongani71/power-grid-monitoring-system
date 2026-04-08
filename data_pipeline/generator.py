"""
Data Generator - Simulates realistic South African grid telemetry data
Generates readings for substations across all 9 provinces.
"""

import random
import math
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

# ─── South African Substations Dataset ───────────────────────────────────────
SUBSTATIONS = [
    # Gauteng
    {"name": "Athena Substation",      "region": "Johannesburg", "province": "Gauteng",     "lat": -26.1952, "lon": 28.0337,  "capacity_mw": 1200, "voltage_kv": 400},
    {"name": "Kendal Power Station",   "region": "Mpumalanga",   "province": "Mpumalanga",  "lat": -26.0803, "lon": 29.0174,  "capacity_mw": 4116, "voltage_kv": 400},
    {"name": "Lethabo Power Station",  "region": "Free State",   "province": "Free State",  "lat": -26.8603, "lon": 27.9927,  "capacity_mw": 3708, "voltage_kv": 400},
    {"name": "Matimba Power Station",  "region": "Lephalale",    "province": "Limpopo",     "lat": -23.6622, "lon": 27.6456,  "capacity_mw": 3990, "voltage_kv": 400},
    {"name": "Medupi Power Station",   "region": "Lephalale",    "province": "Limpopo",     "lat": -23.6767, "lon": 27.6367,  "capacity_mw": 4764, "voltage_kv": 400},
    {"name": "Kusile Power Station",   "region": "eMalahleni",   "province": "Mpumalanga",  "lat": -25.9988, "lon": 29.2028,  "capacity_mw": 4800, "voltage_kv": 400},
    {"name": "Koeberg Nuclear",        "region": "Cape Town",    "province": "Western Cape", "lat": -33.6627, "lon": 18.4352,  "capacity_mw": 1940, "voltage_kv": 400},
    {"name": "Drakensberg Hydro",      "region": "Bergville",    "province": "KwaZulu-Natal","lat": -28.9943, "lon": 29.0803,  "capacity_mw":  920, "voltage_kv": 275},
    {"name": "Cahora Bassa Link",      "region": "Johannesburg", "province": "Gauteng",     "lat": -26.1003, "lon": 28.0520,  "capacity_mw": 1920, "voltage_kv": 533},
    {"name": "Ankerlig OCGT",          "region": "Atlantis",     "province": "Western Cape", "lat": -33.5456, "lon": 18.4881,  "capacity_mw":  1338, "voltage_kv": 400},
    {"name": "Ingula Pump Storage",    "region": "Ladysmith",    "province": "KwaZulu-Natal","lat": -28.4208, "lon": 29.5700,  "capacity_mw": 1332, "voltage_kv": 400},
    {"name": "Tutuka Power Station",   "region": "Standerton",   "province": "Mpumalanga",  "lat": -26.7603, "lon": 29.5500,  "capacity_mw": 3654, "voltage_kv": 400},
    {"name": "Majuba Power Station",   "region": "Volksrust",    "province": "Mpumalanga",  "lat": -27.0897, "lon": 29.7886,  "capacity_mw": 4110, "voltage_kv": 400},
    {"name": "Arnot Power Station",    "region": "Middelburg",   "province": "Mpumalanga",  "lat": -25.9300, "lon": 29.8900,  "capacity_mw": 2352, "voltage_kv": 400},
    {"name": "Camden Power Station",   "region": "Ermelo",       "province": "Mpumalanga",  "lat": -26.5642, "lon": 30.0100,  "capacity_mw": 1520, "voltage_kv": 275},
]


def _time_of_day_factor(hour: int) -> float:
    """
    Models SA load curve: morning peak 07-09h, evening peak 18-21h,
    low loads 01-05h, moderate midday.
    """
    if 1 <= hour < 5:
        return 0.42 + random.uniform(-0.03, 0.03)
    elif 5 <= hour < 7:
        return 0.55 + random.uniform(-0.04, 0.04)
    elif 7 <= hour < 10:
        return 0.82 + random.uniform(-0.05, 0.05)   # Morning peak
    elif 10 <= hour < 15:
        return 0.70 + random.uniform(-0.04, 0.04)
    elif 15 <= hour < 18:
        return 0.75 + random.uniform(-0.04, 0.04)
    elif 18 <= hour < 22:
        return 0.88 + random.uniform(-0.06, 0.06)   # Evening peak
    else:
        return 0.50 + random.uniform(-0.03, 0.03)


def _day_of_week_factor(weekday: int) -> float:
    """Weekends have ~15% lower demand than weekdays."""
    if weekday >= 5:   # Saturday=5, Sunday=6
        return 0.82
    return 1.0


def _temperature_factor(temperature: float) -> float:
    """High summer temps push AC load; cold winters push heating load."""
    if temperature > 30:
        return 1.08 + (temperature - 30) * 0.01
    elif temperature < 10:
        return 1.05 + (10 - temperature) * 0.008
    return 1.0


def generate_reading(substation: dict, timestamp: datetime, fault_chance: float = 0.02) -> dict:
    """
    Generate a single realistic grid reading for a substation at a given timestamp.

    Args:
        substation: dict with substation metadata
        timestamp: datetime of the reading
        fault_chance: probability of a fault event (0-1)

    Returns:
        dict representing one row of grid telemetry
    """
    hour = timestamp.hour
    weekday = timestamp.weekday()

    # Environmental noise
    base_temp = 20 + 10 * math.sin((timestamp.month - 1) * math.pi / 6)  # Seasonal
    temperature = base_temp + random.uniform(-5, 5)
    humidity = random.uniform(30, 85)

    # Compute load percentage
    load_pct = (
        _time_of_day_factor(hour)
        * _day_of_week_factor(weekday)
        * _temperature_factor(temperature)
    )

    # Inject fault / overload spike
    if random.random() < fault_chance:
        load_pct = random.uniform(0.95, 1.15)   # Possible overload

    load_pct = max(0.1, min(load_pct, 1.20))    # Clamp
    load_mw = substation["capacity_mw"] * load_pct

    # Voltage deviates slightly from nominal under load
    nominal_v = substation["voltage_kv"]
    voltage_kv = nominal_v * (1.0 - 0.04 * (load_pct - 0.5) + random.uniform(-0.01, 0.01))

    # Frequency deviates around 50 Hz
    frequency_hz = 50.0 + random.uniform(-0.3, 0.3) - 0.1 * max(0, load_pct - 0.85)

    # Power factor decreases under heavy load
    power_factor = max(0.75, 0.95 - 0.15 * max(0, load_pct - 0.80) + random.uniform(-0.02, 0.02))

    # Current
    current_amps = (load_mw * 1e6) / (math.sqrt(3) * voltage_kv * 1000) if voltage_kv > 0 else 0

    reactive_power = load_mw * math.tan(math.acos(power_factor))
    apparent_power = load_mw / power_factor

    return {
        "substation_name": substation["name"],
        "timestamp": timestamp.isoformat(),
        "load_mw": round(load_mw, 2),
        "load_percentage": round(load_pct * 100, 2),
        "voltage_kv": round(voltage_kv, 3),
        "frequency_hz": round(frequency_hz, 3),
        "power_factor": round(power_factor, 4),
        "current_amps": round(current_amps, 2),
        "reactive_power_mvar": round(reactive_power, 2),
        "apparent_power_mva": round(apparent_power, 2),
        "temperature_celsius": round(temperature, 1),
        "humidity_percent": round(humidity, 1),
    }


def generate_bulk_readings(hours_back: int = 72, interval_minutes: int = 15) -> list[dict]:
    """
    Generate readings for all substations over the past N hours.

    Args:
        hours_back: how many hours of historical data to generate
        interval_minutes: reading interval in minutes

    Returns:
        List of reading dicts
    """
    readings = []
    now = datetime.utcnow()
    steps = int((hours_back * 60) / interval_minutes)

    for step in range(steps):
        ts = now - timedelta(minutes=(steps - step) * interval_minutes)
        for sub in SUBSTATIONS:
            readings.append(generate_reading(sub, ts, fault_chance=0.015))

    return readings


if __name__ == "__main__":
    import json
    sample = generate_bulk_readings(hours_back=1)
    print(f"Generated {len(sample)} readings")
    print(json.dumps(sample[0], indent=2))
