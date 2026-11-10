# Assignment 5 - Part A Design

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
