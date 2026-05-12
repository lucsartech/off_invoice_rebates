# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

"""Strategy Protocol + registry for Rebate Settlement materialization (F3).

Each strategy maps a `settlement_mode` (`credit_note` | `invoice_compensation` |
`payment_entry`) to the concrete downstream document(s) that materialize the
Settlement (Sales Invoice NC, Payment Entry, Journal Entry, etc.).

Strategies are pure document-generation: GL Entry posting belongs to F4 in
:mod:`off_invoice_rebates.accounting`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, ClassVar, Protocol


@dataclass
class SettlementResult:
	"""Returned from each strategy after document generation."""

	settlement_mode: str
	primary_doc_doctype: str
	primary_doc_name: str
	extra_docs: list[tuple[str, str]] = field(default_factory=list)
	notes: str = ""


class RebateSettlementStrategy(Protocol):
	code: ClassVar[str]

	def settle(self, settlement_doc) -> SettlementResult:
		"""Generate downstream document(s) and link them back into settlement_doc
		fields.

		MUST be idempotent at the Settlement level: if the Settlement is already
		linked to a downstream document, the strategy must refuse to re-create
		(raise instead of double-posting).
		"""
		...


_REGISTRY: dict[str, type] = {}


def register(code: str) -> Callable[[type], type]:
	"""Decorator that registers a strategy class under ``code``."""

	def deco(cls: type) -> type:
		cls.code = code  # type: ignore[attr-defined]
		_REGISTRY[code] = cls
		return cls

	return deco


def get_strategy(code: str) -> RebateSettlementStrategy:
	"""Resolve and instantiate the strategy for ``code``.

	Raises a Frappe error in Italian if the code is unknown.
	"""
	if code not in _REGISTRY:
		import frappe
		from frappe import _

		frappe.throw(_("Strategy di liquidazione sconosciuta: {0}").format(code))
	return _REGISTRY[code]()


def registered_codes() -> list[str]:
	"""Debug helper — returns the list of registered strategy codes."""
	return sorted(_REGISTRY.keys())
