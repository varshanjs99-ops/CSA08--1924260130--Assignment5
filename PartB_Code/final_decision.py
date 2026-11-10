"""B4 - 50-complaint sentiment/summarisation experiment and indexed-query test."""
from __future__ import annotations

import csv
import sqlite3
import statistics
import time
from pathlib import Path

try:
    from .ai_tools import sentiment_label, extractive_summary, first_k_summary
except ImportError:  # also supports running this file directly from PartB_Code
    from ai_tools import sentiment_label, extractive_summary, first_k_summary

ROOT = Path(__file__).resolve().parents[1]
COMPLAINTS_PATH = ROOT / "data" / "citizen_complaints.csv"
OUTPUT_DIR = ROOT / "outputs"
INDEX_DB = OUTPUT_DIR / "benchmark_120.db"


def create_complaints() -> None:
    positive = [
        ("The street air is cleaner after the road work. The monitoring team gave a helpful update.", "positive"),
        ("The bus stop is safe and the new dust screen is working. The response was timely.", "positive"),
        ("Pollution has reduced near our school. The residents appreciated the clear report.", "positive"),
        ("The factory filter was fixed and smoke levels improved. Thank you for acting quickly.", "positive"),
        ("The air feels fresh today. The team resolved our complaint.", "positive"),
        ("The traffic change made the area quieter and cleaner. The service was helpful.", "positive"),
        ("The latest update is clear and useful. The station is working properly.", "positive"),
        ("Dust has reduced outside the clinic. The staff were polite and helpful.", "positive"),
        ("The road is clean and the smell is gone. The repair was effective.", "positive"),
        ("The air quality improved after the inspection. The action was quick and appreciated.", "positive"),
    ]
    negative = [
        ("Smoke is heavy near the factory and the air is unhealthy. The complaint is still open.", "negative"),
        ("The road is dirty and dust is high. The response has been slow.", "negative"),
        ("A broken filter releases toxic smoke. The area feels unsafe.", "negative"),
        ("Traffic fumes are terrible near the school. The smell is harmful.", "negative"),
        ("The monitoring display is broken and readings are missing. Please repair it.", "negative"),
        ("The waste site produces a bad smell. The service team has delayed action.", "negative"),
        ("Air is polluted and visibility is poor. Residents are worried about health.", "negative"),
        ("The street is dusty and blocked. The response from the office was rude.", "negative"),
        ("Smoke levels are high and the air is bad. No inspection has happened.", "negative"),
        ("The sensor is broken and the report is missing. The delay is unacceptable.", "negative"),
    ]
    mixed = [
        ("The road is cleaner now, but traffic smoke remains high. The team should inspect the junction.", "neutral"),
        ("The staff were helpful, but the air is still polluted. We need another inspection.", "neutral"),
        ("The dust screen is working, although a bad smell remains near the market. Please follow up.", "neutral"),
        ("The report is clear, but PM2.5 remains high. Residents need a longer-term solution.", "neutral"),
        ("The factory reduced smoke, but trucks still create dust. Both issues need attention.", "neutral"),
        ("The repair was quick, but the sensor is still unreliable. Please verify the readings.", "neutral"),
        ("The road is clean, although noise and traffic fumes continue. The area needs monitoring.", "neutral"),
        ("The office responded quickly, but the blocked drain creates a smell. Please inspect it.", "neutral"),
        ("Air is better in the morning, but smoke increases at night. More measurements are needed.", "neutral"),
        ("The new bus route is helpful, but roadside dust is worse. Please review the station data.", "neutral"),
    ]
    adversarial = [
        ("Great, another day of toxic smoke. Residents are not impressed.", "negative"),
        ("The air is not bad, but the factory smoke is not gone. Please investigate.", "negative"),
        ("The service is not not helpful, but the readings remain confusing. We need clarification.", "neutral"),
        ("No clean air today; the road is not safe for children. Please act.", "negative"),
        ("Wonderful, the sensor broke again. This is not a good update.", "negative"),
        ("The report says no problem, yet the smell is terrible. Residents disagree.", "negative"),
        ("It is not uncommon to see dust here, and the road is dirty again. Please inspect.", "negative"),
        ("The response was not slow, but pollution is still high. More work is required.", "neutral"),
        ("Never have we had such clean air, but today's smoke is worse. Please check.", "negative"),
        ("The station is not broken, but its readings are missing. Please verify the sensor.", "neutral"),
    ]
    rows = []
    groups = [positive, negative, mixed, adversarial, positive]
    number = 1
    for group in groups:
        for complaint, label in group:
            rows.append((f"C{number:03d}", complaint, label))
            number += 1
    with COMPLAINTS_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["complaint_id", "complaint_text", "human_label"])
        writer.writerows(rows)


def run_complaints() -> tuple[int, int, list[str]]:
    with COMPLAINTS_PATH.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    matches = 0
    output_rows = []
    texts = []
    for row in rows:
        predicted = sentiment_label(row["complaint_text"])
        actual = row["human_label"]
        matches += predicted == actual
        output_rows.append((row["complaint_id"], actual, predicted, predicted == actual))
        texts.append(row["complaint_text"])
    with (OUTPUT_DIR / "complaint_predictions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["complaint_id", "human_label", "predicted_label", "agree"])
        writer.writerows(output_rows)
    summary = extractive_summary(texts, k=5)
    baseline = first_k_summary(texts, k=5)
    (OUTPUT_DIR / "complaint_summary.txt").write_text(
        "LEXICON/WORD-FREQUENCY SUMMARY\n" + "\n".join(f"- {s}" for s in summary)
        + "\n\nFIRST-K BASELINE\n" + "\n".join(f"- {s}" for s in baseline) + "\n",
        encoding="utf-8",
    )
    agreement = 100.0 * matches / len(rows)
    print("B4.1 - CITIZEN COMPLAINT AI")
    print(f"Complaints evaluated: {len(rows)}")
    print(f"Sentiment agreement with human labels: {matches}/{len(rows)} ({agreement:.1f}%)")
    print("Extractive summary (top 5 informative sentences):")
    for sentence in summary:
        print(" -", sentence)
    print("First-k baseline selected", len(baseline), "sentences.")
    print("Limitations: sarcasm, mixed sentiment, domain words and implicit context may be misclassified.")
    return len(rows), matches, summary


def benchmark_index() -> tuple[float, float, float]:
    if not INDEX_DB.exists():
        raise FileNotFoundError("Run PartB_Code/benchmark_methods.py first to create benchmark_120.db")
    query = "SELECT AVG(pm25) FROM readings WHERE station_id=? AND day BETWEEN ? AND ?"
    params = (83, 180, 210)
    with sqlite3.connect(INDEX_DB) as con:
        con.execute("DROP INDEX IF EXISTS idx_station_day")
        con.commit()
        plan_without = con.execute("EXPLAIN QUERY PLAN " + query, params).fetchall()
        start = time.perf_counter()
        for _ in range(25):
            con.execute(query, params).fetchone()
        without = (time.perf_counter() - start) / 25
        start_build = time.perf_counter()
        con.execute("CREATE INDEX idx_station_day ON readings(station_id, day)")
        con.commit()
        build_time = time.perf_counter() - start_build
        plan_with = con.execute("EXPLAIN QUERY PLAN " + query, params).fetchall()
        start = time.perf_counter()
        for _ in range(25):
            con.execute(query, params).fetchone()
        with_index = (time.perf_counter() - start) / 25
    print("B4.2 - DATABASE INDEX")
    print(f"Average monthly station query without index: {without:.6f} s")
    print(f"Average monthly station query with index:    {with_index:.6f} s")
    print(f"Index build time: {build_time:.6f} s")
    print("Without-index query plan:", plan_without)
    print("With-index query plan:", plan_with)
    speedup = without / with_index if with_index else float("inf")
    print(f"Observed query speed-up: {speedup:.2f}x")
    return without, with_index, build_time


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    create_complaints()
    count, matches, summary = run_complaints()
    without, with_index, build_time = benchmark_index()
    print("B4.3 - PRODUCTION DECISION")
    print("Store raw CSVs immutably, cleaned readings and quality logs in a relational database,")
    print("and daily/monthly aggregates in indexed summary tables. For 100 more stations at")
    print("15-minute intervals, use batched ingestion and a composite (station_id, day) index.")
    print("The lexicon system is a transparent triage baseline; validate a trained classifier")
    print("on human-labelled local complaints before replacing or automating human review.")
    with (OUTPUT_DIR / "b4_decision_metrics.txt").open("w", encoding="utf-8") as f:
        f.write(f"complaints={count}\nagreement={matches}/{count}\nquery_without_index={without:.8f}\nquery_with_index={with_index:.8f}\nindex_build={build_time:.8f}\n")


if __name__ == "__main__":
    main()
