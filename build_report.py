from __future__ import annotations
import csv
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
    Image, HRFlowable, Preformatted, KeepTogether
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Assignment5_Report.pdf"

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"
FONT_M = "Courier"
try:
    pdfmetrics.registerFont(TTFont("SIMATS", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("SIMATS-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("SIMATS-Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))
    FONT, FONT_B, FONT_M = "SIMATS", "SIMATS-Bold", "SIMATS-Mono"
except Exception:
    pass

NAVY = HexColor("#173B5E")
BLUE = HexColor("#2874A6")
PALE = HexColor("#EAF2F8")
LIGHT = HexColor("#F5F8FA")
INK = HexColor("#25313B")
MUTED = HexColor("#617180")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", fontName=FONT_B, fontSize=22, leading=28, textColor=NAVY, alignment=TA_CENTER, spaceAfter=6))
styles.add(ParagraphStyle(name="CoverSub", fontName=FONT, fontSize=10, leading=15, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1x", fontName=FONT_B, fontSize=15, leading=19, textColor=NAVY, spaceBefore=2, spaceAfter=8))
styles.add(ParagraphStyle(name="H2x", fontName=FONT_B, fontSize=10, leading=13, textColor=BLUE, spaceBefore=7, spaceAfter=4))
styles.add(ParagraphStyle(name="Bodyx", fontName=FONT, fontSize=7.8, leading=11.3, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="Smallx", fontName=FONT, fontSize=6.6, leading=8.7, textColor=INK))
styles.add(ParagraphStyle(name="TableHeadx", fontName=FONT_B, fontSize=6.6, leading=8.2, textColor=colors.white))
styles.add(ParagraphStyle(name="Callx", fontName=FONT, fontSize=7.4, leading=10.4, textColor=INK, backColor=PALE, borderColor=HexColor("#C6D8E5"), borderWidth=.5, borderPadding=6, spaceBefore=3, spaceAfter=6))
styles.add(ParagraphStyle(name="CodeLabelx", fontName=FONT_B, fontSize=8, leading=10, textColor=BLUE, spaceBefore=4, spaceAfter=3))


def P(text: str, style="Bodyx"):
    return Paragraph(text, styles[style])


def table(rows, widths, header=True, font_size=6.6):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0,0), (-1,-1), .35, HexColor("#D6E0E8")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0,0), (-1,0), NAVY))
        if len(rows) > 1:
            commands.append(("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, LIGHT]))
    else:
        commands.append(("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, LIGHT]))
    t.setStyle(TableStyle(commands))
    return t


def footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(HexColor("#D9E2E9"))
    canvas.setLineWidth(.5)
    canvas.line(16*mm, 14*mm, width-16*mm, 14*mm)
    canvas.setFont(FONT, 6.4)
    canvas.setFillColor(MUTED)
    canvas.drawString(16*mm, 9*mm, "SIMATS Engineering | Python Programming - Assignment 5")
    canvas.drawRightString(width-16*mm, 9*mm, f"Page {doc.page}")
    canvas.restoreState()


def code(text: str):
    return Preformatted(text, ParagraphStyle("CodeBlock", fontName=FONT_M, fontSize=6.5, leading=8.4,
                                             textColor=INK, backColor=LIGHT, borderColor=HexColor("#D8E2EA"),
                                             borderWidth=.4, borderPadding=6, spaceBefore=3, spaceAfter=5))


def load_csv(name):
    with (ROOT / "outputs" / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

b1_rows = load_csv("b1_cleaning_benchmark.csv")
b3_rows = load_csv("b3_benchmark_results.csv")
metrics = {}
for line in (ROOT / "outputs" / "b4_decision_metrics.txt").read_text(encoding="utf-8").splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        metrics[k] = v

story = []
# Cover
story += [Spacer(1, 16*mm), P("SIMATS ENGINEERING", "CoverSub"), Spacer(1, 10*mm),
          P("PYTHON PROGRAMMING", "CoverTitle"), P("ASSIGNMENT 5", "CoverTitle"),
          HRFlowable(width="42%", thickness=2, color=BLUE, hAlign="CENTER"), Spacer(1, 5*mm),
          P("Data Acquisition, Cleaning, Analysis and AI Applications (CO5)", "CoverSub"),
          Spacer(1, 18*mm)]
story.append(table([
    [P("Student", "Smallx"), P("Varshan J S", "Smallx")],
    [P("Register number", "Smallx"), P("1924260130A", "Smallx")],
    [P("Institution", "Smallx"), P("SIMATS Engineering", "Smallx")],
    [P("Course outcome", "Smallx"), P("CO5 - Python libraries and tools for data acquisition, cleaning, analysis and introductory AI", "Smallx")],
    [P("Reference runtime", "Smallx"), P("Python 3.13.5; pandas 2.2.3; NumPy 2.3.5; Matplotlib 3.10.8", "Smallx")],
    [P("GitHub repository", "Smallx"), P("To be added after the Assignment 5 repository is created", "Smallx")],
], [45*mm, 115*mm], header=False))
story += [Spacer(1, 14*mm), P("Report scope", "H2x"),
          P("Part A presents the data-source review, database design, cleaning and normalisation rules, chart choices, debugging/profiling plan and AI application design. Part B implements the cleaning pipeline, SQLite storage, visualisations, adversarial tests, three-way aggregation benchmark, complaint AI and final engineering decision."),
          P("Data qualification: the assignment screenshots did not include official monitoring files. The implementation therefore generates reproducible synthetic readings for 12 Chennai-area station names over October 2026. No synthetic value is presented as an official Chennai air-quality measurement.", "Callx"),
          PageBreak()]

# Overall structure and Part A1
story += [P("Assignment Structure and Case Study", "H1x"),
          table([
              [P("Part / task", "TableHeadx"), P("Title", "TableHeadx"), P("Marks", "TableHeadx")],
              [P("A1", "Smallx"), P("Design the Data Acquisition", "Smallx"), P("7", "Smallx")],
              [P("A2", "Smallx"), P("Design the Cleaning and Normalisation", "Smallx"), P("5", "Smallx")],
              [P("A3", "Smallx"), P("Design the Analysis and Visualisation", "Smallx"), P("5", "Smallx")],
              [P("A4", "Smallx"), P("Plan Debugging and Profiling", "Smallx"), P("4", "Smallx")],
              [P("A5", "Smallx"), P("Design an AI Application for Citizen Complaints", "Smallx"), P("4", "Smallx")],
              [P("B1", "Smallx"), P("Implement and Validate the Cleaning Pipeline", "Smallx"), P("7", "Smallx")],
              [P("B2", "Smallx"), P("Engineer Adversarial Data", "Smallx"), P("5", "Smallx")],
              [P("B3", "Smallx"), P("Loops vs Libraries vs SQL", "Smallx"), P("8", "Smallx")],
              [P("B4", "Smallx"), P("Final Engineering Decision", "Smallx"), P("5", "Smallx")],
          ], [25*mm, 110*mm, 25*mm]),
          P("The simulated network includes 12 station identifiers and names: Adyar, Guindy, T Nagar, Anna Nagar, Velachery, Perungudi, Royapuram, Manali, Alandur, Kodambakkam, Nungambakkam and Thiruvottiyur. Each station sends 24 hourly observations per day for a 31-day month. PM2.5, PM10, NO2 and temperature are recorded. Nungambakkam and Thiruvottiyur are marked as Fahrenheit sources in the metadata."),
          P("A1 - Source inspection and storage design", "H2x"),
          P("The CSV contract is station ID, station name, ISO date, hour, PM2.5, PM10, NO2, temperature and temperature unit. Expected faults include missing or non-numeric readings, negative values, values above the sensor limit, duplicate station/date/hour keys, invalid date/hour values, station metadata mismatch, Fahrenheit temperatures, wrong delimiter, missing headers, unsupported encoding and empty files."),
          P("The SQLite design uses stations, readings, quality_log and daily_summary tables. `stations.station_id` is the primary key; readings have a foreign key and a unique key on station/date/hour; quality_log preserves file, line, reason and raw record; daily_summary stores min, max, mean and count. A composite index on station/date supports repeat station-month queries."),
          P("Representative SQL queries", "H2x"),
          code("SELECT station_name, AVG(pm25)\nFROM readings JOIN stations USING(station_id)\nWHERE station_name = ? AND reading_date >= ? AND reading_date < ?\nGROUP BY station_name;\n\nSELECT station_id, reading_date, MIN(pm25), MAX(pm25), AVG(pm25), COUNT(*)\nFROM readings GROUP BY station_id, reading_date;\n\nSELECT hour, AVG(pm25) AS mean_pm25\nFROM readings GROUP BY hour ORDER BY mean_pm25 DESC;"),
          P("An indexed query locates the matching station/date range in approximately O(log n + k), where k rows are read for aggregation. Reloading and parsing all CSV files for every question requires an O(n) scan and memory for the loaded data. SQLite adds database and index storage but is preferable for repeated analysis."),
          P("A1 acquisition algorithm", "H2x"),
          code("ALGORITHM AcquireAndStoreStationFiles\nBEGIN\n  INPUT raw folder and station metadata; connect to SQLite\n  CREATE tables if absent and load station metadata\n  FOR EACH daily CSV file in sorted order\n    OPEN UTF-8 file and validate required header\n    FOR EACH record with line number\n      VALIDATE station, date, hour and measurements\n      CONVERT Fahrenheit temperature to Celsius\n      IF primary PM2.5 or key is invalid THEN log and continue\n      IF station/date/hour duplicate THEN log and continue\n      INSERT values with parameterised SQL\n    END FOR\n  END FOR\n  COMMIT and close database\n  OUTPUT counts and quality log\nEND"), PageBreak()]

# A2/A3
story += [P("Part A - Cleaning, Normalisation and Visualisation", "H1x"),
          P("A2 - Cleaning rules", "H2x"),
          table([
              [P("Condition", "TableHeadx"), P("Rule", "TableHeadx"), P("Reason", "TableHeadx")],
              [P("Missing PM2.5", "Smallx"), P("Drop row; log source and reason", "Smallx"), P("PM2.5 is the primary measure and should not be fabricated", "Smallx")],
              [P("Missing PM10 / NO2", "Smallx"), P("Station-specific median imputation", "Smallx"), P("Retains auxiliary coverage while limiting outlier influence", "Smallx")],
              [P("Missing temperature", "Smallx"), P("Forward-fill within station; leading gap uses station median", "Smallx"), P("Uses local time continuity without crossing station boundaries", "Smallx")],
              [P("Negative / above-999 pollutants", "Smallx"), P("Reject primary PM2.5; invalid auxiliary channels set NULL then imputed", "Smallx"), P("Treats impossible sensor values as faults", "Smallx")],
              [P("Duplicate key", "Smallx"), P("Keep first station/date/hour record; log later duplicate", "Smallx"), P("One observation per station and hour", "Smallx")],
              [P("Fahrenheit reading", "Smallx"), P("Convert using (F - 32) x 5/9", "Smallx"), P("Stores temperature consistently in Celsius", "Smallx")],
          ], [37*mm, 62*mm, 61*mm]),
          P("PM2.5 min-max normalisation uses (x - min) / (max - min). Z-score uses (x - mean) / population standard deviation. Both are calculated per station; the raw PM2.5 value remains available for original-unit reporting. Constant ranges map to zero to avoid division by zero. Dates use YYYY-MM-DD, station names use the metadata spelling, numeric readings are REAL, missing values are SQL NULL and temperature is stored in Celsius."),
          P("A2 cleaning algorithm - key steps", "H2x"),
          code("ALGORITHM CleanAndNormaliseStationReadings\nBEGIN\n  GROUP readings by station and sort each group by date/hour\n  FIND station medians for PM10, NO2 and temperature\n  FOR EACH reading\n    IF PM2.5 missing, negative or above 999 THEN log and remove\n    IF PM10 or NO2 missing/impossible THEN median-impute and log\n    IF temperature missing/impossible THEN forward-fill or use median\n  END FOR\n  COMPUTE station PM2.5 min, max, mean and standard deviation\n  CALCULATE min-max and z-score for retained readings\n  OUTPUT cleaned data and quality log\nEND"),
          P("A3 - Chart design", "H2x"),
          table([
              [P("Question", "TableHeadx"), P("Chart", "TableHeadx"), P("Why it fits", "TableHeadx")],
              [P("Monthly PM2.5 trend", "Smallx"), P("Line chart", "Smallx"), P("Shows daily direction, spikes and changes over time", "Smallx")],
              [P("Station comparison", "Smallx"), P("Bar chart", "Smallx"), P("Ranks station mean values", "Smallx")],
              [P("Temperature vs PM2.5", "Smallx"), P("Scatter plot", "Smallx"), P("Shows association, clusters and outliers, not causation", "Smallx")],
              [P("Hours with worst air", "Smallx"), P("Box plot by hour", "Smallx"), P("Compares median, spread and outliers for each hour", "Smallx")],
          ], [46*mm, 37*mm, 77*mm]),
          P("The daily summary table contains station/date, PM2.5 minimum, maximum, mean and valid observation count. It is produced with SQL GROUP BY and stored for repeated queries. A Python loop and SQL aggregation both take O(n) time; SQL can reduce application-side memory and the summary table speeds repeated reports at the cost of storage."),
          P("A3 daily summary algorithm", "H2x"),
          code("ALGORITHM BuildDailyStationSummary\nBEGIN\n  GROUP cleaned readings by station and date\n  FOR EACH group\n    CALCULATE minimum, maximum and mean PM2.5\n    COUNT valid readings and store summary row\n  END FOR\n  OUTPUT daily summary table\nEND"), PageBreak()]

# A4/A5
story += [P("Part A - Debugging, Profiling and AI Design", "H1x"),
          P("A4 - Debugging plan", "H2x"),
          P("Use temporary print statements to inspect a few raw rows, parsed data types, rejection counts and station/date keys. Add assertions for hour bounds, PM2.5 range, foreign keys and uniqueness. Use the logging module with DEBUG for row-level diagnosis, INFO for batch totals and WARNING/ERROR for invalid records and file failures. Use pdb or the VS Code debugger to step through parsing, conversion, normalisation and SQLite insertion. Preserve malformed examples as regression tests."),
          P("A4 - Profiling plan", "H2x"),
          P("Measure acquisition, cleaning, database insertion, aggregation and chart rendering separately with time.perf_counter(). Use timeit for small functions and cProfile for the plain-Python aggregation. Compare repeated runs against the same input and verify output equality before comparing speed. Thousands of print calls add formatting and terminal I/O overhead; logging levels can be raised to WARNING or ERROR in production."),
          P("A5 - Complaint AI design", "H2x"),
          P("The lexicon baseline adds +1 for a positive token and -1 for a negative token. An immediately preceding negator flips the next opinion token; two consecutive negators cancel by parity. Positive totals are labelled positive, negative totals negative and zero neutral. The extractive summariser splits complaints into sentences, removes common words, counts informative-word frequency and selects sentences with the strongest frequency score."),
          P("The rule-based chatbot identifies a station and measure (PM2.5, PM10, NO2 or temperature), selects an explicit date or the latest date in the sample database, and runs a parameterised SQL query. It must label that date as the latest sample date rather than the actual current day. Sarcasm, mixed opinions and implicit context are limitations. A trained Naive Bayes or language model could improve contextual classification after collecting local labelled examples, but would need model memory, evaluation and monitoring; uncertain complaints should remain subject to human review."),
          code("ALGORITHM AnswerCitizenAirQualityQuestion\nBEGIN\n  INPUT citizen question\n  IDENTIFY pollutant, station and date (or latest stored sample date)\n  IF required field cannot be identified THEN return clarification\n  EXECUTE parameterised SQL query\n  IF no reading exists THEN return no-data message\n  ELSE return average, date and unit\nEND"), PageBreak()]

# B1
story += [P("Part B - Implementation and Experimental Investigation", "H1x"),
          P("B1 - Cleaning pipeline and validation", "H2x"),
          P("The generated dataset contains 12 stations, 31 days and 24 nominal hourly observations per station/day. The code validates required CSV headers, date/hour fields, station identity and sensor ranges. Duplicate keys are rejected, Fahrenheit readings are converted to Celsius, missing PM2.5 rows are dropped, auxiliary gaps are imputed and all actions are written to a quality log. Cleaned readings are stored in SQLite and a daily summary is computed with SQL aggregation."),
          table([
              [P("Measure", "TableHeadx"), P("Result", "TableHeadx")],
              [P("Station count", "Smallx"), P("12", "Smallx")],
              [P("Daily station files", "Smallx"), P("372", "Smallx")],
              [P("Raw rows including injected duplicates", "Smallx"), P("8,931", "Smallx")],
              [P("Clean rows stored", "Smallx"), P("8,873", "Smallx")],
              [P("Quality events", "Smallx"), P("150", "Smallx")],
              [P("Daily summary rows", "Smallx"), P("372", "Smallx")],
          ], [92*mm, 68*mm]),
          P("The small completed-code example returns Adyar 48.0, Guindy 95.0 and Guindy 121.0. The normalised values are 0.000, 0.644 and 1.000. A 1205 test value is skipped. SQL results for the full synthetic month: Adyar mean PM2.5 is 48.01; 372 daily station summaries were created; the top network hours are 08:00 (85.02), 18:00 (84.88) and 19:00 (84.72). Manali has the highest station mean (100.81). These are properties of the generated test sample only."),
          P("CSV loop vs pandas cleaning benchmark", "H2x"),
          table([[P("Input rows", "TableHeadx"), P("Valid", "TableHeadx"), P("CSV time", "TableHeadx"), P("Pandas time", "TableHeadx"), P("CSV result MB", "TableHeadx"), P("Pandas frame MB", "TableHeadx")]] + [
              [P(f"{int(r['input_rows']):,}", "Smallx"), P(f"{int(r['valid_rows']):,}", "Smallx"), P(f"{float(r['csv_loop_seconds']):.4f}s", "Smallx"), P(f"{float(r['pandas_seconds']):.4f}s", "Smallx"), P(r['csv_retained_result_mb'], "Smallx"), P(r['pandas_frame_mb'], "Smallx")]
              for r in b1_rows
          ], [24*mm, 22*mm, 25*mm, 27*mm, 28*mm, 34*mm]),
          P("Both implementations retained the same valid-row count. CSV loops were faster for 1,000 rows, while pandas was faster at 100,000 and 1,000,000 rows. The pandas DataFrame used more memory in this experiment; a chunked CSV pipeline is an option when RAM is constrained.", "Callx"), PageBreak()]

# B1 Charts two per page
story += [P("B1 - Visualisation Evidence", "H1x"),
          P("The chart inputs come from cleaned SQLite readings. The data is simulated, and the units are shown as generated measurements rather than official monitoring outputs."),
          Image(str(ROOT / "charts" / "01_monthly_pm25_trend.png"), width=165*mm, height=74*mm),
          P("Figure 1. Daily mean PM2.5 over October 2026. The line shows recurring variation from day to day; the pattern reflects the deterministic test-data generator and should not be interpreted as a real city trend.", "Smallx"),
          Spacer(1, 2*mm),
          Image(str(ROOT / "charts" / "02_station_comparison.png"), width=165*mm, height=74*mm),
          P("Figure 2. Station mean PM2.5. Manali ranks highest in the simulated sample. The bar chart supports station comparison but does not establish why the readings differ.", "Smallx"), PageBreak()]

story += [P("B1 - Additional Visualisation Evidence", "H1x"),
          Image(str(ROOT / "charts" / "03_temperature_vs_pm25.png"), width=165*mm, height=76*mm),
          P("Figure 3. Temperature versus PM2.5. The scatter plot shows the spread and possible association between variables; correlation does not imply that temperature causes a change in PM2.5.", "Smallx"),
          Spacer(1, 2*mm),
          Image(str(ROOT / "charts" / "04_hourly_pm25_boxplot.png"), width=165*mm, height=76*mm),
          P("Figure 4. Hourly PM2.5 distribution. Comparing medians and spread indicates how the hourly profile varies. 08:00 had the highest average hour in the generated data.", "Smallx"), PageBreak()]

# B2
story += [P("B2 - Adversarial Data and SQL Safety", "H1x"),
          table([
              [P("Adversarial input", "TableHeadx"), P("Observed handling", "TableHeadx"), P("Design lesson", "TableHeadx")],
              [P("Missing CSV column", "Smallx"), P("Rejected with exact missing-column list", "Smallx"), P("Validate schema before processing", "Smallx")],
              [P("Wrong delimiter", "Smallx"), P("Header parsed as one field; required columns absent", "Smallx"), P("Reject rather than silently shift fields", "Smallx")],
              [P("UTF-16 encoding", "Smallx"), P("Rejected as unsupported UTF-8 input", "Smallx"), P("Declare and validate file encoding", "Smallx")],
              [P("Empty file", "Smallx"), P("Rejected as empty/no header", "Smallx"), P("Do not treat empty input as an empty successful batch", "Smallx")],
          ], [37*mm, 61*mm, 62*mm]),
          P("The SQL injection value `Adyar' OR '1'='1` made the string-concatenated demonstration query return all three rows. The parameterised query treated the value literally and returned zero rows. The completed TODO uses one executemany call for all inserts and a question-mark placeholder in the station lookup; the verified averages are Adyar 54.0 and Guindy 108.0."),
          P("The sentiment adversarial set contains sarcasm, double negation and mixed opinions. The simple word-list approach is transparent but does not fully understand sarcasm and sentence contrast. The B4 test on 50 examples is used to quantify its agreement with the reference labels."),
          P("B3 - Three-way aggregation benchmark", "H2x"),
          table([[P("Stations", "TableHeadx"), P("Rows", "TableHeadx"), P("Python loop", "TableHeadx"), P("pandas", "TableHeadx"), P("SQLite total", "TableHeadx"), P("SQL query", "TableHeadx")]] + [
              [P(str(r['stations']), "Smallx"), P(f"{int(r['rows']):,}", "Smallx"), P(f"{float(r['python_loop_seconds']):.4f}s", "Smallx"), P(f"{float(r['pandas_groupby_seconds']):.4f}s", "Smallx"), P(f"{float(r['sqlite_end_to_end_seconds']):.4f}s", "Smallx"), P(f"{float(r['sqlite_query_only_seconds']):.4f}s", "Smallx")]
              for r in b3_rows
          ], [20*mm, 27*mm, 29*mm, 23*mm, 31*mm, 30*mm]),
          P("All three methods agreed for 8,760, 105,120 and 1,051,200 readings. Pandas groupby was fastest for the largest in-memory batch. SQLite end-to-end includes loading rows; query-only time is lower and becomes attractive when the data is already stored. The cProfile report identifies the plain Python loop and repeated dictionary lookups as its main profiled work. The 120-station NumPy input arrays used about 10.03 MB.", "Callx"), PageBreak()]

# B4 decision
story += [P("B4 - Complaint AI and Final Engineering Decision", "H1x"),
          P("B4.1 - Sentiment and extractive summary", "H2x"),
          P(f"The lexicon scorer evaluated 50 generated complaints and agreed with the reference labels on {metrics['agreement']} examples ({100*int(metrics['agreement'].split('/')[0])/int(metrics['agreement'].split('/')[1]):.1f}%). The disagreements are mainly mixed-opinion sentences where the word list counts positive and negative terms without understanding the contrast. `outputs/complaint_predictions.csv` contains each reference label and prediction; `outputs/complaint_summary.txt` compares the top-frequency sentence selection with the first-k baseline."),
          P("A rule-based chatbot answers station/pollutant/date questions by issuing a parameterised SQLite query. It reports the latest available sample date when the question says 'today'; it does not claim that the synthetic October data is real-time. Lexicon AI is a useful transparent triage baseline, but uncertain, sarcastic and health-related complaints require human review."),
          P("B4.2 - Composite index experiment", "H2x"),
          table([
              [P("Measurement", "TableHeadx"), P("Reference result", "TableHeadx")],
              [P("Mean query time without index", "Smallx"), P(f"{float(metrics['query_without_index'])*1000:.3f} ms", "Smallx")],
              [P("Mean query time with index", "Smallx"), P(f"{float(metrics['query_with_index'])*1000:.3f} ms", "Smallx")],
              [P("Index build time", "Smallx"), P(f"{float(metrics['index_build']):.3f} s", "Smallx")],
              [P("Observed speed-up", "Smallx"), P(f"{float(metrics['query_without_index'])/float(metrics['query_with_index']):.1f}x", "Smallx")],
          ], [72*mm, 88*mm]),
          P("Without the index, SQLite scans the benchmark readings table. With the composite (station_id, day) index, the query plan searches the selected station/date range. The index consumes storage and increases update cost, but it substantially reduces repeated station/month query time on the test database."),
          P("B4.3 - Production decision", "H2x"),
          P("At 112 stations reporting every 15 minutes, the board would receive 10,752 readings each day and approximately 3,924,480 per year. Fifty thousand complaints per month is about 1,667 each day. Keep raw CSV files immutable for traceability; store cleaned readings and quality events in a relational database; create daily/monthly summary tables; use batched writes and a composite station/date index. SQLite is appropriate for this single-user prototype, while a concurrent production service should evaluate PostgreSQL or another server database."),
          P("Use the lexicon and extractive summary as a baseline, not as an automated authority. Collect locally labelled complaints, evaluate a trained classifier's precision/recall and class balance, and retain human review for uncertain or high-impact reports.", "Callx"), PageBreak()]

# Conclusion / caveats
story += [P("Overall Evaluation and Submission Notes", "H1x"),
          P("The project demonstrates the assignment workflow: acquire, inspect, clean, normalise, store, query, visualise, profile and interpret. It contains executable source modules, synthetic input files, an SQLite database, quality logs, summary outputs, charts, timing files, cProfile evidence and a README."),
          table([
              [P("Task", "TableHeadx"), P("Implementation result", "TableHeadx"), P("Primary evidence", "TableHeadx")],
              [P("B1", "Smallx"), P("8,873 cleaned rows; 150 quality events; 372 daily summaries", "Smallx"), P("SQLite database, CSV outputs, four charts and 1k/100k/1m benchmark", "Smallx")],
              [P("B2", "Smallx"), P("Four malformed-file tests rejected; injection neutralised by placeholder", "Smallx"), P("Adversarial log and completed SQLite TODO output", "Smallx")],
              [P("B3", "Smallx"), P("All loop/pandas/SQL group means agree up to 1,051,200 rows", "Smallx"), P("Benchmark CSV and cProfile text", "Smallx")],
              [P("B4", "Smallx"), P("42/50 sentiment agreement; measured index improvement", "Smallx"), P("Prediction CSV, summary and index metrics", "Smallx")],
          ], [18*mm, 70*mm, 72*mm]),
          P("Complexity summary", "H2x"),
          P("CSV validation and cleaning are O(n) over n readings. Group aggregation is O(n) for Python, pandas and SQL. A running sum/count dictionary uses O(stations x days) state rather than retaining O(n) readings. A station/date index supports approximately O(log n + k) lookup, where k is the matching range read. Lexicon sentiment is O(w) in the number of complaint tokens; extractive ranking also orders sentence scores."),
          P("Reference environment: Python 3.13.5, pandas 2.2.3, NumPy 2.3.5 and Matplotlib 3.10.8 on the preparation environment. The student's Windows VS Code environment previously reported Python 3.14.2. Re-run the programs on that computer and record local timings before submission; performance values will differ between machines."),
          P("Submission reminder", "H2x"),
          P("Create a public or faculty-shared repository named `CSA08-1924260130A-Assignment5`, add at least one meaningful commit per task, and place the working GitHub URL on this cover page and in README.md. The assignment asks for genuine execution screenshots. The package includes text logs; capture terminal screenshots from the student's own VS Code runs and save them inside the corresponding task folders before uploading."),
          P("Conclusion", "H2x"),
          P("The design combines auditable data-quality decisions, reproducible inputs, relational storage, suitable visualisations, measured performance comparisons, safe SQL parameterisation and a clearly bounded complaint AI baseline. The results are supported by repeatable scripts and are explicitly qualified as synthetic test evidence rather than official environmental measurements.")]


doc = SimpleDocTemplate(str(OUT), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                        topMargin=15*mm, bottomMargin=19*mm,
                        title="SIMATS Engineering - Python Programming Assignment 5",
                        author="Varshan J S",
                        subject="Data Acquisition, Cleaning, Analysis and AI Applications")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(f"Created {OUT} ({OUT.stat().st_size:,} bytes)")
