# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Settlement strategies package.

Importing this package side-effect-registers all built-in strategies into
the registry exposed by :mod:`off_invoice_rebates.settlement.base`.
"""

from off_invoice_rebates.settlement import (
	credit_note,
	invoice_compensation,
	payment_entry,
)
