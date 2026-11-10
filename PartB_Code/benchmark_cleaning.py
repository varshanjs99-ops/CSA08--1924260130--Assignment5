"""B1 - Compare standard-library CSV cleaning with pandas at three input sizes."""
from __future__ import annotations
import csv
import random
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "benchmarks"
OUT = ROOT / "outputs" / "b1_cleaning_benchmark.csv"


def create_file(path: Path, n: int) -> None:
    rng = random.Random(20261109 + n)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["station", "date", "pm25"])
        for i in range(n):
            value = rng.gauss(62, 23)
            token = f"{value:.3f}"
            choice = rng.random()
            if choice < 0.005:
                token = "NA"
            elif choice < 0.007:
                token = "-8"
            elif choice < 0.008:
                token = "1205"
            writer.writerow([f"ST{i % 12 + 1:02d}", f"2026-10-{i % 31 + 1:02d}", token])


def csv_clean(path: Path) -> tuple[int, float, float, int]:
    values: list[float] = []
    start = time.perf_counter()
    with path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = (row.get("pm25") or "").strip()
            if not raw or raw.upper() in {"NA", "N/A", "NULL"}:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if 0 <= value <= 999:
                values.append(value)
    lower, upper = min(values), max(values)
    _normalised = [(v - lower) / (upper - lower) if upper > lower else 0.0 for v in values]
    elapsed = time.perf_counter() - start
    # Approximate memory retained by the result list (excluding interpreter allocator overhead).
    retained = sys.getsizeof(values) + sum(sys.getsizeof(v) for v in values)
    return len(values), elapsed, retained / (1024 * 1024), (upper - lower)


def pandas_clean(path: Path) -> tuple[int, float, float, int]:
    start = time.perf_counter()
    frame = pd.read_csv(path, na_values=["NA", "N/A", "NULL", ""])
    frame["pm25"] = pd.to_numeric(frame["pm25"], errors="coerce")
    frame = frame.dropna(subset=["pm25"])
    frame = frame[(frame["pm25"] >= 0) & (frame["pm25"] <= 999)].copy()
    lower, upper = frame["pm25"].min(), frame["pm25"].max()
    frame["pm25_minmax"] = ((frame["pm25"] - lower) / (upper - lower)).round(3) if upper > lower else 0.0
    elapsed = time.perf_counter() - start
    retained = frame.memory_usage(index=True, deep=True).sum()
    return len(frame), elapsed, retained / (1024 * 1024), int(upper - lower)


def main() -> None:
    rows_out = []
    print("B1 - CSV LOOP VS PANDAS CLEANING")
    for n in (1_000, 100_000, 1_000_000):
        path = DATA_DIR / f"sensor_values_{n}.csv"
        create_file(path, n)
        csv_count, csv_time, csv_mb, span = csv_clean(path)
        pd_count, pd_time, pd_mb, _ = pandas_clean(path)
        assert csv_count == pd_count
        row = {
            "input_rows": n, "valid_rows": csv_count,
            "csv_loop_seconds": round(csv_time, 6),
            "pandas_seconds": round(pd_time, 6),
            "csv_retained_result_mb": round(csv_mb, 3),
            "pandas_frame_mb": round(pd_mb, 3),
            "same_valid_count": True,
        }
        rows_out.append(row)
        print(f"{n:>9,} rows | valid={csv_count:>9,} | CSV={csv_time:.4f}s ({csv_mb:.2f} MB retained) | pandas={pd_time:.4f}s ({pd_mb:.2f} MB frame) | same={csv_count == pd_count}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0]))
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"Results: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
