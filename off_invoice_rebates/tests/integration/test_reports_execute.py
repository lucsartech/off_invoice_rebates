# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Smoke tests for the five Query Reports.

Each report's ``execute(filters)`` must run without error on a populated
fixture set (one Agreement + one submitted Period Run + one Settlement).

We do not assert on row counts — Frappe reports legitimately return [] for
filter combinations a site has no data for. We assert only that the
function does not raise and returns the standard 4- or 5-tuple shape.
"""

from __future__ import annotations

import importlib

from off_invoice_rebates.tests.fixtures.factories import (
	DEFAULT_CUSTOMER,
	make_agreement,
	make_period_run,
	make_settlement,
)
from off_invoice_rebates.tests.integration.base import OIRIntegrationTestCase

REPORTS = (
	"rebate_maturato_per_cliente",
	"rebate_liquidazioni_in_corso",
	"rebate_premi_per_gruppo",
	"rebate_riconciliazione_contabile",
	"rebate_confronto_maturato_vs_target",
)


class TestReportsExecute(OIRIntegrationTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		# Seed enough data so every report has at least one match.
		ag = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
			settlement_mode="payment_entry",
			accounting_policy="memo_only",
		)
		run = make_period_run(agreement=ag, anchor_date="2026-02-15")
		make_settlement(agreement=ag, period_run=run)

	def test_each_report_executes_without_error(self) -> None:
		for short_name in REPORTS:
			mod = importlib.import_module(
				f"off_invoice_rebates.off_invoice_rebates.report.{short_name}.{short_name}"
			)
			result = mod.execute({})
			self.assertIsInstance(result, tuple)
			self.assertGreaterEqual(len(result), 2)
			columns, data = result[0], result[1]
			self.assertIsInstance(columns, list)
			self.assertIsInstance(data, list)
