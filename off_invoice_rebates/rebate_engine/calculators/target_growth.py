# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

from decimal import Decimal

import frappe
from frappe.utils import add_months

from off_invoice_rebates.rebate_engine.calculators.base import (
	PeriodBounds,
	RebateOutcome,
	register,
)


@register("target_growth")
class TargetGrowthCalculator:
	"""Modalità duali:

	- target assoluto (target_amount valorizzato): premio = max(0, current - target) * premium_pct.
	- crescita YoY (target_amount vuoto): premio = (current - baseline) * premium_pct
	  se growth_pct >= growth_threshold_percent, altrimenti 0.
	"""

	def compute(
		self,
		*,
		agreement: dict,
		condition: dict,
		period: PeriodBounds,
		scope_sql: str,
		scope_params: dict,
	) -> RebateOutcome:
		metric = condition.get("target_metric") or "turnover"
		current = self._fetch_metric(
			agreement, period.start, period.end, metric, scope_sql, scope_params
		)

		target_amount = condition.get("target_amount")
		premium_pct = (
			Decimal(str(condition.get("growth_premium_percent") or 0)) / Decimal("100")
		)
		threshold_pct = (
			Decimal(str(condition.get("growth_threshold_percent") or 0))
			/ Decimal("100")
		)

		amount = Decimal("0")
		breakdown: dict = {
			"calculator": "target_growth",
			"metric": metric,
			"current": float(current),
		}

		if target_amount:
			target = Decimal(str(target_amount))
			excess = max(Decimal("0"), current - target)
			amount = excess * premium_pct
			breakdown.update(
				{
					"mode": "absolute_target",
					"target": float(target),
					"excess": float(excess),
					"premium_pct": float(premium_pct * 100),
					"premium": float(amount),
				}
			)
		else:
			months = int(condition.get("growth_baseline_months") or 12)
			b_start = add_months(period.start, -months)
			b_end = add_months(period.end, -months)
			baseline = self._fetch_metric(
				agreement, b_start, b_end, metric, scope_sql, scope_params
			)
			if baseline <= 0:
				breakdown.update(
					{
						"mode": "growth",
						"baseline": 0.0,
						"baseline_start": str(b_start),
						"baseline_end": str(b_end),
						"growth_pct": None,
						"note": "Baseline a zero — nessun premio.",
					}
				)
			else:
				growth = (current - baseline) / baseline
				if growth >= threshold_pct:
					delta = current - baseline
					amount = delta * premium_pct
				breakdown.update(
					{
						"mode": "growth",
						"baseline": float(baseline),
						"baseline_start": str(b_start),
						"baseline_end": str(b_end),
						"growth_pct": float(growth * 100),
						"threshold_pct": float(threshold_pct * 100),
						"premium_pct": float(premium_pct * 100),
						"delta": float(current - baseline),
						"premium": float(amount),
					}
				)

		return RebateOutcome(
			amount=amount,
			currency=agreement["currency"],
			breakdown=breakdown,
		)

	def _fetch_metric(
		self,
		agreement: dict,
		start,
		end,
		metric: str,
		scope_sql: str,
		scope_params: dict,
	) -> Decimal:
		expr = (
			"COALESCE(SUM(sii.qty * sii.net_rate), 0)"
			if metric == "turnover"
			else "COALESCE(SUM(sii.qty), 0)"
		)
		scope_clause = f"AND {scope_sql}" if scope_sql else ""
		sql = f"""
			SELECT {expr}
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			WHERE si.docstatus = 1
			  AND si.is_return = 0
			  AND si.customer = %(customer)s
			  AND si.posting_date BETWEEN %(start)s AND %(end)s
			  {scope_clause}
		"""
		params = {
			"customer": agreement["customer"],
			"start": start,
			"end": end,
			**scope_params,
		}
		return Decimal(str(frappe.db.sql(sql, params)[0][0] or 0))
