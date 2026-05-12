# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (resolving descendants for tree-like dimensions, SQL
# filter generation) belongs to rebate-engine in F2.

from frappe.model.document import Document


class RebateScopeFilter(Document):
	pass
