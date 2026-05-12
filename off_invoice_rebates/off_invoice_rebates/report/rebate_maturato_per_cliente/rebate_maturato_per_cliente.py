# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": _("Cliente"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180,
		},
		{
			"label": _("Ragione Sociale"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Accordo Premio"),
			"fieldname": "agreement",
			"fieldtype": "Link",
			"options": "Rebate Agreement",
			"width": 180,
		},
		{
			"label": _("Periodo"),
			"fieldname": "period_key",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Inizio Periodo"),
			"fieldname": "period_start",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Fine Periodo"),
			"fieldname": "period_end",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Cadenza"),
			"fieldname": "cadence",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Maturato"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Liquidato"),
			"fieldname": "settled_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Residuo"),
			"fieldname": "residual",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Stato Liquidazione"),
			"fieldname": "settlement_status",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Valuta"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 80,
		},
		{
			"label": _("Period Run"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Rebate Period Run",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = ["pr.docstatus = 1"]
	params: dict = {}

	if filters.get("customer"):
		conditions.append("pr.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("agreement"):
		conditions.append("pr.agreement = %(agreement)s")
		params["agreement"] = filters["agreement"]
	if filters.get("from_date"):
		conditions.append("pr.period_end >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("pr.period_start <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	if filters.get("settlement_status"):
		conditions.append("pr.settlement_status = %(settlement_status)s")
		params["settlement_status"] = filters["settlement_status"]

	where = " AND ".join(conditions)
	sql = f"""
		SELECT
			pr.name,
			pr.customer,
			cust.customer_name AS customer_name,
			pr.agreement,
			pr.period_key,
			pr.period_start,
			pr.period_end,
			pr.cadence,
			pr.currency,
			pr.total_amount,
			pr.settled_amount,
			(pr.total_amount - pr.settled_amount) AS residual,
			pr.settlement_status
		FROM `tabRebate Period Run` pr
		LEFT JOIN `tabCustomer` cust ON cust.name = pr.customer
		WHERE {where}
		ORDER BY pr.customer, pr.period_start DESC
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)
	for row in rows:
		row["total_amount"] = flt(row.get("total_amount"))
		row["settled_amount"] = flt(row.get("settled_amount"))
		row["residual"] = flt(row.get("residual"))
	return rows


def get_chart(data):
	if not data:
		return None
	totals: dict = {}
	for row in data:
		customer = row.get("customer_name") or row.get("customer") or _("(senza nome)")
		totals[customer] = totals.get(customer, 0) + flt(row.get("total_amount"))
	top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:10]
	if not top:
		return None
	return {
		"type": "bar",
		"data": {
			"labels": [name for name, _value in top],
			"datasets": [{"name": _("Maturato"), "values": [value for _name, value in top]}],
		},
	}


def get_summary(data):
	if not data:
		return []
	total_accrued = sum(flt(row.get("total_amount")) for row in data)
	total_settled = sum(flt(row.get("settled_amount")) for row in data)
	residual = total_accrued - total_settled
	currency = next((row.get("currency") for row in data if row.get("currency")), None)
	return [
		{
			"value": total_accrued,
			"label": _("Totale Maturato"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Blue",
		},
		{
			"value": total_settled,
			"label": _("Totale Liquidato"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Green",
		},
		{
			"value": residual,
			"label": _("Residuo da Liquidare"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Orange",
		},
	]
