# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Accounting policy: memo_only.

* No JE is posted at Period Run submit.
* No JE is posted at Settlement submit either.
* The Settlement still wires the strategy-level document (here: Payment Entry).
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


class TestMemoOnlyPolicy(OIRIntegrationTestCase):
	def test_no_rebate_je_anywhere(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="memo_only",
			iva_regime="fuori_campo",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-02-15")
		# No JE referencing the period run.
		self.assertEqual(
			frappe.get_all(
				"Journal Entry",
				filters={"cheque_no": run_name, "docstatus": 1},
				pluck="name",
			),
			[],
		)

		s_name = make_settlement(agreement=ag, period_run=run_name)
		settlement = frappe.get_doc("Rebate Settlement", s_name)
		self.assertFalse(settlement.journal_entry)
		# Strategy still wires the PE for payment_entry mode.
		self.assertTrue(settlement.payment_entry)
