# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# Rounding tolerance for residual / total comparisons (cents).
_AMOUNT_TOLERANCE: float = 0.001


class RebateSettlement(Document):
	def validate(self) -> None:
		self._populate_from_agreement()
		self._validate_period_runs()
		self._recompute_total()

	def on_submit(self) -> None:
		self._update_period_run_settlement_status()
		self._dispatch_strategy()
		self._post_accounting()
		# Strategy may have flipped status to "posted"; default to "generated"
		# only when nothing more granular has been written.
		if not self.get("status") or self.status in ("draft", ""):
			self.db_set("status", "generated", update_modified=False)

	def _dispatch_strategy(self) -> None:
		# Importing the package side-effect-registers all built-in strategies.
		from off_invoice_rebates.settlement import (  # noqa: F401
			credit_note,
			invoice_compensation,
			payment_entry,
		)
		from off_invoice_rebates.settlement.base import get_strategy

		strategy = get_strategy(self.settlement_mode)
		strategy.settle(self)

	def _post_accounting(self) -> None:
		# Importing the package side-effect-registers all built-in policies.
		from off_invoice_rebates import accounting  # noqa: F401
		from off_invoice_rebates.accounting.base import get_policy

		policy = get_policy(self.accounting_policy)
		policy.post_settlement(self)

	def on_cancel(self) -> None:
		self._reverse_accounting()
		self._restore_period_run_settlement_status()
		self.db_set("status", "cancelled", update_modified=False)

	def _reverse_accounting(self) -> None:
		from off_invoice_rebates import accounting  # noqa: F401
		from off_invoice_rebates.accounting.base import get_policy

		policy = get_policy(self.accounting_policy)
		policy.reverse_settlement(self)

	# ------------------------------------------------------------------ helpers

	def _populate_from_agreement(self) -> None:
		if not self.agreement:
			return
		try:
			ag = frappe.get_cached_doc("Rebate Agreement", self.agreement)
		except Exception:
			return

		if not self.customer:
			self.customer = ag.customer
		if not self.currency:
			self.currency = ag.currency
		if not self.settlement_mode:
			self.settlement_mode = ag.settlement_mode
		if not self.accounting_policy:
			self.accounting_policy = ag.accounting_policy
		if not self.iva_regime:
			self.iva_regime = ag.iva_regime

		if not self.causale:
			try:
				settings = frappe.get_cached_doc("Rebate Settings")
			except Exception:
				settings = None
			if settings is not None:
				self.causale = (
					settings.default_causale_nc_premio_in_natura
					if self.iva_regime == "in_natura"
					else settings.default_causale_nc_premio_finanziario
				)

	def _validate_period_runs(self) -> None:
		if not self.period_runs:
			frappe.throw(_("Almeno un Period Run da liquidare è obbligatorio."))

		for row in self.period_runs:
			if not row.period_run:
				frappe.throw(
					_("Riga {0}: il Period Run è obbligatorio.").format(row.idx)
				)
			try:
				run = frappe.get_doc("Rebate Period Run", row.period_run)
			except frappe.DoesNotExistError:
				frappe.throw(
					_("Period Run {0} non trovato.").format(row.period_run)
				)
			if run.agreement != self.agreement:
				frappe.throw(
					_(
						"Period Run {0} appartiene a un altro Accordo Premio."
					).format(row.period_run)
				)
			if run.docstatus != 1:
				frappe.throw(
					_("Period Run {0} non è sottomesso.").format(row.period_run)
				)

			already_settled = self._already_settled_excluding_self(row.period_run)
			row.period_total_amount = flt(run.total_amount)
			row.period_already_settled = already_settled
			row.period_key = run.period_key
			residual = flt(run.total_amount) - already_settled

			if flt(row.amount_to_settle) <= 0:
				frappe.throw(
					_(
						"L'importo da liquidare deve essere maggiore di zero per il Period Run {0}."
					).format(row.period_run)
				)
			if flt(row.amount_to_settle) > residual + _AMOUNT_TOLERANCE:
				frappe.throw(
					_(
						"L'importo da liquidare ({0}) eccede il residuo ({1}) per il Period Run {2}."
					).format(flt(row.amount_to_settle), residual, row.period_run)
				)

	def _already_settled_excluding_self(self, period_run_name: str) -> float:
		result = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(srp.amount_to_settle), 0)
			FROM `tabRebate Settlement Period Run` srp
			INNER JOIN `tabRebate Settlement` s ON s.name = srp.parent
			WHERE srp.period_run = %(run)s
			  AND s.docstatus = 1
			  AND s.name != %(self)s
			""",
			{"run": period_run_name, "self": self.name or ""},
		)
		return flt(result[0][0]) if result else 0.0

	def _recompute_total(self) -> None:
		self.total_amount = sum(flt(r.amount_to_settle) for r in (self.period_runs or []))

	def _update_period_run_settlement_status(self) -> None:
		for row in self.period_runs:
			self._sync_period_run_status(row.period_run, include_self_row=row)

	def _restore_period_run_settlement_status(self) -> None:
		for row in self.period_runs:
			# On cancel: recompute excluding *this* document.
			self._sync_period_run_status(row.period_run, include_self_row=None)

	def _sync_period_run_status(self, period_run_name: str, include_self_row) -> None:
		try:
			run = frappe.get_doc("Rebate Period Run", period_run_name)
		except frappe.DoesNotExistError:
			return

		settled = self._already_settled_excluding_self(period_run_name)
		if include_self_row is not None:
			settled += flt(include_self_row.amount_to_settle)

		total = flt(run.total_amount)
		if total and settled >= total - _AMOUNT_TOLERANCE:
			new_status = "settled"
		elif settled > 0:
			new_status = "partial"
		else:
			new_status = "unsettled"

		run.db_set("settled_amount", settled, update_modified=False)
		run.db_set("settlement_status", new_status, update_modified=False)
