# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Computation of `period_already_settled` and validation of
# `amount_to_settle <= period_total_amount - period_already_settled`
# belongs to settlement-accounting in F3 (parent Rebate Settlement
# controller).

from frappe.model.document import Document


class RebateSettlementPeriodRun(Document):
	pass
