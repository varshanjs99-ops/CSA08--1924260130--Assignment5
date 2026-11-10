from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PartB_Code.complete_code_b1 import load_clean, min_max, RAW

if __name__ == '__main__':
    clean = load_clean(RAW)
    print('B1 - COMPLETED TODO CODE')
    print('Before cleaning:')
    print(RAW)
    print('After cleaning:')
    print(clean)
    print('Min-max values:', min_max([pm for _, _, pm in clean]))
    assert clean == [('Adyar', '2026-10-01', 48.0), ('Guindy', '2026-10-01', 95.0), ('Guindy', '2026-10-03', 121.0)]
    print('Outlier >999 skipped: PASS')
