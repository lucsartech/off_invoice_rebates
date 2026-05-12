# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Chart-of-Accounts helpers for F4 policies.

* Company resolution shared between Settlement and Period Run callers (mirrors
  the resolver used by the F3 strategies).
* Account lookup with fallback chain: per-Agreement override → ``Rebate
  Settings`` global default → Italian error.
* Thin wrapper around ``frappe.new_doc("Journal Entry")`` that builds and
  submits a balanced JE in a single call. Reference to the originating Rebate
  document is stored in ``cheque_no`` so ``reverse_*`` can locate the JE
  later without needing a custom field.
"""

from __future__ import annotations

import frappe
from frappe import _


def get_company_from_settlement(settlement_doc) -> str:
	"""Resolve the Company for a Settlement.

	Order: Customer.represents_company → user default → Global Defaults.
	"""
	cust_company = (
		frappe.db.get_value("Customer", settlement_doc.customer, "represents_company")
		if settlement_doc.customer
		else None
	)
	return (
		cust_company
		or frappe.defaults.get_user_default("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or _throw_no_company()
	)


def get_company_from_agreement(agreement_name: str) -> str:
	customer = frappe.db.get_value("Rebate Agreement", agreement_name, "customer")
	cust_company = (
		frappe.db.get_value("Customer", customer, "represents_company")
		if customer
		else None
	)
	return (
		cust_company
		or frappe.defaults.get_user_default("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or _throw_no_company()
	)


def _throw_no_company():
	frappe.throw(_("Impossibile determinare la Company per l'operazione contabile."))


def resolve_account(
	account_field: str,
	agreement_doc=None,
	settings=None,
) -> str:
	"""Resolve an account name from Agreement override → Rebate Settings default."""
	if agreement_doc and getattr(agreement_doc, account_field, None):
		return getattr(agreement_doc, account_field)
	settings = settings or frappe.get_cached_doc("Rebate Settings")
	value = getattr(settings, account_field, None)
	if not value:
		_throw_account(account_field)
	return value


def _throw_account(field: str) -> None:
	frappe.throw(
		_(
			"Conto contabile {0} non configurato (né su Rebate Agreement né su Rebate Settings)."
		).format(field)
	)


def make_journal_entry(
	*,
	company: str,
	posting_date,
	voucher_type: str,
	user_remark: str,
	lines: list[dict],
	reference_doctype: str | None = None,
	reference_name: str | None = None,
) -> str:
	"""Create + submit a balanced Journal Entry. Returns the JE name.

	``lines``: list of dicts with at minimum ``account``,
	``debit_in_account_currency`` and ``credit_in_account_currency``.
	"""
	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = posting_date
	je.voucher_type = voucher_type
	je.user_remark = user_remark
	for line in lines:
		je.append("accounts", line)
	if reference_doctype and reference_name:
		# Use cheque_no/cheque_date as the reverse-lookup handle. A proper
		# Custom Field is on the F5 roadmap for the architect to add.
		je.cheque_no = reference_name
		je.cheque_date = posting_date
	je.insert(ignore_permissions=True)
	je.submit()
	return je.name
