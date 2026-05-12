# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Shared base class for integration tests.

Each subclass inherits ``OIRIntegrationTestCase`` which:
* extends Frappe's ``FrappeTestCase`` (provides ``self.assertDocumentEqual``
  and auto-rollback semantics);
* in ``setUpClass`` ensures the test company, customer, item, and Rebate
  Settings defaults exist;
* in ``tearDown`` calls ``frappe.db.rollback()`` so changes inside each test
  do not leak.
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from off_invoice_rebates.tests.fixtures.factories import (
	DEFAULT_COMPANY,
	DEFAULT_CUSTOMER,
	DEFAULT_ITEM,
	make_company,
	make_customer,
	make_item,
	make_rebate_settings_defaults,
)


class OIRIntegrationTestCase(FrappeTestCase):
	@classmethod
	def setUpClass(cls) -> None:
		super().setUpClass()
		make_company(DEFAULT_COMPANY)
		make_customer(DEFAULT_CUSTOMER)
		make_item(DEFAULT_ITEM)
		make_rebate_settings_defaults(DEFAULT_COMPANY)
		frappe.db.commit()

	def tearDown(self) -> None:
		frappe.db.rollback()
		super().tearDown()
