# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Unit tests for the ``flat_contribution`` calculator.

Pure function: no DB. Three cases per the spec: happy / scaling / error.
"""

from __future__ import annotations

import os
import sys
import unittest
from decimal import Decimal

_HERE = os.path.dirname(__file__)
_APP_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _APP_ROOT not in sys.path:
	sys.path.insert(0, _APP_ROOT)


class TestFlatContributionCalculator(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.rebate_engine.calculators.base import PeriodBounds
			from off_invoice_rebates.rebate_engine.calculators.flat_contribution import (
				FlatContributionCalculator,
			)
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.PeriodBounds = PeriodBounds
		self.calc = FlatContributionCalculator()

	def _period(self, cadence: str) -> object:
		return self.PeriodBounds(
			period_key=f"2026-{cadence}",
			cadence=cadence,
			start="2026-01-01",
			end="2026-01-31",
		)

	def test_annual_to_monthly_scales_to_one_twelfth(self) -> None:
		outcome = self.calc.compute(
			agreement={"currency": "EUR"},
			condition={"flat_amount": 12000, "flat_periodicity": "annual"},
			period=self._period("monthly"),
			scope_sql="",
			scope_params={},
		)
		self.assertEqual(outcome.amount, Decimal("1000"))
		self.assertEqual(outcome.currency, "EUR")
		self.assertEqual(outcome.breakdown["calculator"], "flat_contribution")

	def test_quarterly_to_quarterly_no_scaling(self) -> None:
		outcome = self.calc.compute(
			agreement={"currency": "EUR"},
			condition={"flat_amount": 3000, "flat_periodicity": "quarterly"},
			period=self._period("quarterly"),
			scope_sql="",
			scope_params={},
		)
		self.assertEqual(outcome.amount, Decimal("3000"))

	def test_unknown_cadence_raises(self) -> None:
		with self.assertRaises(ValueError):
			self.calc.compute(
				agreement={"currency": "EUR"},
				condition={"flat_amount": 1000, "flat_periodicity": "annual"},
				period=self.PeriodBounds(
					period_key="2026-W01",
					cadence="weekly",
					start="2026-01-01",
					end="2026-01-07",
				),
				scope_sql="",
				scope_params={},
			)

	def test_unknown_periodicity_raises(self) -> None:
		with self.assertRaises(ValueError):
			self.calc.compute(
				agreement={"currency": "EUR"},
				condition={"flat_amount": 1000, "flat_periodicity": "weekly"},
				period=self._period("monthly"),
				scope_sql="",
				scope_params={},
			)


if __name__ == "__main__":
	unittest.main()
