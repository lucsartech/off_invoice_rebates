# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategy: emit a `Sales Invoice` with ``is_return = 1`` (NC).

Behaviour summary
-----------------
1. Reject if the Settlement already has a linked NC (``sales_invoice_nc``).
2. Resolve the Italian VAT regime via :mod:`off_invoice_rebates.settlement.iva`.
3. Build the Sales Invoice with the rebate naming series, ``is_return = 1``
   and a single rebate line whose total matches ``settlement.total_amount``.
4. For ``in_natura``: pick the most recent submitted Sales Invoice for the
   customer falling inside the period range covered by the Settlement's
   ``period_runs`` and set ``return_against``.
5. For ``fuori_campo``: emit the NC without taxes.
6. Tag the new SI with ``oir_rebate_settlement`` and submit it.
7. Persist the link back on the Settlement via ``db_set``.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, today

from off_invoice_rebates.settlement.base import SettlementResult, register
from off_invoice_rebates.settlement.iva import resolve as resolve_iva

_REBATE_ITEM_CODE = "OIR-Rebate"


@register("credit_note")
class CreditNoteStrategy:
	"""Generates a Sales Invoice with ``is_return = 1`` for the Settlement."""

	def settle(self, settlement_doc) -> SettlementResult:
		if settlement_doc.sales_invoice_nc:
			frappe.throw(
				_("Settlement {0} ha gia' una NC collegata: {1}").format(
					settlement_doc.name, settlement_doc.sales_invoice_nc
				)
			)

		iva = resolve_iva(settlement_doc)
		settings = frappe.get_cached_doc("Rebate Settings")
		company = self._resolve_company(settlement_doc)
		item_code = ensure_rebate_item()

		nc = frappe.new_doc("Sales Invoice")
		nc.naming_series = settings.nc_rebate_naming_series
		nc.customer = settlement_doc.customer
		nc.company = company
		nc.posting_date = settlement_doc.settlement_date or today()
		nc.set_posting_time = 1
		nc.currency = settlement_doc.currency
		nc.is_return = 1
		nc.update_stock = 0
		nc.oir_rebate_settlement = settlement_doc.name

		ref_si_doc = None
		if iva.needs_return_against:
			ref_si = self._pick_return_against(settlement_doc)
			if not ref_si:
				frappe.throw(
					_(
						"Nessuna fattura cliente trovata da referenziare per regime in_natura "
						"sul Settlement {0}. Creare una fattura nel periodo o cambiare regime IVA."
					).format(settlement_doc.name)
				)
			nc.return_against = ref_si
			ref_si_doc = frappe.get_doc("Sales Invoice", ref_si)
			# Copy fiscal preflight fields so the Italian region validator passes
			# (company_address, customer_address, fiscal codes).
			for f in (
				"company_address",
				"customer_address",
				"taxes_and_charges",
				"tax_category",
			):
				v = ref_si_doc.get(f)
				if v:
					nc.set(f, v)

		# is_return = 1 expects negative qty/rate. Use qty = -1 and positive rate
		# so ERPNext flips the sign on amount and the customer balance reduces.
		nc.append(
			"items",
			{
				"item_code": item_code,
				"qty": -1,
				"rate": flt(settlement_doc.total_amount),
				"description": settlement_doc.causale or _("Premio off-invoice"),
			},
		)

		# Tax handling per IVA regime.
		if iva.regime == "fuori_campo":
			# NC fuori campo: emit a single zero-rate tax row carrying the
			# exemption reason (mandatory for IT e-invoice preflight).
			self._apply_fuori_campo_taxes(nc, company)
		elif ref_si_doc is not None:
			# Copy taxes from the original SI so the NC inherits IVA rate(s).
			for t in ref_si_doc.taxes:
				row = {
					"charge_type": t.charge_type,
					"account_head": t.account_head,
					"description": t.description,
					"rate": t.rate,
					"included_in_print_rate": t.included_in_print_rate,
					"cost_center": t.cost_center,
				}
				if getattr(t, "tax_exemption_reason", None):
					row["tax_exemption_reason"] = t.tax_exemption_reason
				if getattr(t, "tax_exemption_law", None):
					row["tax_exemption_law"] = t.tax_exemption_law
				nc.append("taxes", row)

		nc.insert(ignore_permissions=True)
		nc.submit()

		settlement_doc.db_set("sales_invoice_nc", nc.name, update_modified=False)
		return SettlementResult(
			settlement_mode="credit_note",
			primary_doc_doctype="Sales Invoice",
			primary_doc_name=nc.name,
			notes=iva.notes,
		)

	# ------------------------------------------------------------------ helpers

	def _pick_return_against(self, settlement_doc) -> str | None:
		"""Return the most recent submitted, non-return Sales Invoice for the
		Settlement's customer whose ``posting_date`` falls inside the period
		range covered by the Settlement's ``period_runs``.
		"""
		period_run_names = [pr.period_run for pr in settlement_doc.period_runs]
		if not period_run_names:
			return None
		date_range = frappe.db.sql(
			"""SELECT MIN(period_start), MAX(period_end)
			   FROM `tabRebate Period Run`
			   WHERE name IN %(names)s""",
			{"names": tuple(period_run_names)},
		)
		if not date_range or not date_range[0][0]:
			return None
		d_start, d_end = date_range[0]
		return frappe.db.get_value(
			"Sales Invoice",
			{
				"customer": settlement_doc.customer,
				"docstatus": 1,
				"is_return": 0,
				"posting_date": ["between", [d_start, d_end]],
			},
			"name",
			order_by="posting_date desc",
		)

	def _apply_fuori_campo_taxes(self, nc, company: str) -> None:
		"""Append a single zero-rate tax row carrying the 'fuori campo IVA'
		exemption reason. The Italian e-invoice preflight requires at least one
		taxes row even for out-of-scope rebates.

		Account selection: any existing zero-rate Sales Tax account on the
		company, falling back to the first Tax-typed account.
		"""
		account_head = frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Tax", "is_group": 0},
			"name",
		) or frappe.db.get_value(
			"Account",
			{"company": company, "is_group": 0, "account_type": "Tax"},
			"name",
		)
		if not account_head:
			frappe.throw(
				_(
					"Nessun conto IVA configurato sulla Company {0}: impossibile emettere "
					"NC fuori campo. Configurare almeno un conto di tipo Tax."
				).format(company)
			)
		nc.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_head,
				"description": "Fuori campo IVA art. 15 DPR 633/72",
				"rate": 0,
				"tax_exemption_reason": "N1-Escluse ex art. 15",
				"tax_exemption_law": "Art. 15 DPR 633/72",
			},
		)

	def _resolve_company(self, settlement_doc) -> str:
		company = (
			frappe.db.get_value("Customer", settlement_doc.customer, "represents_company")
			or frappe.defaults.get_user_default("company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)
		if not company:
			frappe.throw(
				_("Impossibile risolvere la Company per il Settlement {0}").format(settlement_doc.name)
			)
		return company


def ensure_rebate_item() -> str:
	"""Return the stable item code reserved for rebate lines, creating it on
	first use. The item is a non-stock service item so it can be safely used in
	any company.
	"""
	if not frappe.db.exists("Item", _REBATE_ITEM_CODE):
		item = frappe.new_doc("Item")
		item.item_code = _REBATE_ITEM_CODE
		item.item_name = "Rebate Off-Invoice"
		item.item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
		item.is_stock_item = 0
		item.include_item_in_manufacturing = 0
		item.description = "Articolo di servizio per emissione NC/Settlement Rebate Off-Invoice"
		item.insert(ignore_permissions=True)
	return _REBATE_ITEM_CODE
