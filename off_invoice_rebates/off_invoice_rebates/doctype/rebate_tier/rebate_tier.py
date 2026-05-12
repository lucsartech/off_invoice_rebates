# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (validation of tier monotonicity / gaps) belongs to
# rebate-engine / doctype-builder in F2.

from frappe.model.document import Document


class RebateTier(Document):
	pass
