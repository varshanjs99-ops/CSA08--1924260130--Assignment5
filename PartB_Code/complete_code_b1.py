"""B1 - Completed TODO functions from the assignment's small CSV example."""
from __future__ import annotations
import csv
import io

RAW = """station,date,pm25
Adyar,2026-10-01,48
Adyar,2026-10-02,NA
Adyar,2026-10-03,
Guindy,2026-10-01,95
Guindy,2026-10-02,-5
Guindy,2026-10-03,121
Guindy,2026-10-04,1205
"""


def load_clean(text: str):
    """Read CSV text; skip blank, NA, negative and >999 PM2.5 values."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    required = {"station", "date", "pm25"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("CSV must contain station,date,pm25 columns")
    for row in reader:
        raw = (row.get("pm25") or "").strip()
        if not raw or raw.upper() in {"NA", "N/A", "NULL"}:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if value < 0 or value > 999:
            continue
        rows.append((row["station"].strip(), row["date"].strip(), value))
    return rows


def min_max(values):
    """Return min-max values rounded to 3 decimals; constant inputs map to 0."""
    values = list(values)
    if not values:
        return []
    lower, upper = min(values), max(values)
    if upper == lower:
        return [0.0 for _ in values]
    return [round((value - lower) / (upper - lower), 3) for value in values]


if __name__ == "__main__":
    clean = load_clean(RAW)
    print("B1 - COMPLETED TODO CODE")
    print("Before cleaning:")
    print(RAW)
    print("After cleaning:")
    print(clean)
    print("Min-max values:", min_max([pm for _, _, pm in clean]))
    assert clean == [("Adyar", "2026-10-01", 48.0), ("Guindy", "2026-10-01", 95.0), ("Guindy", "2026-10-03", 121.0)]
    assert min_max([48.0, 95.0, 121.0]) == [0.0, 0.644, 1.0]
    print("Outlier >999 skipped: PASS")
