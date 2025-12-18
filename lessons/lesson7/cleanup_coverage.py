import os
import shutil
from pathlib import Path
ROOT= Path(__file__).resolve().parent

for p in ROOT.glob(".coverage"):
    try:
        p.unlink()
    except FileNotFoundError:
        pass

htmlcov = ROOT / "htmlcov"
if htmlcov.is_dir():
    shutil.rmtree(htmlcov)
    