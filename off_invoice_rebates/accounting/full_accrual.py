# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Accounting policy: ``full_accrual``.

Books the rebate expense at competenza (Period Run submit) and transfers the
accrued liability to a payable at settlement time.

* Accrual JE  ``Dr rebate_expense_account / Cr rebate_accrued_liability_account``
  for ``period_run.total_amount`` — posted on ``Rebate Period Run.on_submit``.
* Settlement JE  ``Dr rebate_accrued_liability_account / Cr rebate_payable_account``
  for ``settlement.total_amount`` — posted on ``Rebate Settlement.on_submit``
  AFTER the F3 strategy. Net effect: the rebate cost is recognised at competenza,
  then the rateo flows into a payable at liquidation; the strategy-emitted
  document (NC / PE / compensation) eventually clears that payable from the
  customer side.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt

from off_invoice_rebates.accounting.base import AccountingResult, register
from off_invoice_rebates.accounting.coa_helpers import (
	get_company_from_agreement,
	get_company_from_settlement,
	make_journal_entry,
	resolve_account,
)


@register("full_accrual")
class FullAccrualPolicy:
	def post_accrual(self, period_run_doc) -> AccountingResult | None:
		amount = flt(period_run_doc.total_amount)
		if amount <= 0:
			return None

		agreement = frappe.get_cached_doc("Rebate Agreement", period_run_doc.agreement)
		company = get_company_from_agreement(period_run_doc.agreement)

		expense_account = resolve_account("rebate_expense_account", agreement)
		accrued_liability = resolve_account("rebate_accrued_liability_account", agreement)

		je_name = make_journal_entry(
			company=company,
			posting_date=period_run_doc.period_end,
			voucher_type="Journal Entry",
			user_remark=_("Accrual Premio Off-Invoice — {0} {1}").format(
				period_run_doc.agreement, period_run_doc.period_key
			),
			lines=[
				{
					"account": expense_account,
					"debit_in_account_currency": amount,
					"credit_in_account_currency": 0,
				},
				{
					"account": accrued_liability,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": amount,
				},
			],
			reference_doctype="Rebate Period Run",
			reference_name=period_run_doc.name,
		)
		return AccountingResult(
			policy="full_accrual",
			posted_doc_doctype="Journal Entry",
			posted_doc_name=je_name,
			notes="Accrual rateo passivo per competenza",
		)

	def post_settlement(self, settlement_doc) -> AccountingResult | None:
		amount = flt(settlement_doc.total_amount)
		if amount <= 0:
			return None

		agreement = frappe.get_cached_doc("Rebate Agreement", settlement_doc.agreement)
		company = get_company_from_settlement(settlement_doc)

		accrued_liability = resolve_account("rebate_accrued_liability_account", agreement)
		payable = resolve_account("rebate_payable_account", agreement)

		je_name = make_journal_entry(
			company=company,
			posting_date=settlement_doc.settlement_date,
			voucher_type="Journal Entry",
			user_remark=_("Trasferimento rateo→debito per liquidazione {0}").format(settlement_doc.name),
			lines=[
				{
					"account": accrued_liability,
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
			policy="full_accrual",
			posted_doc_doctype="Journal Entry",
			posted_doc_name=je_name,
			notes="Rateo→Debito v/Clienti per Premi",
		)

	def reverse_accrual(self, period_run_doc) -> AccountingResult | None:
		return _cancel_je_referencing(period_run_doc.name, policy="full_accrual")

	def reverse_settlement(self, settlement_doc) -> AccountingResult | None:
		if not settlement_doc.journal_entry:
			# Fallback: walk by reference_name in case the field was not set.
			return _cancel_je_referencing(settlement_doc.name, policy="full_accrual")
		try:
			je = frappe.get_doc("Journal Entry", settlement_doc.journal_entry)
			if je.docstatus == 1:
				je.cancel()
		except frappe.DoesNotExistError:
			return None
		return AccountingResult(
			policy="full_accrual",
			posted_doc_doctype="Journal Entry",
			posted_doc_name=settlement_doc.journal_entry,
			notes="Annullato",
		)


def _cancel_je_referencing(ref_name: str, *, policy: str) -> AccountingResult | None:
	"""Find submitted JEs whose ``cheque_no`` references ``ref_name`` and cancel
	them. Returns the first cancelled JE name (the caller cares only about
	whether something was reversed)."""
	names = frappe.get_all(
		"Journal Entry",
		filters={"cheque_no": ref_name, "docstatus": 1},
		pluck="name",
	)
	for n in names:
		je = frappe.get_doc("Journal Entry", n)
		je.cancel()
	if names:
		return AccountingResult(
			policy=policy,
			posted_doc_doctype="Journal Entry",
			posted_doc_name=names[0],
			notes=f"JE annullati: {', '.join(names)}",
		)
	return None
