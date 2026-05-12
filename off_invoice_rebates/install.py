import os

import frappe
from frappe.modules.import_file import import_file_by_path


def after_install():
	_sync_workflows()


def after_migrate():
	_sync_workflows()


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
