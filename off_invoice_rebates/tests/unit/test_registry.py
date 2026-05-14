# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Unit tests for the three registries (calculators / settlement strategies /
accounting policies).

Each registry uses a module-level ``_REGISTRY`` populated by the ``register``
decorator on import. We verify every code resolves to a class with the
required protocol entry-points.
"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(__file__)
_APP_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _APP_ROOT not in sys.path:
	sys.path.insert(0, _APP_ROOT)


class TestCalculatorRegistry(unittest.TestCase):
	def setUp(self) -> None:
		try:
			# Trigger registration of all four calculators.
			from off_invoice_rebates.rebate_engine.calculators import (
				flat_contribution,
				target_growth,
				turnover_tiered,
				volume,
			)
			from off_invoice_rebates.rebate_engine.calculators.base import (
				all_codes,
				get_calculator,
			)
			from off_invoice_rebates.rebate_engine.exceptions import UnknownCalculator
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.all_codes = all_codes
		self.get_calculator = get_calculator
		self.UnknownCalculator = UnknownCalculator

	def test_all_four_codes_registered(self) -> None:
		codes = set(self.all_codes())
		self.assertEqual(
			codes,
			{"turnover_tiered", "volume", "target_growth", "flat_contribution"},
		)

	def test_each_code_resolves_to_instance_with_compute(self) -> None:
		for code in self.all_codes():
			calc = self.get_calculator(code)
			self.assertTrue(hasattr(calc, "compute"))
			self.assertEqual(calc.code, code)

	def test_unknown_code_raises(self) -> None:
		with self.assertRaises(self.UnknownCalculator):
			self.get_calculator("nonexistent_calculator")


class TestSettlementRegistry(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.settlement import (
				credit_note,
				invoice_compensation,
				payment_entry,
			)
			from off_invoice_rebates.settlement.base import registered_codes
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.registered_codes = registered_codes

	def test_three_strategies_registered(self) -> None:
		self.assertEqual(
			set(self.registered_codes()),
			{"credit_note", "invoice_compensation", "payment_entry"},
		)


class TestAccountingRegistry(unittest.TestCase):
	def setUp(self) -> None:
		try:
			from off_invoice_rebates.accounting import (
				full_accrual,
				memo_only,
				on_settlement,
			)
			from off_invoice_rebates.accounting.base import registered_codes
		except ModuleNotFoundError:
			self.skipTest("frappe not importable - run via bench instead")
		self.registered_codes = registered_codes

	def test_three_policies_registered(self) -> None:
		self.assertEqual(
			set(self.registered_codes()),
			{"full_accrual", "on_settlement", "memo_only"},
		)


if __name__ == "__main__":
	unittest.main()
