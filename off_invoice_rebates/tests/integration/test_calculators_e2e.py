# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""End-to-end calculator tests.

For each of the four calculators we build a Rebate Agreement, post one or
more Sales Invoices into the period range, then run the dispatcher and
assert the resulting Period Run total.
"""

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe.utils import flt

from off_invoice_rebates.tests.fixtures.factories import (
	DEFAULT_COMPANY,
	DEFAULT_CUSTOMER,
	DEFAULT_ITEM,
	make_agreement,
	make_period_run,
	make_sales_invoice,
)
from off_invoice_rebates.tests.integration.base import OIRIntegrationTestCase


from off_invoice_rebates.tests.fixtures.factories import make_customer


class TestFlatContributionE2E(OIRIntegrationTestCase):
	def test_flat_annual_scaled_to_monthly_run(self) -> None:
		cust = make_customer("OIR Cust Flat")
		ag = make_agreement(
			customer=cust,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 12000, "flat_periodicity": "annual"},
			cadence="monthly",
		)
		run_name = make_period_run(
			agreement=ag, anchor_date="2026-03-15", submit=False
		)
		run = frappe.get_doc("Rebate Period Run", run_name)
		self.assertEqual(flt(run.total_amount), 1000.0)
		self.assertEqual(run.compute_status, "computed")
		self.assertEqual(len(run.accruals), 1)


class TestTurnoverTieredE2E(OIRIntegrationTestCase):
	def test_single_tier_one_percent(self) -> None:
		cust = make_customer("OIR Cust Tier", fresh=True)
		make_sales_invoice(
			customer=cust,
			company=DEFAULT_COMPANY,
			item_code=DEFAULT_ITEM,
			qty=10,
			rate=1000,
			posting_date="2026-03-15",
		)
		ag = make_agreement(
			customer=cust,
			calculator_code="turnover_tiered",
			condition_overrides={
				"tier_metric": "turnover",
				"tiers": [{"from_amount": 0, "to_amount": 0, "percentage": 1}],
			},
			cadence="monthly",
		)
		run_name = make_period_run(
			agreement=ag, anchor_date="2026-03-15", submit=False
		)
		run = frappe.get_doc("Rebate Period Run", run_name)
		# 10 * 1000 * 1% = 100
		self.assertAlmostEqual(flt(run.total_amount), 100.0, places=2)

	def test_zero_turnover_yields_zero(self) -> None:
		cust = make_customer("OIR Cust TierZero")
		ag = make_agreement(
			customer=cust,
			calculator_code="turnover_tiered",
			condition_overrides={
				"tier_metric": "turnover",
				"tiers": [{"from_amount": 0, "to_amount": 0, "percentage": 2}],
			},
			cadence="monthly",
		)
		run_name = make_period_run(
			agreement=ag, anchor_date="2026-05-15", submit=False
		)
		run = frappe.get_doc("Rebate Period Run", run_name)
		self.assertEqual(flt(run.total_amount), 0.0)


class TestVolumeCalculatorE2E(OIRIntegrationTestCase):
	def test_unit_amount_times_qty(self) -> None:
		cust = make_customer("OIR Cust Vol", fresh=True)
		make_sales_invoice(
			customer=cust,
			company=DEFAULT_COMPANY,
			item_code=DEFAULT_ITEM,
			qty=50,
			rate=10,
			posting_date="2026-04-10",
		)
		ag = make_agreement(
			customer=cust,
			calculator_code="volume",
			condition_overrides={"volume_unit_amount": 2, "volume_unit_of_measure": "Nos"},
			cadence="monthly",
		)
		run_name = make_period_run(
			agreement=ag, anchor_date="2026-04-10", submit=False
		)
		run = frappe.get_doc("Rebate Period Run", run_name)
		# 50 * 2 = 100
		self.assertEqual(flt(run.total_amount), 100.0)


class TestTargetGrowthCalculatorE2E(OIRIntegrationTestCase):
	def test_absolute_target_mode_above_target(self) -> None:
		cust = make_customer("OIR Cust Target", fresh=True)
		# Period 2026-06: turnover = 30 * 100 = 3000
		make_sales_invoice(
			customer=cust,
			company=DEFAULT_COMPANY,
			item_code=DEFAULT_ITEM,
			qty=30,
			rate=100,
			posting_date="2026-06-10",
		)
		ag = make_agreement(
			customer=cust,
			calculator_code="target_growth",
			condition_overrides={
				"target_metric": "turnover",
				"target_amount": 1000,
				"growth_premium_percent": 10,
			},
			cadence="monthly",
		)
		run_name = make_period_run(
			agreement=ag, anchor_date="2026-06-10", submit=False
		)
		run = frappe.get_doc("Rebate Period Run", run_name)
		# excess = 3000 - 1000 = 2000; premio = 200
		self.assertEqual(flt(run.total_amount), 200.0)

	def test_absolute_target_below_target_yields_zero(self) -> None:
		cust = make_customer("OIR Cust TargetLow", fresh=True)
		make_sales_invoice(
			customer=cust,
			company=DEFAULT_COMPANY,
			item_code=DEFAULT_ITEM,
			qty=1,
			rate=10,
			posting_date="2026-07-10",
		)
		ag = make_agreement(
			customer=cust,
			calculator_code="target_growth",
			condition_overrides={
				"target_metric": "turnover",
				"target_amount": 50000,
				"growth_premium_percent": 5,
			},
			cadence="monthly",
		)
		run_name = make_period_run(
			agreement=ag, anchor_date="2026-07-10", submit=False
		)
		run = frappe.get_doc("Rebate Period Run", run_name)
		self.assertEqual(flt(run.total_amount), 0.0)
