"""B3 - Benchmark Python loops, pandas groupby and SQLite GROUP BY.

Default performs all required scales: 1, 12 and 120 stations x 8,760 hours.
Run a quicker smoke-test with: py PartB_Code/benchmark_methods.py --quick
"""
from __future__ import annotations

import argparse
import cProfile
import csv
import io
import pstats
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
PROFILE_PATH = ROOT / "evidence" / "b3_python_profile.txt"
RESULT_PATH = ROOT / "outputs" / "b3_benchmark_results.csv"
INDEX_DB = OUTPUT_DIR / "benchmark_120.db"
HOURS_PER_YEAR = 365 * 24


def make_data(station_count: int, rows_per_station: int = HOURS_PER_YEAR):
    rng = np.random.default_rng(20261109 + station_count)
    station_codes = np.repeat(np.arange(station_count, dtype=np.int32), rows_per_station)
    day_codes = np.tile(np.repeat(np.arange(365, dtype=np.int16), 24), station_count)
    hours = np.tile(np.arange(24, dtype=np.int8), station_count * 365)
    pm25 = np.clip(rng.normal(loc=58.0, scale=24.0, size=station_count * rows_per_station), 0, 350).astype(np.float32)
    return station_codes, day_codes, hours, pm25


def python_loop(stations, days, values) -> dict[tuple[int, int], float]:
    sums: dict[tuple[int, int], float] = {}
    counts: dict[tuple[int, int], int] = {}
    for station, day, value in zip(stations, days, values):
        key = (int(station), int(day))
        sums[key] = sums.get(key, 0.0) + float(value)
        counts[key] = counts.get(key, 0) + 1
    return {key: sums[key] / counts[key] for key in sums}


def pandas_group(stations, days, values) -> dict[tuple[int, int], float]:
    frame = pd.DataFrame({"station": stations, "day": days, "pm25": values})
    result = frame.groupby(["station", "day"], sort=True)["pm25"].mean()
    return {(int(station), int(day)): float(value) for (station, day), value in result.items()}


def sqlite_group(stations, days, values, persist_path: Path | None = None) -> tuple[dict[tuple[int, int], float], float]:
    if persist_path is None:
        connection = sqlite3.connect(":memory:")
    else:
        if persist_path.exists():
            persist_path.unlink()
        connection = sqlite3.connect(persist_path)
    try:
        connection.execute("CREATE TABLE readings(station_id INTEGER, day INTEGER, hour INTEGER, pm25 REAL)")
        rows = ((int(s), int(d), int(h), float(v)) for s, d, h, v in zip(stations, days, np.tile(np.arange(24, dtype=np.int8), len(stations)//24), values))
        connection.executemany("INSERT INTO readings VALUES (?,?,?,?)", rows)
        connection.commit()
        start = time.perf_counter()
        result_rows = connection.execute("SELECT station_id, day, AVG(pm25) FROM readings GROUP BY station_id, day").fetchall()
        query_seconds = time.perf_counter() - start
        grouped = {(int(s), int(d)): float(avg) for s, d, avg in result_rows}
        return grouped, query_seconds
    finally:
        connection.close()


def run_one(station_count: int, persist: bool = False) -> dict:
    stations, days, hours, values = make_data(station_count)
    expected_rows = station_count * HOURS_PER_YEAR
    t0 = time.perf_counter()
    loop_result = python_loop(stations, days, values)
    loop_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    pandas_result = pandas_group(stations, days, values)
    pandas_time = time.perf_counter() - t0
    dataframe_mb = (stations.nbytes + days.nbytes + values.nbytes) / (1024 * 1024)

    persist_path = INDEX_DB if persist else None
    t0 = time.perf_counter()
    sql_result, sql_query_time = sqlite_group(stations, days, values, persist_path)
    sql_total_time = time.perf_counter() - t0

    keys_match = loop_result.keys() == pandas_result.keys() == sql_result.keys()
    values_match = keys_match and all(
        abs(loop_result[k] - pandas_result[k]) < 1e-5 and abs(loop_result[k] - sql_result[k]) < 1e-5
        for k in loop_result
    )
    if not values_match:
        raise AssertionError(f"Methods disagree for {station_count} stations")

    return {
        "stations": station_count,
        "rows": expected_rows,
        "groups": len(loop_result),
        "python_loop_seconds": loop_time,
        "pandas_groupby_seconds": pandas_time,
        "sqlite_end_to_end_seconds": sql_total_time,
        "sqlite_query_only_seconds": sql_query_time,
        "numpy_arrays_mb": dataframe_mb,
        "all_methods_agree": values_match,
    }


def save_profile() -> None:
    stations, days, hours, values = make_data(1)
    profile = cProfile.Profile()
    profile.enable()
    python_loop(stations, days, values)
    profile.disable()
    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(20)
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_PATH.write_text(stream.getvalue(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Use a smaller smoke-test dataset")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    station_sizes = [1, 12, 120]
    if args.quick:
        station_sizes = [1, 12]
    results = []
    print("B3 - LOOPS VS PANDAS VS SQL")
    for count in station_sizes:
        result = run_one(count, persist=(count == 120))
        results.append(result)
        print(
            f"{count:3} stations | {result['rows']:>9,} rows | "
            f"loops={result['python_loop_seconds']:.3f}s | "
            f"pandas={result['pandas_groupby_seconds']:.3f}s | "
            f"SQL total={result['sqlite_end_to_end_seconds']:.3f}s "
            f"(query={result['sqlite_query_only_seconds']:.3f}s) | agree={result['all_methods_agree']}"
        )
    with RESULT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    save_profile()
    print(f"Results: {RESULT_PATH.relative_to(ROOT)}")
    print(f"cProfile report: {PROFILE_PATH.relative_to(ROOT)}")
    if not args.quick:
        print(f"B4 index test database: {INDEX_DB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
