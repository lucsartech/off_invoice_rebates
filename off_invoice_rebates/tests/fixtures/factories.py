# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Idempotent factory helpers for integration tests.

Each helper returns the existing record when one matches the requested name,
otherwise it creates a fresh one. This keeps tests resilient against shared
fixtures while remaining safe to call inside a ``setUp`` that wraps everything
in ``frappe.db.rollback()``.

Helpers exposed:
* :func:`make_company` - default Italian company with COA + default accounts
* :func:`make_customer` - customer + Customer Group + Territory
* :func:`make_item` - service item used in NCs and Sales Invoices
* :func:`make_uom`
* :func:`make_rebate_settings_defaults` - ensures Rebate Settings has the
  three rebate accounts and naming series configured
* :func:`make_agreement` - submits a Rebate Agreement with a single condition
* :func:`make_sales_invoice` - submitted SI used to fill the period base
* :func:`make_period_run` - dispatcher-driven Period Run
* :func:`make_settlement` - submittable Rebate Settlement linked to runs
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

import frappe
from frappe.utils import flt, today

DEFAULT_CURRENCY: str = "EUR"
DEFAULT_COMPANY: str = "Test Rebate Co"
DEFAULT_COMPANY_ABBR: str = "TRC"
DEFAULT_CUSTOMER: str = "Test Rebate Customer"
DEFAULT_ITEM: str = "TEST-REB-ITEM"
DEFAULT_UOM: str = "Nos"


def make_company(name: str = DEFAULT_COMPANY, abbr: str = DEFAULT_COMPANY_ABBR) -> str:
	"""Ensure a non-regional company exists with a CoA and the rebate-relevant
	default accounts populated.

	We deliberately set ``country = "United States"`` to side-step the
	Italian-region SI validators (Tax ID, fiscal code, customer/company
	address, taxes and charges) - the rebate logic itself is country-agnostic.
	"""
	if frappe.db.exists("Company", name):
		_ensure_company_defaults(name)
		return name

	company = frappe.new_doc("Company")
	company.company_name = name
	company.abbr = abbr
	company.default_currency = DEFAULT_CURRENCY
	company.country = "United States"
	company.create_chart_of_accounts_based_on = "Standard Template"
	company.chart_of_accounts = "Standard"
	company.insert(ignore_permissions=True)
	frappe.db.commit()
	_ensure_company_defaults(name)
	return name


def _ensure_company_address(company: str) -> None:
	"""(Unused for the US-defaulted test company; retained for sites that
	switch the factory to an Italian configuration.)
	"""
	address_title = f"{company} HQ"
	if frappe.db.exists("Address", {"address_title": address_title}):
		return
	addr = frappe.new_doc("Address")
	addr.address_title = address_title
	addr.address_type = "Billing"
	addr.address_line1 = "1 Test Way"
	addr.city = "Testville"
	addr.country = "United States"
	addr.pincode = "00000"
	addr.is_primary_address = 1
	addr.append("links", {"link_doctype": "Company", "link_name": company})
	addr.insert(ignore_permissions=True)


def _ensure_company_defaults(company: str) -> None:
	"""Populate default cash / receivable / tax accounts on the company so the
	settlement strategies can resolve them. Picks the first matching account
	of each type when not already set.
	"""
	doc = frappe.get_doc("Company", company)

	def _pick(account_type: str) -> str | None:
		return frappe.db.get_value(
			"Account",
			{"company": company, "account_type": account_type, "is_group": 0},
			"name",
		)

	updates = {
		"default_cash_account": _pick("Cash") or _pick("Bank"),
		"default_receivable_account": _pick("Receivable"),
		"default_payable_account": _pick("Payable"),
		"default_expense_account": _pick("Expense Account") or _pick("Cost of Goods Sold"),
		"default_income_account": _pick("Income Account"),
	}
	changed = False
	for field, value in updates.items():
		if value and not doc.get(field):
			doc.set(field, value)
			changed = True
	if changed:
		doc.save(ignore_permissions=True)
		frappe.db.commit()


def make_uom(uom: str = DEFAULT_UOM) -> str:
	if not frappe.db.exists("UOM", uom):
		doc = frappe.new_doc("UOM")
		doc.uom_name = uom
		doc.must_be_whole_number = 1
		doc.insert(ignore_permissions=True)
	return uom


def make_item(item_code: str = DEFAULT_ITEM, uom: str = DEFAULT_UOM) -> str:
	if frappe.db.exists("Item", item_code):
		return item_code
	make_uom(uom)
	item = frappe.new_doc("Item")
	item.item_code = item_code
	item.item_name = item_code
	item.item_group = (
		frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
	)
	item.stock_uom = uom
	item.is_stock_item = 0
	item.include_item_in_manufacturing = 0
	item.insert(ignore_permissions=True)
	return item_code


def make_customer(name: str = DEFAULT_CUSTOMER, fresh: bool = False) -> str:
	"""Idempotent customer factory.

	When ``fresh=True``, also cancels and deletes any prior Sales Invoices
	pointing at this customer so an Agreement built against a unique customer
	starts from a clean base. We need this because ``si.submit()`` commits its
	GL entries, which breaks the ``FrappeTestCase`` savepoint-based rollback
	for cross-test isolation.
	"""
	if frappe.db.exists("Customer", name):
		# Backfill default_currency + tax_id on pre-existing customers so the
		# Italian region SI validator passes.
		if not frappe.db.get_value("Customer", name, "default_currency"):
			frappe.db.set_value("Customer", name, "default_currency", DEFAULT_CURRENCY)
		if not frappe.db.get_value("Customer", name, "tax_id"):
			frappe.db.set_value("Customer", name, "tax_id", "IT99988877766")
		_ensure_customer_address(name)
		if fresh:
			_purge_customer_invoices(name)
		return name
	group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name") or "All Customer Groups"
	territory = frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories"
	cust = frappe.new_doc("Customer")
	cust.customer_name = name
	cust.customer_group = group
	cust.territory = territory
	cust.customer_type = "Company"
	cust.default_currency = DEFAULT_CURRENCY
	cust.tax_id = "IT99988877766"
	cust.insert(ignore_permissions=True)
	_ensure_customer_address(name)
	return cust.name


def _purge_customer_invoices(customer: str) -> None:
	"""Cancel + delete all Sales Invoices for ``customer`` so the test starts
	from zero. Best-effort - any cancel error is swallowed.
	"""
	for si_name in frappe.get_all(
		"Sales Invoice",
		filters={"customer": customer},
		pluck="name",
	):
		try:
			si = frappe.get_doc("Sales Invoice", si_name)
			if si.docstatus == 1:
				si.cancel()
			frappe.delete_doc(
				"Sales Invoice", si_name, force=True, ignore_permissions=True
			)
		except Exception:
			pass
	frappe.db.commit()


def _ensure_customer_address(customer: str) -> None:
	"""Side-effect helper retained for sites that opt back into the Italian
	regional validators. The US-defaulted test company doesn't need this.
	"""
	address_title = f"{customer} HQ"
	if frappe.db.exists("Address", {"address_title": address_title}):
		return
	addr = frappe.new_doc("Address")
	addr.address_title = address_title
	addr.address_type = "Billing"
	addr.address_line1 = "1 Customer St"
	addr.city = "Testville"
	addr.country = "United States"
	addr.pincode = "00000"
	addr.is_primary_address = 1
	addr.append("links", {"link_doctype": "Customer", "link_name": customer})
	addr.insert(ignore_permissions=True)


def make_rebate_settings_defaults(company: str = DEFAULT_COMPANY) -> None:
	"""Populate Rebate Settings with the three rebate accounts plus reasonable
	naming series defaults. Idempotent - leaves existing values untouched.

	Also points Global Defaults at ``company`` so policy helpers that look up
	``default_company`` resolve to the test company.
	"""
	# Make our test company the site-wide default so the F4 policy resolvers
	# pick its accounts.
	gd = frappe.get_single("Global Defaults")
	if gd.default_company != company:
		gd.default_company = company
		gd.save(ignore_permissions=True)
		frappe.db.commit()

	settings = frappe.get_single("Rebate Settings")

	# Pick existing accounts compatible with the rebate flow. We deliberately
	# steer away from ``Payable``/``Receivable`` account_types because the
	# standard Journal Entry validator requires Party Type/Party on those.
	def _pick_account(account_type: str | None, root_type: str | None = None) -> str | None:
		filters: dict = {"company": company, "is_group": 0}
		if account_type:
			filters["account_type"] = account_type
		if root_type:
			filters["root_type"] = root_type
		return frappe.db.get_value("Account", filters, "name")

	def _pick_non_party_liability() -> str | None:
		# Any non-Payable liability leaf account, preferably non-tax.
		row = frappe.db.sql(
			"""
			SELECT name FROM `tabAccount`
			WHERE company = %s
			  AND is_group = 0
			  AND root_type = 'Liability'
			  AND (account_type IS NULL OR account_type NOT IN ('Payable','Tax','Receivable'))
			ORDER BY lft
			LIMIT 1
			""",
			(company,),
		)
		return row[0][0] if row else None

	expense = _pick_account("Expense Account") or _pick_account(None, root_type="Expense")
	payable = _pick_non_party_liability() or _pick_account(None, root_type="Liability")
	accrued = payable

	if not settings.rebate_expense_account and expense:
		settings.rebate_expense_account = expense
	if not settings.rebate_accrued_liability_account and accrued:
		settings.rebate_accrued_liability_account = accrued
	if not settings.rebate_payable_account and payable:
		settings.rebate_payable_account = payable

	if not settings.agreement_naming_series:
		settings.agreement_naming_series = "REB-AGR-.YYYY.-.#####"
	if not settings.period_run_naming_series:
		settings.period_run_naming_series = "REB-RUN-.YYYY.-.#####"
	if not settings.settlement_naming_series:
		settings.settlement_naming_series = "REB-SET-.YYYY.-.#####"
	if not settings.nc_rebate_naming_series:
		settings.nc_rebate_naming_series = "NC-REB-.YYYY.-.#####"
	if not settings.default_settlement_mode:
		settings.default_settlement_mode = "credit_note"
	if not settings.default_accounting_policy:
		settings.default_accounting_policy = "on_settlement"
	if not settings.default_iva_regime:
		settings.default_iva_regime = "fuori_campo"

	settings.save(ignore_permissions=True)
	frappe.db.commit()


def make_agreement(
	*,
	customer: str = DEFAULT_CUSTOMER,
	calculator_code: str = "flat_contribution",
	condition_overrides: dict | None = None,
	settlement_mode: str = "payment_entry",
	accounting_policy: str = "memo_only",
	iva_regime: str = "fuori_campo",
	cadence: str = "monthly",
	start_date: str = "2026-01-01",
	end_date: str = "2026-12-31",
	currency: str = DEFAULT_CURRENCY,
	scope_filters: list[dict] | None = None,
	expense_account: str | None = None,
	payable_account: str | None = None,
	accrued_account: str | None = None,
	submit: bool = True,
) -> str:
	"""Create and (optionally) submit a Rebate Agreement.

	``condition_overrides`` is a dict merged into the single child row built
	for ``calculator_code``. Defaults yield a minimal but valid configuration:
	* ``turnover_tiered`` - one tier 0..unlimited @ 1%
	* ``volume`` - 1.00 per Nos
	* ``target_growth`` - 10% premium, 5% threshold, 1y baseline
	* ``flat_contribution`` - 1200 annual
	"""
	make_customer(customer)
	ag = frappe.new_doc("Rebate Agreement")
	ag.customer = customer
	ag.start_date = start_date
	ag.end_date = end_date
	ag.currency = currency
	ag.settlement_mode = settlement_mode
	ag.accounting_policy = accounting_policy
	ag.iva_regime = iva_regime
	if expense_account:
		ag.rebate_expense_account = expense_account
	if payable_account:
		ag.rebate_payable_account = payable_account
	if accrued_account:
		ag.rebate_accrued_liability_account = accrued_account

	condition = _default_condition_for(calculator_code)
	if condition_overrides:
		tiers_override = condition_overrides.pop("tiers", None)
	else:
		tiers_override = None
	if condition_overrides:
		condition.update(condition_overrides)
	cond_row = ag.append("conditions", condition)
	# In-memory tier rows to satisfy ``_validate_condition_row`` (which checks
	# ``c.tiers`` is non-empty). These do NOT persist as grandchildren on
	# ``ag.insert`` - Frappe only auto-saves direct children - so we re-insert
	# them explicitly after the parent Rebate Condition has a stable name.
	tiers_in_memory: list[dict] = []
	if calculator_code == "turnover_tiered":
		tiers_in_memory = tiers_override or [
			{"from_amount": 0, "to_amount": 0, "percentage": 1}
		]
		for t in tiers_in_memory:
			cond_row.append("tiers", t)

	ag.append("schedules", {"cadence": cadence, "anchor_date": start_date})
	if scope_filters:
		for sf in scope_filters:
			ag.append("scope_filters", sf)

	ag.insert(ignore_permissions=True)

	# Persist the grandchildren now that ``cond_row.name`` is stable, then
	# re-attach the loaded tiers onto the in-memory cond rows so the controller
	# ``validate`` (which reads ``c.tiers`` directly) sees them at submit time.
	if tiers_in_memory:
		ag.reload()
		saved_cond = ag.conditions[0]
		for idx, t in enumerate(tiers_in_memory, start=1):
			tier = frappe.new_doc("Rebate Tier")
			tier.parent = saved_cond.name
			tier.parenttype = "Rebate Condition"
			tier.parentfield = "tiers"
			tier.idx = idx
			tier.from_amount = t.get("from_amount", 0)
			tier.to_amount = t.get("to_amount", 0)
			tier.percentage = t.get("percentage", 0)
			tier.insert(ignore_permissions=True)
		# Hydrate the tiers child table on the in-memory document so that
		# ``ag.submit()`` -> validate -> ``c.tiers`` finds them.
		ag.reload()
		hydrated = frappe.get_all(
			"Rebate Tier",
			filters={"parent": saved_cond.name, "parenttype": "Rebate Condition"},
			fields=["name", "from_amount", "to_amount", "percentage", "idx"],
			order_by="idx asc",
		)
		ag.conditions[0].tiers = [
			frappe.get_doc("Rebate Tier", row["name"]) for row in hydrated
		]
	if submit:
		ag.submit()
	return ag.name


def _default_condition_for(code: str) -> dict:
	if code == "turnover_tiered":
		return {
			"calculator_code": code,
			"description": "Test tiered",
			"tier_metric": "turnover",
		}
	if code == "volume":
		return {
			"calculator_code": code,
			"description": "Test volume",
			"volume_unit_amount": 1,
			"volume_unit_of_measure": DEFAULT_UOM,
		}
	if code == "target_growth":
		return {
			"calculator_code": code,
			"description": "Test target",
			"target_metric": "turnover",
			"growth_premium_percent": 10,
			"growth_threshold_percent": 5,
			"growth_baseline_months": 12,
		}
	if code == "flat_contribution":
		return {
			"calculator_code": code,
			"description": "Test flat",
			"flat_amount": 1200,
			"flat_periodicity": "annual",
		}
	raise ValueError(f"Unknown calculator code: {code}")


def make_sales_invoice(
	*,
	customer: str,
	company: str = DEFAULT_COMPANY,
	item_code: str = DEFAULT_ITEM,
	qty: float = 10,
	rate: float = 100,
	posting_date: str | None = None,
	submit: bool = True,
) -> str:
	make_item(item_code)
	make_customer(customer)
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	si.company = company
	si.posting_date = posting_date or today()
	si.set_posting_time = 1
	si.currency = DEFAULT_CURRENCY
	si.conversion_rate = 1
	si.update_stock = 0
	si.append(
		"items",
		{
			"item_code": item_code,
			"qty": qty,
			"rate": rate,
			"uom": DEFAULT_UOM,
		},
	)
	si.insert(ignore_permissions=True)
	if submit:
		si.submit()
	return si.name


def make_period_run(
	*,
	agreement: str,
	anchor_date: str,
	cadence: str | None = None,
	submit: bool = True,
) -> str:
	"""Run the dispatcher for the given agreement+anchor, then optionally
	submit the resulting Period Run.
	"""
	from off_invoice_rebates.rebate_engine.dispatcher import run_period_for_agreement

	cad = cadence or frappe.db.get_value(
		"Rebate Schedule",
		{"parent": agreement},
		"cadence",
	) or "monthly"
	run_name = run_period_for_agreement(
		agreement=agreement, cadence=cad, anchor_date=anchor_date
	)
	if submit:
		run = frappe.get_doc("Rebate Period Run", run_name)
		if run.docstatus == 0:
			run.submit()
	return run_name


def make_settlement(
	*,
	agreement: str,
	period_run: str,
	amount_to_settle: float | Decimal | None = None,
	settlement_mode: str | None = None,
	accounting_policy: str | None = None,
	iva_regime: str | None = None,
	settlement_date: str | None = None,
	submit: bool = True,
) -> str:
	run = frappe.get_doc("Rebate Period Run", period_run)
	amount = float(amount_to_settle) if amount_to_settle is not None else flt(run.total_amount)
	ag = frappe.get_doc("Rebate Agreement", agreement)

	s = frappe.new_doc("Rebate Settlement")
	s.agreement = agreement
	s.customer = ag.customer
	s.currency = ag.currency
	s.settlement_mode = settlement_mode or ag.settlement_mode
	s.accounting_policy = accounting_policy or ag.accounting_policy
	s.iva_regime = iva_regime or ag.iva_regime
	s.settlement_date = settlement_date or today()
	s.append(
		"period_runs",
		{"period_run": period_run, "amount_to_settle": amount},
	)
	s.insert(ignore_permissions=True)
	if submit:
		s.submit()
	return s.name


def get_gl_balance(voucher_no: str) -> tuple[float, float]:
	"""Return (sum_debit, sum_credit) for the GL Entries tied to ``voucher_no``.

	Useful in policy tests that need to verify Σ debits == Σ credits.
	"""
	rows = frappe.get_all(
		"GL Entry",
		filters={"voucher_no": voucher_no, "is_cancelled": 0},
		fields=["debit", "credit"],
	)
	total_debit = sum(flt(r.debit) for r in rows)
	total_credit = sum(flt(r.credit) for r in rows)
	return total_debit, total_credit


def force_set_oir_today(date_str: str) -> None:
	"""Tiny helper test-cases can call to deterministically anchor any
	module-level ``today()`` invocation.

	Falls back to a no-op when ``frappe.flags`` is unavailable (unit tests
	running outside a bench).
	"""
	try:
		frappe.flags.current_date = date_str
	except Exception:
		pass


__all__: Iterable[str] = (
	"DEFAULT_CURRENCY",
	"DEFAULT_COMPANY",
	"DEFAULT_COMPANY_ABBR",
	"DEFAULT_CUSTOMER",
	"DEFAULT_ITEM",
	"DEFAULT_UOM",
	"make_company",
	"make_customer",
	"make_item",
	"make_uom",
	"make_rebate_settings_defaults",
	"make_agreement",
	"make_sales_invoice",
	"make_period_run",
	"make_settlement",
	"get_gl_balance",
	"force_set_oir_today",
)
