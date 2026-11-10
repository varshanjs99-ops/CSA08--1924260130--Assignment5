"""Generate reproducible synthetic CSV files for the SIMATS Assignment 5 case study.

The readings are simulated for software testing and are NOT official Chennai measurements.
Run: py generate_data.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw"
META_FILE = ROOT / "data" / "stations.csv"
SEED = 20261109
DAYS = 31
START_DATE = date(2026, 10, 1)

STATIONS = [
    ("ST01", "Adyar", "C"),
    ("ST02", "Guindy", "C"),
    ("ST03", "T_Nagar", "C"),
    ("ST04", "Anna_Nagar", "C"),
    ("ST05", "Velachery", "C"),
    ("ST06", "Perungudi", "C"),
    ("ST07", "Royapuram", "C"),
    ("ST08", "Manali", "C"),
    ("ST09", "Alandur", "C"),
    ("ST10", "Kodambakkam", "C"),
    ("ST11", "Nungambakkam", "F"),
    ("ST12", "Thiruvottiyur", "F"),
]
BASE_PM25 = {
    "Adyar": 43, "Guindy": 82, "T_Nagar": 75, "Anna_Nagar": 55,
    "Velachery": 61, "Perungudi": 68, "Royapuram": 72, "Manali": 96,
    "Alandur": 58, "Kodambakkam": 70, "Nungambakkam": 63,
    "Thiruvottiyur": 77,
}
FIELDS = ["station_id", "station", "date", "hour", "pm25", "pm10", "no2", "temperature", "temperature_unit"]


def maybe_missing(value: float, rng: random.Random, probability: float = 0.004) -> str:
    if rng.random() < probability:
        return "NA" if rng.random() < 0.5 else ""
    return f"{value:.2f}"


def generate() -> int:
    rng = random.Random(SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    META_FILE.parent.mkdir(parents=True, exist_ok=True)

    with META_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["station_id", "station", "temperature_unit", "data_type"])
        for station_id, station, unit in STATIONS:
            writer.writerow([station_id, station, unit, "synthetic"])

    total_rows = 0
    for day_index in range(DAYS):
        current_day = START_DATE + timedelta(days=day_index)
        day_folder = RAW_DIR / current_day.isoformat()
        day_folder.mkdir(parents=True, exist_ok=True)
        for station_id, station, unit in STATIONS:
            path = day_folder / f"{station_id}_{station}.csv"
            rows: list[list[str]] = []
            for hour in range(24):
                # Simulated diurnal pattern and station-specific pollution baseline.
                traffic_peak = 13 if hour in (7, 8, 9, 18, 19, 20) else 0
                night_adjustment = -7 if 0 <= hour <= 5 else 0
                day_adjustment = (day_index % 5) * 1.7
                pm25 = max(3.0, rng.gauss(BASE_PM25[station] + traffic_peak + night_adjustment + day_adjustment, 8.0))
                pm10 = max(5.0, rng.gauss(pm25 * 1.75, 13.0))
                no2 = max(2.0, rng.gauss(pm25 * 0.62 + traffic_peak * 0.7, 7.0))
                temp_c = rng.gauss(30.5 + 2.0 * (hour in range(12, 16)) - 1.3 * (hour in range(0, 5)), 2.1)
                temp_value = temp_c if unit == "C" else temp_c * 9 / 5 + 32

                pm25_text = maybe_missing(pm25, rng, 0.006)
                pm10_text = maybe_missing(pm10, rng, 0.004)
                no2_text = maybe_missing(no2, rng, 0.004)
                temp_text = maybe_missing(temp_value, rng, 0.003)

                # Controlled adversarial sensor faults, distributed throughout the month.
                sequence = day_index * 24 + hour + (int(station_id[-2:]) * 11)
                if sequence % 997 == 0:
                    pm25_text = "-12.50"
                elif sequence % 1301 == 0:
                    pm25_text = "1205.00"  # impossible sensor value; B1 also tests >999
                if sequence % 1499 == 0:
                    pm10_text = "-7.00"
                if sequence % 1733 == 0:
                    temp_text = "180.00" if unit == "C" else "350.00"

                rows.append([
                    station_id, station, current_day.isoformat(), str(hour),
                    pm25_text, pm10_text, no2_text, temp_text, unit,
                ])

            # Introduce a small number of exact duplicate records for deduplication tests.
            if day_index == 5 and station_id in {"ST02", "ST07"}:
                rows.append(rows[8].copy())
            if day_index == 19 and station_id == "ST04":
                rows.append(rows[17].copy())

            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)
                writer.writerows(rows)
            total_rows += len(rows)

    print("Synthetic air-quality CSV dataset generated.")
    print(f"Stations: {len(STATIONS)} | Days: {DAYS} | Hourly rows (including duplicates): {total_rows:,}")
    print(f"Raw directory: {RAW_DIR.relative_to(ROOT)}")
    print("Note: all readings are simulated; they are not official monitoring data.")
    return total_rows


if __name__ == "__main__":
    generate()
