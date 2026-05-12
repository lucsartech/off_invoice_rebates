# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

from decimal import Decimal

import frappe

from off_invoice_rebates.rebate_engine.calculators.base import (
	PeriodBounds,
	RebateOutcome,
	register,
)


@register("turnover_tiered")
class TurnoverTieredCalculator:
	"""Calcola il premio applicando in modo marginale gli scaglioni configurati
	sulla metrica selezionata (turnover = Σ qty * net_rate; quantity = Σ qty).
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
		base = self._fetch_base(agreement, condition, period, scope_sql, scope_params)

		tiers = sorted(
			condition.get("tiers") or [],
			key=lambda t: Decimal(str(t.get("from_amount") or 0)),
		)
		amount = Decimal("0")
		tier_breakdown: list[dict] = []
		for t in tiers:
			t_from = Decimal(str(t.get("from_amount") or 0))
			t_to_raw = t.get("to_amount")
			# `to_amount` empty (None) or 0 means: nessun limite superiore (+∞).
			t_to = None
			if t_to_raw not in (None, ""):
				candidate = Decimal(str(t_to_raw))
				if candidate > 0:
					t_to = candidate
			pct = Decimal(str(t.get("percentage") or 0)) / Decimal("100")
			if base <= t_from:
				break
			slice_top = min(base, t_to) if t_to else base
			slice_amt = slice_top - t_from
			if slice_amt <= 0:
				continue
			premium = slice_amt * pct
			amount += premium
			tier_breakdown.append(
				{
					"from": float(t_from),
					"to": float(t_to) if t_to else None,
					"percentage": float(pct * 100),
					"slice": float(slice_amt),
					"premium": float(premium),
				}
			)

		return RebateOutcome(
			amount=amount,
			currency=agreement["currency"],
			breakdown={
				"calculator": "turnover_tiered",
				"tier_metric": condition.get("tier_metric") or "turnover",
				"base": float(base),
				"tiers": tier_breakdown,
			},
		)

	def _fetch_base(
		self,
		agreement: dict,
		condition: dict,
		period: PeriodBounds,
		scope_sql: str,
		scope_params: dict,
	) -> Decimal:
		tier_metric = condition.get("tier_metric") or "turnover"
		if tier_metric == "turnover":
			sum_expr = "COALESCE(SUM(sii.qty * sii.net_rate), 0)"
		else:
			sum_expr = "COALESCE(SUM(sii.qty), 0)"

		scope_clause = f"AND {scope_sql}" if scope_sql else ""
		sql = f"""
			SELECT {sum_expr}
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
			"start": period.start,
			"end": period.end,
			**scope_params,
		}
		result = frappe.db.sql(sql, params)
		return Decimal(str(result[0][0] or 0))
