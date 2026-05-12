# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategy: invoice compensation (compensazione su prossima fattura).

Two-stage flow:

1. ``InvoiceCompensationStrategy.settle`` does NOT generate any document
   immediately. It marks the Settlement as ``status = generated`` to signal
   that it is waiting to be consumed by the next outgoing Sales Invoice.
2. A ``doc_event`` on ``Sales Invoice.validate`` calls
   :func:`apply_pending_compensations_on_sales_invoice`, which appends a
   negative-rate line item for each pending compensation Settlement matching
   the invoice's customer + currency, then flips the Settlement to
   ``status = posted`` so the same compensation cannot be applied twice.

GL Entry side-effects belong to F4 in the accounting layer.
"""

from __future__ import annotations

import frappe
from frappe import _

from off_invoice_rebates.settlement.base import SettlementResult, register
from off_invoice_rebates.settlement.credit_note import ensure_rebate_item


@register("invoice_compensation")
class InvoiceCompensationStrategy:
	"""Marks the Settlement as pending-compensation; the actual line is added
	to the next customer Sales Invoice by the validate hook.
	"""

	def settle(self, settlement_doc) -> SettlementResult:
		if settlement_doc.status == "posted":
			frappe.throw(_("Settlement {0} gia' applicato.").format(settlement_doc.name))

		settlement_doc.db_set("status", "generated", update_modified=False)
		return SettlementResult(
			settlement_mode="invoice_compensation",
			primary_doc_doctype="Rebate Settlement",
			primary_doc_name=settlement_doc.name,
			notes="In attesa di applicazione sulla prossima fattura cliente.",
		)


def apply_pending_compensations_on_sales_invoice(doc, method=None) -> None:
	"""``doc_event`` hook on ``Sales Invoice.validate``.

	For each pending ``invoice_compensation`` Settlement matching the invoice's
	customer + currency, append a negative-rate line item carrying the rebate
	amount and tag the line with ``oir_rebate_settlement``. The Settlement is
	then marked ``status = posted`` so it cannot be re-consumed.
	"""
	if getattr(doc, "is_return", 0):
		return
	if getattr(doc, "docstatus", 0) != 0:
		return
	if not getattr(doc, "customer", None) or not getattr(doc, "items", None):
		return
	# Skip our own rebate NCs.
	if getattr(doc, "oir_rebate_settlement", None):
		return

	pending = frappe.get_all(
		"Rebate Settlement",
		filters={
			"customer": doc.customer,
			"settlement_mode": "invoice_compensation",
			"docstatus": 1,
			"status": "generated",
		},
		fields=["name", "total_amount", "causale", "currency"],
	)
	if not pending:
		return

	item_code = ensure_rebate_item()
	for s in pending:
		if s.currency and doc.currency and s.currency != doc.currency:
			# Currency mismatch: defer to F4 / manual handling.
			continue
		line = doc.append(
			"items",
			{
				"item_code": item_code,
				"qty": 1,
				"rate": -float(s.total_amount),
				"description": s.causale
				or _("Compensazione Premio {0}").format(s.name),
			},
		)
		# Tag the line with the settlement link (Custom Field on Sales Invoice
		# Item — may not exist yet in F3; tolerate absence).
		try:
			line.oir_rebate_settlement = s.name
		except Exception:
			pass
		frappe.db.set_value("Rebate Settlement", s.name, "status", "posted")


def revert_compensation_on_invoice_cancel(doc, method=None) -> None:
	"""``doc_event`` hook on ``Sales Invoice.on_cancel``.

	When a Sales Invoice that previously consumed pending compensation
	Settlements is cancelled, flip each linked Settlement back from
	``posted`` to ``generated`` so it can be re-applied on a future invoice.

	Looks for ``oir_rebate_settlement`` either on the invoice header (set on
	rebate NCs by the credit_note strategy) or on individual item rows (set
	by the invoice_compensation hook above). Header tagging is skipped — the
	header link identifies our own NC, not a consumed compensation.
	"""
	if doc.docstatus != 2:  # only act on cancelled docs
		return
	if not doc.items:
		return
	# A rebate NC has its own header oir_rebate_settlement link — its
	# settlement is the NC itself, not a compensation it consumed.
	if getattr(doc, "oir_rebate_settlement", None):
		return

	settlement_names: set[str] = set()
	for item in doc.items:
		s = getattr(item, "oir_rebate_settlement", None)
		if s:
			settlement_names.add(s)
	if not settlement_names:
		return

	for s_name in settlement_names:
		try:
			current_status = frappe.db.get_value(
				"Rebate Settlement", s_name, "status"
			)
			if current_status == "posted":
				frappe.db.set_value(
					"Rebate Settlement", s_name, "status", "generated"
				)
		except Exception as e:
			frappe.log_error(
				f"revert_compensation failed for {s_name}: {e}",
				"OIR settlement",
			)
