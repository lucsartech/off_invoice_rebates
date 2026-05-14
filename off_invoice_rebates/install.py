import os

import frappe
from frappe.modules.import_file import import_file_by_path


def after_install():
	_sync_workflows()
	_seed_rebate_item()


def after_migrate():
	_sync_workflows()


def before_tests():
	"""Seed the standard ERPNext test environment before our test suite runs.

	`bench run-tests --app off_invoice_rebates` invokes OUR `before_tests`, not
	ERPNext's. Without this, a fresh CI site has no Company / Warehouse Type /
	Item Group / Fiscal Year fixtures, and the test factory's `make_company`
	fails (e.g. `Could not find Warehouse Type: Transit`). Delegating to
	ERPNext's `before_tests` runs the setup wizard once and seeds everything.
	"""
	from erpnext.setup.utils import before_tests as erpnext_before_tests

	erpnext_before_tests()


def _sync_workflows():
	"""Workflow non è in IMPORTABLE_DOCTYPES → bench install/migrate non lo carica:
	importiamo manualmente i JSON in <module>/workflow/."""
	workflow_root = os.path.join(frappe.get_module_path("Off-Invoice Rebates"), "workflow")
	if not os.path.isdir(workflow_root):
		return
	for entry in os.listdir(workflow_root):
		json_path = os.path.join(workflow_root, entry, f"{entry}.json")
		if os.path.isfile(json_path):
			import_file_by_path(json_path, force=True)


def _seed_rebate_item():
	"""Seed the stable ``OIR-Rebate`` Item used by NC / compensation lines.

	Idempotent: skips when the Item already exists. Lives at install-time only
	so that the runtime ``ensure_rebate_item`` helper in
	``settlement.credit_note`` remains a safety-net for sites that miss it.
	"""
	if frappe.db.exists("Item", "OIR-Rebate"):
		return
	# Skip if ERPNext Item Group tree isn't seeded yet (e.g. fresh CI install
	# before setup wizard). settlement.credit_note.ensure_rebate_item() will
	# lazily create the Item on first NC emission.
	group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	if not group:
		return
	item = frappe.new_doc("Item")
	item.item_code = "OIR-Rebate"
	item.item_name = "Rebate Off-Invoice"
	item.item_group = group
	item.is_stock_item = 0
	item.include_item_in_manufacturing = 0
	item.description = (
		"Articolo di servizio per emissione documenti rebate. "
		"Generato automaticamente da off_invoice_rebates."
	)
	item.insert(ignore_permissions=True)
