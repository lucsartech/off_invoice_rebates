# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategy: emit a `Payment Entry` (no fiscal document).

The strategy uses ``payment_type = "Pay"`` with ``party_type = "Customer"``,
representing cash going out to settle a rebate we owe the customer.

GL Entry detail is delegated to ERPNext's standard Payment Entry posting in
F3. F4 may extend this with rebate-specific GL postings via the accounting
policies (e.g. moving the offset to ``rebate_expense_account`` instead of the
customer receivable).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, today

from off_invoice_rebates.settlement.base import SettlementResult, register


@register("payment_entry")
class PaymentEntryStrategy:
	def settle(self, settlement_doc) -> SettlementResult:
		if settlement_doc.payment_entry:
			frappe.throw(
				_("Settlement {0} ha gia' un Payment Entry collegato: {1}").format(
					settlement_doc.name, settlement_doc.payment_entry
				)
			)

		company = self._resolve_company(settlement_doc)
		paid_from, paid_to = self._resolve_accounts(company)
		posting_date = settlement_doc.settlement_date or today()

		pe = frappe.new_doc("Payment Entry")
		pe.payment_type = "Pay"
		pe.party_type = "Customer"
		pe.party = settlement_doc.customer
		pe.posting_date = posting_date
		pe.company = company
		pe.paid_amount = flt(settlement_doc.total_amount)
		pe.received_amount = flt(settlement_doc.total_amount)
		pe.paid_from = paid_from
		pe.paid_to = paid_to
		pe.paid_from_account_currency = settlement_doc.currency
		pe.paid_to_account_currency = settlement_doc.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.reference_no = settlement_doc.name
		pe.reference_date = posting_date

		pe.insert(ignore_permissions=True)
		pe.submit()

		settlement_doc.db_set("payment_entry", pe.name, update_modified=False)
		return SettlementResult(
			settlement_mode="payment_entry",
			primary_doc_doctype="Payment Entry",
			primary_doc_name=pe.name,
			notes=(
				"Pagamento separato - nessun documento fiscale; dettaglio GL "
				"gestito in F4 secondo accounting_policy."
			),
		)

	# ------------------------------------------------------------------ helpers

	def _resolve_company(self, settlement_doc) -> str:
		company = (
			frappe.db.get_value("Customer", settlement_doc.customer, "represents_company")
			or frappe.defaults.get_user_default("company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)
		if not company:
			frappe.throw(
				_("Impossibile risolvere la Company per il Settlement {0}").format(
					settlement_doc.name
				)
			)
		return company

	def _resolve_accounts(self, company: str) -> tuple[str, str]:
		"""Pick the bank/cash account (``paid_from``) and the customer
		receivable (``paid_to``) for the Payment Entry.

		Selection order:
		  * ``paid_from``: Company.default_cash_account → default_bank_account.
		  * ``paid_to``: Company.default_receivable_account →
			Rebate Settings.rebate_payable_account.
		"""
		settings = frappe.get_cached_doc("Rebate Settings")
		company_doc = frappe.get_cached_doc("Company", company)

		paid_from = (
			company_doc.default_cash_account or company_doc.default_bank_account
		)
		if not paid_from:
			frappe.throw(
				_(
					"Configurare un Cash o Bank Account di default sulla Company {0}."
				).format(company)
			)

		paid_to = (
			company_doc.default_receivable_account
			or settings.rebate_payable_account
		)
		if not paid_to:
			frappe.throw(
				_(
					"Configurare il conto debitori di default sulla Company {0} "
					"oppure il Conto Debiti v/Clienti per Premi Liquidati in Rebate Settings."
				).format(company)
			)
		return paid_from, paid_to
