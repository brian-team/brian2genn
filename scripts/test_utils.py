"""
Utility functions for testing.
"""
from pathlib import Path
def get_skip_args():
    fname = Path(__file__).parent / 'skip_tests.txt'
    if not fname.exists():
        return []
    with open(fname) as f:
        lines = f.readlines()
        return ["--deselect="+line.strip() for line in lines if line.strip() and not line.startswith('#')]
