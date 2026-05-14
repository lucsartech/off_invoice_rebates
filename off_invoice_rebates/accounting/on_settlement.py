# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Accounting policy: ``on_settlement``.

No accrual entry. The full rebate cost is recognised at liquidation:

* On Period Run submit → no-op.
* On Settlement submit → ``Dr rebate_expense_account / Cr rebate_payable_account``
  for ``settlement.total_amount``. The strategy-emitted document then clears
  the payable from the customer side.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from off_invoice_rebates.accounting.base import AccountingResult, register
from off_invoice_rebates.accounting.coa_helpers import (
	get_company_from_settlement,
	make_journal_entry,
	resolve_account,
)


@register("on_settlement")
class OnSettlementPolicy:
	def post_accrual(self, period_run_doc) -> AccountingResult | None:
		# No accrual posting under this policy.
		return None

	def post_settlement(self, settlement_doc) -> AccountingResult | None:
		amount = flt(settlement_doc.total_amount)
		if amount <= 0:
			return None

		agreement = frappe.get_cached_doc("Rebate Agreement", settlement_doc.agreement)
		company = get_company_from_settlement(settlement_doc)

		expense_account = resolve_account("rebate_expense_account", agreement)
		payable = resolve_account("rebate_payable_account", agreement)

		je_name = make_journal_entry(
			company=company,
			posting_date=settlement_doc.settlement_date,
			voucher_type="Journal Entry",
			user_remark=_("Costo Premio Off-Invoice — Settlement {0}").format(settlement_doc.name),
			lines=[
				{
					"account": expense_account,
					"debit_in_account_currency": amount,
					"credit_in_account_currency": 0,
				},
				{
					"account": payable,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount,
				},
			],
			reference_doctype="Rebate Settlement",
			reference_name=settlement_doc.name,
		)
		settlement_doc.db_set("journal_entry", je_name, update_modified=False)
		return AccountingResult(
			policy="on_settlement",
			posted_doc_doctype="Journal Entry",
			posted_doc_name=je_name,
			notes="Costo riconosciuto a liquidazione",
		)

	def reverse_accrual(self, period_run_doc) -> AccountingResult | None:
		return None

	def reverse_settlement(self, settlement_doc) -> AccountingResult | None:
		if not settlement_doc.journal_entry:
			# Fallback by reference_name on cheque_no.
			names = frappe.get_all(
				"Journal Entry",
				filters={"cheque_no": settlement_doc.name, "docstatus": 1},
				pluck="name",
			)
			for n in names:
				je = frappe.get_doc("Journal Entry", n)
				je.cancel()
			if names:
				return AccountingResult(
					policy="on_settlement",
					posted_doc_doctype="Journal Entry",
					posted_doc_name=names[0],
					notes=f"JE annullati: {', '.join(names)}",
				)
			return None
		try:
			je = frappe.get_doc("Journal Entry", settlement_doc.journal_entry)
			if je.docstatus == 1:
				je.cancel()
		except frappe.DoesNotExistError:
			return None
		return AccountingResult(
			policy="on_settlement",
			posted_doc_doctype="Journal Entry",
			posted_doc_name=settlement_doc.journal_entry,
			notes="Annullato",
		)
