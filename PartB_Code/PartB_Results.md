# Assignment 5 - Part B: Implementation and Experimental Investigation

**Student:** Varshan J S  
**Register number:** 1924260130A  
**Case study:** Synthetic Chennai-area air-quality monitoring network  

> The source screenshots do not include official station data. All station readings and 50 complaint examples used below are generated test records. Results demonstrate program behaviour and are not an air-quality assessment of Chennai.

## B1 - Implement and Validate the Cleaning Pipeline (7 marks)

The completed small CSV TODO uses `csv.DictReader`, converts PM2.5 to float, and skips blank, `NA`, negative and above-999 values. For the assignment's sample, the accepted records are Adyar 48.0, Guindy 95.0 and Guindy 121.0. Min-max output is `[0.0, 0.644, 1.0]`. An additional 1205 test value is rejected.

The full generator creates one daily CSV for each of 12 stations across 31 days, with 24 hourly measurements per file. Three exact duplicates are included. Two stations are marked as Fahrenheit sources and converted to Celsius before validation. Cleaning stores accepted readings in SQLite, records invalid/dropped/imputed data in `quality_log`, computes per-station min-max and z-score PM2.5, and builds daily summaries using SQL aggregation.

| Item | Observed result |
|---|---:|
| Stations | 12 |
| Daily source files | 372 |
| Raw rows including injected duplicates | 8,931 |
| Clean rows stored | 8,873 |
| Quality events logged | 150 |
| Daily station summary rows | 372 |

The daily summary stores station/date, minimum PM2.5, maximum PM2.5, mean PM2.5 and number of valid observations. The SQL answer for Adyar October mean PM2.5 is 48.01; 372 station/day summaries were produced. The top network hours are 08:00 (85.02), 18:00 (84.88) and 19:00 (84.72). Manali had the highest station mean (100.81). These results depend on the fixed synthetic generator seed.

Four labelled charts are produced: a line chart for the monthly PM2.5 trend, a bar chart for station comparison, a scatter plot for temperature versus PM2.5, and a box plot comparing hourly PM2.5 distributions. The scatter plot shows association only and cannot establish that temperature causes a PM2.5 change.

### CSV-loop cleaning compared with pandas

Both methods produced the same valid-row count at each input size. Timings below are reference measurements from Python 3.13.5 on the preparation environment and will vary by machine.

| Input rows | Valid rows | CSV loop time | pandas time | CSV retained result memory | pandas DataFrame memory |
|---:|---:|---:|---:|---:|---:|
| 1,000 | 990 | 0.0014 s | 0.0053 s | 0.03 MB | 0.13 MB |
| 100,000 | 98,865 | 0.1369 s | 0.0335 s | 3.03 MB | 12.82 MB |
| 1,000,000 | 988,468 | 1.3026 s | 0.2153 s | 30.68 MB | 128.20 MB |

The simple CSV loop wins for a tiny one-off input and has a lower retained result footprint in this experiment. Pandas becomes much faster at 100,000 and 1,000,000 rows because vectorised operations run in compiled code, but the DataFrame uses more memory. For regular million-row batch cleaning, pandas is preferable if memory is available; for memory-constrained streaming ingestion, process CSV rows in chunks and retain only aggregation state.

## B2 - Engineer Adversarial Data (5 marks)

The file tests deliberately supply a missing column, semicolon delimiter, UTF-16 encoding and an empty file. The current CSV contract is UTF-8 with the required header, so all four malformed files are rejected with a specific explanation before any measurements are inserted. The design avoids silently accepting a file whose columns may have shifted.

The SQL injection string is `Adyar' OR '1'='1`. A query assembled by string concatenation returns all three demonstration rows. The parameterised query with `WHERE station = ?` treats the attack as a literal station name and returns no rows. The completed SQLite TODO inserts all four observations with one `executemany()` call and a parameterised lookup; Adyar mean is 54.0 and Guindy mean is 108.0.

Sentiment adversarial examples cover sarcasm, negation, double negation and mixed opinions. The rule-based scorer handles the prompt's `not helpful` and `not bad` examples, but it can misread sarcasm or sentences containing both positive and negative facts. These cases reveal that a word-list model is useful for transparent triage but not sufficient for fully automated public-health decisions.

## B3 - Loops vs Libraries vs SQL (8 marks)

The same deterministic one-year dataset is generated for 1, 12 and 120 stations, with 8,760 hourly readings per station. The mean for each station/day is computed with a plain Python dictionary accumulator, pandas `groupby`, and SQL `GROUP BY`.

| Stations | Rows | Python loops | pandas groupby | SQLite end-to-end | SQL query only | Agreement |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 8,760 | 0.0026 s | 0.0023 s | 0.0111 s | 0.0025 s | Yes |
| 12 | 105,120 | 0.0326 s | 0.0066 s | 0.1835 s | 0.0332 s | Yes |
| 120 | 1,051,200 | 0.3576 s | 0.0527 s | 1.5994 s | 0.4395 s | Yes |

SQLite end-to-end includes loading the generated data into the database; SQL query-only measures just the grouped query after the data is stored. Pandas is fastest for this in-memory batch aggregation on the largest generated data. SQL has an initial load cost but leaves the records stored and supports repeated indexed queries. The plain Python implementation is easiest to inspect and profile, but it is slower than pandas as the row count grows.

The cProfile output identifies the `python_loop` aggregation as the main profiled function; dictionary `.get()` operations account for its repeated per-record work. The raw arrays for the 120-station case occupy about 10.03 MB in the generated benchmark. A one-pass running sum/count dictionary needs O(stations x days) aggregation state instead of retaining all O(n) readings, while both approaches process n readings in O(n) time.

## B4 - Final Engineering Decision (5 marks)

### B4.1 Complaint sentiment and summary

The lexicon scorer and frequency-based extractive summariser were run on 50 generated complaints. The sentiment output agreed with the supplied reference labels on 42 of 50 examples (84%). The eight disagreements were mostly mixed-opinion records, where the simple lexicon added positive and negative words without fully understanding the contrast, and a sarcastic or negated phrase where context mattered. The five top-frequency sentences and the first-five-sentence baseline are both saved in `outputs/complaint_summary.txt` for inspection.

The lexicon is fast, explainable and requires little memory. It is a baseline rather than a validated classifier. Human review should remain in place for mixed, neutral or low-confidence complaints. A trained local-language or multilingual classifier should only be introduced after collecting labelled local complaints and evaluating its precision, recall and class balance.

### B4.2 Database index

A composite index on `(station_id, day)` was tested against a monthly station query over the 1,051,200-row benchmark database.

| Measurement | Reference result |
|---|---:|
| Average query without index | 0.032168 s |
| Average query with index | 0.000082 s |
| Index creation time | 0.304854 s |
| Observed query speed-up | 394.2x |

The unindexed plan scans the readings table. The indexed plan uses `idx_station_day` to search the selected station/date range. The index consumes disk space and adds update cost, but substantially reduces repeated station/month lookups in this test.

### B4.3 Production decision

With 100 additional stations, the network would have 112 stations. At 15-minute intervals, each station sends 96 readings a day, so the network generates 10,752 observations daily and approximately 3,924,480 annually. Fifty thousand complaints a month is about 1,667 per day.

Keep immutable raw CSVs for traceability, use a relational database for cleaned readings and quality logs, and pre-compute daily/monthly summary tables. In production, batch inserts and keep a composite station/date index. A single-user SQLite prototype is appropriate for the assignment and small deployments; a multi-user service with concurrent writers, access controls and operational monitoring should migrate to a server database such as PostgreSQL. Keep the lexicon and summariser as a transparent first-line triage aid, then evaluate a trained model against human-labelled local complaints before deciding whether its accuracy justifies the extra memory, deployment and monitoring cost.

## Conclusion

The implementation follows the required workflow: acquire, inspect, clean, normalise, store, query, visualise, profile and interpret. It demonstrates reproducible inputs, auditable data-quality decisions, equivalent aggregation results across three methods, SQL parameterisation, measured index benefit and explicit limitations of a basic complaint AI. All measurements in this document refer to generated test data and the preparation environment, not official city monitoring records.
