# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Accounting policy: ``memo_only``.

No rebate-specific GL posting at any stage. The strategy-emitted document
(NC / PE / compensation line) carries its own standard ERPNext postings;
this policy intentionally adds nothing on top.
"""

from __future__ import annotations

from off_invoice_rebates.accounting.base import AccountingResult, register


@register("memo_only")
class MemoOnlyPolicy:
	def post_accrual(self, period_run_doc) -> AccountingResult | None:
		return AccountingResult(
			policy="memo_only",
			posted_doc_doctype=None,
			posted_doc_name=None,
			notes="Solo memo: nessun posting contabile",
		)

	def post_settlement(self, settlement_doc) -> AccountingResult | None:
		return AccountingResult(
			policy="memo_only",
			posted_doc_doctype=None,
			posted_doc_name=None,
			notes="Solo memo: nessun posting contabile",
		)

	def reverse_accrual(self, period_run_doc) -> AccountingResult | None:
		return None

	def reverse_settlement(self, settlement_doc) -> AccountingResult | None:
		return None
