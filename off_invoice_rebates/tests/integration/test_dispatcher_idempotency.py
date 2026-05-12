# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Dispatcher idempotency tests.

* Running the dispatcher twice for the same ``(agreement, period_key)`` must
  reuse the existing Period Run, not create a second.
* Once a Period Run is submitted, calling ``run_period`` again must raise
  ``RebatePeriodLocked``.
"""

from __future__ import annotations

import frappe

from off_invoice_rebates.rebate_engine.dispatcher import run_period
from off_invoice_rebates.rebate_engine.exceptions import RebatePeriodLocked
from off_invoice_rebates.rebate_engine.period import bounds_for_cadence
from off_invoice_rebates.tests.fixtures.factories import DEFAULT_CUSTOMER, make_agreement
from off_invoice_rebates.tests.integration.base import OIRIntegrationTestCase


class TestDispatcherIdempotency(OIRIntegrationTestCase):
	def test_second_run_reuses_existing_period_run(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
		)
		period = bounds_for_cadence("monthly", "2026-08-15")
		first = run_period(ag, period)
		second = run_period(ag, period)
		self.assertEqual(first, second)

	def test_submitted_run_blocks_recompute(self) -> None:
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
		)
		period = bounds_for_cadence("monthly", "2026-09-15")
		name = run_period(ag, period)
		run = frappe.get_doc("Rebate Period Run", name)
		run.submit()
		with self.assertRaises(RebatePeriodLocked):
			run_period(ag, period)
