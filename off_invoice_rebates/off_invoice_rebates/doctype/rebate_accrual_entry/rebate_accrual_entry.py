# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Population of `amount`, `condition_description`, and `breakdown` is
# performed by rebate-engine in F2 via the calculator strategy registry.

from frappe.model.document import Document


class RebateAccrualEntry(Document):
	pass
