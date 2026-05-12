# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Accounting policy: on_settlement.

* No JE is posted at Period Run submit time.
* A single balanced JE is posted at Settlement submit
  (``Dr expense / Cr payable``).
"""

from __future__ import annotations

import frappe
from frappe.utils import flt

from off_invoice_rebates.tests.fixtures.factories import (
	DEFAULT_CUSTOMER,
	make_agreement,
	make_period_run,
	make_settlement,
)
from off_invoice_rebates.tests.integration.base import OIRIntegrationTestCase


class TestOnSettlementPolicy(OIRIntegrationTestCase):
	def test_no_je_on_period_run_then_je_on_settlement(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="on_settlement",
			iva_regime="fuori_campo",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-02-15")

		accrual_jes = frappe.get_all(
			"Journal Entry",
			filters={"cheque_no": run_name, "docstatus": 1},
			pluck="name",
		)
		self.assertEqual(accrual_jes, [], "on_settlement must not post at accrual time")

		s_name = make_settlement(agreement=ag, period_run=run_name)
		settlement = frappe.get_doc("Rebate Settlement", s_name)
		self.assertTrue(settlement.journal_entry)
		je = frappe.get_doc("Journal Entry", settlement.journal_entry)
		total_debit = sum(flt(a.debit_in_account_currency) for a in je.accounts)
		total_credit = sum(flt(a.credit_in_account_currency) for a in je.accounts)
		self.assertEqual(total_debit, total_credit)
		self.assertEqual(total_debit, flt(settlement.total_amount))
