"""B1 - SQL summaries and visualisations required by A3/B1.4."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import csv

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "air_quality.db"
CHART_DIR = ROOT / "charts"
OUTPUT_DIR = ROOT / "outputs"


def create_visualisations() -> dict[str, str]:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        daily = con.execute("""SELECT reading_date, AVG(pm25) FROM readings
                              GROUP BY reading_date ORDER BY reading_date""").fetchall()
        station = con.execute("""SELECT s.station_name, AVG(r.pm25) FROM readings r
                                JOIN stations s USING(station_id)
                                GROUP BY s.station_name ORDER BY AVG(r.pm25) DESC""").fetchall()
        scatter = con.execute("""SELECT temperature_c, pm25 FROM readings
                                WHERE temperature_c IS NOT NULL""").fetchall()
        hourly = con.execute("""SELECT hour, pm25 FROM readings ORDER BY hour""").fetchall()
        hourly_means = con.execute("""SELECT hour, AVG(pm25) AS mean_pm25 FROM readings
                                   GROUP BY hour ORDER BY mean_pm25 DESC""").fetchall()
        adyar_october = con.execute("""SELECT AVG(pm25) FROM readings r JOIN stations s USING(station_id)
                                    WHERE s.station_name='Adyar' AND reading_date >= '2026-10-01'
                                    AND reading_date < '2026-11-01'""").fetchone()[0]
        summary = con.execute("""SELECT s.station_name, d.reading_date, d.pm25_min,
            d.pm25_max, d.pm25_mean, d.valid_readings FROM daily_summary d
            JOIN stations s USING(station_id) ORDER BY s.station_name,d.reading_date""").fetchall()

    with (OUTPUT_DIR / "daily_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["station", "date", "pm25_min", "pm25_max", "pm25_mean", "valid_readings"])
        writer.writerows(summary)

    # 1. Line chart: monthly trend.
    dates, means = zip(*daily)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(dates, means, marker="o", linewidth=1.7)
    ax.set_title("Daily Mean PM2.5 Across the Monitoring Network")
    ax.set_xlabel("Date")
    ax.set_ylabel("PM2.5 (simulated units)")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "01_monthly_pm25_trend.png", dpi=160)
    plt.close(fig)

    # 2. Bar chart: station comparison.
    names, values = zip(*station)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(names, values)
    ax.set_title("Average PM2.5 by Monitoring Station")
    ax.set_xlabel("Station")
    ax.set_ylabel("Mean PM2.5")
    ax.tick_params(axis="x", rotation=40)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "02_station_comparison.png", dpi=160)
    plt.close(fig)

    # 3. Scatter chart: temperature/PM2.5 relationship.
    x, y = zip(*scatter)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(x, y, alpha=0.35, s=14)
    ax.set_title("Temperature and PM2.5 Relationship")
    ax.set_xlabel("Temperature (°C)")
    ax.set_ylabel("PM2.5")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "03_temperature_vs_pm25.png", dpi=160)
    plt.close(fig)

    # 4. Box plot: distribution by hour.
    hour_groups = [[pm for hour, pm in hourly if hour == h] for h in range(24)]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.boxplot(hour_groups, positions=list(range(24)), showfliers=False)
    ax.set_title("Hourly PM2.5 Distribution")
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("PM2.5")
    ax.set_xticks(range(24))
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "04_hourly_pm25_boxplot.png", dpi=160)
    plt.close(fig)

    worst_hour = max(range(24), key=lambda h: sum(hour_groups[h]) / len(hour_groups[h]))
    print("B1.3 - SQL QUESTIONS")
    print(f"Adyar October mean PM2.5: {adyar_october:.2f}")
    print(f"Daily station summaries produced: {len(summary)}")
    print("Top 3 hours by network mean PM2.5:", [(hour, round(value, 2)) for hour, value in hourly_means[:3]])
    print("B1.4 - VISUALISATION")
    print(f"Daily trend points: {len(daily)}")
    print(f"Stations compared: {len(station)}")
    print(f"Highest average station: {names[0]} ({values[0]:.2f})")
    print(f"Worst average hour: {worst_hour:02d}:00")
    print("Charts saved: 4 PNG files in charts/")
    print("Interpretation: daily trend shows date variation; bar chart ranks station means;")
    print("scatter shows association, not causation; box plot compares hourly distributions.")
    return {"worst_hour": f"{worst_hour:02d}:00", "top_station": names[0]}


if __name__ == "__main__":
    create_visualisations()
