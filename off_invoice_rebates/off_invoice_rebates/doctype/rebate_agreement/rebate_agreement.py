# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# Fields whose default lives on Rebate Settings.
_AGREEMENT_DEFAULTS_FROM_SETTINGS: dict[str, str] = {
	"settlement_mode": "default_settlement_mode",
	"accounting_policy": "default_accounting_policy",
	"iva_regime": "default_iva_regime",
	"rebate_expense_account": "rebate_expense_account",
	"rebate_accrued_liability_account": "rebate_accrued_liability_account",
	"rebate_payable_account": "rebate_payable_account",
}


class RebateAgreement(Document):
	def before_insert(self) -> None:
		self._populate_defaults_from_settings()

	def validate(self) -> None:
		self._validate_dates()
		self._validate_conditions()
		self._validate_single_schedule()
		self._set_title_if_empty()

	def on_submit(self) -> None:
		# Lifecycle hook reserved for rebate-engine wiring (F2.2).
		# Workflow handles the Draft -> Active state transition automatically.
		pass

	def on_cancel(self) -> None:
		if frappe.db.exists("Rebate Period Run", {"agreement": self.name, "docstatus": 1}):
			frappe.throw(
				_("Impossibile cancellare l'Accordo: esistono Period Run sottomessi.")
			)

	# ------------------------------------------------------------------ helpers

	def _populate_defaults_from_settings(self) -> None:
		try:
			settings = frappe.get_cached_doc("Rebate Settings")
		except Exception:
			return

		# naming_series default if blank.
		if not (self.naming_series or "").strip() and settings.agreement_naming_series:
			self.naming_series = settings.agreement_naming_series

		for ag_field, settings_field in _AGREEMENT_DEFAULTS_FROM_SETTINGS.items():
			if not self.get(ag_field):
				value = settings.get(settings_field)
				if value:
					self.set(ag_field, value)

	def _validate_dates(self) -> None:
		if self.start_date and self.end_date and self.end_date <= self.start_date:
			frappe.throw(_("La data di fine deve essere successiva alla data di inizio."))

	def _validate_conditions(self) -> None:
		if not self.conditions:
			frappe.throw(_("Almeno una Condizione di calcolo è obbligatoria."))
		for row in self.conditions:
			self._validate_condition_row(row)

	def _validate_condition_row(self, c) -> None:
		code = c.calculator_code
		if not code:
			frappe.throw(
				_("Riga {0}: il codice calcolatore è obbligatorio.").format(c.idx)
			)

		if code == "turnover_tiered":
			tiers = self._resolve_tiers(c)
			if not tiers:
				frappe.throw(
					_(
						"Riga {0}: la condizione 'Scaglioni di Fatturato' richiede almeno "
						"una riga di scaglione."
					).format(c.idx)
				)
			self._validate_tiers_monotonic(c, tiers)
		elif code == "volume":
			if not flt(c.volume_unit_amount) or not c.volume_unit_of_measure:
				frappe.throw(
					_(
						"Riga {0}: la condizione 'Volume' richiede importo unitario e UOM."
					).format(c.idx)
				)
		elif code == "target_growth":
			if not flt(c.growth_premium_percent):
				frappe.throw(
					_(
						"Riga {0}: la condizione 'Target & Crescita' richiede growth_premium_percent."
					).format(c.idx)
				)
		elif code == "flat_contribution":
			if not flt(c.flat_amount) or not c.flat_periodicity:
				frappe.throw(
					_(
						"Riga {0}: la condizione 'Forfettario' richiede importo e periodicità."
					).format(c.idx)
				)

	def _resolve_tiers(self, condition) -> list:
		"""Return tiers either from the in-memory child table or from DB.
		Tiers are grandchildren (Rebate Agreement → Rebate Condition → Rebate Tier),
		and Frappe does NOT auto-load grandchildren on parent reload — so callers
		that re-validate after persistence need this DB fallback."""
		in_memory = list(condition.get("tiers") or [])
		if in_memory:
			return in_memory
		if not getattr(condition, "name", None):
			return []
		return frappe.get_all(
			"Rebate Tier",
			filters={"parent": condition.name, "parenttype": "Rebate Condition"},
			fields=["from_amount", "to_amount", "percentage", "idx"],
			order_by="idx asc",
		)

	def _validate_tiers_monotonic(self, condition, tiers=None) -> None:
		tiers = tiers if tiers is not None else self._resolve_tiers(condition)
		tiers = sorted(tiers, key=lambda t: flt(t.get("from_amount") if isinstance(t, dict) else t.from_amount))
		prev_to: float | None = None
		for idx, t in enumerate(tiers, start=1):
			from_amt = flt(t.get("from_amount") if isinstance(t, dict) else t.from_amount)
			raw_to = t.get("to_amount") if isinstance(t, dict) else t.to_amount
			to_amt = flt(raw_to) if raw_to is not None else None
			if to_amt is not None and to_amt and to_amt <= from_amt:
				frappe.throw(
					_("Scaglione {0}: 'A Importo' deve essere maggiore di 'Da Importo'.").format(idx)
				)
			if prev_to is not None and from_amt and from_amt < prev_to:
				frappe.throw(
					_("Scaglioni sovrapposti tra le righe — verificare i campi Da/A Importo.")
				)
			prev_to = to_amt if to_amt is not None else prev_to

	def _validate_single_schedule(self) -> None:
		if not self.schedules:
			frappe.throw(_("La Cadenza è obbligatoria."))
		if len(self.schedules) > 1:
			frappe.throw(_("È ammessa esattamente una riga di Cadenza per Accordo."))

	def _set_title_if_empty(self) -> None:
		if not self.title and self.customer:
			label = self.customer_name or self.customer
			self.title = f"{label} {self.start_date or ''} → {self.end_date or ''}".strip()
