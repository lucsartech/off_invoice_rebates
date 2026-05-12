# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Accounting policy: full_accrual.

* On Period Run submit, a balanced Journal Entry is posted
  (``Dr expense / Cr accrued_liability``).
* On Settlement submit, a second balanced JE transfers the rateo to the
  payable (``Dr accrued_liability / Cr payable``).
* Both JEs reference back to the originating doc via ``cheque_no``.
* Σ debits == Σ credits for every JE.
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


class TestFullAccrualPolicy(OIRIntegrationTestCase):
	def test_je_posted_on_period_run_submit_and_balanced(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="full_accrual",
			iva_regime="fuori_campo",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-02-15")

		jes = frappe.get_all(
			"Journal Entry",
			filters={"cheque_no": run_name, "docstatus": 1},
			pluck="name",
		)
		self.assertGreaterEqual(len(jes), 1, "Expected an accrual JE for the Period Run")
		je = frappe.get_doc("Journal Entry", jes[0])
		total_debit = sum(flt(a.debit_in_account_currency) for a in je.accounts)
		total_credit = sum(flt(a.credit_in_account_currency) for a in je.accounts)
		self.assertEqual(total_debit, total_credit)
		self.assertEqual(total_debit, 50.0)  # 600/12

	def test_je_posted_on_settlement_balances_and_links(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="full_accrual",
			iva_regime="fuori_campo",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-04-15")
		s_name = make_settlement(agreement=ag, period_run=run_name)
		settlement = frappe.get_doc("Rebate Settlement", s_name)
		self.assertTrue(settlement.journal_entry)
		je = frappe.get_doc("Journal Entry", settlement.journal_entry)
		total_debit = sum(flt(a.debit_in_account_currency) for a in je.accounts)
		total_credit = sum(flt(a.credit_in_account_currency) for a in je.accounts)
		self.assertEqual(total_debit, total_credit)
