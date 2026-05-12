# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Rebate Settlement residual rule.

The sum of ``amount_to_settle`` across all submitted Settlements for the same
Period Run must not exceed the run total. The controller validates this in
``RebateSettlement._validate_period_runs``.

We also exercise the partial-settlement path: a first Settlement liquidates
half the period, a second liquidates the remaining half.
"""

from __future__ import annotations

import frappe

from off_invoice_rebates.tests.fixtures.factories import (
	DEFAULT_CUSTOMER,
	make_agreement,
	make_period_run,
	make_settlement,
)
from off_invoice_rebates.tests.integration.base import OIRIntegrationTestCase


class TestSettlementResidual(OIRIntegrationTestCase):
	def test_excess_amount_rejected(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="memo_only",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-02-15")
		with self.assertRaises(frappe.ValidationError):
			make_settlement(
				agreement=ag,
				period_run=run_name,
				amount_to_settle=999.0,  # period total is 100 (1200/12)
			)

	def test_partial_then_residual_settlement_ok(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="memo_only",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-03-15")
		make_settlement(agreement=ag, period_run=run_name, amount_to_settle=40.0)
		make_settlement(agreement=ag, period_run=run_name, amount_to_settle=60.0)
		# At this point the run is fully settled.
		run = frappe.get_doc("Rebate Period Run", run_name)
		self.assertEqual(run.settlement_status, "settled")
