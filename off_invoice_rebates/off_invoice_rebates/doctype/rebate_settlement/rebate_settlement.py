# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (validate that period_runs belong to the same agreement,
# enforce amount_to_settle <= period_total - period_already_settled,
# settlement strategy dispatch, default causale from Rebate Settings,
# status transitions, totals roll-up from period_runs) belongs to
# settlement-accounting in F3 and rebate-engine in F2.

from frappe.model.document import Document


class RebateSettlement(Document):
	pass
