# Assignment 5 - Part A Design

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
