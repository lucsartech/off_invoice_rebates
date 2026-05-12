# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Pytest configuration for unit tests.

Anchors a deterministic "today" so calculator/period tests are reproducible
regardless of the wallclock.

Integration tests bypass pytest and use Frappe's standard test runner
(``bench run-tests``); they do not consume this conftest.
"""

from __future__ import annotations

import os

# Deterministic anchor used across unit tests.
DETERMINISTIC_TODAY: str = "2026-06-15"
DETERMINISTIC_YEAR: int = 2026
DETERMINISTIC_CURRENCY: str = "EUR"

# Expose the anchor through env so helper modules can read it without needing
# a pytest fixture.
os.environ.setdefault("OIR_TEST_TODAY", DETERMINISTIC_TODAY)
