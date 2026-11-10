# B3 - Loops vs Libraries vs SQL

Run `py TaskB3/run_benchmark.py` from the project root. The script generates one-year datasets for 1, 12 and 120 stations, compares Python loops, pandas groupby and SQLite GROUP BY, saves timings, and writes a cProfile report. It also creates `outputs/benchmark_120.db` for the B4 index test; that large generated file is ignored by Git and can be rebuilt by rerunning B3.
