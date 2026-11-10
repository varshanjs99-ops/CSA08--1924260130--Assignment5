"""B2 - Deliberately malformed files, SQL injection attempt and sentiment edge cases."""
from __future__ import annotations

import csv
import io
import sqlite3
import tempfile
from pathlib import Path

try:
    from .ai_tools import sentiment_label
    from .pipeline import REQUIRED_COLUMNS
except ImportError:  # also supports running this file directly from PartB_Code
    from ai_tools import sentiment_label
    from pipeline import REQUIRED_COLUMNS


def inspect_csv(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return "REJECTED: unsupported text encoding (expected UTF-8)"
    except OSError as exc:
        return f"REJECTED: file access error: {exc}"
    if not text.strip():
        return "REJECTED: empty file"
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return "REJECTED: missing CSV header"
    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        return "REJECTED: missing columns: " + ", ".join(sorted(missing))
    return "ACCEPTED: expected header found"


def test_sql_injection() -> tuple[int, int]:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE stations(station TEXT, pm25 REAL)")
    con.executemany("INSERT INTO stations VALUES (?,?)", [("Adyar", 48.0), ("Guindy", 95.0), ("Manali", 121.0)])
    attack = "Adyar' OR '1'='1"
    vulnerable = f"SELECT COUNT(*) FROM stations WHERE station = '{attack}'"
    vulnerable_count = con.execute(vulnerable).fetchone()[0]
    safe_count = con.execute("SELECT COUNT(*) FROM stations WHERE station = ?", (attack,)).fetchone()[0]
    con.close()
    return vulnerable_count, safe_count


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        header = ",".join(sorted(REQUIRED_COLUMNS)) + "\n"
        files = {
            "missing_column.csv": folder / "missing_column.csv",
            "wrong_delimiter.csv": folder / "wrong_delimiter.csv",
            "utf16.csv": folder / "utf16.csv",
            "empty.csv": folder / "empty.csv",
        }
        files["missing_column.csv"].write_text("station_id,station,date,hour,pm25,pm10,no2,temperature\n", encoding="utf-8")
        files["wrong_delimiter.csv"].write_text(";".join(sorted(REQUIRED_COLUMNS)) + "\n", encoding="utf-8")
        files["utf16.csv"].write_text(header, encoding="utf-16")
        files["empty.csv"].write_text("", encoding="utf-8")
        print("B2 - ADVERSARIAL FILE TESTS")
        for label, path in files.items():
            print(f"{label}: {inspect_csv(path)}")

    vulnerable, safe = test_sql_injection()
    print("SQL injection test:")
    print(f"  String concatenation rows returned: {vulnerable}")
    print(f"  Parameterised query rows returned: {safe}")
    print("Sentiment edge cases:")
    for text in [
        "Great, another day of toxic smoke.",
        "The air is not bad and the roads are clean.",
        "The service is not not helpful.",
        "The air is good but the smoke is terrible.",
    ]:
        print(f"  {sentiment_label(text):8} | {text}")


if __name__ == "__main__":
    main()
