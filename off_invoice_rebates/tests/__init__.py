# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Test suite for off_invoice_rebates.

Layout
------
* ``unit/`` - pure-Python tests runnable with ``pytest`` (no bench site).
* ``integration/`` - tests that need a Frappe site, run via
  ``bench --site <site> run-tests --app off_invoice_rebates``.
* ``fixtures/factories.py`` - idempotent factory helpers used across both layers.
"""
