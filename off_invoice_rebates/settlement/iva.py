# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Italian VAT regime resolver for Rebate Settlements (F3).

The resolver enforces the project's Italian fiscal rules:

* ``iva_regime = "in_natura"`` → NC con IVA che riduce la base imponibile
  (art. 26 DPR 633/72). The NC must carry ``return_against`` linking to the
  original Sales Invoice.
* ``iva_regime = "fuori_campo"`` → NC fuori campo IVA (art. 15 DPR 633/72)
  OR — for cash rebates — a Journal Entry (no fiscal document). In F3 we only
  emit an NC fuori campo when ``settlement_mode = credit_note``; the JE
  variant is handled by the accounting policy in F4.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IvaResolution:
	regime: str
	generates_credit_note: bool
	needs_return_against: bool
	notes: str = ""


def resolve(settlement_doc) -> IvaResolution:
	regime = settlement_doc.iva_regime
	if regime == "in_natura":
		return IvaResolution(
			regime="in_natura",
			generates_credit_note=True,
			needs_return_against=True,
			notes="NC con IVA art. 26 DPR 633/72 - riduzione base imponibile",
		)
	if regime == "fuori_campo":
		# NC fuori campo only when the mode actually generates a credit note.
		# For payment_entry/invoice_compensation the JE handling is F4 scope.
		return IvaResolution(
			regime="fuori_campo",
			generates_credit_note=(settlement_doc.settlement_mode == "credit_note"),
			needs_return_against=False,
			notes="Premio fuori campo IVA art. 15 DPR 633/72",
		)
	import frappe
	from frappe import _

	frappe.throw(_("Regime IVA non riconosciuto: {0}").format(regime))
