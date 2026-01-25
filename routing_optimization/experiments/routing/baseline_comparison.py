"""Baseline vs standard vs robust comparison runner."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)

from run_experiment import run_comparison_experiment  # noqa: E402


if __name__ == "__main__":
    run_comparison_experiment()
