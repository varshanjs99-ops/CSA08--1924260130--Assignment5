# Assignment 5 - Part A Design

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
