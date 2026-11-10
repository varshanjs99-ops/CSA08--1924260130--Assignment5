# Assignment 5 - Part A: Data and Program Design

**Student:** Varshan J S  
**Register number:** 1924260130A  
**Institution:** SIMATS Engineering  
**Course outcome:** CO5 - Python libraries and tools for data acquisition, cleaning, visualisation and analysis  
**Case study:** City Air-Quality Monitoring Network  
**Marks:** 25

> **Data qualification.** The assignment screenshots do not include real station CSV files. The proposed implementation therefore uses reproducible synthetic station data for testing. No generated value is represented as an official Chennai pollution measurement.

## A1 - Design the Data Acquisition (7 marks)

### A1.1 Inspect the source

Each station sends one CSV file per day. Each record represents one hourly observation. The implementation uses the following header:

`station_id,station,date,hour,pm25,pm10,no2,temperature,temperature_unit`

| Field | Meaning | Example | Expected type |
|---|---|---|---|
| station_id | Stable station identifier | ST01 | Text |
| station | Human-readable station name | Adyar | Text |
| date | Observation date | 2026-10-01 | ISO date text |
| hour | Hour of day | 8 | Integer 0-23 |
| pm25 | Fine particulate reading | 48.0 | Real |
| pm10 | Coarse particulate reading | 91.0 | Real |
| no2 | Nitrogen dioxide reading | 30.5 | Real |
| temperature | Sensor temperature | 31.2 or 88.2 | Real |
| temperature_unit | Unit reported by station | C or F | Text |

Expected data-quality problems and controls:

| Problem | Example | Control |
|---|---|---|
| Missing numeric value | blank, `NA` | Drop row when PM2.5 is missing; impute auxiliary fields using documented rules |
| Negative pollutant | PM2.5 = -12 | Reject as impossible and record the source row |
| Implausibly large sensor value | PM2.5 = 1205 | Reject pollutant values outside 0-999 |
| Duplicate observation | Same station/date/hour twice | Keep the first occurrence and record the duplicate |
| Fahrenheit temperature | 88.2 F | Convert to Celsius using (F - 32) x 5/9 |
| Invalid date or hour | 2026/31/99, hour 27 | Reject row with line number and reason |
| Station mismatch | ST01 labelled as Guindy | Compare the ID/name pair with station metadata |
| File-format fault | Missing header or wrong delimiter | Validate required CSV columns before processing |
| Text encoding fault | UTF-16 file when UTF-8 is required | Catch decoding error and record the rejected file |

### A1.2 Design the storage

Use three core SQLite tables plus a derived daily summary. `stations` stores stable station metadata. `readings` stores one cleaned hourly observation. `quality_log` preserves rejected or imputed data events. `daily_summary` stores results that are repeatedly requested by the board.

```sql
CREATE TABLE stations (
    station_id TEXT PRIMARY KEY,
    station_name TEXT NOT NULL UNIQUE,
    temperature_unit_source TEXT NOT NULL,
    data_type TEXT NOT NULL
);

CREATE TABLE readings (
    reading_id INTEGER PRIMARY KEY,
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    reading_date TEXT NOT NULL,
    hour INTEGER NOT NULL,
    pm25 REAL NOT NULL,
    pm10 REAL,
    no2 REAL,
    temperature_c REAL,
    pm25_minmax REAL,
    pm25_zscore REAL,
    source_file TEXT NOT NULL,
    UNIQUE(station_id, reading_date, hour)
);

CREATE TABLE quality_log (
    quality_id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    station_id TEXT,
    reading_date TEXT,
    issue TEXT NOT NULL,
    raw_record TEXT
);

CREATE TABLE daily_summary (
    station_id TEXT NOT NULL REFERENCES stations(station_id),
    reading_date TEXT NOT NULL,
    pm25_min REAL NOT NULL,
    pm25_max REAL NOT NULL,
    pm25_mean REAL NOT NULL,
    valid_readings INTEGER NOT NULL,
    PRIMARY KEY(station_id, reading_date)
);
```

CSV-to-database mapping: `station_id` joins to `stations.station_id`; `station` is stored as `stations.station_name`; `date` maps to `readings.reading_date`; `hour` maps to `readings.hour`; PM2.5, PM10 and NO2 map to their REAL columns; Fahrenheit temperature is converted before storing in `temperature_c`; `source_file` records provenance. The unique key on `(station_id, reading_date, hour)` prevents a duplicate hourly reading from being stored twice. A composite index on `(station_id, reading_date)` supports common station/date queries.

**Acquisition and storage pseudocode (SIMATS-style algorithmic form):**

```text
ALGORITHM AcquireAndStoreStationFiles
BEGIN
    INPUT raw_folder, station_metadata
    CONNECT to air_quality_database
    CREATE stations, readings and quality_log tables if absent
    LOAD station_metadata into stations table
    FOR EACH file IN sorted daily_station_files
        OPEN file using UTF-8 decoding
        READ and validate the required CSV header
        IF header is invalid THEN
            RECORD file-level error
            CONTINUE with next file
        END IF
        FOR EACH record with its line number
            VALIDATE station ID, date and hour
            CONVERT temperature to Celsius when source unit is Fahrenheit
            VALIDATE PM2.5, PM10, NO2 and temperature
            IF record has invalid primary PM2.5 or invalid key THEN
                RECORD the rejected record and reason
                CONTINUE with next record
            END IF
            IF station/date/hour key already exists THEN
                RECORD duplicate and CONTINUE with next record
            END IF
            INSERT cleaned record using parameterised values
        END FOR
        CLOSE file
    END FOR
    COMMIT database transaction
    CLOSE database connection
    OUTPUT cleaned record count and quality log
END
```

### A1.3 CSV or SQL?

Three common board questions and their SQL form are:

**1. What was the average PM2.5 at Adyar during October?**

```sql
SELECT s.station_name, AVG(r.pm25) AS mean_pm25
FROM readings AS r
JOIN stations AS s ON s.station_id = r.station_id
WHERE s.station_name = 'Adyar'
  AND r.reading_date >= '2026-10-01'
  AND r.reading_date < '2026-11-01'
GROUP BY s.station_name;
```

**2. What are each station's minimum, maximum and mean PM2.5 values for each day?**

```sql
SELECT station_id, reading_date,
       MIN(pm25), MAX(pm25), AVG(pm25), COUNT(pm25)
FROM readings
GROUP BY station_id, reading_date;
```

**3. Which hours have the highest average PM2.5 across the network?**

```sql
SELECT hour, AVG(pm25) AS mean_pm25
FROM readings
GROUP BY hour
ORDER BY mean_pm25 DESC;
```

Repeatedly loading every CSV into a DataFrame requires a full O(n) scan for each question and consumes memory proportional to the loaded data. SQLite stores the data on disk and can use indexes to locate matching station/date rows in approximately O(log n + k), where k is the number of matching rows still needed for aggregation. An index adds disk space and maintenance cost, but avoids repeatedly parsing all CSV files. For one small one-off file, CSV is convenient; for recurring monthly questions, multiple stations and reusable summaries, SQLite is preferable.

## A2 - Design the Cleaning and Normalisation (5 marks)

### A2.1 Cleaning rules

1. **Primary measure missing:** blank, `NA` or non-numeric PM2.5 is dropped because the main analysis cannot be computed without it. Record the source filename, row number and reason.
2. **Auxiliary measure missing:** missing PM10 and NO2 are imputed with the median valid value for that station. Keep an audit record of each imputation. If no valid station values exist, keep NULL rather than invent a value.
3. **Temperature missing:** forward-fill from the previous valid temperature at the same station after chronological sorting. A leading gap uses the station median. Never fill across stations.
4. **Impossible measurements:** negative pollutant values and pollutant values above 999 are rejected or stored as NULL for auxiliary channels. Temperature outside -20 to 60 Celsius after unit conversion is treated as a sensor fault and imputed using the temperature rule.
5. **Duplicates:** use `(station_id, date, hour)` as the natural observation key; preserve the first record and log later occurrences.
6. **Fahrenheit:** convert the two Fahrenheit-reporting stations to Celsius before validation and storage. Preserve the original unit in station metadata.

The primary PM2.5 row-drop rule avoids manufacturing the outcome variable. Median imputation of auxiliary channels is robust to skewed distributions; forward fill is suitable for a short temperature gap because adjacent hourly readings are close in time. All imputation must be flagged so an analyst can distinguish measured from estimated values.

### A2.2 Normalisation

For a station's PM2.5 values x:

- **Min-max normalisation:** `x_scaled = (x - minimum) / (maximum - minimum)`. This maps the station's observed range to 0-1. It is useful for visual comparison on a common scale, but is sensitive to extreme values.
- **Z-score standardisation:** `z = (x - mean) / population_standard_deviation`. This expresses how far a reading is from the station's typical level in standard deviations. It is useful for relative anomaly analysis and does not force values into a fixed range. If the standard deviation is zero, define z as zero; if max equals min, define min-max as zero.

Normalisation is calculated per station so that differences in station baselines do not dominate the scale. Raw PM2.5 remains stored for reporting in original units.

**Cleaning and normalisation pseudocode:**

```text
ALGORITHM CleanAndNormaliseStationReadings
BEGIN
    INPUT parsed_records
    GROUP records by station ID
    FOR EACH station group
        SORT records by date and hour
        FIND station median for PM10, NO2 and temperature
        SET previous_temperature to NOT_AVAILABLE
        FOR EACH record
            IF PM2.5 is missing, negative or above 999 THEN
                LOG issue and REMOVE record
                CONTINUE with next record
            END IF
            IF PM10 or NO2 is missing or impossible THEN
                REPLACE it with the station median when one exists
                LOG the imputation
            END IF
            IF temperature is missing or impossible THEN
                USE previous valid temperature, otherwise station median
                LOG the imputation
            END IF
            UPDATE previous_temperature
        END FOR
        COMPUTE station PM2.5 minimum, maximum, mean and standard deviation
        FOR EACH retained record
            CALCULATE min-max and z-score values
        END FOR
    END FOR
    OUTPUT cleaned records and quality log
END
```

### A2.3 Standard formats

- Dates: ISO 8601 `YYYY-MM-DD`.
- Times: integer hour 0-23; if minute-level data is introduced, use ISO timestamp with an explicit timezone.
- Station names: trimmed, canonical spelling from the `stations` table.
- Pollutants: floating-point numeric values; PM2.5, PM10 and NO2 retained in their source measurement units.
- Temperature: Celsius in the cleaned database, rounded only for display.
- Missing values: SQL NULL, not the text strings `NA`, `N/A` or an empty string.

If missing values were all dropped, daily means could become biased when missingness is systematic. Forward fill is O(n) and avoids sorting, while a median generally requires O(n log n) time to sort (or expected O(n) selection) and additional storage. A station-specific median is safer than using one city-wide median.

## A3 - Design the Analysis and Visualisation (5 marks)

### A3.1 Chart selection

| Board question | Chart | Reason |
|---|---|---|
| PM2.5 trend over a month | Line chart of daily mean PM2.5 | Shows temporal direction, spikes and changes |
| Compare stations | Bar chart of station mean PM2.5 | Makes ranking and differences between stations easy to compare |
| Temperature-PM2.5 relationship | Scatter plot | Shows association, clustering and possible outliers without implying causation |
| Hours with the worst air | Box plot by hour | Compares median, spread and outliers across hourly distributions |

Every chart needs a descriptive title, labelled axes, units, date range and an indication that the data is synthetic. Use the same aggregation rule and cleaned data for all charts.

**Daily summary pseudocode:**

```text
ALGORITHM BuildDailyStationSummary
BEGIN
    INPUT cleaned_readings
    GROUP readings by station ID and reading date
    FOR EACH station/date group
        CALCULATE minimum PM2.5
        CALCULATE maximum PM2.5
        CALCULATE mean PM2.5
        COUNT valid PM2.5 observations
        STORE one summary row
    END FOR
    OUTPUT daily summary table
END
```

### A3.2 Daily summary table

One row per station/day: `station_id`, `reading_date`, `pm25_min`, `pm25_max`, `pm25_mean`, `valid_readings`. Produce it with an SQL `GROUP BY station_id, reading_date`, using `MIN`, `MAX`, `AVG` and `COUNT`. Index the source table by station/date. SQL performs aggregation close to stored data and avoids loading every reading into a Python object. Both SQL aggregation and a one-pass Python accumulator are O(n) in the number of readings; SQL can use lower application memory, while a Python loop must retain at least a dictionary of group accumulators or a materialised input list. A summary table consumes additional disk space but makes repeated reports faster.

## A4 - Plan Debugging and Profiling (4 marks)

### A4.1 Debugging plan

- Add temporary print statements for the first few raw rows, parsed types, rejected-row count and the station/date key. Remove or disable verbose output after diagnosis.
- Add assertions for invariants: valid hour is 0-23, stored PM2.5 is between 0 and 999, every station foreign key exists, and no duplicate station/date/hour key exists.
- Use the logging module with DEBUG for row-level investigation, INFO for batch totals and WARNING/ERROR for rejected records and file-level failures. Configure logging levels so production does not write thousands of debug messages.
- Use `pdb` or the IDE debugger to set breakpoints in parsing, unit conversion, normalisation and SQL insertion. Inspect a known malformed row and trace its path.
- Keep failing input examples as regression tests.

### A4.2 Profiling plan

Measure elapsed time around file acquisition, cleaning, database insertion, SQL aggregation and chart rendering using `time.perf_counter()`. Use `timeit` for small isolated functions. Run `cProfile` on the plain-Python aggregation path and inspect cumulative time to find the slowest function. Repeat measurements at increasing data sizes, use the same generated input and compare outputs before comparing speed. Profiling output and benchmark CSVs are saved in `evidence/` and `outputs/`.

Using print statements for every one of thousands of rows adds I/O and formatting overhead and can make the measured program much slower. Logging provides levels and can be disabled or raised to WARNING. A debugger is used interactively and does not need to run in production. Keep only concise batch summaries in normal operation.

## A5 - Design an AI Application for Citizen Complaints (4 marks)

### A5.1 Sentiment and summary

Use a transparent word-list sentiment baseline. Positive words add +1, negative words add -1, and a directly preceding negator flips the next sentiment word. Two adjacent negators cancel under the simple parity rule. The total above zero is positive, below zero is negative and zero is neutral. The approach is easy to explain and fast, but sarcasm, implicit meaning, domain terms and long-range grammar can cause errors.

For extractive summarisation, split complaints into sentences, remove common stop words, count informative word frequencies and score each sentence using the frequencies of its terms. Select the highest-scoring sentences while preserving their original text. A first-k-sentence baseline is constant-time selection after sentence splitting but may miss important topics; frequency scoring takes O(w) over w tokens plus ranking cost and needs a word-frequency map.

### A5.2 Basic chatbot

The rule-based chatbot detects a station name and a requested measure (PM2.5, PM10, NO2 or temperature), extracts an explicit date when supplied, or uses the latest available date in the sample database. It submits a parameterised SQL query and explains when no data is available. The latest sample date must not be presented as the real current date. This chatbot is retrieval-based, not generative.

**Chatbot pseudocode:**

```text
ALGORITHM AnswerCitizenAirQualityQuestion
BEGIN
    INPUT citizen_question
    IDENTIFY requested pollutant and station name
    IDENTIFY explicit date; otherwise select latest date available in sample data
    IF pollutant or station cannot be identified THEN
        RETURN a request for a supported pollutant/station
    END IF
    EXECUTE a parameterised SQL query for station, date and pollutant
    IF no valid reading exists THEN
        RETURN a no-data message
    ELSE
        RETURN the computed average with date and measurement unit
    END IF
END
```

A trained Naive Bayes classifier or a suitable language model could better recognise context, sarcasm and local complaint language if trained/evaluated on labelled local examples. It requires labelled data, model storage, validation and monitoring. A pre-trained language model generally uses more memory and compute per complaint than a small lexicon, and may still hallucinate or misread local references. Keep the simple model as a transparent baseline and human-review uncertain complaints.
