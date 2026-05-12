# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class RebatePeriodRun(Document):
	def validate(self) -> None:
		self._validate_period_dates()
		self._populate_from_agreement()
		self._validate_unique_period()
		self._recompute_totals()

	def before_submit(self) -> None:
		if self.compute_status != "computed":
			frappe.throw(
				_(
					"Period Run sottomettibile solo con compute_status='computed'. "
					"Stato attuale: {0}"
				).format(self.compute_status or "—")
			)

	def on_submit(self) -> None:
		# Lock — re-computation forbidden after submit.
		# Settlement logic reads from this Run in F3.
		pass

	def on_cancel(self) -> None:
		linked = frappe.db.exists(
			"Rebate Settlement Period Run",
			{
				"period_run": self.name,
				"parenttype": "Rebate Settlement",
				"docstatus": 1,
			},
		)
		if linked:
			frappe.throw(
				_(
					"Impossibile cancellare: questo Period Run è già stato liquidato "
					"in un Settlement."
				)
			)

	# ------------------------------------------------------------------ helpers

	def _validate_period_dates(self) -> None:
		if self.period_end and self.period_start and self.period_end <= self.period_start:
			frappe.throw(_("La fine periodo deve essere successiva all'inizio periodo."))

	def _validate_unique_period(self) -> None:
		if not (self.agreement and self.period_key):
			return
		existing = frappe.db.get_value(
			"Rebate Period Run",
			{
				"agreement": self.agreement,
				"period_key": self.period_key,
				"name": ("!=", self.name or ""),
				"docstatus": ("!=", 2),
			},
			"name",
		)
		if existing:
			frappe.throw(
				_(
					"Esiste già un Period Run per Accordo {0} periodo {1}: {2}."
				).format(self.agreement, self.period_key, existing)
			)

	def _populate_from_agreement(self) -> None:
		if not self.agreement:
			return
		try:
			ag = frappe.get_cached_doc("Rebate Agreement", self.agreement)
		except Exception:
			return

		if not self.currency:
			self.currency = ag.currency
		if not self.agreement_title:
			self.agreement_title = ag.title
		if not self.customer:
			self.customer = ag.customer

		# Cadence is mandatory on the JSON schema — populate from the single
		# schedule row on the Agreement when not provided by the caller.
		if not self.cadence and ag.schedules:
			self.cadence = ag.schedules[0].cadence

	def _recompute_totals(self) -> None:
		total = sum(flt(a.amount) for a in (self.accruals or []))
		self.total_amount = total
		if not self.settlement_status:
			self.settlement_status = "unsettled"
		if self.settled_amount is None:
			self.settled_amount = 0
