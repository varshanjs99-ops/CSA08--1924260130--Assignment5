from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PartB_Code.final_decision import main

if __name__ == '__main__':
    main()
