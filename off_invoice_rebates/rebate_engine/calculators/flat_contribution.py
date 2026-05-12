# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

from decimal import Decimal

from off_invoice_rebates.rebate_engine.calculators.base import (
	PeriodBounds,
	RebateOutcome,
	register,
)

_MONTHS = {"monthly": 1, "quarterly": 3, "annual": 12}


@register("flat_contribution")
class FlatContributionCalculator:
	"""Importo forfettario scalato dalla periodicità configurata alla cadenza del Run.

	Esempio: flat=12000 annuale, run mensile → 1000 al mese.
	"""

	def compute(
		self,
		*,
		agreement: dict,
		condition: dict,
		period: PeriodBounds,
		scope_sql: str,
		scope_params: dict,
	) -> RebateOutcome:
		flat_amount = Decimal(str(condition.get("flat_amount") or 0))
		flat_periodicity = condition.get("flat_periodicity") or "annual"

		if period.cadence not in _MONTHS:
			raise ValueError(f"Cadenza sconosciuta: {period.cadence}")
		if flat_periodicity not in _MONTHS:
			raise ValueError(f"Periodicità forfettario sconosciuta: {flat_periodicity}")

		run_months = _MONTHS[period.cadence]
		flat_months = _MONTHS[flat_periodicity]
		scaled = flat_amount * Decimal(run_months) / Decimal(flat_months)

		return RebateOutcome(
			amount=scaled,
			currency=agreement["currency"],
			breakdown={
				"calculator": "flat_contribution",
				"flat_amount": float(flat_amount),
				"flat_periodicity": flat_periodicity,
				"run_cadence": period.cadence,
				"scaled_to_run": float(scaled),
			},
		)
