# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (validate, on_submit, on_cancel, single-row schedule
# enforcement, defaults from Rebate Settings, auto-title generation, etc.)
# belongs to doctype-builder in F2.

from frappe.model.document import Document


class RebateAgreement(Document):
	pass
