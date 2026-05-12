# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategy: credit_note (NC fuori campo).

Verifies the Settlement on submit:
* creates a submitted Sales Invoice with ``is_return = 1``;
* the NC line carries the rebate total via negative qty + positive rate;
* the NC has the rebate naming series and the back-link header field set.

We use ``fuori_campo`` to keep the test independent of a real Italian
e-invoice address / fiscal-code preflight.
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


class TestCreditNoteStrategy(OIRIntegrationTestCase):
	def test_credit_note_nc_emitted_on_settlement_submit(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="credit_note",
			accounting_policy="memo_only",
			iva_regime="fuori_campo",
		)
		run = make_period_run(agreement=ag, anchor_date="2026-02-15")
		s_name = make_settlement(agreement=ag, period_run=run)
		settlement = frappe.get_doc("Rebate Settlement", s_name)

		self.assertTrue(settlement.sales_invoice_nc)
		nc = frappe.get_doc("Sales Invoice", settlement.sales_invoice_nc)
		self.assertEqual(nc.is_return, 1)
		self.assertEqual(nc.customer, DEFAULT_CUSTOMER)
		# Rebate line: qty = -1, rate = settlement total.
		self.assertEqual(len(nc.items), 1)
		self.assertEqual(flt(nc.items[0].qty), -1.0)
		self.assertEqual(flt(nc.items[0].rate), flt(settlement.total_amount))
		# Back-link must be set on the NC for downstream traceability.
		self.assertEqual(nc.oir_rebate_settlement, settlement.name)

	def test_credit_note_strategy_refuses_double_settle(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="credit_note",
			accounting_policy="memo_only",
			iva_regime="fuori_campo",
		)
		run = make_period_run(agreement=ag, anchor_date="2026-03-15")
		s_name = make_settlement(agreement=ag, period_run=run)
		from off_invoice_rebates.settlement import credit_note  # noqa: F401
		from off_invoice_rebates.settlement.base import get_strategy

		settlement = frappe.get_doc("Rebate Settlement", s_name)
		strategy = get_strategy("credit_note")
		with self.assertRaises(frappe.ValidationError):
			strategy.settle(settlement)
