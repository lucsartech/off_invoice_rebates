# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt
"""
Rebate Riconciliazione Contabile - per ciascuna Liquidazione Premio verifica
la presenza dei documenti contabili attesi in base alla politica e alla
modalita' di liquidazione, evidenziando le scritture mancanti (utile per
spotting di Settlement che hanno saltato il posting GL).
"""

import frappe
from frappe import _
from frappe.utils import flt

EXPECTED_DOC_BY_MODE = {
	"credit_note": "sales_invoice_nc",
	"invoice_compensation": "journal_entry",
	"payment_entry": "payment_entry",
}


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
			"label": _("Accordo Premio"),
			"fieldname": "agreement",
			"fieldtype": "Link",
			"options": "Rebate Agreement",
			"width": 170,
		},
		{
			"label": _("Data"),
			"fieldname": "settlement_date",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Modalita'"),
			"fieldname": "settlement_mode",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Politica Contabile"),
			"fieldname": "accounting_policy",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Stato"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Importo"),
			"fieldname": "total_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Valuta"),
			"fieldname": "currency",
			"fieldtype": "Link",
			"options": "Currency",
			"width": 70,
		},
		{
			"label": _("Doc. Atteso"),
			"fieldname": "expected_doc",
			"fieldtype": "Data",
			"width": 140,
		},
		{
			"label": _("Doc. Collegato"),
			"fieldname": "linked_doc",
			"fieldtype": "Dynamic Link",
			"options": "linked_doctype",
			"width": 170,
		},
		{
			"label": _("Totale GL Registrato"),
			"fieldname": "gl_total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"label": _("Differenza"),
			"fieldname": "diff",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130,
		},
		{
			"label": _("Stato Riconciliazione"),
			"fieldname": "reconciliation_status",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("DocType"),
			"fieldname": "linked_doctype",
			"fieldtype": "Data",
			"hidden": 1,
			"width": 0,
		},
	]


def get_data(filters):
	conditions = ["s.docstatus < 2"]
	params: dict = {}
	if filters.get("from_date"):
		conditions.append("s.settlement_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("s.settlement_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]
	if filters.get("customer"):
		conditions.append("s.customer = %(customer)s")
		params["customer"] = filters["customer"]
	if filters.get("agreement"):
		conditions.append("s.agreement = %(agreement)s")
		params["agreement"] = filters["agreement"]
	if filters.get("status"):
		conditions.append("s.status = %(status)s")
		params["status"] = filters["status"]

	where = " AND ".join(conditions)
	sql = f"""
		SELECT
			s.name,
			s.customer,
			s.agreement,
			s.settlement_date,
			s.settlement_mode,
			s.accounting_policy,
			s.status,
			s.currency,
			s.total_amount,
			s.sales_invoice_nc,
			s.payment_entry,
			s.journal_entry
		FROM `tabRebate Settlement` s
		WHERE {where}
		ORDER BY s.settlement_date DESC, s.name
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)
	output = []
	for row in rows:
		mode = row.get("settlement_mode")
		expected_field = EXPECTED_DOC_BY_MODE.get(mode)
		linked_doctype, linked_doc = _resolve_linked_doc(row, expected_field)

		gl_total = _gl_total(linked_doctype, linked_doc) if linked_doc else 0.0
		amount = flt(row.get("total_amount"))
		diff = gl_total - amount

		if not linked_doc and row.get("status") == "posted":
			status = _("MANCANTE - scrittura attesa non collegata")
		elif not linked_doc:
			status = _("In attesa")
		elif abs(diff) < 0.01:
			status = _("Riconciliato")
		else:
			status = _("Differenza")

		output.append(
			{
				"name": row.get("name"),
				"customer": row.get("customer"),
				"agreement": row.get("agreement"),
				"settlement_date": row.get("settlement_date"),
				"settlement_mode": mode,
				"accounting_policy": row.get("accounting_policy"),
				"status": row.get("status"),
				"total_amount": amount,
				"currency": row.get("currency"),
				"expected_doc": _label_for_field(expected_field),
				"linked_doctype": linked_doctype,
				"linked_doc": linked_doc,
				"gl_total": flt(gl_total),
				"diff": diff,
				"reconciliation_status": status,
			}
		)
	return output


def _label_for_field(field):
	return {
		"sales_invoice_nc": _("Nota di Credito"),
		"payment_entry": _("Payment Entry"),
		"journal_entry": _("Scrittura Contabile"),
	}.get(field, "")


def _resolve_linked_doc(row, expected_field):
	if not expected_field:
		return (None, None)
	doctype_map = {
		"sales_invoice_nc": "Sales Invoice",
		"payment_entry": "Payment Entry",
		"journal_entry": "Journal Entry",
	}
	return (doctype_map.get(expected_field), row.get(expected_field) or None)


def _gl_total(doctype, name):
	if not (doctype and name):
		return 0.0
	# Sum absolute (debit + credit) / 2 per voucher to estimate net amount posted.
	# For balanced JE/SI/PE this equals the document amount.
	res = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit), 0) AS debit, COALESCE(SUM(credit), 0) AS credit
		FROM `tabGL Entry`
		WHERE voucher_type = %s AND voucher_no = %s AND is_cancelled = 0
		""",
		(doctype, name),
		as_dict=True,
	)
	if not res:
		return 0.0
	return flt(res[0].get("debit") or 0.0)


def get_chart(data):
	if not data:
		return None
	buckets = {
		_("Riconciliato"): 0,
		_("In attesa"): 0,
		_("Differenza"): 0,
		_("MANCANTE - scrittura attesa non collegata"): 0,
	}
	for row in data:
		buckets[row.get("reconciliation_status")] = buckets.get(row.get("reconciliation_status"), 0) + 1
	labels = list(buckets.keys())
	values = [buckets[k] for k in labels]
	return {
		"type": "pie",
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Liquidazioni"), "values": values}],
		},
	}


def get_summary(data):
	if not data:
		return []
	reconciled = sum(1 for row in data if row.get("reconciliation_status") == _("Riconciliato"))
	missing = sum(
		1
		for row in data
		if row.get("reconciliation_status") == _("MANCANTE - scrittura attesa non collegata")
	)
	differing = sum(1 for row in data if row.get("reconciliation_status") == _("Differenza"))
	return [
		{
			"value": reconciled,
			"label": _("Riconciliate"),
			"datatype": "Int",
			"indicator": "Green",
		},
		{
			"value": missing,
			"label": _("Scritture Mancanti"),
			"datatype": "Int",
			"indicator": "Red",
		},
		{
			"value": differing,
			"label": _("Differenze"),
			"datatype": "Int",
			"indicator": "Orange",
		},
	]
