# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (per-calculator field consistency checks, dispatch to
# RebateCalculator implementations) belongs to rebate-engine in F2.

from frappe.model.document import Document


class RebateCondition(Document):
	pass
