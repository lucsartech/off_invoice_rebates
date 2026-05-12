# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt
"""
Rebate Premi per Gruppo - aggrega gli importi maturati per dimensione di perimetro
(item_group, brand, territory, customer_group) derivata dagli scope_filters
dell'Accordo Premio collegato al Period Run.

Nota: lo scope e' definito a livello di Accordo, non per singola riga di accrual.
Il report attribuisce l'intero maturato del Period Run alla combinazione di
dimensioni dichiarate sull'Accordo. Se un Accordo ha piu' scope filter, il
maturato viene contato una volta per dimensione (con un raggruppamento per
valore dimensione/Accordo per evitare doppie somme).
"""

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns(filters):
	dimension_label = {
		"item_group": _("Gruppo Articolo"),
		"brand": _("Marchio"),
		"territory": _("Territorio"),
		"customer_group": _("Gruppo Cliente"),
	}.get(filters.get("dimension"), _("Dimensione"))

	return [
		{
			"label": _("Dimensione"),
			"fieldname": "dimension",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": dimension_label,
			"fieldname": "dimension_value",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Accordo Premio"),
			"fieldname": "agreement",
			"fieldtype": "Link",
			"options": "Rebate Agreement",
			"width": 180,
		},
		{
			"label": _("Cliente"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("Periodi"),
			"fieldname": "period_count",
			"fieldtype": "Int",
			"width": 90,
		},
		{
			"label": _("Maturato"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("Valuta"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
	]


def get_data(filters):
	dimension = filters.get("dimension") or "item_group"
	dim_field_map = {
		"item_group": "sf.item_group",
		"brand": "sf.brand",
		"territory": "sf.territory",
		"customer_group": "sf.customer_group",
	}
	dim_col = dim_field_map.get(dimension, "sf.item_group")

	conditions = ["pr.docstatus = 1", "sf.dimension = %(dimension)s", f"{dim_col} IS NOT NULL"]
	params: dict = {"dimension": dimension}

	if filters.get("from_date"):
		conditions.append("pr.period_end >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("pr.period_start <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	if filters.get("agreement"):
		conditions.append("pr.agreement = %(agreement)s")
		params["agreement"] = filters["agreement"]
	if filters.get("customer"):
		conditions.append("pr.customer = %(customer)s")
		params["customer"] = filters["customer"]

	where = " AND ".join(conditions)
	sql = f"""
		SELECT
			sf.dimension AS dimension,
			{dim_col} AS dimension_value,
			pr.agreement AS agreement,
			pr.customer AS customer,
			pr.currency AS currency,
			COUNT(DISTINCT pr.name) AS period_count,
			SUM(pr.total_amount) AS total_amount
		FROM `tabRebate Period Run` pr
		INNER JOIN `tabRebate Scope Filter` sf ON sf.parent = pr.agreement
		WHERE {where}
		GROUP BY sf.dimension, {dim_col}, pr.agreement, pr.customer, pr.currency
		ORDER BY total_amount DESC
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)
	for row in rows:
		row["total_amount"] = flt(row.get("total_amount"))
	return rows


def get_chart(data):
	if not data:
		return None
	totals: dict = {}
	for row in data:
		key = row.get("dimension_value") or _("(senza valore)")
		totals[key] = totals.get(key, 0) + flt(row.get("total_amount"))
	top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:10]
	return {
		"type": "bar",
		"data": {
			"labels": [k for k, _v in top],
			"datasets": [{"name": _("Maturato"), "values": [v for _k, v in top]}],
		},
	}


def get_summary(data):
	if not data:
		return []
	total = sum(flt(row.get("total_amount")) for row in data)
	currency = next((row.get("currency") for row in data if row.get("currency")), None)
	return [
		{
			"value": total,
			"label": _("Totale Maturato (Perimetro)"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Blue",
		},
		{
			"value": len({row.get("dimension_value") for row in data}),
			"label": _("Valori Distinti"),
			"datatype": "Int",
			"indicator": "Grey",
		},
	]
