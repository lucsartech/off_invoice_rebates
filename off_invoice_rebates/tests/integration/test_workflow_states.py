# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Rebate Agreement workflow transitions.

The agent definition spec calls out three transitions:
* Draft -> Active via Submit;
* Active -> Cancelled via Cancel;
* Active -> Expired by scheduler hint (we don't actually run a scheduler in
  the test — instead we verify the workflow definition allows that
  transition and the docstatus mapping matches).

We rely on the workflow JSON loaded by ``install.after_install``. The test
checks the state names + docstatus alignment rather than invoking the
workflow engine UI flow (which requires Workflow Manager perms in test mode).
"""

from __future__ import annotations

import frappe

from off_invoice_rebates.tests.fixtures.factories import (
	DEFAULT_CUSTOMER,
	make_agreement,
)
from off_invoice_rebates.tests.integration.base import OIRIntegrationTestCase


class TestRebateAgreementWorkflow(OIRIntegrationTestCase):
	def test_workflow_states_loaded(self) -> None:
		if not frappe.db.exists("Workflow", "Rebate Agreement Workflow"):
			self.skipTest("Workflow not installed - skipping")
		wf = frappe.get_doc("Workflow", "Rebate Agreement Workflow")
		states = {s.state: s.doc_status for s in wf.states}
		self.assertEqual(states.get("Draft"), "0")
		self.assertEqual(states.get("Active"), "1")
		self.assertEqual(states.get("Cancelled"), "2")
		# Expired is optional in some installations but should be wired here.
		self.assertIn("Expired", states)

	def test_workflow_transitions_loaded(self) -> None:
		if not frappe.db.exists("Workflow", "Rebate Agreement Workflow"):
			self.skipTest("Workflow not installed - skipping")
		wf = frappe.get_doc("Workflow", "Rebate Agreement Workflow")
		transitions = {(t.state, t.action, t.next_state) for t in wf.transitions}
		self.assertIn(("Draft", "Submit", "Active"), transitions)
		self.assertIn(("Active", "Cancel", "Cancelled"), transitions)
		self.assertIn(("Active", "Expire", "Expired"), transitions)

	def test_submitting_agreement_moves_to_active_docstatus(self) -> None:
		ag_name = make_agreement(
			customer=DEFAULT_CUSTOMER,
			calculator_code="flat_contribution",
			condition_overrides={"flat_amount": 1200, "flat_periodicity": "annual"},
			cadence="monthly",
		)
		ag = frappe.get_doc("Rebate Agreement", ag_name)
		self.assertEqual(ag.docstatus, 1)
