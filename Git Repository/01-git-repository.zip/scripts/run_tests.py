"""Run from any working directory: python scripts/run_tests.py."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
suite = unittest.defaultTestLoader.discover(str(ROOT / "Unit Tests"), pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
