# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Unit tests for ``rebate_engine.period``.

Covers cadence bounds derivation, next-period stepping and
is-period-complete decisioning. These tests rely on
``frappe.utils.{get_first_day,get_last_day,getdate}`` only - no DB.
"""

from __future__ import annotations

import os
import sys
import unittest

# Ensure the app package is importable when the test is run via plain pytest
# from outside a bench (CI unit job).
_HERE = os.path.dirname(__file__)
_APP_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _APP_ROOT not in sys.path:
	sys.path.insert(0, _APP_ROOT)


class TestPeriodBoundsForCadence(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.rebate_engine.period import bounds_for_cadence
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.bounds_for_cadence = bounds_for_cadence

	def test_monthly_bounds(self) -> None:
		p = self.bounds_for_cadence("monthly", "2026-03-17")
		self.assertEqual(p.cadence, "monthly")
		self.assertEqual(p.start, "2026-03-01")
		self.assertEqual(p.end, "2026-03-31")
		self.assertEqual(p.period_key, "2026-03")

	def test_quarterly_bounds_q2(self) -> None:
		p = self.bounds_for_cadence("quarterly", "2026-05-12")
		self.assertEqual(p.cadence, "quarterly")
		self.assertEqual(p.start, "2026-04-01")
		self.assertEqual(p.end, "2026-06-30")
		self.assertEqual(p.period_key, "2026-Q2")

	def test_quarterly_bounds_q4(self) -> None:
		p = self.bounds_for_cadence("quarterly", "2026-12-31")
		self.assertEqual(p.start, "2026-10-01")
		self.assertEqual(p.end, "2026-12-31")
		self.assertEqual(p.period_key, "2026-Q4")

	def test_annual_bounds(self) -> None:
		p = self.bounds_for_cadence("annual", "2026-08-04")
		self.assertEqual(p.cadence, "annual")
		self.assertEqual(p.start, "2026-01-01")
		self.assertEqual(p.end, "2026-12-31")
		self.assertEqual(p.period_key, "2026")

	def test_unknown_cadence_raises(self) -> None:
		with self.assertRaises(ValueError):
			self.bounds_for_cadence("weekly", "2026-03-17")


class TestPeriodNextAndComplete(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.rebate_engine.period import (
				bounds_for_cadence,
				is_period_complete,
				next_period_after,
			)
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.bounds_for_cadence = bounds_for_cadence
		self.is_period_complete = is_period_complete
		self.next_period_after = next_period_after

	def test_next_period_after_monthly(self) -> None:
		nxt = self.next_period_after("monthly", "2026-03-31")
		self.assertEqual(nxt.start, "2026-04-01")
		self.assertEqual(nxt.end, "2026-04-30")
		self.assertEqual(nxt.period_key, "2026-04")

	def test_next_period_after_quarter_rollover(self) -> None:
		nxt = self.next_period_after("quarterly", "2026-12-31")
		self.assertEqual(nxt.start, "2027-01-01")
		self.assertEqual(nxt.end, "2027-03-31")

	def test_is_period_complete_after_end(self) -> None:
		p = self.bounds_for_cadence("monthly", "2026-03-17")
		self.assertTrue(self.is_period_complete(p, today="2026-04-01"))

	def test_is_period_not_complete_on_end_day(self) -> None:
		p = self.bounds_for_cadence("monthly", "2026-03-17")
		self.assertFalse(self.is_period_complete(p, today="2026-03-31"))


if __name__ == "__main__":
	unittest.main()
