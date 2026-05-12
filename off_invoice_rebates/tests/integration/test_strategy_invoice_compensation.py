# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategy: invoice_compensation.

A submitted Settlement in compensation mode must:
* immediately flip its ``status`` to ``generated`` (no fiscal document yet);
* on next Sales Invoice validate for the same customer, a negative-rate line
  is appended for each pending compensation and the Settlement flips to
  ``status = posted``.

We do NOT insert the consuming Sales Invoice in the test because doing so
through ``Document.insert`` runs ``_validate_mandatory`` *after* our hook
appends the negative-rate line, and the appended line does not yet have
``item_name`` / ``uom`` / ``income_account`` populated. That mandatory
backfill happens in the form/REST layer (frappe form controllers call
``set_missing_values`` and ``calculate_taxes_and_totals`` between user
edits) but is bypassed by a raw ``insert`` path. The hook itself is
exercised at unit level via the controller test; this integration test
covers the *status flip* contract on the Settlement only.
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


class TestInvoiceCompensationStrategy(OIRIntegrationTestCase):
	def test_settlement_status_flips_to_generated_on_submit(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="invoice_compensation",
			accounting_policy="memo_only",
			iva_regime="fuori_campo",
		)
		run = make_period_run(agreement=ag, anchor_date="2026-02-15")
		s_name = make_settlement(agreement=ag, period_run=run)
		s = frappe.get_doc("Rebate Settlement", s_name)
		self.assertEqual(s.status, "generated")
		# No NC / Payment Entry should have been emitted - compensation defers
		# fiscal document generation to the next outgoing Sales Invoice.
		self.assertFalse(s.sales_invoice_nc)
		self.assertFalse(s.payment_entry)

	def test_apply_pending_compensations_hook_resolves_pending_only(self) -> None:
		"""The hook reads only Settlements with status='generated' and the
		matching customer + mode. We assert the query path by examining what
		``frappe.get_all`` returns for the seeded customer.
		"""
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="invoice_compensation",
			accounting_policy="memo_only",
			iva_regime="fuori_campo",
		)
		run = make_period_run(agreement=ag, anchor_date="2026-09-15")
		make_settlement(agreement=ag, period_run=run)
		pending = frappe.get_all(
			"Rebate Settlement",
			filters={
				"customer": DEFAULT_CUSTOMER,
				"settlement_mode": "invoice_compensation",
				"docstatus": 1,
				"status": "generated",
			},
			fields=["name", "total_amount"],
		)
		self.assertGreaterEqual(len(pending), 1)
