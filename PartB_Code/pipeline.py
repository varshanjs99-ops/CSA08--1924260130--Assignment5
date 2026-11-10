"""B1 - Validate, clean, normalise and store air-quality records in SQLite."""
from __future__ import annotations

import csv
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median, mean, pstdev

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
META_FILE = ROOT / "data" / "stations.csv"
OUTPUT_DIR = ROOT / "outputs"
DB_PATH = OUTPUT_DIR / "air_quality.db"
CLEAN_CSV = OUTPUT_DIR / "cleaned_readings.csv"
QUALITY_CSV = OUTPUT_DIR / "quality_log.csv"
SUMMARY_CSV = OUTPUT_DIR / "daily_summary.csv"

REQUIRED_COLUMNS = {
    "station_id", "station", "date", "hour", "pm25", "pm10", "no2", "temperature", "temperature_unit"
}
POLLUTANTS = ("pm25", "pm10", "no2")
MAX_POLLUTANT = 999.0


def setup_logging() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=OUTPUT_DIR / "pipeline.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        force=True,
    )


def as_float(value: str | None) -> float | None:
    if value is None or not str(value).strip() or str(value).strip().upper() in {"NA", "N/A", "NULL", "NONE"}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def celsius(value: float | None, unit: str) -> float | None:
    if value is None:
        return None
    unit = unit.strip().upper()
    return (value - 32.0) * 5.0 / 9.0 if unit == "F" else value


def create_database(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS stations (
            station_id TEXT PRIMARY KEY,
            station_name TEXT NOT NULL UNIQUE,
            temperature_unit_source TEXT NOT NULL CHECK (temperature_unit_source IN ('C','F')),
            data_type TEXT NOT NULL DEFAULT 'synthetic'
        );
        CREATE TABLE IF NOT EXISTS readings (
            reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT NOT NULL REFERENCES stations(station_id),
            reading_date TEXT NOT NULL,
            hour INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
            pm25 REAL NOT NULL CHECK (pm25 >= 0 AND pm25 <= 999),
            pm10 REAL,
            no2 REAL,
            temperature_c REAL,
            pm25_minmax REAL,
            pm25_zscore REAL,
            source_file TEXT NOT NULL,
            UNIQUE (station_id, reading_date, hour)
        );
        CREATE TABLE IF NOT EXISTS quality_log (
            quality_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            station_id TEXT,
            reading_date TEXT,
            issue TEXT NOT NULL,
            raw_record TEXT
        );
        CREATE TABLE IF NOT EXISTS daily_summary (
            station_id TEXT NOT NULL REFERENCES stations(station_id),
            reading_date TEXT NOT NULL,
            pm25_min REAL NOT NULL,
            pm25_max REAL NOT NULL,
            pm25_mean REAL NOT NULL,
            valid_readings INTEGER NOT NULL,
            PRIMARY KEY (station_id, reading_date)
        );
    """)
    connection.commit()


def load_station_metadata(connection: sqlite3.Connection) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    with META_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            station_id = row["station_id"].strip()
            station = row["station"].strip().replace("_", " ")
            unit = row["temperature_unit"].strip().upper()
            metadata[station_id] = {"station": station, "unit": unit}
            connection.execute(
                "INSERT OR REPLACE INTO stations(station_id, station_name, temperature_unit_source, data_type) VALUES (?,?,?,'synthetic')",
                (station_id, station, unit),
            )
    connection.commit()
    return metadata


def add_quality_issue(issues: list[tuple], file_name: str, line_no: int, row: dict | None, issue: str) -> None:
    row = row or {}
    issues.append((
        file_name, line_no, row.get("station_id"), row.get("date"), issue,
        repr(row)[:500],
    ))


def read_raw_files(metadata: dict[str, dict[str, str]]) -> tuple[list[dict], list[tuple], dict[str, list[float]]]:
    records: list[dict] = []
    issues: list[tuple] = []
    station_pm25: dict[str, list[float]] = defaultdict(list)
    seen: set[tuple[str, str, int]] = set()

    files = sorted(RAW_DIR.glob("*/*.csv"))
    if not files:
        raise FileNotFoundError(f"No station CSV files found under {RAW_DIR}. Run generate_data.py first.")

    for file_path in files:
        try:
            with file_path.open("r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    add_quality_issue(issues, str(file_path.relative_to(ROOT)), 1, None, "empty file or missing header")
                    continue
                missing = REQUIRED_COLUMNS - set(reader.fieldnames)
                if missing:
                    add_quality_issue(issues, str(file_path.relative_to(ROOT)), 1, None,
                                      f"missing required columns: {', '.join(sorted(missing))}")
                    continue
                for line_no, row in enumerate(reader, start=2):
                    source_name = str(file_path.relative_to(ROOT))
                    station_id = (row.get("station_id") or "").strip()
                    station_name = (row.get("station") or "").strip().replace("_", " ")
                    try:
                        reading_date = datetime.strptime((row.get("date") or "").strip(), "%Y-%m-%d").date().isoformat()
                        hour = int((row.get("hour") or "").strip())
                        if not 0 <= hour <= 23:
                            raise ValueError("hour must be between 0 and 23")
                    except ValueError as exc:
                        add_quality_issue(issues, source_name, line_no, row, f"invalid date/hour: {exc}")
                        continue
                    if station_id not in metadata or metadata[station_id]["station"] != station_name:
                        add_quality_issue(issues, source_name, line_no, row, "station ID/name not found in metadata")
                        continue
                    key = (station_id, reading_date, hour)
                    if key in seen:
                        add_quality_issue(issues, source_name, line_no, row, "duplicate station/date/hour record")
                        continue
                    seen.add(key)

                    pm_values = {col: as_float(row.get(col)) for col in POLLUTANTS}
                    # The main PM2.5 measure is mandatory for all PM2.5 analyses. Drop blank/NA rows.
                    if pm_values["pm25"] is None:
                        add_quality_issue(issues, source_name, line_no, row, "missing or non-numeric PM2.5; row dropped")
                        continue
                    if pm_values["pm25"] < 0 or pm_values["pm25"] > MAX_POLLUTANT:
                        add_quality_issue(issues, source_name, line_no, row, "impossible PM2.5 outside [0, 999]; row dropped")
                        continue

                    # Auxiliary pollutants may be missing; keep NULL in the database and report valid PM2.5.
                    for pollutant in ("pm10", "no2"):
                        value = pm_values[pollutant]
                        if value is not None and (value < 0 or value > MAX_POLLUTANT):
                            add_quality_issue(issues, source_name, line_no, row,
                                              f"impossible {pollutant.upper()} outside [0,999]; stored as NULL")
                            pm_values[pollutant] = None

                    temp_raw = as_float(row.get("temperature"))
                    unit = (row.get("temperature_unit") or metadata[station_id]["unit"]).strip().upper()
                    if unit not in {"C", "F"}:
                        add_quality_issue(issues, source_name, line_no, row, "unknown temperature unit; temperature set to NULL")
                        temp_c = None
                    else:
                        temp_c = celsius(temp_raw, unit)
                        if temp_c is not None and not -20 <= temp_c <= 60:
                            add_quality_issue(issues, source_name, line_no, row, "impossible temperature outside [-20,60] C; set to NULL")
                            temp_c = None

                    record = {
                        "station_id": station_id,
                        "station": station_name,
                        "date": reading_date,
                        "hour": hour,
                        "pm25": pm_values["pm25"],
                        "pm10": pm_values["pm10"],
                        "no2": pm_values["no2"],
                        "temperature_c": temp_c,
                        "source_file": source_name,
                    }
                    records.append(record)
                    station_pm25[station_id].append(pm_values["pm25"])
        except UnicodeDecodeError as exc:
            add_quality_issue(issues, str(file_path.relative_to(ROOT)), 0, None, f"encoding error: {exc}")
        except OSError as exc:
            add_quality_issue(issues, str(file_path.relative_to(ROOT)), 0, None, f"file access error: {exc}")

    return records, issues, station_pm25


def normalise_records(records: list[dict], issues: list[tuple]) -> None:
    """Impute secondary channels, then calculate station-level PM2.5 normalisations."""
    grouped = _group_by_station(records)
    for station_id, rows in grouped.items():
        rows.sort(key=lambda row: (row["date"], row["hour"]))
        # PM10/NO2 gaps are replaced by the same station's median and disclosed in the audit log.
        for field in ("pm10", "no2"):
            available = [row[field] for row in rows if row[field] is not None]
            fill_value = median(available) if available else None
            for row in rows:
                if row[field] is None and fill_value is not None:
                    row[field] = fill_value
                    issues.append((row["source_file"], 0, station_id, row["date"],
                                   f"{field.upper()} missing/invalid; imputed with station median {fill_value:.2f}", ""))
        # Temperature uses forward-fill within a station; leading gaps use the station median.
        temps = [row["temperature_c"] for row in rows if row["temperature_c"] is not None]
        temp_median = median(temps) if temps else None
        previous = None
        for row in rows:
            if row["temperature_c"] is None:
                replacement = previous if previous is not None else temp_median
                if replacement is not None:
                    row["temperature_c"] = replacement
                    issues.append((row["source_file"], 0, station_id, row["date"],
                                   f"temperature missing/invalid; filled with {'previous value' if previous is not None else 'station median'} ({replacement:.2f} C)", ""))
            previous = row["temperature_c"]
        values = [row["pm25"] for row in rows]
        lo, hi = min(values), max(values)
        avg = mean(values)
        sd = pstdev(values)
        for row in rows:
            row["pm25_minmax"] = round((row["pm25"] - lo) / (hi - lo), 3) if hi > lo else 0.0
            row["pm25_zscore"] = round((row["pm25"] - avg) / sd, 3) if sd > 0 else 0.0


def _group_by_station(records: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in records:
        grouped[row["station_id"]].append(row)
    return grouped


def write_csv_outputs(records: list[dict], issues: list[tuple]) -> None:
    with CLEAN_CSV.open("w", newline="", encoding="utf-8") as f:
        fields = ["station_id", "station", "date", "hour", "pm25", "pm10", "no2", "temperature_c", "pm25_minmax", "pm25_zscore", "source_file"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    with QUALITY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_file", "line_number", "station_id", "date", "issue", "raw_record"])
        writer.writerows(issues)


def store_records(records: list[dict], issues: list[tuple]) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as connection:
        create_database(connection)
        load_station_metadata(connection)
        connection.executemany(
            """INSERT INTO readings(station_id, reading_date, hour, pm25, pm10, no2,
               temperature_c, pm25_minmax, pm25_zscore, source_file)
               VALUES (:station_id,:date,:hour,:pm25,:pm10,:no2,:temperature_c,:pm25_minmax,:pm25_zscore,:source_file)""",
            records,
        )
        connection.executemany(
            "INSERT INTO quality_log(source_file,line_number,station_id,reading_date,issue,raw_record) VALUES (?,?,?,?,?,?)",
            issues,
        )
        connection.execute("CREATE INDEX idx_readings_station_date ON readings(station_id, reading_date)")
        connection.commit()


def create_daily_summary() -> int:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DELETE FROM daily_summary")
        connection.execute("""INSERT INTO daily_summary(station_id,reading_date,pm25_min,pm25_max,pm25_mean,valid_readings)
            SELECT station_id, reading_date, MIN(pm25), MAX(pm25), AVG(pm25), COUNT(pm25)
            FROM readings GROUP BY station_id, reading_date""")
        connection.commit()
        rows = connection.execute("""SELECT s.station_name, d.reading_date, d.pm25_min, d.pm25_max,
            d.pm25_mean, d.valid_readings FROM daily_summary d JOIN stations s USING(station_id)
            ORDER BY s.station_name, d.reading_date""").fetchall()
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["station", "date", "pm25_min", "pm25_max", "pm25_mean", "valid_readings"])
        writer.writerows(rows)
    return len(rows)


def run_pipeline() -> dict[str, int]:
    setup_logging()
    meta: dict[str, dict[str, str]] = {}
    with META_FILE.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            meta[row["station_id"].strip()] = {
                "station": row["station"].strip().replace("_", " "),
                "unit": row["temperature_unit"].strip().upper(),
            }
    records, issues, _ = read_raw_files(meta)
    normalise_records(records, issues)
    write_csv_outputs(records, issues)
    store_records(records, issues)
    summary_rows = create_daily_summary()
    logging.info("Pipeline complete: %s cleaned rows; %s quality events", len(records), len(issues))
    print("B1 - CLEANING PIPELINE")
    print(f"Clean rows stored: {len(records):,}")
    print(f"Quality issues logged: {len(issues):,}")
    print(f"Daily summary rows: {summary_rows:,}")
    print(f"Database: {DB_PATH.relative_to(ROOT)}")
    print(f"Clean CSV: {CLEAN_CSV.relative_to(ROOT)}")
    print(f"Quality log: {QUALITY_CSV.relative_to(ROOT)}")
    return {"clean_rows": len(records), "issues": len(issues), "summary_rows": summary_rows}


if __name__ == "__main__":
    run_pipeline()
