# Copyright (c) 2026, Lucsartech Srl and contributors
# For license information, please see license.txt

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, ClassVar, Protocol


@dataclass
class RebateOutcome:
	amount: Decimal
	currency: str
	breakdown: dict = field(default_factory=dict)


@dataclass
class PeriodBounds:
	period_key: str
	cadence: str
	start: str
	end: str


class RebateCalculator(Protocol):
	code: ClassVar[str]

	def compute(
		self,
		*,
		agreement: dict,
		condition: dict,
		period: PeriodBounds,
		scope_sql: str,
		scope_params: dict,
	) -> RebateOutcome: ...


_REGISTRY: dict[str, type] = {}


def register(code: str) -> Callable[[type], type]:
	def deco(cls: type) -> type:
		cls.code = code
		_REGISTRY[code] = cls
		return cls

	return deco


def get_calculator(code: str):
	if code not in _REGISTRY:
		from off_invoice_rebates.rebate_engine.exceptions import UnknownCalculator

		raise UnknownCalculator(
			f"Nessun calcolatore registrato per il codice: {code}"
		)
	return _REGISTRY[code]()


def all_codes() -> list[str]:
	return list(_REGISTRY.keys())
