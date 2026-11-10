"""Run every Assignment 5 implementation task in the required order and save logs."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"

STEPS = [
    ("Generate synthetic station CSV files", ["generate_data.py"], "00_generate_data.txt"),
    ("B1 completed TODO", ["TaskB1/complete_code.py"], "b1_complete_code.txt"),
    ("B1 clean/store/visualise", ["TaskB1/run_pipeline.py"], "b1_pipeline_and_charts.txt"),
    ("B1 CSV vs pandas cleaning benchmark", ["TaskB1/run_cleaning_benchmark.py"], "b1_cleaning_benchmark.txt"),
    ("B2 completed SQLite TODO", ["TaskB2/complete_code.py"], "b2_complete_code.txt"),
    ("B2 adversarial input tests", ["TaskB2/run_adversarial_tests.py"], "b2_adversarial_tests.txt"),
    ("B3 loops vs pandas vs SQL benchmark", ["TaskB3/run_benchmark.py"], "b3_benchmark.txt"),
    ("B4 final engineering decision", ["TaskB4/run_final_decision.py"], "b4_final_decision.txt"),
]


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for title, args, evidence_name in STEPS:
        print(f"\n{'=' * 72}\n{title}\n{'=' * 72}", flush=True)
        process = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
        combined = process.stdout + ("\nSTDERR:\n" + process.stderr if process.stderr else "")
        (EVIDENCE / evidence_name).write_text(combined, encoding="utf-8")
        print(combined, end="", flush=True)
        if process.returncode != 0:
            raise SystemExit(f"Failed at: {title} (exit code {process.returncode})")
        print(f"[PASS] {title}", flush=True)
    print("\nAll Assignment 5 implementation tasks completed successfully.")


if __name__ == "__main__":
    main()
