# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date, timedelta

from frappe.utils import get_first_day, get_last_day, getdate

from off_invoice_rebates.rebate_engine.calculators.base import PeriodBounds


def bounds_for_cadence(cadence: str, anchor) -> PeriodBounds:
	"""Ritorna i PeriodBounds che contengono `anchor` per la cadenza richiesta."""
	anchor = getdate(anchor)
	if cadence == "monthly":
		start = get_first_day(anchor)
		end = get_last_day(anchor)
		key = anchor.strftime("%Y-%m")
	elif cadence == "quarterly":
		q = (anchor.month - 1) // 3
		start = date(anchor.year, q * 3 + 1, 1)
		end = get_last_day(date(anchor.year, q * 3 + 3, 1))
		key = f"{anchor.year}-Q{q + 1}"
	elif cadence == "annual":
		start = date(anchor.year, 1, 1)
		end = date(anchor.year, 12, 31)
		key = str(anchor.year)
	else:
		raise ValueError(f"Cadenza non gestita: {cadence}")
	return PeriodBounds(
		period_key=key,
		cadence=cadence,
		start=str(start),
		end=str(end),
	)


def next_period_after(cadence: str, current_end) -> PeriodBounds:
	"""Ritorna il PeriodBounds del periodo successivo a `current_end`."""
	return bounds_for_cadence(cadence, getdate(current_end) + timedelta(days=1))


def is_period_complete(period: PeriodBounds, today=None) -> bool:
	"""Un periodo è 'chiuso' quando oggi è successivo all'ultimo giorno."""
	today = getdate(today) if today is not None else getdate()
	return today > getdate(period.end)
