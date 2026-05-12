# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from off_invoice_rebates.rebate_engine.calculators.base import (
	PeriodBounds,
	RebateOutcome,
	get_calculator,
)
from off_invoice_rebates.rebate_engine.exceptions import RebatePeriodLocked
from off_invoice_rebates.rebate_engine.scope import build_scope_sql


def run_period(agreement_name: str, period: PeriodBounds) -> str:
	"""Crea o aggiorna in modo idempotente il `Rebate Period Run`
	per la coppia (agreement, period_key). Restituisce il name del Run.

	Stati `compute_status`:
	  pending → computing (inizio) → computed (successo) | failed (errore)
	"""
	agreement = frappe.get_doc("Rebate Agreement", agreement_name)
	if agreement.docstatus != 1:
		frappe.throw(
			_("Accordo {0} non è in stato submitted.").format(agreement_name)
		)

	existing = frappe.db.get_value(
		"Rebate Period Run",
		{
			"agreement": agreement_name,
			"period_key": period.period_key,
			"docstatus": ("!=", 2),
		},
		"name",
	)
	if existing:
		run = frappe.get_doc("Rebate Period Run", existing)
		if run.docstatus == 1:
			raise RebatePeriodLocked(
				f"Period Run {existing} sottomesso — ricalcolo non consentito."
			)
		run.set("accruals", [])
	else:
		run = frappe.new_doc("Rebate Period Run")
		run.agreement = agreement_name
		run.period_key = period.period_key
		run.period_start = period.start
		run.period_end = period.end
		run.cadence = period.cadence
		run.compute_status = "pending"

	run.compute_status = "computing"
	run.compute_started_at = frappe.utils.now()
	run.failure_reason = None

	try:
		scope_filters = [dict(s.as_dict()) for s in (agreement.scope_filters or [])]
		scope_sql, scope_params = build_scope_sql(scope_filters)

		agreement_dict = dict(agreement.as_dict())

		for cond in agreement.conditions:
			cond_dict = dict(cond.as_dict())
			# Rebate Tier is a grandchild table (Agreement → Condition → Tier).
			# Frappe does not auto-hydrate grandchildren — fetch from DB.
			tiers_from_db = frappe.get_all(
				"Rebate Tier",
				filters={"parent": cond.name, "parenttype": "Rebate Condition"},
				fields=["from_amount", "to_amount", "percentage", "idx"],
				order_by="idx asc",
			)
			cond_dict["tiers"] = (
				tiers_from_db
				if tiers_from_db
				else [dict(t.as_dict()) for t in (cond.tiers or [])]
			)
			calc = get_calculator(cond_dict["calculator_code"])
			outcome: RebateOutcome = calc.compute(
				agreement=agreement_dict,
				condition=cond_dict,
				period=period,
				scope_sql=scope_sql,
				scope_params=scope_params,
			)
			run.append(
				"accruals",
				{
					"calculator_code": cond_dict["calculator_code"],
					"condition_description": cond.description,
					"amount": float(outcome.amount),
					"breakdown": frappe.as_json(outcome.breakdown, indent=2),
				},
			)

		run.compute_status = "computed"
		run.compute_completed_at = frappe.utils.now()
		start_ts = frappe.utils.get_datetime(run.compute_started_at)
		end_ts = frappe.utils.get_datetime(run.compute_completed_at)
		run.compute_duration_seconds = (end_ts - start_ts).total_seconds()
		run.save(ignore_permissions=True)
		frappe.db.commit()
		return run.name
	except RebatePeriodLocked:
		raise
	except Exception as e:
		run.compute_status = "failed"
		run.compute_completed_at = frappe.utils.now()
		run.failure_reason = f"{type(e).__name__}: {e}"
		try:
			# Save best-effort to persist the failure trace; ignore secondary errors.
			run.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
		frappe.log_error(
			f"run_period({agreement_name}, {period.period_key}) failed: {e}",
			"OIR dispatcher",
		)
		raise


def get_settled_accruals(agreement: str, period_key: str) -> list[dict]:
	"""Hand-off API for the settlement layer (F3).

	Returns the list of accrual rows (as dicts) for the given (agreement, period)
	whose Period Run is computed and submitted.
	"""
	run = frappe.db.get_value(
		"Rebate Period Run",
		{
			"agreement": agreement,
			"period_key": period_key,
			"docstatus": 1,
			"compute_status": "computed",
		},
		["name", "total_amount", "settled_amount", "settlement_status", "currency"],
		as_dict=True,
	)
	if not run:
		return []
	accruals = frappe.get_all(
		"Rebate Accrual Entry",
		filters={"parent": run.name},
		fields=["calculator_code", "condition_description", "amount", "breakdown"],
		order_by="idx asc",
	)
	for a in accruals:
		a["run"] = run.name
		a["currency"] = run.currency
	return accruals


@frappe.whitelist()
def run_period_for_agreement(
	agreement: str,
	cadence: str | None = None,
	anchor_date: str | None = None,
) -> str:
	"""Manual entry point per UI / console.

	Se `anchor_date` è fornita, calcola il periodo che contiene quella data per la
	cadenza richiesta. Altrimenti tenta di proseguire dal periodo successivo
	all'ultimo Run esistente, ripiegando sull'anchor della Rebate Schedule.
	"""
	from off_invoice_rebates.rebate_engine.period import (
		bounds_for_cadence,
		next_period_after,
	)

	ag = frappe.get_doc("Rebate Agreement", agreement)
	cad = cadence or (ag.schedules[0].cadence if ag.schedules else "monthly")

	if anchor_date:
		period = bounds_for_cadence(cad, anchor_date)
	else:
		last = frappe.db.get_value(
			"Rebate Period Run",
			{"agreement": agreement, "cadence": cad, "docstatus": ("!=", 2)},
			"period_end",
			order_by="period_end desc",
		)
		if last:
			period = next_period_after(cad, last)
		else:
			schedule_anchor = (
				ag.schedules[0].anchor_date if ag.schedules else ag.start_date
			)
			period = bounds_for_cadence(cad, schedule_anchor)

	return run_period(agreement, period)
