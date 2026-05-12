# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

# Minimal stub controller required by Frappe to load the DocType.
# Business logic (validate, on_submit, on_cancel, calculator dispatch,
# accrual recomputation, idempotency, totals roll-up, etc.) belongs to
# rebate-engine in F2.
#
# TODO F2: enforce unique(agreement, period_key) in validate.
# TODO F2: lock accruals child table once docstatus == 1.
# TODO F2: recompute total_amount from accruals on save.
# TODO F2: recompute settled_amount and settlement_status from linked
#          submitted Rebate Settlement / Rebate Settlement Period Run rows.

from frappe.model.document import Document


class RebatePeriodRun(Document):
	pass
