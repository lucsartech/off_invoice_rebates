# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import getdate

from off_invoice_rebates.rebate_engine.dispatcher import run_period
from off_invoice_rebates.rebate_engine.exceptions import RebatePeriodLocked
from off_invoice_rebates.rebate_engine.period import (
	bounds_for_cadence,
	is_period_complete,
	next_period_after,
)


def run_due_periods() -> None:
	"""Entry point dello scheduler giornaliero.

	Per ogni Rebate Agreement attivo, percorre i periodi a partire dall'anchor
	della Rebate Schedule e crea un Period Run per ogni periodo già chiuso che
	non ne ha ancora uno (idempotenza garantita dal dispatcher).
	"""
	try:
		settings = frappe.get_cached_doc("Rebate Settings")
	except Exception:
		return
	if not settings.enable_auto_period_run:
		return

	today = getdate()
	agreements = frappe.get_all(
		"Rebate Agreement",
		filters={"docstatus": 1},
		pluck="name",
	)

	for ag_name in agreements:
		try:
			_run_due_periods_for_agreement(ag_name, today)
		except Exception as e:
			frappe.log_error(
				f"run_due_periods failed for {ag_name}: {e}",
				"OIR scheduler",
			)


def _run_due_periods_for_agreement(ag_name: str, today) -> None:
	ag = frappe.get_doc("Rebate Agreement", ag_name)
	if not ag.schedules:
		return
	cadence = ag.schedules[0].cadence
	anchor = ag.schedules[0].anchor_date or ag.start_date
	if not anchor:
		return

	end_boundary = getdate(ag.end_date) if ag.end_date else today
	period = bounds_for_cadence(cadence, anchor)
	# safety cap to avoid runaway loops on misconfigured anchors.
	max_periods = 240
	steps = 0

	while is_period_complete(period, today) and getdate(period.start) <= end_boundary:
		steps += 1
		if steps > max_periods:
			frappe.log_error(
				f"run_due_periods: safety cap reached for {ag_name}", "OIR scheduler"
			)
			break
		exists = frappe.db.exists(
			"Rebate Period Run",
			{
				"agreement": ag_name,
				"period_key": period.period_key,
				"docstatus": ("!=", 2),
			},
		)
		if not exists:
			try:
				run_period(ag_name, period)
			except RebatePeriodLocked:
				pass
			except Exception as e:
				frappe.log_error(
					f"run_period failed for {ag_name} {period.period_key}: {e}",
					"OIR scheduler",
				)
		period = next_period_after(cadence, period.end)
