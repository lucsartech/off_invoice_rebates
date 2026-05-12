# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt
"""
Rebate Confronto Maturato vs Target - per gli Accordi che includono una
condizione di tipo `target_growth` confronta il maturato finora accumulato
con il target dichiarato (target_amount), evidenziando lo stato di
raggiungimento.
"""

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
			"label": _("Accordo Premio"),
			"fieldname": "agreement",
			"fieldtype": "Link",
			"options": "Rebate Agreement",
			"width": 200,
		},
		{
			"label": _("Cliente"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 160,
		},
		{
			"label": _("Ragione Sociale"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Inizio"),
			"fieldname": "start_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Fine"),
			"fieldname": "end_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Target"),
			"fieldname": "target_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("Maturato"),
			"fieldname": "accrued_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("% Raggiungimento"),
			"fieldname": "achievement_percent",
			"fieldtype": "Percent",
			"width": 130,
		},
		{
			"label": _("Scarto"),
			"fieldname": "gap_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 140,
		},
		{
			"label": _("Soglia Crescita %"),
			"fieldname": "growth_threshold_percent",
			"fieldtype": "Percent",
			"width": 120,
		},
		{
			"label": _("Premio Crescita %"),
			"fieldname": "growth_premium_percent",
			"fieldtype": "Percent",
			"width": 120,
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
	conditions = ["c.calculator_code = 'target_growth'", "ag.docstatus < 2"]
	params: dict = {}

	if filters.get("agreement"):
		conditions.append("ag.name = %(agreement)s")
		params["agreement"] = filters["agreement"]
	if filters.get("customer"):
		conditions.append("ag.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("from_date"):
		conditions.append("ag.end_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("ag.start_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	where = " AND ".join(conditions)

	sql = f"""
		SELECT
			ag.name AS agreement,
			ag.customer,
			cust.customer_name AS customer_name,
			ag.start_date,
			ag.end_date,
			ag.currency,
			c.target_amount,
			c.growth_threshold_percent,
			c.growth_premium_percent,
			COALESCE((
				SELECT SUM(pr.total_amount)
				FROM `tabRebate Period Run` pr
				WHERE pr.agreement = ag.name AND pr.docstatus = 1
			), 0) AS accrued_amount
		FROM `tabRebate Agreement` ag
		INNER JOIN `tabRebate Condition` c ON c.parent = ag.name
		LEFT JOIN `tabCustomer` cust ON cust.name = ag.customer
		WHERE {where}
		ORDER BY ag.start_date DESC, ag.name
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)
	for row in rows:
		target = flt(row.get("target_amount"))
		accrued = flt(row.get("accrued_amount"))
		row["target_amount"] = target
		row["accrued_amount"] = accrued
		row["gap_amount"] = accrued - target
		row["achievement_percent"] = (accrued / target * 100) if target else 0.0
	return rows


def get_chart(data):
	if not data:
		return None
	rows = [r for r in data if r.get("target_amount")][:10]
	if not rows:
		return None
	labels = [r.get("agreement") for r in rows]
	targets = [flt(r.get("target_amount")) for r in rows]
	accrued = [flt(r.get("accrued_amount")) for r in rows]
	return {
		"type": "bar",
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Target"), "values": targets},
				{"name": _("Maturato"), "values": accrued},
			],
		},
	}


def get_summary(data):
	if not data:
		return []
	total_target = sum(flt(row.get("target_amount")) for row in data)
	total_accrued = sum(flt(row.get("accrued_amount")) for row in data)
	achieved = sum(1 for row in data if flt(row.get("accrued_amount")) >= flt(row.get("target_amount")) > 0)
	currency = next((row.get("currency") for row in data if row.get("currency")), None)
	return [
		{
			"value": total_target,
			"label": _("Target Totale"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Grey",
		},
		{
			"value": total_accrued,
			"label": _("Maturato Totale"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Blue",
		},
		{
			"value": achieved,
			"label": _("Accordi a Target"),
			"datatype": "Int",
			"indicator": "Green",
		},
		{
			"value": len(data) - achieved,
			"label": _("Accordi sotto Target"),
			"datatype": "Int",
			"indicator": "Orange",
		},
	]
