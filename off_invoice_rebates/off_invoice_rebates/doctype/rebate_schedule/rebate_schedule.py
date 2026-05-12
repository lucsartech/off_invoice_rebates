# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (period boundary computation, next_run_date updates)
# belongs to rebate-engine in F2.

from frappe.model.document import Document


class RebateSchedule(Document):
	pass
