# Lucid Titan Test Environment

## Overview

Complete test suite for the Lucid Titan V7.0 SINGULARITY platform, covering:

- **`test_browser_profile.py`** — BrowserProfile dataclass creation, serialization, all personas
- **`test_temporal_displacement.py`** — libfaketime integration, activation/deactivation, apparent time
- **`test_genesis_engine.py`** — Profile synthesis, seed generation, Stripe/Adyen tokens, browsing history, cookies, profile CRUD
- **`test_titan_controller.py`** — Central orchestrator, persona switching, config persistence, browser env, status, shutdown
- **`test_profile_isolation.py`** — ResourceLimits, CgroupManager, ProfileIsolatorError
- **`test_profgen_config.py`** — Profgen constants, domain lists, circadian hours, Pareto visits, subpages, phases
- **`test_integration.py`** — End-to-end workflows: profile lifecycle, persona interaction, data integrity, shutdown persistence

## Quick Start

```powershell
cd C:\Users\Administrator\CascadeProjects\lucid-titan

# Install test dependencies
pip install -r tests/requirements-test.txt

# Run all tests
python -m pytest

# Run unit tests only
python tests/run_tests.py --unit

# Run integration tests only
python tests/run_tests.py --integration

# Run with coverage
python tests/run_tests.py --coverage

# Generate HTML report
python tests/run_tests.py --html
```

## Test Structure

```
tests/
├── __init__.py                    # Package marker
├── conftest.py                    # Shared fixtures & helpers
├── requirements-test.txt          # Test dependencies
├── run_tests.py                   # Test runner with options
├── README.md                      # This file
├── test_browser_profile.py        # BrowserProfile unit tests
├── test_temporal_displacement.py  # TemporalDisplacement unit tests
├── test_genesis_engine.py         # GenesisEngine unit tests
├── test_titan_controller.py       # TitanController unit tests
├── test_profile_isolation.py      # ProfileIsolator unit tests
├── test_profgen_config.py         # profgen/config.py unit tests
└── test_integration.py            # Cross-module integration tests
```

## Fixtures (conftest.py)

| Fixture | Description |
|---------|-------------|
| `tmp_titan_dir` | Clean temp directory for Titan operations |
| `tmp_profiles_dir` | Clean temp profiles directory |
| `temporal` | TemporalDisplacement instance |
| `genesis` | GenesisEngine with temp directory |
| `titan_controller` | TitanController with temp directory |
| `sample_profile` | Pre-built Windows BrowserProfile |
| `sample_profile_linux` | Pre-built Linux BrowserProfile |
| `sample_profile_macos` | Pre-built macOS BrowserProfile |
| `helpers` | TitanTestHelpers utility methods |

## Coverage Targets

| Module | Target |
|--------|--------|
| `titan/titan_core.py` | ≥90% |
| `titan/profile_isolation.py` | ≥70% (Linux-specific code) |
| `profgen/config.py` | ≥85% |
