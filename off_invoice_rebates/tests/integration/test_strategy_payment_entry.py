# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategy: payment_entry.

A submitted Settlement with ``settlement_mode = payment_entry`` must:
* create a submitted Payment Entry with ``payment_type = Pay`` and
  ``party_type = Customer``;
* its paid amount equals ``settlement.total_amount``;
* its reference_no points back at the Settlement.
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


class TestPaymentEntryStrategy(OIRIntegrationTestCase):
	def test_payment_entry_emitted_on_settlement_submit(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="memo_only",
			iva_regime="fuori_campo",
		)
		run = make_period_run(agreement=ag, anchor_date="2026-02-15")
		s_name = make_settlement(agreement=ag, period_run=run)
		settlement = frappe.get_doc("Rebate Settlement", s_name)

		self.assertTrue(settlement.payment_entry)
		pe = frappe.get_doc("Payment Entry", settlement.payment_entry)
		self.assertEqual(pe.payment_type, "Pay")
		self.assertEqual(pe.party_type, "Customer")
		self.assertEqual(pe.party, DEFAULT_CUSTOMER)
		self.assertEqual(flt(pe.paid_amount), flt(settlement.total_amount))
		self.assertEqual(pe.reference_no, settlement.name)
