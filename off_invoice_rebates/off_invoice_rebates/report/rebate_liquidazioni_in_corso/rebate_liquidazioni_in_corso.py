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
			"label": _("Liquidazione"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Rebate Settlement",
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
			"label": _("Data Liquidazione"),
			"fieldname": "settlement_date",
			"fieldtype": "Date",
			"width": 120,
		},
		{
			"label": _("Modalita'"),
			"fieldname": "settlement_mode",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Regime IVA"),
			"fieldname": "iva_regime",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Stato"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Totale"),
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
		{
			"label": _("Nota di Credito"),
			"fieldname": "sales_invoice_nc",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"width": 150,
		},
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150,
		},
		{
			"label": _("Scrittura Contabile"),
			"fieldname": "journal_entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 150,
		},
	]


def get_data(filters):
	# Default: show docs that are not yet 'posted' or 'cancelled' (i.e. in flight)
	status_filter = filters.get("status")
	conditions = []
	params: dict = {}

	if status_filter:
		conditions.append("s.status = %(status)s")
		params["status"] = status_filter
	else:
		conditions.append("s.status IN ('draft', 'generated')")

	if filters.get("customer"):
		conditions.append("s.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("agreement"):
		conditions.append("s.agreement = %(agreement)s")
		params["agreement"] = filters["agreement"]
	if filters.get("settlement_mode"):
		conditions.append("s.settlement_mode = %(settlement_mode)s")
		params["settlement_mode"] = filters["settlement_mode"]
	if filters.get("from_date"):
		conditions.append("s.settlement_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("s.settlement_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	conditions.append("s.docstatus < 2")
	where = " AND ".join(conditions)

	sql = f"""
		SELECT
			s.name,
			s.customer,
			cust.customer_name AS customer_name,
			s.agreement,
			s.settlement_date,
			s.settlement_mode,
			s.iva_regime,
			s.status,
			s.currency,
			s.total_amount,
			s.sales_invoice_nc,
			s.payment_entry,
			s.journal_entry
		FROM `tabRebate Settlement` s
		LEFT JOIN `tabCustomer` cust ON cust.name = s.customer
		WHERE {where}
		ORDER BY s.settlement_date DESC, s.name
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)
	for row in rows:
		row["total_amount"] = flt(row.get("total_amount"))
	return rows


def get_chart(data):
	if not data:
		return None
	mode_totals: dict = {}
	for row in data:
		mode = row.get("settlement_mode") or _("(non impostato)")
		mode_totals[mode] = mode_totals.get(mode, 0) + flt(row.get("total_amount"))
	if not mode_totals:
		return None
	labels = list(mode_totals.keys())
	values = [mode_totals[label] for label in labels]
	return {
		"type": "pie",
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Totale per Modalita'"), "values": values}],
		},
	}


def get_summary(data):
	if not data:
		return []
	total = sum(flt(row.get("total_amount")) for row in data)
	currency = next((row.get("currency") for row in data if row.get("currency")), None)
	by_status: dict = {}
	for row in data:
		by_status.setdefault(row.get("status") or "?", 0)
		by_status[row.get("status") or "?"] += 1
	summary = [
		{
			"value": len(data),
			"label": _("Liquidazioni Aperte"),
			"datatype": "Int",
			"indicator": "Orange",
		},
		{
			"value": total,
			"label": _("Totale Liquidazioni Aperte"),
			"datatype": "Currency",
			"currency": currency,
			"indicator": "Blue",
		},
	]
	for status, count in by_status.items():
		summary.append(
			{
				"value": count,
				"label": _("Stato: {0}").format(_(status)),
				"datatype": "Int",
				"indicator": "Grey",
			}
		)
	return summary
