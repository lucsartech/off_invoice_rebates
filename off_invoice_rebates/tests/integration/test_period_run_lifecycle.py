# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Rebate Period Run lifecycle tests.

* ``compute_status`` becomes ``computed`` after a successful dispatcher run.
* ``before_submit`` must reject a run whose status is not ``computed``.
* ``on_cancel`` must reject a run already linked to a submitted Settlement.
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


class TestPeriodRunLifecycle(OIRIntegrationTestCase):
	def test_compute_status_computed_after_dispatch(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-02-15", submit=False)
		run = frappe.get_doc("Rebate Period Run", run_name)
		self.assertEqual(run.compute_status, "computed")

	def test_before_submit_rejects_pending_status(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-03-15", submit=False)
		run = frappe.get_doc("Rebate Period Run", run_name)
		# Force-flip status to pending and try to submit.
		run.db_set("compute_status", "pending", update_modified=False)
		run.reload()
		with self.assertRaises(frappe.ValidationError):
			run.submit()

	def test_on_cancel_blocked_when_settlement_links_run(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 600, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="memo_only",
		)
		run_name = make_period_run(agreement=ag, anchor_date="2026-04-15")
		make_settlement(agreement=ag, period_run=run_name)
		run = frappe.get_doc("Rebate Period Run", run_name)
		with self.assertRaises(frappe.ValidationError):
			run.cancel()
