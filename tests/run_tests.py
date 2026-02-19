#!/usr/bin/env python3
"""
Lucid Titan Test Runner
=======================
Runs the complete test suite with coverage reporting.

Usage:
    python tests/run_tests.py                    # Run all tests
    python tests/run_tests.py --unit             # Unit tests only
    python tests/run_tests.py --integration      # Integration tests only
    python tests/run_tests.py --coverage         # With coverage report
    python tests/run_tests.py --html             # Generate HTML report
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_tests(args=None):
    """Run pytest with the given arguments."""
    cmd = [sys.executable, "-m", "pytest"]

    if args is None:
        args = sys.argv[1:]

    # Parse custom flags
    if "--unit" in args:
        args.remove("--unit")
        cmd.extend([
            "tests/test_browser_profile.py",
            "tests/test_temporal_displacement.py",
            "tests/test_genesis_engine.py",
            "tests/test_titan_controller.py",
            "tests/test_profile_isolation.py",
            "tests/test_profgen_config.py",
        ])
    elif "--integration" in args:
        args.remove("--integration")
        cmd.append("tests/test_integration.py")

    if "--coverage" in args:
        args.remove("--coverage")
        cmd.extend([
            "--cov=titan",
            "--cov=profgen",
            "--cov-report=term-missing",
            "--cov-report=html:tests/htmlcov",
        ])

    if "--html" in args:
        args.remove("--html")
        cmd.extend(["--html=tests/report.html", "--self-contained-html"])

    # Pass remaining args through
    cmd.extend(args)

    print(f"Running: {' '.join(cmd)}")
    print(f"Working directory: {PROJECT_ROOT}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
