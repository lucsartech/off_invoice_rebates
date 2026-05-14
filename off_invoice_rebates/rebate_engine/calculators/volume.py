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


@register("volume")
class VolumeCalculator:
	"""Premio = somma qty (per UOM indicata) per importo per unita'."""

	def compute(
		self,
		*,
		agreement: dict,
		condition: dict,
		period: PeriodBounds,
		scope_sql: str,
		scope_params: dict,
	) -> RebateOutcome:
		uom = condition.get("volume_unit_of_measure")
		unit_amount = Decimal(str(condition.get("volume_unit_amount") or 0))

		scope_clause = f"AND {scope_sql}" if scope_sql else ""
		sql = f"""
			SELECT COALESCE(SUM(sii.qty), 0)
			FROM `tabSales Invoice Item` sii
			INNER JOIN `tabSales Invoice` si ON si.name = sii.parent
			WHERE si.docstatus = 1
			  AND si.is_return = 0
			  AND si.customer = %(customer)s
			  AND si.posting_date BETWEEN %(start)s AND %(end)s
			  AND sii.uom = %(uom)s
			  {scope_clause}
		"""
		params = {
			"customer": agreement["customer"],
			"start": period.start,
			"end": period.end,
			"uom": uom,
			**scope_params,
		}
		qty = Decimal(str(frappe.db.sql(sql, params)[0][0] or 0))
		amount = qty * unit_amount

		return RebateOutcome(
			amount=amount,
			currency=agreement["currency"],
			breakdown={
				"calculator": "volume",
				"uom": uom,
				"quantity": float(qty),
				"unit_amount": float(unit_amount),
			},
		)
