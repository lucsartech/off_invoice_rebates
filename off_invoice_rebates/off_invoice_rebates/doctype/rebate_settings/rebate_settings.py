# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

# Tokens we accept as a valid Frappe naming-series pattern.
_NAMING_SERIES_TOKENS: tuple[str, ...] = (".YYYY.", ".YY.", ".MM.", ".#####", ".####")

# Naming-series fields managed by Rebate Settings.
_NAMING_SERIES_FIELDS: tuple[str, ...] = (
	"agreement_naming_series",
	"period_run_naming_series",
	"settlement_naming_series",
	"nc_rebate_naming_series",
)


class RebateSettings(Document):
	def validate(self) -> None:
		self._validate_naming_series_patterns()
		self._validate_nc_series_distinct()

	def _validate_naming_series_patterns(self) -> None:
		"""Every naming series must contain a Frappe placeholder token."""
		for fieldname in _NAMING_SERIES_FIELDS:
			value: str | None = (self.get(fieldname) or "").strip()
			if not value:
				continue
			if not any(tok in value for tok in _NAMING_SERIES_TOKENS):
				label = self.meta.get_label(fieldname) or fieldname
				frappe.throw(
					_(
						"La serie di numerazione '{0}' ('{1}') non contiene alcun placeholder valido "
						"(es. .YYYY., .MM., .#####)."
					).format(label, value)
				)

	def _validate_nc_series_distinct(self) -> None:
		"""The NC naming series must be distinct from the other rebate series and
		should not collide with the standard Sales Invoice naming series options."""
		nc_series: str = (self.nc_rebate_naming_series or "").strip()
		if not nc_series:
			return

		for other in ("agreement_naming_series", "period_run_naming_series", "settlement_naming_series"):
			other_value: str = (self.get(other) or "").strip()
			if other_value and nc_series == other_value:
				label = self.meta.get_label(other) or other
				frappe.throw(
					_(
						"La 'Naming Series NC Premio' deve essere distinta dalle altre serie. "
						"Coincide con '{0}'."
					).format(label)
				)

		# Soft-collision check against Sales Invoice naming_series options.
		try:
			sales_invoice_options = frappe.get_meta("Sales Invoice").get_field("naming_series")
		except Exception:
			sales_invoice_options = None

		if sales_invoice_options and sales_invoice_options.options:
			existing_series = {
				line.strip()
				for line in sales_invoice_options.options.split("\n")
				if line.strip()
			}
			if nc_series in existing_series:
				frappe.msgprint(
					_(
						"Attenzione: la 'Naming Series NC Premio' ({0}) coincide con una serie "
						"standard di Sales Invoice. Per separare correttamente i registri IVA "
						"si consiglia una serie dedicata."
					).format(nc_series),
					indicator="orange",
					alert=True,
				)
