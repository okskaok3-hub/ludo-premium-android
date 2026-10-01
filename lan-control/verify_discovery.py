"""Run discovery and connection verification for the current companion UI."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name("verify_premium.py")),run_name="__main__")
