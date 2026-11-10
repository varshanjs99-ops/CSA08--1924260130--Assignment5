# Assignment 5 - Part A Design

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
