# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Protocol + registry for Rebate Accounting Policies (F4).

A policy is responsible for the *rebate-specific* GL postings that complement
the strategy-generated documents from F3. Settlement strategies emit the
customer-facing fiscal document (NC / PE / compensation line) and rely on
ERPNext's standard posting; policies layer an additional Journal Entry that
routes the rebate expense / accrual to the dedicated accounts configured in
``Rebate Settings`` (with per-Agreement override).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, ClassVar, Protocol


@dataclass
class AccountingResult:
	"""Returned from each policy after a posting (or a no-op)."""

	policy: str
	posted_doc_doctype: str | None
	posted_doc_name: str | None
	notes: str = ""


class RebateAccountingPolicy(Protocol):
	code: ClassVar[str]

	def post_accrual(self, period_run_doc) -> AccountingResult | None:
		"""Called on ``Rebate Period Run.on_submit``. May return ``None`` if no
		posting applies (e.g. ``on_settlement`` / ``memo_only``)."""
		...

	def post_settlement(self, settlement_doc) -> AccountingResult | None:
		"""Called on ``Rebate Settlement.on_submit`` AFTER the strategy has run."""
		...

	def reverse_accrual(self, period_run_doc) -> AccountingResult | None:
		"""Called on ``Rebate Period Run.on_cancel``."""
		...

	def reverse_settlement(self, settlement_doc) -> AccountingResult | None:
		"""Called on ``Rebate Settlement.on_cancel``."""
		...


_REGISTRY: dict[str, type] = {}


def register(code: str) -> Callable[[type], type]:
	"""Decorator registering a policy class under ``code``."""

	def deco(cls: type) -> type:
		cls.code = code  # type: ignore[attr-defined]
		_REGISTRY[code] = cls
		return cls

	return deco


def get_policy(code: str) -> RebateAccountingPolicy:
	"""Resolve and instantiate the policy for ``code``.

	Raises a Frappe error in Italian if the code is unknown.
	"""
	if code not in _REGISTRY:
		import frappe
		from frappe import _

		frappe.throw(_("Politica contabile sconosciuta: {0}").format(code))
	return _REGISTRY[code]()


def registered_codes() -> list[str]:
	"""Debug helper — returns the list of registered policy codes."""
	return sorted(_REGISTRY.keys())
