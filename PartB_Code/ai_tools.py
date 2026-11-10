"""A5/B4 - Lexicon sentiment, extractive complaint summary and SQLite chatbot."""
from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "air_quality.db"

POSITIVE = {
    "good", "clean", "fast", "helpful", "improved", "better", "clear", "safe",
    "excellent", "restored", "reduced", "resolved", "appreciated", "working",
    "timely", "great", "pleasant", "effective", "fixed", "fresh", "quiet",
}
NEGATIVE = {
    "bad", "dirty", "slow", "rude", "smoke", "broken", "polluted", "severe",
    "unsafe", "delayed", "missing", "high", "worse", "toxic", "blocked", "smell",
    "harmful", "dust", "noise", "leak", "irritating", "unhealthy", "terrible",
}
NEGATORS = {"not", "never", "no", "hardly", "without", "isnt", "wasnt", "dont", "doesnt"}
STOP_WORDS = {
    "the", "a", "an", "and", "or", "is", "are", "was", "were", "to", "of", "in",
    "on", "for", "at", "it", "this", "that", "with", "from", "by", "as", "be",
    "we", "i", "our", "my", "have", "has", "had", "today", "yesterday", "please",
    "there", "here", "after", "again", "very", "too", "much", "more", "about",
}
TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")


def tokens(text: str) -> list[str]:
    return [t.lower().replace("'", "") for t in TOKEN_RE.findall(text)]


def sentiment_score(text: str) -> int:
    """Score +/-1 per lexicon token; an odd count of nearby negators flips the token."""
    words = tokens(text)
    total = 0
    for index, word in enumerate(words):
        value = 1 if word in POSITIVE else -1 if word in NEGATIVE else 0
        if value:
            # A contiguous negator immediately before the opinion word flips it.
            # Two consecutive negators cancel each other (a simple double-negative rule).
            negation_count = 0
            cursor = index - 1
            while cursor >= 0 and words[cursor] in NEGATORS:
                negation_count += 1
                cursor -= 1
            if negation_count % 2:
                value *= -1
            total += value
    return total


def sentiment_label(text: str) -> str:
    value = sentiment_score(text)
    return "positive" if value > 0 else "negative" if value < 0 else "neutral"


def extractive_summary(complaints: list[str], k: int = 5) -> list[str]:
    """Select the k sentences with highest informative-word frequency score."""
    sentences = [s.strip() for complaint in complaints for s in re.split(r"(?<=[.!?])\s+", complaint) if s.strip()]
    frequencies = Counter(
        token for sentence in sentences for token in tokens(sentence)
        if token not in STOP_WORDS and len(token) > 2
    )
    scored = []
    for order, sentence in enumerate(sentences):
        terms = [t for t in tokens(sentence) if t not in STOP_WORDS and len(t) > 2]
        score = sum(frequencies[t] for t in terms) / max(1, len(terms))
        scored.append((score, -order, sentence))
    return [item[2] for item in sorted(scored, reverse=True)[:k]]


def first_k_summary(complaints: list[str], k: int = 5) -> list[str]:
    sentences = [s.strip() for complaint in complaints for s in re.split(r"(?<=[.!?])\s+", complaint) if s.strip()]
    return sentences[:k]


def chatbot(question: str) -> str:
    """Answer a simple station/pollutant/date question from the local SQLite database."""
    if not DB_PATH.exists():
        return "The air-quality database is not available. Run the cleaning pipeline first."
    lowered = question.lower()
    pollutant_map = {
        "pm2.5": "pm25", "pm25": "pm25", "pm 2.5": "pm25",
        "pm10": "pm10", "pm 10": "pm10", "no2": "no2", "nitrogen dioxide": "no2",
        "temperature": "temperature_c", "temp": "temperature_c",
    }
    selected = next(((label, col) for label, col in pollutant_map.items() if label in lowered), None)
    if not selected:
        return "Please ask about PM2.5, PM10, NO2 or temperature for a named station."

    with sqlite3.connect(DB_PATH) as con:
        stations = con.execute("SELECT station_name FROM stations ORDER BY LENGTH(station_name) DESC").fetchall()
        station = next((name for (name,) in stations if name.lower().replace("_", " ") in lowered), None)
        if not station:
            return "I could not identify a station in the question. Try Adyar, Guindy or another listed station."
        date_match = re.search(r"20\d{2}-\d{2}-\d{2}", question)
        if date_match:
            day = date_match.group(0)
        else:
            day = con.execute("SELECT MAX(reading_date) FROM readings").fetchone()[0]
        label, column = selected
        if column == "temperature_c":
            sql = "SELECT AVG(temperature_c) FROM readings r JOIN stations s USING(station_id) WHERE s.station_name=? AND r.reading_date=?"
        else:
            sql = f"SELECT AVG({column}) FROM readings r JOIN stations s USING(station_id) WHERE s.station_name=? AND r.reading_date=?"
        value = con.execute(sql, (station, day)).fetchone()[0]
    if value is None:
        return f"No valid {label} readings were stored for {station} on {day}."
    unit = " °C" if column == "temperature_c" else ""
    date_note = " (latest date in the sample dataset)" if not date_match else ""
    return f"Average {label} at {station} on {day}{date_note}: {value:.2f}{unit}."


if __name__ == "__main__":
    examples = [
        "Roads are clean and the bus was fast.",
        "Smoke from the factory, air is bad.",
        "The staff were not helpful.",
        "Not bad, service improved.",
    ]
    print("A5 - SENTIMENT SCORER")
    for text in examples:
        print(f"{sentiment_label(text):8} | {text}")
    print("A5 - CHATBOT")
    print(chatbot("What is the PM2.5 in Adyar today?"))
