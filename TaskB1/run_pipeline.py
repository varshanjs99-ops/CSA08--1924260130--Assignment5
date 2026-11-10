from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PartB_Code.pipeline import run_pipeline
from PartB_Code.analysis_visuals import create_visualisations

if __name__ == '__main__':
    run_pipeline()
    create_visualisations()
